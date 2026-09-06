"""Assembly position solver — BFS graph traversal to compute part transforms."""

from __future__ import annotations

import math
from collections import deque

from scadgen.assembly.connectors import (
    compute_connector_direction,
    compute_connector_diameter,
    compute_connector_position,
)
from scadgen.assembly.part import ConnectorInstance, Part, Transform
from scadgen.types import ConnectorDef

if False:  # TYPE_CHECKING
    from scadgen.assembly.assembly import Assembly


def solve_assembly(
    assembly: Assembly, root_id: str | None = None,
) -> dict[str, Transform]:
    if not assembly.parts:
        return {}

    if root_id is None:
        root_id = next(iter(assembly.parts))
    if root_id not in assembly.parts:
        raise ValueError(f"Root part '{root_id}' not in assembly")

    adj: dict[str, list[tuple[str, object]]] = {pid: [] for pid in assembly.parts}
    for conn in assembly.connections:
        adj[conn.part_a].append((conn.part_b, conn))
        adj[conn.part_b].append((conn.part_a, conn))

    transforms: dict[str, Transform] = {root_id: Transform.identity()}
    queue: deque[str] = deque([root_id])

    while queue:
        parent_id = queue.popleft()
        parent = assembly.parts[parent_id]
        parent_tf = transforms[parent_id]

        for neighbor_id, conn in adj[parent_id]:
            if neighbor_id in transforms:
                continue

            if conn.part_a == parent_id:
                p_conn_name, c_conn_name = conn.connector_a, conn.connector_b
            else:
                p_conn_name, c_conn_name = conn.connector_b, conn.connector_a

            child = assembly.parts[neighbor_id]
            p_conn_def = _find_connector(parent, p_conn_name)
            c_conn_def = _find_connector(child, c_conn_name)

            p_local_pos = compute_connector_position(p_conn_def, parent.parameters)
            p_local_dir = compute_connector_direction(p_conn_def, parent.parameters)
            p_rot = _euler_to_matrix(parent_tf.rotation)
            p_world_pos = _vadd(_mat_apply(p_rot, p_local_pos), parent_tf.translation)
            p_world_dir = _mat_apply(p_rot, p_local_dir)

            c_local_pos = compute_connector_position(c_conn_def, child.parameters)
            c_local_dir = compute_connector_direction(c_conn_def, child.parameters)

            target_dir = (
                _vscale(p_world_dir, -1) if conn.type == "mate" else p_world_dir
            )

            rot_matrix = _rotation_between(c_local_dir, target_dir)
            euler = _euler_from_matrix(rot_matrix)
            rotated_c_pos = _mat_apply(rot_matrix, c_local_pos)

            offset_vec = _vscale(_normalize(p_world_dir), conn.offset)
            translation = _vadd(_vsub(p_world_pos, rotated_c_pos), offset_vec)

            euler = _clean(euler)
            translation = _clean(translation)

            transforms[neighbor_id] = Transform(translation, euler)
            queue.append(neighbor_id)

    if len(transforms) < len(assembly.parts):
        missing = set(assembly.parts) - set(transforms)
        raise ValueError(f"Disconnected parts: {missing}")

    return transforms


def compute_world_connectors(
    part: Part, transform: Transform,
) -> dict[str, ConnectorInstance]:
    rot = _euler_to_matrix(transform.rotation)
    instances: dict[str, ConnectorInstance] = {}
    for cdef in part.template.connectors:
        lp = compute_connector_position(cdef, part.parameters)
        ld = compute_connector_direction(cdef, part.parameters)
        wp = _vadd(_mat_apply(rot, lp), transform.translation)
        wd = _mat_apply(rot, ld)
        diam = compute_connector_diameter(cdef, part.parameters)
        instances[cdef.name] = ConnectorInstance(
            definition=cdef,
            world_origin=_clean(wp),
            world_direction=_clean(wd),
            diameter=diam,
        )
    return instances


def _find_connector(part: Part, name: str) -> ConnectorDef:
    for c in part.template.connectors:
        if c.name == name:
            return c
    raise ValueError(
        f"Connector '{name}' not found on part '{part.part_id}' "
        f"(available: {[c.name for c in part.template.connectors]})"
    )


# ── Vector helpers ──────────────────────────────────────────────────────


def _normalize(v: tuple[float, ...]) -> tuple[float, float, float]:
    mag = math.sqrt(sum(c * c for c in v))
    if mag < 1e-10:
        return (0.0, 0.0, 0.0)
    return (v[0] / mag, v[1] / mag, v[2] / mag)


def _dot(a: tuple[float, ...], b: tuple[float, ...]) -> float:
    return sum(ai * bi for ai, bi in zip(a, b))


def _cross(
    a: tuple[float, ...], b: tuple[float, ...],
) -> tuple[float, float, float]:
    return (
        a[1] * b[2] - a[2] * b[1],
        a[2] * b[0] - a[0] * b[2],
        a[0] * b[1] - a[1] * b[0],
    )


def _vadd(
    a: tuple[float, ...], b: tuple[float, ...],
) -> tuple[float, float, float]:
    return (a[0] + b[0], a[1] + b[1], a[2] + b[2])


def _vsub(
    a: tuple[float, ...], b: tuple[float, ...],
) -> tuple[float, float, float]:
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def _vscale(v: tuple[float, ...], s: float) -> tuple[float, float, float]:
    return (v[0] * s, v[1] * s, v[2] * s)


def _clean(v: tuple[float, ...]) -> tuple[float, float, float]:
    return tuple(round(c, 6) if abs(c) > 1e-9 else 0.0 for c in v)


# ── Matrix helpers ──────────────────────────────────────────────────────

_Mat3 = list[list[float]]


def _mat_apply(m: _Mat3, p: tuple[float, ...]) -> tuple[float, float, float]:
    return (
        m[0][0] * p[0] + m[0][1] * p[1] + m[0][2] * p[2],
        m[1][0] * p[0] + m[1][1] * p[1] + m[1][2] * p[2],
        m[2][0] * p[0] + m[2][1] * p[1] + m[2][2] * p[2],
    )


def _matmul(a: _Mat3, b: _Mat3) -> _Mat3:
    r: _Mat3 = [[0.0] * 3 for _ in range(3)]
    for i in range(3):
        for j in range(3):
            for k in range(3):
                r[i][j] += a[i][k] * b[k][j]
    return r


def _euler_to_matrix(euler_deg: tuple[float, float, float]) -> _Mat3:
    ax, ay, az = (math.radians(d) for d in euler_deg)
    cx, sx = math.cos(ax), math.sin(ax)
    cy, sy = math.cos(ay), math.sin(ay)
    cz, sz = math.cos(az), math.sin(az)
    rx: _Mat3 = [[1, 0, 0], [0, cx, -sx], [0, sx, cx]]
    ry: _Mat3 = [[cy, 0, sy], [0, 1, 0], [-sy, 0, cy]]
    rz: _Mat3 = [[cz, -sz, 0], [sz, cz, 0], [0, 0, 1]]
    return _matmul(rz, _matmul(ry, rx))


def _euler_from_matrix(m: _Mat3) -> tuple[float, float, float]:
    if abs(m[2][0]) < 0.9999:
        by = math.asin(max(-1.0, min(1.0, -m[2][0])))
        ax = math.atan2(m[2][1], m[2][2])
        cz = math.atan2(m[1][0], m[0][0])
    else:
        by = math.pi / 2 if m[2][0] < 0 else -math.pi / 2
        ax = math.atan2(-m[0][1], m[1][1])
        cz = 0.0
    return (math.degrees(ax), math.degrees(by), math.degrees(cz))


def _rotation_from_axis_angle(axis: tuple[float, ...], angle: float) -> _Mat3:
    c = math.cos(angle)
    s = math.sin(angle)
    t = 1.0 - c
    x, y, z = axis
    return [
        [t * x * x + c, t * x * y - s * z, t * x * z + s * y],
        [t * x * y + s * z, t * y * y + c, t * y * z - s * x],
        [t * x * z - s * y, t * y * z + s * x, t * z * z + c],
    ]


def _rotation_between(
    v_from: tuple[float, ...], v_to: tuple[float, ...],
) -> _Mat3:
    a = _normalize(v_from)
    b = _normalize(v_to)
    d = _dot(a, b)

    if d > 0.9999:
        return [[1, 0, 0], [0, 1, 0], [0, 0, 1]]

    if d < -0.9999:
        perp = (
            _normalize(_cross(a, (1, 0, 0)))
            if abs(a[0]) < 0.9
            else _normalize(_cross(a, (0, 1, 0)))
        )
        return _rotation_from_axis_angle(perp, math.pi)

    axis = _normalize(_cross(a, b))
    angle = math.acos(max(-1.0, min(1.0, d)))
    return _rotation_from_axis_angle(axis, angle)
