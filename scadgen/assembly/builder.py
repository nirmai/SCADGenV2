"""High-level assembly builder API."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from scadgen.assembly.assembly import Assembly, Connection
from scadgen.assembly.part import Part, Transform
from scadgen.assembly.renderer import render_assembly
from scadgen.assembly.solver import compute_world_connectors, solve_assembly
from scadgen.core.engine import SCADEngine
from scadgen.types import GenerationResult


@dataclass
class _PartSpec:
    template_id: str
    params: dict[str, Any]
    gen_result: GenerationResult | None = None
    pattern: dict[str, Any] | None = None


class AssemblyBuilder:
    def __init__(self, engine: SCADEngine):
        self._engine = engine
        self._specs: dict[str, _PartSpec] = {}
        self._connections: list[Connection] = []
        self._root: str | None = None
        self._colors: dict[str, str] = {}
        self._warnings: list[str] = []

    def add_part(
        self,
        part_id: str,
        template_id: str,
        params: dict[str, Any] | None = None,
        pattern: dict[str, Any] | None = None,
    ) -> None:
        if part_id in self._specs:
            raise ValueError(f"Duplicate part_id: '{part_id}'")
        self._specs[part_id] = _PartSpec(template_id, params or {}, pattern=pattern)

    def connect(
        self,
        part_a: str,
        connector_a: str,
        part_b: str,
        connector_b: str,
        type: str = "mate",
        offset: float = 0.0,
    ) -> None:
        for pid in (part_a, part_b):
            if pid not in self._specs:
                raise ValueError(f"Unknown part '{pid}' — add_part first")
        self._connections.append(
            Connection(part_a, connector_a, part_b, connector_b, type, offset)
        )

    def set_root(self, part_id: str) -> None:
        if part_id not in self._specs:
            raise ValueError(f"Unknown part '{part_id}'")
        self._root = part_id

    def set_color(self, part_id: str, color: str) -> None:
        self._colors[part_id] = color

    def build(self) -> Assembly:
        self._warnings.clear()
        assembly = Assembly(assembly_id="assembly")
        for part_id, spec in self._specs.items():
            result = self._engine.generate(
                template_id=spec.template_id, params=spec.params,
            )
            spec.gen_result = result
            self._warnings.extend(result.warnings)
            part = Part(
                part_id=part_id,
                template=result.template,
                parameters=result.parameters,
                pattern=spec.pattern,
            )
            assembly.add_part(part)

        assembly.connections = list(self._connections)
        transforms = solve_assembly(assembly, self._root)

        for part_id, tf in transforms.items():
            part = assembly.parts[part_id]
            part.transform = tf
            part.connectors = compute_world_connectors(part, tf)

        return assembly

    def render(self, output_path: str | None = None) -> str:
        assembly = self.build()
        transforms = {pid: p.transform for pid, p in assembly.parts.items()}
        scad = render_assembly(assembly, transforms, self._colors or None)

        if output_path:
            out = Path(output_path)
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(scad, encoding="utf-8")

        return scad

    @property
    def warnings(self) -> list[str]:
        return list(self._warnings)
