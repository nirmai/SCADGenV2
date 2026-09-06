"""Top-level orchestrator for the agentic assembly pipeline."""

from __future__ import annotations

import sys
from pathlib import Path

from scadgen.agentic.connection_planner import ConnectionPlanner
from scadgen.agentic.decomposer import AssemblyDecomposer
from scadgen.agentic.executor import AssemblyExecutor
from scadgen.agentic.inventory import TemplateInventory
from scadgen.agentic.template_generator import TemplateGenerator
from scadgen.agentic.types import AssemblyResult
from scadgen.core.engine import SCADEngine
from scadgen.nlp.providers import create_provider


def run_pipeline(
    description: str,
    engine: SCADEngine,
    output_path: str = "",
    output_dir: str = "output",
    max_retries: int = 3,
    dry_run: bool = False,
    verbose: bool = False,
) -> AssemblyResult:
    """Run the full agentic assembly pipeline."""
    provider = create_provider(engine.config)
    registry = engine.registry

    _log(verbose, f"[1/5] Decomposing: \"{description}\"")
    decomposer = AssemblyDecomposer(provider, registry)
    plan = decomposer.decompose(description)
    _log(verbose, f"  -> {len(plan.parts)} parts, {len(plan.connections)} connections")
    for p in plan.parts:
        _log(verbose, f"    - {p.part_id} ({p.suggested_template}): {p.description}")

    _log(verbose, "[2/5] Checking template inventory")
    inventory = TemplateInventory(registry)
    plan = inventory.check(plan)
    _log(verbose, f"  -> Found: {plan.templates_found}")
    if plan.templates_needed:
        _log(verbose, f"  -> Need to generate: {plan.templates_needed}")
    else:
        _log(verbose, "  -> All templates available")

    if dry_run:
        _log(True, "\n[dry-run] Assembly plan:")
        _log(True, f"  Name: {plan.name}")
        _log(True, f"  Root: {plan.root_part}")
        _log(True, f"  Parts: {[p.part_id for p in plan.parts]}")
        _log(True, f"  Templates found: {plan.templates_found}")
        _log(True, f"  Templates needed: {plan.templates_needed}")
        for c in plan.connections:
            _log(
                True,
                f"  Connection: {c.from_part}.{c.from_connector} -> "
                f"{c.to_part}.{c.to_connector} ({c.type})",
            )
        return AssemblyResult(
            scad_code="",
            output_path="",
            plan=plan,
            warnings=[],
            success=True,
        )

    generated_paths: list[str] = []
    warnings: list[str] = []
    if plan.templates_needed:
        _log(verbose, "[3/5] Generating missing templates")
        template_dir = registry.template_dir()
        if template_dir is None:
            template_dir = Path(output_dir) / "generated_templates"
        generator = TemplateGenerator(
            provider, registry, template_dir, max_retries=max_retries,
        )
        generated_paths = generator.generate_missing(plan)
        for p in generated_paths:
            _log(verbose, f"  -> Created: {p}")
        for tid, err in generator.failures:
            _log(verbose, f"  !! Failed to generate {tid}: {err}")
            warnings.append(f"Template generation failed for {tid}: {err}")
            failed_part_id = _part_id_for_template(plan, tid)
            plan.parts = [p for p in plan.parts if p.suggested_template != tid]
            plan.connections = [
                c for c in plan.connections
                if c.from_part != failed_part_id and c.to_part != failed_part_id
            ]
    else:
        _log(verbose, "[3/5] No template generation needed")

    if not plan.parts:
        return AssemblyResult(
            scad_code="",
            output_path="",
            plan=plan,
            warnings=warnings + ["No parts survived template generation"],
            success=False,
        )

    _log(verbose, "[4/5] Refining connections")
    planner = ConnectionPlanner(provider, registry)
    plan = planner.refine(plan)
    for w in planner.warnings:
        _log(verbose, f"  ~ {w}")
    warnings.extend(planner.warnings)
    _log(verbose, f"  -> {len(plan.connections)} connections resolved")

    _log(verbose, "[5/5] Executing assembly")
    executor = AssemblyExecutor(engine)
    result = executor.execute(plan, output_path=output_path, output_dir=output_dir)
    result.generated_templates = generated_paths
    result.warnings.extend(warnings)
    _log(verbose, f"  -> Output: {result.output_path}")
    _log(verbose, f"  -> {len(result.scad_code)} bytes")

    return result


def _part_id_for_template(plan, template_id: str) -> str:
    """Find the part_id that uses a given template."""
    for p in plan.parts:
        if p.suggested_template == template_id:
            return p.part_id
    return ""


def _log(verbose: bool, msg: str) -> None:
    if verbose:
        print(msg, file=sys.stderr)
