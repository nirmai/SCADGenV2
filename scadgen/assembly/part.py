from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from scadgen.types import ConnectorDef, Template


@dataclass
class Transform:
    translation: tuple[float, float, float] = (0.0, 0.0, 0.0)
    rotation: tuple[float, float, float] = (0.0, 0.0, 0.0)

    @classmethod
    def identity(cls) -> Transform:
        return cls()


@dataclass
class ConnectorInstance:
    definition: ConnectorDef
    world_origin: tuple[float, float, float] = (0.0, 0.0, 0.0)
    world_direction: tuple[float, float, float] = (0.0, 0.0, 1.0)
    diameter: float = 0.0


@dataclass
class Part:
    part_id: str
    template: Template
    parameters: dict[str, Any] = field(default_factory=dict)
    transform: Transform = field(default_factory=Transform.identity)
    connectors: dict[str, ConnectorInstance] = field(default_factory=dict)
    # Optional render-time repetition (radial/linear); see PartSpec.pattern.
    pattern: dict[str, Any] | None = None
