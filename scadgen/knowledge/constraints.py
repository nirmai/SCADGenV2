"""Cross-parameter constraint checking and linked dimension re-derivation."""

from __future__ import annotations

from typing import Any, Callable

from scadgen.types import Template
from scadgen.knowledge.standards import (
    ISO_COUNTERSUNK,
    ISO_GEAR_MODULES,
    ISO_METRIC_THREADS,
    ISO_SHCS,
    ISO_WASHERS,
    lookup_keyway,
    nearest_gear_module,
)


def check_template_constraints(
    template: Template, params: dict[str, Any],
) -> tuple[list[str], list[str]]:
    """Evaluate YAML-declared constraints against params.

    Returns (errors, warnings).
    """
    errors: list[str] = []
    warnings: list[str] = []

    for constraint in template.constraints:
        try:
            result = eval(constraint.check, {"__builtins__": {}}, params)  # noqa: S307
        except Exception:
            continue

        if not result:
            msg = constraint.message
            if msg:
                try:
                    msg = msg.format(**params)
                except (KeyError, ValueError):
                    pass
            else:
                msg = f"Constraint failed: {constraint.check}"

            if constraint.severity == "warning":
                warnings.append(msg)
            else:
                errors.append(msg)

    return errors, warnings


def check_engineering_warnings(
    template: Template, params: dict[str, Any],
) -> list[str]:
    """Standards-based soft checks that need lookup table access."""
    warnings: list[str] = []
    checker = _WARNING_CHECKERS.get(template.template_id)
    if checker:
        checker(params, warnings)
    return warnings


def _check_gear_warnings(params: dict[str, Any], warnings: list[str]) -> None:
    modul = params.get("modul", 0)
    if modul > 0 and modul not in ISO_GEAR_MODULES:
        nearest = nearest_gear_module(modul)
        warnings.append(
            f"Module {modul}mm is not in the ISO 54 standard series. "
            f"Nearest standard: {nearest}mm"
        )


def _check_bolt_warnings(params: dict[str, Any], warnings: list[str]) -> None:
    shaft_diam = params.get("shaft_diam", 0)
    thread_pitch = params.get("thread_pitch", 0)
    add_threads = params.get("add_threads", True)

    if add_threads and shaft_diam > 0 and thread_pitch > shaft_diam * 0.25:
        warnings.append(
            f"Thread pitch ({thread_pitch}mm) is unusually large "
            f"relative to shaft diameter ({shaft_diam}mm)"
        )

    iso_match = find_iso_by_shaft_diam(shaft_diam)
    if iso_match:
        key, data = iso_match
        head_flat = params.get("head_flat", 0)
        head_height = params.get("head_height", 0)
        if head_flat and abs(head_flat - data["head_flat"]) > 0.1:
            warnings.append(
                f"Head across-flats ({head_flat}mm) doesn't match "
                f"{key} standard ({data['head_flat']}mm)"
            )
        if head_height and abs(head_height - data["head_height"]) > 0.1:
            warnings.append(
                f"Head height ({head_height}mm) doesn't match "
                f"{key} standard ({data['head_height']}mm)"
            )



def _check_shcs_warnings(params: dict[str, Any], warnings: list[str]) -> None:
    shaft_diam = params.get("shaft_diam", 0)
    thread_pitch = params.get("thread_pitch", 0)
    add_threads = params.get("add_threads", True)

    if add_threads and shaft_diam > 0 and thread_pitch > shaft_diam * 0.25:
        warnings.append(
            f"Thread pitch ({thread_pitch}mm) is unusually large "
            f"relative to shaft diameter ({shaft_diam}mm)"
        )

    iso = _find_shcs_by_shaft(shaft_diam)
    if iso:
        key, data = iso
        head_diam = params.get("head_diam", 0)
        head_height = params.get("head_height", 0)
        if head_diam and abs(head_diam - data["head_diam"]) > 0.1:
            warnings.append(
                f"Head diameter ({head_diam}mm) doesn't match "
                f"{key} SHCS standard ({data['head_diam']}mm)"
            )
        if head_height and abs(head_height - data["head_height"]) > 0.1:
            warnings.append(
                f"Head height ({head_height}mm) doesn't match "
                f"{key} SHCS standard ({data['head_height']}mm)"
            )


def _check_countersunk_warnings(params: dict[str, Any], warnings: list[str]) -> None:
    shaft_diam = params.get("shaft_diam", 0)
    thread_pitch = params.get("thread_pitch", 0)
    add_threads = params.get("add_threads", True)

    if add_threads and shaft_diam > 0 and thread_pitch > shaft_diam * 0.25:
        warnings.append(
            f"Thread pitch ({thread_pitch}mm) is unusually large "
            f"relative to shaft diameter ({shaft_diam}mm)"
        )

    iso = _find_countersunk_by_shaft(shaft_diam)
    if iso:
        key, data = iso
        head_diam = params.get("head_diam", 0)
        if head_diam and abs(head_diam - data["head_diam"]) > 0.1:
            warnings.append(
                f"Head diameter ({head_diam}mm) doesn't match "
                f"{key} countersunk standard ({data['head_diam']}mm)"
            )


def validate_constraints(
    template: Template, params: dict[str, Any],
) -> tuple[list[str], list[str]]:
    """Run all constraint checks. Returns (errors, warnings)."""
    errors, warnings = check_template_constraints(template, params)
    warnings.extend(check_engineering_warnings(template, params))
    return errors, warnings


def find_iso_by_shaft_diam(shaft_diam: float) -> tuple[str, dict] | None:
    """Find ISO metric thread entry by shaft diameter."""
    for key, data in ISO_METRIC_THREADS.items():
        if abs(data["shaft_diam"] - shaft_diam) < 0.01:
            return key, data
    return None


def harmonize_linked_params(
    template: Template,
    params: dict[str, Any],
    user_explicit: set[str],
) -> tuple[dict[str, Any], list[str]]:
    """Re-derive linked dimensions when a driving parameter changes.

    Only updates params NOT in user_explicit (i.e., params the user didn't
    directly set). Returns (updated_params, info_messages).
    """
    messages: list[str] = []
    harmonizer = _HARMONIZERS.get(template.template_id)
    if harmonizer:
        harmonizer(params, user_explicit, messages)
    _clamp_thread_len(params, user_explicit, messages)
    return params, messages


def _clamp_thread_len(
    params: dict[str, Any], user_explicit: set[str], messages: list[str],
) -> None:
    thread_len = params.get("thread_len")
    shaft_len = params.get("shaft_len")
    if thread_len is None or shaft_len is None:
        return
    if "thread_len" not in user_explicit and thread_len > shaft_len:
        params["thread_len"] = shaft_len
        messages.append(f"Clamped thread_len to shaft_len ({shaft_len}mm)")


def _harmonize_bolt(
    params: dict[str, Any], user_explicit: set[str], messages: list[str],
) -> None:
    shaft_diam = params.get("shaft_diam", 0)
    iso_match = find_iso_by_shaft_diam(shaft_diam)

    if iso_match:
        key, data = iso_match
        updated = []
        if "head_flat" not in user_explicit:
            params["head_flat"] = data["head_flat"]
            updated.append(f"head_flat={data['head_flat']}")
        if "head_height" not in user_explicit:
            params["head_height"] = data["head_height"]
            updated.append(f"head_height={data['head_height']}")
        if "thread_pitch" not in user_explicit:
            params["thread_pitch"] = data["pitch_coarse"]
            updated.append(f"thread_pitch={data['pitch_coarse']}")
        if updated:
            messages.append(f"Re-derived for {key}: {', '.join(updated)}")
    elif "shaft_diam" in user_explicit and shaft_diam > 0:
        messages.append(
            f"shaft_diam={shaft_diam}mm does not match any ISO metric size; "
            f"head and pitch values may be inconsistent"
        )


def _harmonize_nut(
    params: dict[str, Any], user_explicit: set[str], messages: list[str],
) -> None:
    thread_diam = params.get("thread_diam", 0)
    iso_match = find_iso_by_shaft_diam(thread_diam)

    if iso_match:
        key, data = iso_match
        updated = []
        if "flat" not in user_explicit:
            params["flat"] = data["nut_flat"]
            updated.append(f"flat={data['nut_flat']}")
        if "thickness" not in user_explicit:
            params["thickness"] = data["nut_height"]
            updated.append(f"thickness={data['nut_height']}")
        if "pitch" not in user_explicit:
            params["pitch"] = data["pitch_coarse"]
            updated.append(f"pitch={data['pitch_coarse']}")
        if updated:
            messages.append(f"Re-derived for {key} nut: {', '.join(updated)}")
    elif "thread_diam" in user_explicit and thread_diam > 0:
        messages.append(
            f"thread_diam={thread_diam}mm does not match any ISO metric size; "
            f"nut dimensions may be inconsistent"
        )


def _find_shcs_by_shaft(shaft_diam: float) -> tuple[str, dict] | None:
    for key, data in ISO_SHCS.items():
        if abs(data["shaft_diam"] - shaft_diam) < 0.01:
            return key, data
    return None


def _find_countersunk_by_shaft(shaft_diam: float) -> tuple[str, dict] | None:
    for key, data in ISO_COUNTERSUNK.items():
        if abs(data["shaft_diam"] - shaft_diam) < 0.01:
            return key, data
    return None


def _find_washer_by_bolt_diam(bolt_diam: float) -> tuple[str, dict] | None:
    for key, data in ISO_WASHERS.items():
        nominal = data["inner_diam"] - bolt_diam
        if 0 < nominal < bolt_diam * 0.15:
            return key, data
    return None


def _harmonize_shcs(
    params: dict[str, Any], user_explicit: set[str], messages: list[str],
) -> None:
    shaft_diam = params.get("shaft_diam", 0)
    iso = _find_shcs_by_shaft(shaft_diam)

    if iso:
        key, data = iso
        updated = []
        if "head_diam" not in user_explicit:
            params["head_diam"] = data["head_diam"]
            updated.append(f"head_diam={data['head_diam']}")
        if "head_height" not in user_explicit:
            params["head_height"] = data["head_height"]
            updated.append(f"head_height={data['head_height']}")
        if "socket_size" not in user_explicit:
            params["socket_size"] = data["socket_size"]
            updated.append(f"socket_size={data['socket_size']}")
        if "socket_depth" not in user_explicit:
            params["socket_depth"] = data["socket_depth"]
            updated.append(f"socket_depth={data['socket_depth']}")
        thread_iso = find_iso_by_shaft_diam(shaft_diam)
        if thread_iso and "thread_pitch" not in user_explicit:
            params["thread_pitch"] = thread_iso[1]["pitch_coarse"]
            updated.append(f"thread_pitch={thread_iso[1]['pitch_coarse']}")
        if updated:
            messages.append(f"Re-derived for {key} SHCS: {', '.join(updated)}")
    elif "shaft_diam" in user_explicit and shaft_diam > 0:
        messages.append(
            f"shaft_diam={shaft_diam}mm does not match any ISO 4762 SHCS size; "
            f"head and socket values may be inconsistent"
        )


def _harmonize_countersunk(
    params: dict[str, Any], user_explicit: set[str], messages: list[str],
) -> None:
    shaft_diam = params.get("shaft_diam", 0)
    iso = _find_countersunk_by_shaft(shaft_diam)

    if iso:
        key, data = iso
        updated = []
        if "head_diam" not in user_explicit:
            params["head_diam"] = data["head_diam"]
            updated.append(f"head_diam={data['head_diam']}")
        if "head_height" not in user_explicit:
            params["head_height"] = data["head_height"]
            updated.append(f"head_height={data['head_height']}")
        if "socket_size" not in user_explicit:
            params["socket_size"] = data["socket_size"]
            updated.append(f"socket_size={data['socket_size']}")
        thread_iso = find_iso_by_shaft_diam(shaft_diam)
        if thread_iso and "thread_pitch" not in user_explicit:
            params["thread_pitch"] = thread_iso[1]["pitch_coarse"]
            updated.append(f"thread_pitch={thread_iso[1]['pitch_coarse']}")
        if updated:
            messages.append(f"Re-derived for {key} countersunk: {', '.join(updated)}")
    elif "shaft_diam" in user_explicit and shaft_diam > 0:
        messages.append(
            f"shaft_diam={shaft_diam}mm does not match any ISO 10642 size; "
            f"head dimensions may be inconsistent"
        )


def _harmonize_washer(
    params: dict[str, Any], user_explicit: set[str], messages: list[str],
) -> None:
    inner_diam = params.get("inner_diam", 0)
    bolt_diam_guess = inner_diam - inner_diam * 0.05
    iso = _find_washer_by_bolt_diam(bolt_diam_guess)
    if not iso:
        for key, data in ISO_WASHERS.items():
            if abs(data["inner_diam"] - inner_diam) < 0.01:
                iso = key, data
                break
    if iso:
        key, data = iso
        updated = []
        if "inner_diam" not in user_explicit:
            params["inner_diam"] = data["inner_diam"]
            updated.append(f"inner_diam={data['inner_diam']}")
        if "outer_diam" not in user_explicit:
            params["outer_diam"] = data["outer_diam"]
            updated.append(f"outer_diam={data['outer_diam']}")
        if "thickness" not in user_explicit:
            params["thickness"] = data["thickness"]
            updated.append(f"thickness={data['thickness']}")
        if updated:
            messages.append(f"Re-derived for {key} washer: {', '.join(updated)}")


# ── Engine template harmonization ──────────────────────────────────


def _harmonize_valve(
    params: dict[str, Any], user_explicit: set[str], messages: list[str],
) -> None:
    head_diam = params.get("head_diam", 0)
    if head_diam <= 0:
        return
    updated = []
    if "stem_diam" not in user_explicit:
        new_val = round(head_diam * 0.2, 1)
        new_val = max(new_val, 3.0)
        params["stem_diam"] = new_val
        updated.append(f"stem_diam={new_val}")
    if "seat_width" not in user_explicit:
        new_val = round(head_diam * 0.05, 1)
        new_val = max(new_val, 0.5)
        params["seat_width"] = new_val
        updated.append(f"seat_width={new_val}")
    if "margin_width" not in user_explicit:
        new_val = round(head_diam * 0.035, 1)
        new_val = max(new_val, 0.3)
        params["margin_width"] = new_val
        updated.append(f"margin_width={new_val}")
    if updated:
        messages.append(f"Re-derived valve from head_diam={head_diam}: {', '.join(updated)}")


def _harmonize_shaft(
    params: dict[str, Any], user_explicit: set[str], messages: list[str],
) -> None:
    diameter = params.get("diameter", 0)
    has_keyway = params.get("has_keyway", False)
    if not has_keyway or diameter <= 0:
        return

    dims = lookup_keyway(diameter)
    if not dims:
        return

    key_w, key_h, shaft_depth, _hub_depth = dims
    updated = []
    if "keyway_width" not in user_explicit:
        params["keyway_width"] = float(key_w)
        updated.append(f"keyway_width={key_w}")
    if "keyway_depth" not in user_explicit:
        params["keyway_depth"] = float(shaft_depth)
        updated.append(f"keyway_depth={shaft_depth}")
    if updated:
        messages.append(
            f"Re-derived keyway from DIN 6885 for {diameter}mm shaft: "
            f"{', '.join(updated)}"
        )


def _harmonize_piston(
    params: dict[str, Any], user_explicit: set[str], messages: list[str],
) -> None:
    bore_diam = params.get("bore_diam", 0)
    if bore_diam <= 0:
        return
    updated = []
    if "pin_bore_diam" not in user_explicit:
        new_val = round(bore_diam * 0.25, 1)
        params["pin_bore_diam"] = new_val
        updated.append(f"pin_bore_diam={new_val}")
    if "ring_width" not in user_explicit:
        new_val = round(bore_diam * 0.025, 1)
        new_val = max(new_val, 0.5)
        params["ring_width"] = new_val
        updated.append(f"ring_width={new_val}")
    if "ring_depth" not in user_explicit:
        new_val = round(bore_diam * 0.02, 1)
        new_val = max(new_val, 0.5)
        params["ring_depth"] = new_val
        updated.append(f"ring_depth={new_val}")
    if "wall_thickness" not in user_explicit:
        new_val = round(bore_diam * 0.06, 1)
        new_val = max(new_val, 2.0)
        params["wall_thickness"] = new_val
        updated.append(f"wall_thickness={new_val}")
    if updated:
        messages.append(
            f"Re-derived piston from bore_diam={bore_diam}: {', '.join(updated)}"
        )


def _harmonize_connecting_rod(
    params: dict[str, Any], user_explicit: set[str], messages: list[str],
) -> None:
    big_end_bore = params.get("big_end_bore", 0)
    small_end_bore = params.get("small_end_bore", 0)
    updated = []
    if big_end_bore > 0:
        if "big_end_width" not in user_explicit:
            new_val = round(big_end_bore * 1.4, 1)
            params["big_end_width"] = new_val
            updated.append(f"big_end_width={new_val}")
        if "thickness" not in user_explicit:
            new_val = round(big_end_bore * 0.45, 1)
            new_val = max(new_val, 5.0)
            params["thickness"] = new_val
            updated.append(f"thickness={new_val}")
    if small_end_bore > 0 and "small_end_width" not in user_explicit:
        new_val = round(small_end_bore * 1.5, 1)
        params["small_end_width"] = new_val
        updated.append(f"small_end_width={new_val}")
    if updated:
        messages.append(f"Re-derived connecting rod: {', '.join(updated)}")


def _harmonize_cylinder_block(
    params: dict[str, Any], user_explicit: set[str], messages: list[str],
) -> None:
    bore_diam = params.get("bore_diam", 0)
    bore_count = params.get("bore_count", 1)
    wall = params.get("wall_thickness", 8)
    if bore_diam <= 0:
        return
    updated = []
    if "bore_spacing" not in user_explicit:
        new_val = round(bore_diam * 1.12, 1)
        params["bore_spacing"] = new_val
        updated.append(f"bore_spacing={new_val}")
    if "block_width" not in user_explicit:
        new_val = round(bore_diam + 2 * wall + 10, 1)
        params["block_width"] = new_val
        updated.append(f"block_width={new_val}")

    spacing = params.get("bore_spacing", bore_diam * 1.12)
    if "block_length" not in user_explicit:
        new_val = round(spacing * (bore_count - 1) + bore_diam + 2 * wall + 20, 1)
        params["block_length"] = new_val
        updated.append(f"block_length={new_val}")
    if updated:
        messages.append(
            f"Re-derived block from bore_diam={bore_diam}, "
            f"bore_count={bore_count}: {', '.join(updated)}"
        )


def _harmonize_cylinder_head(
    params: dict[str, Any], user_explicit: set[str], messages: list[str],
) -> None:
    bore_diam = params.get("bore_diam", 0)
    bore_count = params.get("bore_count", 1)
    bore_spacing = params.get("bore_spacing", 90)
    if bore_diam <= 0:
        return
    updated = []
    if "valve_bore_diam" not in user_explicit:
        new_val = round(bore_diam * 0.1, 1)
        new_val = max(new_val, 3.0)
        params["valve_bore_diam"] = new_val
        updated.append(f"valve_bore_diam={new_val}")
    if "width" not in user_explicit:
        new_val = round(bore_diam + 40, 1)
        params["width"] = new_val
        updated.append(f"width={new_val}")
    if "length" not in user_explicit:
        new_val = round(bore_spacing * (bore_count - 1) + bore_diam + 40, 1)
        params["length"] = new_val
        updated.append(f"length={new_val}")
    if updated:
        messages.append(
            f"Re-derived head from bore_diam={bore_diam}, "
            f"bore_count={bore_count}: {', '.join(updated)}"
        )


# ── Engine template engineering warnings ───────────────────────────


def _check_shaft_warnings(params: dict[str, Any], warnings: list[str]) -> None:
    has_keyway = params.get("has_keyway", False)
    if not has_keyway:
        return
    diameter = params.get("diameter", 0)
    keyway_width = params.get("keyway_width", 0)
    keyway_depth = params.get("keyway_depth", 0)
    dims = lookup_keyway(diameter)
    if dims:
        std_w, _std_h, std_depth, _hub = dims
        if abs(keyway_width - std_w) > 0.1:
            warnings.append(
                f"Keyway width ({keyway_width}mm) doesn't match "
                f"DIN 6885 standard ({std_w}mm) for {diameter}mm shaft"
            )
        if abs(keyway_depth - std_depth) > 0.1:
            warnings.append(
                f"Keyway depth ({keyway_depth}mm) doesn't match "
                f"DIN 6885 standard ({std_depth}mm) for {diameter}mm shaft"
            )


def _check_piston_warnings(params: dict[str, Any], warnings: list[str]) -> None:
    bore_diam = params.get("bore_diam", 0)
    height = params.get("height", 0)
    if bore_diam > 0 and height > 0:
        ratio = height / bore_diam
        if ratio < 0.3 or ratio > 1.5:
            warnings.append(
                f"Height/bore ratio ({ratio:.2f}) is outside typical range "
                f"(0.3–1.5) for {bore_diam}mm bore"
            )


def _check_connecting_rod_warnings(
    params: dict[str, Any], warnings: list[str],
) -> None:
    length = params.get("length", 0)
    big_end_bore = params.get("big_end_bore", 0)
    if big_end_bore > 0 and length > 0:
        ratio = length / big_end_bore
        if ratio < 2.0:
            warnings.append(
                f"Length/big-end-bore ratio ({ratio:.1f}) is below 2.0; "
                f"rod may be too short for {big_end_bore}mm crank journal"
            )


def _check_cylinder_block_warnings(
    params: dict[str, Any], warnings: list[str],
) -> None:
    bore_diam = params.get("bore_diam", 0)
    bore_spacing = params.get("bore_spacing", 0)
    wall_thickness = params.get("wall_thickness", 0)
    if bore_diam > 0 and bore_spacing > 0:
        inter_bore_wall = bore_spacing - bore_diam
        if inter_bore_wall < 4:
            warnings.append(
                f"Inter-bore wall ({inter_bore_wall:.1f}mm) is less than 4mm; "
                f"may be structurally weak"
            )


# ── Tier 3 template harmonization ────────────────────────────────────


def _harmonize_spring(
    params: dict[str, Any], user_explicit: set[str], messages: list[str],
) -> None:
    coil_diam = params.get("coil_diam", 0)
    if coil_diam <= 0:
        return
    updated = []
    if "wire_diam" not in user_explicit:
        new_val = round(coil_diam * 0.1, 1)
        new_val = max(new_val, 0.3)
        params["wire_diam"] = new_val
        updated.append(f"wire_diam={new_val}")
    if updated:
        messages.append(
            f"Re-derived spring from coil_diam={coil_diam}: {', '.join(updated)}"
        )


def _harmonize_gasket(
    params: dict[str, Any], user_explicit: set[str], messages: list[str],
) -> None:
    inner_diam = params.get("inner_diam", 0)
    if inner_diam <= 0:
        return
    updated = []
    if "outer_diam" not in user_explicit:
        new_val = round(inner_diam * 1.5, 1)
        params["outer_diam"] = new_val
        updated.append(f"outer_diam={new_val}")
    if "bolt_circle_diam" not in user_explicit:
        new_val = round(inner_diam * 1.25, 1)
        params["bolt_circle_diam"] = new_val
        updated.append(f"bolt_circle_diam={new_val}")
    if updated:
        messages.append(
            f"Re-derived gasket from inner_diam={inner_diam}: {', '.join(updated)}"
        )


def _harmonize_bearing_shell(
    params: dict[str, Any], user_explicit: set[str], messages: list[str],
) -> None:
    bore = params.get("bore", 0)
    if bore <= 0:
        return
    updated = []
    if "wall_thickness" not in user_explicit:
        new_val = round(bore * 0.06, 1)
        new_val = max(new_val, 1.5)
        params["wall_thickness"] = new_val
        updated.append(f"wall_thickness={new_val}")
    wt = params.get("wall_thickness", 3.0)
    if "outer_diam" not in user_explicit:
        new_val = round(bore + 2 * wt, 1)
        params["outer_diam"] = new_val
        updated.append(f"outer_diam={new_val}")
    if updated:
        messages.append(
            f"Re-derived bearing shell from bore={bore}: {', '.join(updated)}"
        )


def _harmonize_pulley(
    params: dict[str, Any], user_explicit: set[str], messages: list[str],
) -> None:
    pitch_diam = params.get("pitch_diam", 0)
    if pitch_diam <= 0:
        return
    updated = []
    if "hub_diam" not in user_explicit:
        new_val = round(pitch_diam * 0.5, 1)
        params["hub_diam"] = new_val
        updated.append(f"hub_diam={new_val}")
    if "groove_depth" not in user_explicit:
        new_val = round(pitch_diam * 0.1, 1)
        new_val = max(new_val, 3.0)
        params["groove_depth"] = new_val
        updated.append(f"groove_depth={new_val}")
    if updated:
        messages.append(
            f"Re-derived pulley from pitch_diam={pitch_diam}: {', '.join(updated)}"
        )


def _harmonize_flywheel(
    params: dict[str, Any], user_explicit: set[str], messages: list[str],
) -> None:
    outer_diam = params.get("outer_diam", 0)
    if outer_diam <= 0:
        return
    updated = []
    if "bore_diam" not in user_explicit:
        new_val = round(outer_diam * 0.125, 1)
        params["bore_diam"] = new_val
        updated.append(f"bore_diam={new_val}")
    if "bolt_circle_diam" not in user_explicit:
        new_val = round(outer_diam * 0.75, 1)
        params["bolt_circle_diam"] = new_val
        updated.append(f"bolt_circle_diam={new_val}")
    if updated:
        messages.append(
            f"Re-derived flywheel from outer_diam={outer_diam}: {', '.join(updated)}"
        )


def _harmonize_oil_pan(
    params: dict[str, Any], user_explicit: set[str], messages: list[str],
) -> None:
    length = params.get("length", 0)
    width = params.get("width", 0)
    if length <= 0 and width <= 0:
        return
    updated = []
    if "flange_width" not in user_explicit and (length > 0 or width > 0):
        perimeter = 2 * (length + width) if length > 0 and width > 0 else max(length, width) * 4
        new_val = round(perimeter * 0.014, 1)
        new_val = max(new_val, 10.0)
        params["flange_width"] = new_val
        updated.append(f"flange_width={new_val}")
    if updated:
        messages.append(
            f"Re-derived oil pan from length={length}, width={width}: "
            f"{', '.join(updated)}"
        )


# ── Tier 3 engineering warnings ──────────────────────────────────────


def _check_spring_warnings(params: dict[str, Any], warnings: list[str]) -> None:
    coil_diam = params.get("coil_diam", 0)
    wire_diam = params.get("wire_diam", 0)
    if wire_diam > 0 and coil_diam > 0:
        spring_index = coil_diam / wire_diam
        if spring_index < 3:
            warnings.append(
                f"Spring index ({spring_index:.1f}) is below 3; "
                f"spring will be very stiff and hard to manufacture"
            )
        elif spring_index > 20:
            warnings.append(
                f"Spring index ({spring_index:.1f}) is above 20; "
                f"spring may buckle or tangle"
            )


def _check_bearing_shell_warnings(
    params: dict[str, Any], warnings: list[str],
) -> None:
    bore = params.get("bore", 0)
    width = params.get("width", 0)
    if bore > 0 and width > 0:
        ratio = width / bore
        if ratio < 0.2:
            warnings.append(
                f"Width/bore ratio ({ratio:.2f}) is very narrow; "
                f"bearing may not distribute load adequately"
            )


# ── Dispatch registries ─────────────────────────────────────────────

_HARMONIZERS: dict[str, Callable] = {
    "hex_bolt": _harmonize_bolt,
    "hex_nut": _harmonize_nut,
    "socket_head_cap_screw": _harmonize_shcs,
    "countersunk_screw": _harmonize_countersunk,
    "washer": _harmonize_washer,
    "valve": _harmonize_valve,
    "shaft": _harmonize_shaft,
    "piston": _harmonize_piston,
    "connecting_rod": _harmonize_connecting_rod,
    "cylinder_block": _harmonize_cylinder_block,
    "cylinder_head": _harmonize_cylinder_head,
    "spring_compression": _harmonize_spring,
    "gasket": _harmonize_gasket,
    "bearing_shell": _harmonize_bearing_shell,
    "pulley": _harmonize_pulley,
    "flywheel": _harmonize_flywheel,
    "oil_pan": _harmonize_oil_pan,
}

_WARNING_CHECKERS: dict[str, Callable] = {
    "gear_spur": _check_gear_warnings,
    "hex_bolt": _check_bolt_warnings,
    "socket_head_cap_screw": _check_shcs_warnings,
    "countersunk_screw": _check_countersunk_warnings,
    "shaft": _check_shaft_warnings,
    "piston": _check_piston_warnings,
    "connecting_rod": _check_connecting_rod_warnings,
    "cylinder_block": _check_cylinder_block_warnings,
    "spring_compression": _check_spring_warnings,
    "bearing_shell": _check_bearing_shell_warnings,
}
