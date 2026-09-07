"""Step 1: Decompose a natural-language description into parts + connections."""

from __future__ import annotations

from typing import Any

from scadgen.agentic.prompts import build_decomposition_prompt
from scadgen.agentic.types import AssemblyPlan, ConnectionSpec, PartSpec
from scadgen.core.template_registry import TemplateRegistry
from scadgen.exceptions import DecompositionError
from scadgen.nlp.json_utils import parse_json_response
from scadgen.nlp.providers import ImageInput, LLMProvider


class AssemblyDecomposer:
    def __init__(self, provider: LLMProvider, registry: TemplateRegistry):
        self._provider = provider
        self._registry = registry

    def decompose(
        self, description: str, image: ImageInput | None = None,
    ) -> AssemblyPlan:
        templates = self._registry.list_templates()
        system, user = build_decomposition_prompt(
            description, templates, has_image=image is not None,
        )
        # Extended-thinking models can spend a large share of a small token
        # budget on invisible reasoning, leaving too little room for the
        # actual JSON — leave generous headroom.
        raw = self._provider.chat(user, system=system, image=image, max_tokens=8192)

        try:
            data = parse_json_response(raw)
        except ValueError as e:
            raise DecompositionError(f"Failed to parse decomposition: {e}") from e

        return self._build_plan(description, data)

    def _build_plan(self, description: str, data: dict[str, Any]) -> AssemblyPlan:
        parts = []
        for p in data.get("parts", []):
            parts.append(PartSpec(
                part_id=p["part_id"],
                description=p.get("description", ""),
                suggested_template=p["suggested_template"],
                suggested_params=p.get("suggested_params", {}),
                role=p.get("role", "structural"),
                custom=bool(p.get("custom", False)),
                pattern=_clean_pattern(p.get("pattern")),
            ))

        connections = []
        for c in data.get("connections", []):
            connections.append(ConnectionSpec(
                from_part=c["from_part"],
                from_connector=c["from_connector"],
                to_part=c["to_part"],
                to_connector=c["to_connector"],
                type=c.get("type", "mate"),
                offset=float(c.get("offset", 0)),
            ))

        if not parts:
            raise DecompositionError("LLM returned zero parts")

        return AssemblyPlan(
            name=data.get("assembly_name", "assembly"),
            description=description,
            root_part=data.get("root_part", parts[0].part_id),
            parts=parts,
            connections=connections,
            colors=data.get("colors", {}),
        )


def _clean_pattern(raw: Any) -> dict[str, Any] | None:
    """Validate and normalize an LLM-supplied repetition pattern."""
    if not isinstance(raw, dict):
        return None
    ptype = str(raw.get("type", "")).lower()
    if ptype not in ("radial", "linear"):
        return None
    try:
        count = int(raw.get("count", 0))
    except (TypeError, ValueError):
        return None
    if count <= 1:
        return None
    count = min(count, 64)

    if ptype == "radial":
        return {"type": "radial", "count": count,
                "radius": _as_float(raw.get("radius", 0))}
    axis = str(raw.get("axis", "x")).lower()
    if axis not in ("x", "y", "z"):
        axis = "x"
    return {"type": "linear", "count": count,
            "spacing": _as_float(raw.get("spacing", 0)), "axis": axis}


def _as_float(v: Any) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0
