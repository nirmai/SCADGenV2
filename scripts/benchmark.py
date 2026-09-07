"""Small, manual generation-fidelity benchmark. Not part of the test suite —
it makes real, paid Claude API calls and takes a few minutes to run.

Runs a fixed set of prompts through the agentic pipeline, pinned to
Anthropic, and reports:
  - whether each assembly succeeded
  - how many parts it has
  - for any brand-new templates the LLM had to write: how many attempts it
    took to pass validation + the OpenSCAD render-check (1 = first try)

Usage:
    python scripts/benchmark.py
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scadgen.agentic import assemble
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


def run() -> None:
    engine = SCADEngine(provider="anthropic")
    results = []

    for i, prompt in enumerate(PROMPTS, 1):
        print(f"\n[{i}/{len(PROMPTS)}] {prompt}")
        start = time.time()
        try:
            result = assemble(
                description=prompt,
                engine=engine,
                output_dir=OUTPUT_DIR,
                output_path=f"{OUTPUT_DIR}/bench_{i}.scad",
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

    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)

    ok = sum(1 for _, r, err, _ in results if r is not None and r.success)
    print(f"Assemblies succeeded: {ok}/{len(PROMPTS)}")

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


if __name__ == "__main__":
    run()
