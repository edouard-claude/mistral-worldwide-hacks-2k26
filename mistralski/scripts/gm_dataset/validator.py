"""Validation of generated GM outputs.

Validates JSON structure against Pydantic schemas, checks for
duplicates, and provides detailed error reporting.
"""

import json

import structlog
from pydantic import ValidationError

from scripts.gm_dataset.schemas import GM_OUTPUT_MODELS, HeadlineOutput

logger = structlog.get_logger(__name__)


class ValidationResult:
    """Result of validating a single scenario output."""

    def __init__(
        self,
        scenario: dict,
        output: dict | None,
        is_valid: bool = False,
        errors: list[str] | None = None,
        validated_output: dict | None = None,
    ) -> None:
        self.scenario = scenario
        self.output = output
        self.is_valid = is_valid
        self.errors = errors or []
        self.validated_output = validated_output


def validate_output(
    scenario: dict,
    output: dict | None,
) -> ValidationResult:
    """Validate a single GM output against its Pydantic schema.

    Args:
        scenario: The input scenario dict.
        output: The generated output dict (or None if generation failed).

    Returns:
        ValidationResult with is_valid flag and errors if any.
    """
    if output is None:
        return ValidationResult(
            scenario=scenario,
            output=None,
            is_valid=False,
            errors=["Generation returned None"],
        )

    gm_type = scenario["type"]
    model_class = GM_OUTPUT_MODELS.get(gm_type)

    if model_class is None:
        return ValidationResult(
            scenario=scenario,
            output=output,
            is_valid=False,
            errors=[f"Unknown GM type: {gm_type}"],
        )

    # Ensure the type field is set
    if "type" not in output:
        output["type"] = gm_type

    try:
        validated = model_class.model_validate(output)
        return ValidationResult(
            scenario=scenario,
            output=output,
            is_valid=True,
            validated_output=validated.model_dump(),
        )
    except ValidationError as e:
        errors = [f"{err['loc']}: {err['msg']}" for err in e.errors()]
        logger.debug(
            "validation_failed",
            scenario_id=scenario.get("scenario_id"),
            gm_type=gm_type,
            error_count=len(errors),
        )
        return ValidationResult(
            scenario=scenario,
            output=output,
            is_valid=False,
            errors=errors,
        )


def validate_batch(
    results: list[tuple[dict, dict | None]],
) -> tuple[list[ValidationResult], list[ValidationResult]]:
    """Validate a batch of scenario/output pairs.

    Args:
        results: List of (scenario, output) tuples.

    Returns:
        (valid_results, invalid_results) tuple.
    """
    valid: list[ValidationResult] = []
    invalid: list[ValidationResult] = []

    for scenario, output in results:
        result = validate_output(scenario, output)
        if result.is_valid:
            valid.append(result)
        else:
            invalid.append(result)

    logger.info(
        "batch_validation",
        total=len(results),
        valid=len(valid),
        invalid=len(invalid),
    )
    return valid, invalid


def check_duplicates(valid_results: list[ValidationResult]) -> list[ValidationResult]:
    """Remove results with duplicate headline texts.

    Args:
        valid_results: List of validated results.

    Returns:
        Deduplicated list.
    """
    seen_headlines: set[str] = set()
    deduplicated: list[ValidationResult] = []

    for result in valid_results:
        output = result.validated_output
        if output is None:
            continue

        # Extract all headline texts from the output
        headlines: list[str] = []
        if "headline" in output:
            headlines.append(output["headline"]["text"])
        if "headlines" in output:
            headlines.extend(h["text"] for h in output["headlines"])

        # Check for duplicates
        is_dup = False
        for text in headlines:
            if text in seen_headlines:
                is_dup = True
                break
            seen_headlines.add(text)

        if not is_dup:
            deduplicated.append(result)
        else:
            logger.debug(
                "duplicate_removed",
                scenario_id=result.scenario.get("scenario_id"),
            )

    if len(deduplicated) < len(valid_results):
        logger.info(
            "duplicates_removed",
            original=len(valid_results),
            deduplicated=len(deduplicated),
        )

    return deduplicated


def format_jsonl_entry(
    result: ValidationResult,
    system_prompt: str,
) -> str:
    """Format a validated result as a Mistral fine-tuning JSONL entry.

    Args:
        result: Validated result with scenario and output.
        system_prompt: System prompt for the GM type.

    Returns:
        Single JSONL line.
    """
    user_content = json.dumps(
        {
            "type": result.scenario["type"],
            "game_state": result.scenario["game_state"],
            "real_news_sample": result.scenario["real_news_sample"],
        },
        ensure_ascii=False,
    )

    assistant_content = json.dumps(
        result.validated_output,
        ensure_ascii=False,
    )

    entry = {
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
            {"role": "assistant", "content": assistant_content},
        ],
    }
    return json.dumps(entry, ensure_ascii=False)


def print_validation_report(
    valid: list[ValidationResult],
    invalid: list[ValidationResult],
) -> None:
    """Print a summary of validation results."""
    total = len(valid) + len(invalid)
    print(f"\n{'='*60}")
    print(f"VALIDATION REPORT")
    print(f"{'='*60}")
    print(f"Total:   {total}")
    print(f"Valid:   {len(valid)} ({len(valid)/total*100:.1f}%)" if total > 0 else "Valid: 0")
    print(f"Invalid: {len(invalid)} ({len(invalid)/total*100:.1f}%)" if total > 0 else "Invalid: 0")

    if invalid:
        # Group by GM type
        by_type: dict[str, int] = {}
        for r in invalid:
            gm_type = r.scenario.get("type", "unknown")
            by_type[gm_type] = by_type.get(gm_type, 0) + 1

        print(f"\nFailures by type:")
        for gm_type, count in sorted(by_type.items()):
            print(f"  {gm_type}: {count}")

        print(f"\nFirst 5 errors:")
        for r in invalid[:5]:
            sid = r.scenario.get("scenario_id", "?")
            print(f"  Scenario {sid} ({r.scenario.get('type')}):")
            for err in r.errors[:3]:
                print(f"    - {err}")

    print(f"{'='*60}\n")
