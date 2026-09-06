"""Step 4: Validate and refine connection references against actual connectors."""

from __future__ import annotations

from scadgen.agentic.prompts import build_connection_refinement_prompt
from scadgen.agentic.types import AssemblyPlan, ConnectionSpec
from scadgen.core.template_registry import TemplateRegistry
from scadgen.exceptions import ConnectionPlanError
from scadgen.nlp.json_utils import parse_json_response
from scadgen.nlp.providers import LLMProvider


class ConnectionPlanner:
    def __init__(self, provider: LLMProvider, registry: TemplateRegistry):
        self._provider = provider
        self._registry = registry

    def refine(self, plan: AssemblyPlan) -> AssemblyPlan:
        """Validate connector references; use LLM to fix mismatches."""
        template_map = self._build_template_map(plan)
        mismatches = self._find_mismatches(plan, template_map)

        if not mismatches:
            return plan

        template_connectors = {}
        for part in plan.parts:
            tmpl = self._registry.get(part.suggested_template)
            template_connectors[part.part_id] = [
                {"name": c.name, "type": c.type, "direction": list(c.direction)}
                for c in tmpl.connectors
            ]

        system, user = build_connection_refinement_prompt(
            plan, mismatches, template_connectors,
        )
        raw = self._provider.chat(user, system=system)

        try:
            data = parse_json_response(raw)
        except ValueError as e:
            raise ConnectionPlanError(
                f"Failed to parse connection refinement: {e}"
            ) from e

        plan.connections = [
            ConnectionSpec(
                from_part=c["from_part"],
                from_connector=c["from_connector"],
                to_part=c["to_part"],
                to_connector=c["to_connector"],
                type=c.get("type", "mate"),
                offset=float(c.get("offset", 0)),
            )
            for c in data.get("connections", [])
        ]

        # Verify the refinement actually fixed things
        remaining = self._find_mismatches(plan, template_map)
        if remaining:
            raise ConnectionPlanError(
                "Connection refinement failed to resolve: "
                + "; ".join(m["error"] for m in remaining)
            )

        return plan

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
