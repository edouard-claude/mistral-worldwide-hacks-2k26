#!/usr/bin/env python3
"""Generate the Game Master fine-tuning dataset.

Entry point: python scripts/generate_gm_dataset.py

Pipeline:
1. Generate 240 deterministic scenarios (200 train + 40 val)
2. Call vLLM batch to generate GM outputs
3. Validate with Pydantic schemas + retry failures
4. Deduplicate headlines
5. Write JSONL files for Mistral fine-tuning

Output:
- data/finetune/gm_train.jsonl (200 lines)
- data/finetune/gm_val.jsonl (40 lines)
"""

import asyncio
import sys
from pathlib import Path

import structlog

# Add project root to path for imports
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from scripts.gm_dataset.generator import generate_batch, retry_failed
from scripts.gm_dataset.prompts import get_system_prompt
from scripts.gm_dataset.scenarios import generate_all_scenarios
from scripts.gm_dataset.validator import (
    ValidationResult,
    check_duplicates,
    format_jsonl_entry,
    print_validation_report,
    validate_batch,
)

logger = structlog.get_logger(__name__)

OUTPUT_DIR = PROJECT_ROOT / "data" / "finetune"
TRAIN_FILE = OUTPUT_DIR / "gm_train.jsonl"
VAL_FILE = OUTPUT_DIR / "gm_val.jsonl"


def write_jsonl(
    results: list[ValidationResult],
    output_path: Path,
) -> int:
    """Write validated results to JSONL file.

    Args:
        results: Validated and deduplicated results.
        output_path: Path to output JSONL file.

    Returns:
        Number of lines written.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)

    lines_written = 0
    with open(output_path, "w", encoding="utf-8") as f:
        for result in results:
            gm_type = result.scenario["type"]
            system_prompt = get_system_prompt(gm_type)
            line = format_jsonl_entry(result, system_prompt)
            f.write(line + "\n")
            lines_written += 1

    logger.info("jsonl_written", path=str(output_path), lines=lines_written)
    return lines_written


async def run_pipeline() -> None:
    """Run the full dataset generation pipeline."""
    print("=" * 60)
    print("GORAFI SIMULATOR — Game Master Dataset Generator")
    print("=" * 60)

    # Step 1: Generate scenarios
    print("\n[1/5] Generating 240 scenarios (seed=42)...")
    train_scenarios, val_scenarios = generate_all_scenarios(seed=42)
    print(f"  Train: {len(train_scenarios)} scenarios")
    print(f"  Val:   {len(val_scenarios)} scenarios")

    # Count by type
    for split_name, scenarios in [("Train", train_scenarios), ("Val", val_scenarios)]:
        by_type: dict[str, int] = {}
        for s in scenarios:
            by_type[s["type"]] = by_type.get(s["type"], 0) + 1
        print(f"  {split_name} distribution: {dict(sorted(by_type.items()))}")

    # Step 2: Generate outputs via vLLM
    print("\n[2/5] Generating train outputs via vLLM...")
    train_results = await generate_batch(train_scenarios)

    print("\n[3/5] Generating val outputs via vLLM...")
    val_results = await generate_batch(val_scenarios)

    # Step 3: Validate
    print("\n[4/5] Validating outputs...")
    train_valid, train_invalid = validate_batch(train_results)
    val_valid, val_invalid = validate_batch(val_results)

    # Retry failed
    if train_invalid:
        print(f"  Retrying {len(train_invalid)} failed train scenarios...")
        failed_scenarios = [r.scenario for r in train_invalid]
        retry_results = await retry_failed(failed_scenarios)
        retry_valid, retry_still_invalid = validate_batch(retry_results)
        train_valid.extend(retry_valid)
        train_invalid = retry_still_invalid

    if val_invalid:
        print(f"  Retrying {len(val_invalid)} failed val scenarios...")
        failed_scenarios = [r.scenario for r in val_invalid]
        retry_results = await retry_failed(failed_scenarios)
        retry_valid, retry_still_invalid = validate_batch(retry_results)
        val_valid.extend(retry_valid)
        val_invalid = retry_still_invalid

    # Deduplicate
    train_valid = check_duplicates(train_valid)
    val_valid = check_duplicates(val_valid)

    # Report
    print("\n--- TRAIN ---")
    print_validation_report(train_valid, train_invalid)
    print("--- VAL ---")
    print_validation_report(val_valid, val_invalid)

    # Step 4: Write JSONL
    print("[5/5] Writing JSONL files...")
    train_count = write_jsonl(train_valid, TRAIN_FILE)
    val_count = write_jsonl(val_valid, VAL_FILE)

    # Summary
    print(f"\n{'='*60}")
    print(f"DONE!")
    print(f"  {TRAIN_FILE}: {train_count} lines")
    print(f"  {VAL_FILE}: {val_count} lines")
    print(f"{'='*60}")

    if train_count < 200 or val_count < 40:
        print(
            f"\nWARNING: Expected 200 train + 40 val, got {train_count} + {val_count}."
            f"\nSome scenarios failed generation/validation. Re-run or check vLLM."
        )


def main() -> None:
    """CLI entry point."""
    asyncio.run(run_pipeline())


if __name__ == "__main__":
    main()
