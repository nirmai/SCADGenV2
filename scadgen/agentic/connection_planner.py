"""Step 4: Validate and refine connection references against actual connectors."""

from __future__ import annotations

from scadgen.agentic.prompts import build_connection_refinement_prompt
from scadgen.agentic.types import AssemblyPlan, ConnectionSpec
from scadgen.core.template_registry import TemplateRegistry
from scadgen.nlp.json_utils import parse_json_response
from scadgen.nlp.providers import LLMProvider


class ConnectionPlanner:
    def __init__(self, provider: LLMProvider, registry: TemplateRegistry):
        self._provider = provider
        self._registry = registry
        self.warnings: list[str] = []

    def refine(self, plan: AssemblyPlan) -> AssemblyPlan:
        """Validate connector references, fixing or dropping bad ones.

        Layers of repair, most robust last:
          1. Auto-snap: if a part has exactly one connector, use it.
          2. LLM refine: ask the model to remap remaining mismatches.
          3. Drop: any connection still referencing a nonexistent
             connector is removed with a warning (never crashes).
        """
        self.warnings = []
        template_map = self._build_template_map(plan)

        # Layer 1: auto-snap single-connector parts
        self._auto_snap(plan, template_map)
        mismatches = self._find_mismatches(plan, template_map)
        if not mismatches:
            return plan

        # Layer 2: LLM refinement
        self._llm_refine(plan, mismatches)

        # Layer 3: drop anything still broken rather than failing
        remaining = self._find_mismatches(plan, template_map)
        if remaining:
            kept: list[ConnectionSpec] = []
            broken_keys = {
                (m["from_part"], m["from_connector"], m["to_part"], m["to_connector"])
                for m in remaining
            }
            for conn in plan.connections:
                key = (conn.from_part, conn.from_connector, conn.to_part, conn.to_connector)
                if key in broken_keys:
                    self.warnings.append(
                        f"Dropped unresolvable connection "
                        f"{conn.from_part}.{conn.from_connector} -> "
                        f"{conn.to_part}.{conn.to_connector}"
                    )
                else:
                    kept.append(conn)
            plan.connections = kept

        return plan

    def _auto_snap(self, plan: AssemblyPlan, template_map: dict[str, set[str]]) -> None:
        """If a referenced connector is invalid but the part has exactly one
        connector, snap the reference to it."""
        for conn in plan.connections:
            from_conns = template_map.get(conn.from_part, set())
            to_conns = template_map.get(conn.to_part, set())
            if conn.from_connector not in from_conns and len(from_conns) == 1:
                only = next(iter(from_conns))
                self.warnings.append(
                    f"Snapped {conn.from_part}.{conn.from_connector} -> "
                    f"{conn.from_part}.{only} (sole connector)"
                )
                conn.from_connector = only
            if conn.to_connector not in to_conns and len(to_conns) == 1:
                only = next(iter(to_conns))
                self.warnings.append(
                    f"Snapped {conn.to_part}.{conn.to_connector} -> "
                    f"{conn.to_part}.{only} (sole connector)"
                )
                conn.to_connector = only

    def _llm_refine(self, plan: AssemblyPlan, mismatches: list[dict]) -> None:
        """Ask the LLM to remap mismatched connectors. Best-effort — on any
        failure the plan is left as-is for Layer 3 to clean up."""
        template_connectors = {}
        for part in plan.parts:
            try:
                tmpl = self._registry.get(part.suggested_template)
            except Exception:
                template_connectors[part.part_id] = []
                continue
            template_connectors[part.part_id] = [
                {"name": c.name, "type": c.type, "direction": list(c.direction)}
                for c in tmpl.connectors
            ]

        system, user = build_connection_refinement_prompt(
            plan, mismatches, template_connectors,
        )
        try:
            # Thinking off — like decomposition, this returns structured JSON
            # (remapped connector names), not open-ended reasoning.
            raw = self._provider.chat(
                user, system=system, max_tokens=8192, thinking=False,
            )
            data = parse_json_response(raw)
        except Exception:
            return

        new_connections = []
        for c in data.get("connections", []):
            try:
                new_connections.append(ConnectionSpec(
                    from_part=c["from_part"],
                    from_connector=c["from_connector"],
                    to_part=c["to_part"],
                    to_connector=c["to_connector"],
                    type=c.get("type", "mate"),
                    offset=float(c.get("offset", 0)),
                ))
            except (KeyError, TypeError, ValueError):
                continue

        if new_connections:
            plan.connections = new_connections

    def _build_template_map(self, plan: AssemblyPlan) -> dict[str, set[str]]:
        """Map part_id → set of connector names on its template."""
        result = {}
        for part in plan.parts:
            try:
                tmpl = self._registry.get(part.suggested_template)
                result[part.part_id] = {c.name for c in tmpl.connectors}
            except Exception:
                result[part.part_id] = set()
        return result

    def _find_mismatches(
        self,
        plan: AssemblyPlan,
        template_map: dict[str, set[str]],
    ) -> list[dict]:
        """Find connections that reference nonexistent connectors."""
        mismatches = []
        for conn in plan.connections:
            from_connectors = template_map.get(conn.from_part, set())
            to_connectors = template_map.get(conn.to_part, set())

            if conn.from_connector not in from_connectors:
                available = ", ".join(sorted(from_connectors)) or "none"
                mismatches.append({
                    "from_part": conn.from_part,
                    "from_connector": conn.from_connector,
                    "to_part": conn.to_part,
                    "to_connector": conn.to_connector,
                    "error": (
                        f"'{conn.from_part}' has no connector '{conn.from_connector}' "
                        f"(available: {available})"
                    ),
                })
            elif conn.to_connector not in to_connectors:
                available = ", ".join(sorted(to_connectors)) or "none"
                mismatches.append({
                    "from_part": conn.from_part,
                    "from_connector": conn.from_connector,
                    "to_part": conn.to_part,
                    "to_connector": conn.to_connector,
                    "error": (
                        f"'{conn.to_part}' has no connector '{conn.to_connector}' "
                        f"(available: {available})"
                    ),
                })

        return mismatches
