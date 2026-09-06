"""Connector position computation for assembly support."""

from __future__ import annotations

from typing import Any

from scadgen.types import ConnectorDef


def _eval_component(value: float | str, params: dict[str, Any]) -> float:
    if isinstance(value, str):
        return float(eval(value, {"__builtins__": {}}, params))  # noqa: S307
    return float(value)


def compute_connector_position(
    connector: ConnectorDef, params: dict[str, Any],
) -> tuple[float, float, float]:
    return (
        _eval_component(connector.origin[0], params),
        _eval_component(connector.origin[1], params),
        _eval_component(connector.origin[2], params),
    )


def compute_connector_direction(
    connector: ConnectorDef, params: dict[str, Any],
) -> tuple[float, float, float]:
    return (
        _eval_component(connector.direction[0], params),
        _eval_component(connector.direction[1], params),
        _eval_component(connector.direction[2], params),
    )


def compute_connector_diameter(
    connector: ConnectorDef, params: dict[str, Any],
) -> float:
    if connector.diameter_ref and connector.diameter_ref in params:
        return float(params[connector.diameter_ref])
    return 0.0
