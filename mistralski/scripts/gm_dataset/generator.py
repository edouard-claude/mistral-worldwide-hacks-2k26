"""vLLM batch inference for GM dataset generation.

Calls Qwen 3.5 on 51.159.151.86:8000 to generate GM outputs
for each scenario. Batches of 10 concurrent requests.

Qwen 3.5 specifics:
- Produces <think>...</think> blocks automatically → stripped before JSON parse
- Orphan </think> tags possible (vLLM strips opening tag) → handled
- /no_think NOT supported → use prompt instructions for JSON-only output
"""

import asyncio
import json
import re

import httpx
import structlog

from scripts.gm_dataset.constants import (
    BATCH_SIZE,
    GENERATION_MAX_TOKENS,
    GENERATION_TEMPERATURE,
    VLLM_API_KEY,
    VLLM_BASE_URL,
    VLLM_MODEL,
)
from scripts.gm_dataset.prompts import META_TEACHER_PROMPT, get_system_prompt
from scripts.gm_dataset.scenarios import scenario_to_user_message

logger = structlog.get_logger(__name__)


def _strip_thinking(content: str) -> str:
    """Strip Qwen 3.5 <think>...</think> blocks and orphan </think> tags.

    Args:
        content: Raw LLM response that may contain thinking tags.

    Returns:
        Content with all thinking blocks removed.
    """
    # Full <think>...</think> blocks (greedy — handles nested edge cases)
    content = re.sub(r"<think>[\s\S]*?</think>", "", content)
    # Orphan </think> at start (vLLM may strip <think> but leave </think>)
    content = re.sub(r"^\s*</think>\s*", "", content)
    return content.strip()


async def _call_vllm(
    client: httpx.AsyncClient,
    system_prompt: str,
    user_message: str,
    scenario_id: int,
) -> dict | None:
    """Call vLLM (Qwen 3.5) for a single scenario.

    Args:
        client: Async HTTP client.
        system_prompt: System prompt for the GM type.
        user_message: JSON-stringified game state.
        scenario_id: For logging.

    Returns:
        Parsed JSON dict or None on failure.
    """
    payload = {
        "model": VLLM_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt + "\n\n" + META_TEACHER_PROMPT},
            {"role": "user", "content": user_message},
        ],
        "temperature": GENERATION_TEMPERATURE,
        "max_tokens": GENERATION_MAX_TOKENS,
        "response_format": {"type": "json_object"},
    }

    try:
        resp = await client.post(
            f"{VLLM_BASE_URL}/v1/chat/completions",
            json=payload,
            timeout=120.0,
        )
        resp.raise_for_status()
        data = resp.json()
        content = data["choices"][0]["message"]["content"]

        # Strip Qwen 3.5 thinking blocks
        content = _strip_thinking(content)

        # Try to extract JSON if wrapped in markdown code blocks
        if content.startswith("```"):
            match = re.search(r"```(?:json)?\s*([\s\S]*?)```", content)
            if match:
                content = match.group(1).strip()

        parsed = json.loads(content)
        logger.debug("vllm_success", scenario_id=scenario_id)
        return parsed

    except json.JSONDecodeError as e:
        logger.warning(
            "vllm_json_error",
            scenario_id=scenario_id,
            error=str(e),
            content_preview=content[:200] if content else "empty",
        )
        return None
    except httpx.HTTPStatusError as e:
        logger.warning(
            "vllm_http_error",
            scenario_id=scenario_id,
            status=e.response.status_code,
            body=e.response.text[:200],
        )
        return None
    except Exception as e:
        logger.warning("vllm_error", scenario_id=scenario_id, error=str(e))
        return None


async def generate_batch(
    scenarios: list[dict],
    batch_size: int = BATCH_SIZE,
) -> list[tuple[dict, dict | None]]:
    """Generate GM outputs for a batch of scenarios.

    Args:
        scenarios: List of scenario dicts.
        batch_size: Concurrent requests per batch.

    Returns:
        List of (scenario, output) tuples. Output is None on failure.
    """
    results: list[tuple[dict, dict | None]] = []
    headers = {"Authorization": f"Bearer {VLLM_API_KEY}"}

    async with httpx.AsyncClient(headers=headers) as client:
        for i in range(0, len(scenarios), batch_size):
            batch = scenarios[i:i + batch_size]
            logger.info(
                "generating_batch",
                batch_start=i,
                batch_size=len(batch),
                total=len(scenarios),
            )

            tasks = []
            for scenario in batch:
                gm_type = scenario["type"]
                system_prompt = get_system_prompt(gm_type)
                user_msg = scenario_to_user_message(scenario)
                tasks.append(
                    _call_vllm(client, system_prompt, user_msg, scenario["scenario_id"])
                )

            outputs = await asyncio.gather(*tasks)

            for scenario, output in zip(batch, outputs):
                results.append((scenario, output))

            # Brief pause between batches to avoid overwhelming vLLM
            if i + batch_size < len(scenarios):
                await asyncio.sleep(2.0)

    success_count = sum(1 for _, o in results if o is not None)
    logger.info(
        "generation_complete",
        total=len(scenarios),
        success=success_count,
        failed=len(scenarios) - success_count,
    )
    return results


async def retry_failed(
    failed_scenarios: list[dict],
    max_retries: int = 2,
) -> list[tuple[dict, dict | None]]:
    """Retry generation for failed scenarios.

    Args:
        failed_scenarios: Scenarios that failed on first attempt.
        max_retries: Max retry attempts.

    Returns:
        List of (scenario, output) tuples after retries.
    """
    remaining = failed_scenarios.copy()
    all_results: list[tuple[dict, dict | None]] = []

    for attempt in range(max_retries):
        if not remaining:
            break

        logger.info(
            "retry_attempt",
            attempt=attempt + 1,
            count=len(remaining),
        )

        results = await generate_batch(remaining, batch_size=BATCH_SIZE)

        still_failed: list[dict] = []
        for scenario, output in results:
            if output is not None:
                all_results.append((scenario, output))
            else:
                still_failed.append(scenario)

        remaining = still_failed

    # Append remaining failures as None
    for scenario in remaining:
        all_results.append((scenario, None))

    return all_results
