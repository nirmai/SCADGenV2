"""Small, manual generation-fidelity benchmark. Not part of the test suite —
it makes real, paid Claude API calls and takes a few minutes per run.

Runs a fixed set of prompts through the agentic pipeline, pinned to
Anthropic, and reports per prompt:
  - whether the assembly succeeded
  - how many parts it has
  - for any brand-new templates the LLM had to write: how many attempts it
    took to pass validation + the OpenSCAD render-check (1 = first try)

Each run starts from a CLEARED generated-templates cache, so every run
measures fresh generation rather than reusing a previous run's templates
(persistence — see `scadgen clear-generated` — is a real feature, but it
would hide the fidelity signal this benchmark exists to measure). Run
multiple times with --runs to see whether a result was representative or
one lucky/unlucky draw — there's real run-to-run variance in both part
counts and which templates need repair.

Usage:
    python scripts/benchmark.py            # one run
    python scripts/benchmark.py --runs 3   # three runs + an aggregate summary
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scadgen.agentic import assemble
from scadgen.config import Config
from scadgen.core.engine import SCADEngine
from scadgen.exceptions import AgenticError, ProviderError

# A mix of prompts the library already covers (regression check) and
# prompts that force the LLM to write brand-new templates (fidelity check).
PROMPTS = [
    "make a desk lamp",
    "build a 4-cylinder engine top end",
    "a birdcage with a domed top and vertical bars",
    "a spoked wheel with a hub and eight radial spokes",
    "a small tripod camera stand with three folding legs",
    "a wall-mounted coat hook with three pegs",
]

OUTPUT_DIR = "output/benchmark"


def clear_generated_cache(config: Config) -> int:
    """Delete cached generated templates. Returns how many were removed.

    Mirrors `scadgen clear-generated --yes` but callable in-process, since a
    fresh SCADEngine still needs to be constructed afterward to avoid a
    stale in-memory registry (the old engine keeps generated templates
    registered even after their files are deleted).
    """
    gen_dir = Path(config.generated_templates_dir)
    if not gen_dir.is_dir():
        return 0
    files = list(gen_dir.glob("*.scad"))
    for f in files:
        f.unlink()
    return len(files)


def run_once(run_idx: int, total_runs: int) -> list[tuple]:
    """Run every prompt once against a fresh engine + cleared cache.

    Returns a list of (prompt, AssemblyResult|None, error|None, elapsed) —
    one entry per prompt.
    """
    label = f"[run {run_idx}/{total_runs}]" if total_runs > 1 else ""
    engine = SCADEngine(provider="anthropic")
    removed = clear_generated_cache(engine.config)
    if removed:
        print(f"{label} Cleared {removed} cached generated template(s)")

    results = []
    for i, prompt in enumerate(PROMPTS, 1):
        print(f"\n{label}[{i}/{len(PROMPTS)}] {prompt}")
        start = time.time()
        try:
            result = assemble(
                description=prompt,
                engine=engine,
                output_dir=OUTPUT_DIR,
                output_path=f"{OUTPUT_DIR}/bench_{run_idx}_{i}.scad",
            )
            elapsed = time.time() - start
            results.append((prompt, result, None, elapsed))
            status = "OK" if result.success else "FAILED (no parts survived)"
            print(f"  {status} — {len(result.plan.parts)} parts, "
                  f"{len(result.generated_templates)} generated, {elapsed:.1f}s")
            for tid, attempts in result.generated_attempts.items():
                print(f"    {tid}: {attempts} attempt(s) to pass")
        except (AgenticError, ProviderError) as e:
            elapsed = time.time() - start
            results.append((prompt, None, str(e), elapsed))
            print(f"  ERROR — {e}")

    print_summary(results, header="SUMMARY" if total_runs == 1 else f"RUN {run_idx} SUMMARY")
    return results


def print_summary(results: list[tuple], header: str) -> None:
    print("\n" + "=" * 60)
    print(header)
    print("=" * 60)

    ok = sum(1 for _, r, _, _ in results if r is not None and r.success)
    print(f"Assemblies succeeded: {ok}/{len(results)}")

    all_attempts = [
        n for _, r, _, _ in results if r is not None
        for n in r.generated_attempts.values()
    ]
    if all_attempts:
        first_try = sum(1 for n in all_attempts if n == 1)
        avg = sum(all_attempts) / len(all_attempts)
        print(f"Novel templates generated: {len(all_attempts)}")
        print(f"  First-attempt passes: {first_try}/{len(all_attempts)}")
        print(f"  Average attempts to pass: {avg:.2f}")
    else:
        print("No novel templates were generated this run.")

    total_time = sum(elapsed for *_, elapsed in results)
    print(f"Total wall time: {total_time:.1f}s")


def print_aggregate(all_runs: list[list[tuple]]) -> None:
    print("\n" + "#" * 60)
    print(f"AGGREGATE ACROSS {len(all_runs)} RUNS")
    print("#" * 60)

    total_prompts = sum(len(r) for r in all_runs)
    total_ok = sum(
        1 for run in all_runs for _, r, _, _ in run if r is not None and r.success
    )
    print(f"Overall success rate: {total_ok}/{total_prompts} "
          f"({100 * total_ok / total_prompts:.0f}%)")

    # Per-prompt consistency — flags anything that only sometimes succeeds.
    per_prompt: dict[str, list[bool]] = {p: [] for p in PROMPTS}
    for run in all_runs:
        for prompt, r, _, _ in run:
            per_prompt[prompt].append(r is not None and r.success)
    print("\nPer-prompt consistency:")
    for prompt, outcomes in per_prompt.items():
        successes = sum(outcomes)
        flag = "  <- inconsistent" if 0 < successes < len(outcomes) else ""
        print(f"  {successes}/{len(outcomes)}  {prompt}{flag}")

    all_attempts = [
        n for run in all_runs for _, r, _, _ in run if r is not None
        for n in r.generated_attempts.values()
    ]
    if all_attempts:
        first_try = sum(1 for n in all_attempts if n == 1)
        avg = sum(all_attempts) / len(all_attempts)
        print(f"\nNovel templates generated (all runs): {len(all_attempts)}")
        print(f"  First-attempt passes: {first_try}/{len(all_attempts)} "
              f"({100 * first_try / len(all_attempts):.0f}%)")
        print(f"  Average attempts to pass: {avg:.2f}")
    else:
        print("\nNo novel templates were generated across any run.")

    total_time = sum(elapsed for run in all_runs for *_, elapsed in run)
    print(f"\nTotal wall time (all runs): {total_time:.1f}s")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--runs", type=int, default=1,
        help="Number of full passes over the prompt set (default: 1). "
             "Each run clears the generated-templates cache first.",
    )
    args = parser.parse_args()

    all_runs = [run_once(i, args.runs) for i in range(1, args.runs + 1)]

    if args.runs > 1:
        print_aggregate(all_runs)


if __name__ == "__main__":
    main()
