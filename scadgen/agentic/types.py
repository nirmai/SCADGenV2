"""Data types for the agentic assembly pipeline."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class PartSpec:
    part_id: str
    description: str
    suggested_template: str
    suggested_params: dict[str, Any] = field(default_factory=dict)
    role: str = "structural"
    # True when the LLM marks this as a complex, non-primitive part that must
    # be generated rather than fuzzy-matched to a catalog primitive.
    custom: bool = False
    # Optional repetition, e.g. {"type": "radial", "count": 12, "radius": 60}
    # or {"type": "linear", "count": 5, "spacing": 20, "axis": "x"}.
    pattern: dict[str, Any] | None = None


@dataclass
class ConnectionSpec:
    from_part: str
    from_connector: str
    to_part: str
    to_connector: str
    type: str = "mate"
    offset: float = 0.0


@dataclass
class AssemblyPlan:
    name: str
    description: str
    root_part: str
    parts: list[PartSpec] = field(default_factory=list)
    connections: list[ConnectionSpec] = field(default_factory=list)
    colors: dict[str, str] = field(default_factory=dict)
    templates_found: list[str] = field(default_factory=list)
    templates_needed: list[str] = field(default_factory=list)


@dataclass
class AssemblyResult:
    scad_code: str
    output_path: str
    plan: AssemblyPlan
    generated_templates: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    success: bool = True
