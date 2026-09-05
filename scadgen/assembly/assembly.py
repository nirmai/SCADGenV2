from __future__ import annotations

from dataclasses import dataclass, field

from scadgen.assembly.part import Part


@dataclass
class Connection:
    part_a: str
    connector_a: str
    part_b: str
    connector_b: str
    type: str = "coaxial"
    offset: float = 0.0


@dataclass
class Assembly:
    assembly_id: str
    parts: dict[str, Part] = field(default_factory=dict)
    connections: list[Connection] = field(default_factory=list)

    def add_part(self, part: Part) -> None:
        self.parts[part.part_id] = part

    def connect(
        self,
        part_a_id: str,
        connector_a: str,
        part_b_id: str,
        connector_b: str,
        type: str = "coaxial",
        offset: float = 0.0,
    ) -> None:
        self.connections.append(
            Connection(part_a_id, connector_a, part_b_id, connector_b, type, offset)
        )
