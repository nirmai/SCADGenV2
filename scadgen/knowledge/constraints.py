"""Cross-parameter constraint checking and linked dimension re-derivation."""

from __future__ import annotations

from typing import Any

from scadgen.types import Template
from scadgen.knowledge.standards import ISO_GEAR_MODULES, ISO_METRIC_THREADS, nearest_gear_module


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
    tid = template.template_id

    if tid == "gear_spur":
        _check_gear_warnings(params, warnings)
    elif tid == "hex_bolt":
        _check_bolt_warnings(params, warnings)

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
    tid = template.template_id

    if tid == "hex_bolt":
        _harmonize_bolt(params, user_explicit, messages)
    elif tid == "hex_nut":
        _harmonize_nut(params, user_explicit, messages)

    return params, messages


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
