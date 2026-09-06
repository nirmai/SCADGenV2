"""Step 5: Execute an AssemblyPlan through the AssemblyBuilder.

Escalation ladder (each rung is more conservative than the last):
  1. LLM connections + clamped params, requiring sane geometry
  2. Deterministic vertical auto-stack + clamped params
  3. Auto-stack + template defaults
  4. Auto-stack + defaults + drop orphaned parts

The first rung that produces a valid, non-degenerate assembly wins, so a
good LLM plan is used as-is and a broken one falls back to a clean stack.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from scadgen.agentic.types import AssemblyPlan, AssemblyResult, ConnectionSpec
from scadgen.assembly.builder import AssemblyBuilder
from scadgen.core.engine import SCADEngine
from scadgen.core.template_registry import TemplateRegistry
from scadgen.exceptions import AssemblyExecutionError

# Connector-name preferences when auto-stacking, best first.
_TOP_PREFS = ["top_face", "top", "stem_mount", "shade_mount", "deck_face", "center_axis"]
_BOTTOM_PREFS = ["bottom_face", "bottom", "base_end", "socket", "center_axis"]

_BAD_COLORS = {"none", "not_applicable", "n/a", "", "default", "null"}


class _NeedsFallback(Exception):
    """Raised internally when an assembly builds but the geometry is unusable."""


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
            warnings.append(f"{template_id}.{key}: clamped {val} up to min {pdef.min}")
            clamped[key] = type(val)(pdef.min)
        if pdef.max is not None and val > pdef.max:
            warnings.append(f"{template_id}.{key}: clamped {val} down to max {pdef.max}")
            clamped[key] = type(val)(pdef.max)

    return clamped, warnings


def _clean_colors(colors: dict[str, str]) -> dict[str, str]:
    """Drop obviously-invalid color values (e.g. 'not_applicable')."""
    clean = {}
    for k, v in colors.items():
        if not isinstance(v, str):
            continue
        s = v.strip()
        if s.lower() in _BAD_COLORS or "_" in s or " " in s:
            continue
        clean[k] = s
    return clean


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
        warnings: list[str] = []

        if not output_path:
            out_dir = Path(output_dir)
            out_dir.mkdir(parents=True, exist_ok=True)
            output_path = str(out_dir / f"{plan.name}_assembly.scad")

        for part in plan.parts:
            params, cw = _clamp_params(
                part.suggested_template, part.suggested_params, self._engine.registry,
            )
            warnings.extend(cw)
            part.suggested_params = params

        # Rung 1: trust the LLM's connections, but require sane geometry.
        try:
            scad, builder = self._try_build(plan, output_path, require_good=True)
            return self._result(scad, builder, plan, output_path, warnings)
        except _NeedsFallback as e:
            warnings.append(f"LLM geometry unusable ({e}); using deterministic stack")
        except Exception as e:
            warnings.append(f"LLM assembly failed ({e}); using deterministic stack")

        # Rung 2: deterministic vertical stack with the given params.
        plan = self._auto_stack_plan(plan)
        try:
            scad, builder = self._try_build(plan, output_path, require_good=False)
            return self._result(scad, builder, plan, output_path, warnings)
        except Exception as e:
            warnings.append(f"Stack with given params failed ({e}); retrying with defaults")

        # Rung 3: auto-stack with template defaults.
        for part in plan.parts:
            part.suggested_params = {}
        try:
            scad, builder = self._try_build(plan, output_path, require_good=False)
            return self._result(scad, builder, plan, output_path, warnings)
        except Exception as e:
            warnings.append(f"Stack with defaults failed ({e}); dropping orphans")

        # Rung 4: drop orphaned parts and try once more.
        dropped = self._drop_orphans(plan)
        if dropped:
            warnings.append(f"Dropped parts to recover: {', '.join(dropped)}")
        try:
            scad, builder = self._try_build(plan, output_path, require_good=False)
            return self._result(scad, builder, plan, output_path, warnings)
        except Exception as e:
            raise AssemblyExecutionError(f"Assembly execution failed: {e}") from e

    def _result(
        self,
        scad: str,
        builder: AssemblyBuilder,
        plan: AssemblyPlan,
        output_path: str,
        warnings: list[str],
    ) -> AssemblyResult:
        return AssemblyResult(
            scad_code=scad,
            output_path=output_path,
            plan=plan,
            warnings=warnings + builder.warnings,
            success=True,
        )

    def _try_build(
        self, plan: AssemblyPlan, output_path: str, require_good: bool,
    ) -> tuple[str, AssemblyBuilder]:
        builder = AssemblyBuilder(self._engine)
        for part in plan.parts:
            builder.add_part(
                part_id=part.part_id,
                template_id=part.suggested_template,
                params=part.suggested_params,
            )
        builder.set_root(plan.root_part)
        for color_part, color_name in _clean_colors(plan.colors).items():
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

        assembly = builder.build()
        if require_good and self._positions_broken(assembly, plan.root_part):
            raise _NeedsFallback("parts overlap or sit below the base")

        scad = builder.render(output_path)
        return scad, builder

    def _positions_broken(self, assembly, root_id: str) -> bool:
        """Detect degenerate geometry: parts stacked on the same point, or
        parts sitting well below the root."""
        parts = list(assembly.parts.values())
        if len(parts) < 2:
            return False

        positions = [p.transform.translation for p in parts]

        # Exact overlap: two parts at essentially the same point.
        for i in range(len(positions)):
            for j in range(i + 1, len(positions)):
                dist = sum((a - b) ** 2 for a, b in zip(positions[i], positions[j])) ** 0.5
                if dist < 0.5:
                    return True

        # Below-root: any part sitting more than 1mm below the root.
        root = assembly.parts.get(root_id)
        if root is not None:
            root_z = root.transform.translation[2]
            for p in parts:
                if p.transform.translation[2] < root_z - 1.0:
                    return True

        return False

    def _auto_stack_plan(self, plan: AssemblyPlan) -> AssemblyPlan:
        """Replace connections with a clean vertical stack: root on the
        ground, each subsequent part's bottom mated to the previous top."""
        ordered = [p for p in plan.parts if p.part_id == plan.root_part]
        ordered += [p for p in plan.parts if p.part_id != plan.root_part]

        conns: list[ConnectionSpec] = []
        for lower, upper in zip(ordered, ordered[1:]):
            top = self._pick_connector(lower.suggested_template, _TOP_PREFS)
            bottom = self._pick_connector(upper.suggested_template, _BOTTOM_PREFS)
            if top and bottom:
                conns.append(ConnectionSpec(
                    from_part=lower.part_id, from_connector=top,
                    to_part=upper.part_id, to_connector=bottom, type="mate",
                ))
        plan.connections = conns
        if ordered:
            plan.root_part = ordered[0].part_id
        return plan

    def _pick_connector(self, template_id: str, prefs: list[str]) -> str | None:
        try:
            tmpl = self._engine.registry.get(template_id)
        except Exception:
            return None
        names = {c.name for c in tmpl.connectors}
        for pref in prefs:
            if pref in names:
                return pref
        return next(iter(names)) if names else None

    def _drop_orphans(self, plan: AssemblyPlan) -> list[str]:
        """Remove parts not reachable from the root via connections."""
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
