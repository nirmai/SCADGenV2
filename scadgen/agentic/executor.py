"""Step 5: Execute an AssemblyPlan through the AssemblyBuilder."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from scadgen.agentic.types import AssemblyPlan, AssemblyResult
from scadgen.assembly.builder import AssemblyBuilder
from scadgen.core.engine import SCADEngine
from scadgen.core.template_registry import TemplateRegistry
from scadgen.exceptions import AssemblyExecutionError


def _clamp_params(
    template_id: str,
    params: dict[str, Any],
    registry: TemplateRegistry,
) -> tuple[dict[str, Any], list[str]]:
    """Clamp LLM-suggested params to template min/max ranges."""
    try:
        tmpl = registry.get(template_id)
    except Exception:
        return params, []

    clamped = dict(params)
    warnings: list[str] = []
    param_defs = {p.name: p for p in tmpl.parameters}

    for key, val in list(clamped.items()):
        if key not in param_defs:
            continue
        pdef = param_defs[key]
        if not isinstance(val, (int, float)):
            continue
        if pdef.min is not None and val < pdef.min:
            warnings.append(
                f"{template_id}.{key}: clamped {val} up to min {pdef.min}"
            )
            clamped[key] = type(val)(pdef.min)
        if pdef.max is not None and val > pdef.max:
            warnings.append(
                f"{template_id}.{key}: clamped {val} down to max {pdef.max}"
            )
            clamped[key] = type(val)(pdef.max)

    return clamped, warnings


class AssemblyExecutor:
    def __init__(self, engine: SCADEngine):
        self._engine = engine

    def execute(
        self,
        plan: AssemblyPlan,
        output_path: str = "",
        output_dir: str = "output",
    ) -> AssemblyResult:
        """Run the plan through AssemblyBuilder and render to .scad."""
        clamp_warnings: list[str] = []

        if not output_path:
            out_dir = Path(output_dir)
            out_dir.mkdir(parents=True, exist_ok=True)
            output_path = str(out_dir / f"{plan.name}_assembly.scad")

        # First attempt: use LLM-suggested params (clamped to ranges)
        for part in plan.parts:
            params, cw = _clamp_params(
                part.suggested_template,
                part.suggested_params,
                self._engine.registry,
            )
            clamp_warnings.extend(cw)
            part.suggested_params = params

        try:
            scad, builder = self._build_and_render(plan, output_path)
        except Exception as first_err:
            # Retry with template defaults if LLM params caused constraint violations
            clamp_warnings.append(
                f"LLM params failed ({first_err}), retrying with template defaults"
            )
            for part in plan.parts:
                part.suggested_params = {}
            try:
                scad, builder = self._build_and_render(plan, output_path)
            except Exception as second_err:
                # Last resort: drop orphaned parts (disconnected from root) so
                # the rest of the assembly still renders instead of crashing.
                dropped = self._drop_orphans(plan)
                if not dropped:
                    raise AssemblyExecutionError(
                        f"Assembly execution failed: {second_err}"
                    ) from second_err
                clamp_warnings.append(
                    f"Dropped orphaned parts to recover: {', '.join(dropped)}"
                )
                try:
                    scad, builder = self._build_and_render(plan, output_path)
                except Exception as e:
                    raise AssemblyExecutionError(
                        f"Assembly execution failed: {e}"
                    ) from e

        return AssemblyResult(
            scad_code=scad,
            output_path=output_path,
            plan=plan,
            warnings=clamp_warnings + builder.warnings,
            success=True,
        )

    def _drop_orphans(self, plan: AssemblyPlan) -> list[str]:
        """Remove parts not reachable from the root via connections.

        Returns the part_ids that were dropped.
        """
        if not plan.parts:
            return []

        root = plan.root_part or plan.parts[0].part_id
        adj: dict[str, set[str]] = {p.part_id: set() for p in plan.parts}
        for conn in plan.connections:
            if conn.from_part in adj and conn.to_part in adj:
                adj[conn.from_part].add(conn.to_part)
                adj[conn.to_part].add(conn.from_part)

        reachable = {root}
        stack = [root]
        while stack:
            cur = stack.pop()
            for nb in adj.get(cur, ()):
                if nb not in reachable:
                    reachable.add(nb)
                    stack.append(nb)

        orphans = [p.part_id for p in plan.parts if p.part_id not in reachable]
        if not orphans:
            return []

        plan.parts = [p for p in plan.parts if p.part_id in reachable]
        plan.connections = [
            c for c in plan.connections
            if c.from_part in reachable and c.to_part in reachable
        ]
        return orphans

    def _build_and_render(
        self, plan: AssemblyPlan, output_path: str
    ) -> tuple[str, AssemblyBuilder]:
        builder = AssemblyBuilder(self._engine)

        for part in plan.parts:
            builder.add_part(
                part_id=part.part_id,
                template_id=part.suggested_template,
                params=part.suggested_params,
            )

        builder.set_root(plan.root_part)

        for color_part, color_name in plan.colors.items():
            builder.set_color(color_part, color_name)

        for conn in plan.connections:
            builder.connect(
                part_a=conn.from_part,
                connector_a=conn.from_connector,
                part_b=conn.to_part,
                connector_b=conn.to_connector,
                type=conn.type,
                offset=conn.offset,
            )

        scad = builder.render(output_path)
        return scad, builder
