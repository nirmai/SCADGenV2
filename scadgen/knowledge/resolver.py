"""Engineering standards resolver.

Pattern-matches standard designations in free text and resolves them
to concrete parameter values using the lookup tables in standards.py.
"""

from __future__ import annotations

import re
from typing import Any, Callable

from scadgen.types import ResolvedInput
from scadgen.knowledge.standards import (
    ISO_METRIC_THREADS,
    ISO_METRIC_FINE_PITCH,
    UNC_THREADS,
    ISO_GEAR_MODULES,
    BEARING_SERIES,
    FIT_KEYWORDS,
    ORING_CROSS_SECTIONS,
    NOMINAL_PIPE_SIZES,
    lookup_keyway,
    nearest_gear_module,
)


def _resolve_iso_metric(m: re.Match) -> tuple[dict[str, Any], list[str], str | None, float]:
    size_str = m.group(1)
    fine_pitch = m.group(2)

    key = f"M{size_str}"
    if "." not in size_str:
        key = f"M{int(float(size_str))}"

    data = ISO_METRIC_THREADS.get(key)
    if not data:
        return {}, [], None, 0.0

    params: dict[str, Any] = {
        "shaft_diam": data["shaft_diam"],
        "head_flat": data["head_flat"],
        "head_height": data["head_height"],
    }

    if fine_pitch:
        pitch = float(fine_pitch)
        fine_options = ISO_METRIC_FINE_PITCH.get(key, [])
        if pitch in fine_options:
            params["thread_pitch"] = pitch
            params["pitch"] = pitch
            standard = f"ISO metric {key}x{pitch}"
        else:
            params["thread_pitch"] = pitch
            params["pitch"] = pitch
            standard = f"{key}x{pitch} (non-standard fine pitch)"
    else:
        params["thread_pitch"] = data["pitch_coarse"]
        params["pitch"] = data["pitch_coarse"]
        standard = f"ISO metric {key} coarse"

    return params, [standard], None, 0.85


def _resolve_unc(m: re.Match) -> tuple[dict[str, Any], list[str], str | None, float]:
    num_size = m.group(1)
    num_tpi = m.group(2)
    frac_size = m.group(3)
    frac_tpi = m.group(4)

    if num_size is not None:
        key = f"#{num_size}-{num_tpi}"
    else:
        key = f"{frac_size}-{frac_tpi}"

    data = UNC_THREADS.get(key)
    if not data:
        return {}, [], None, 0.0

    params = {
        "shaft_diam": data["shaft_diam"],
        "thread_pitch": data["pitch_mm"],
        "pitch": data["pitch_mm"],
    }
    return params, [f"ASME B1.1 {key} UNC"], None, 0.80


def _resolve_bearing(m: re.Match) -> tuple[dict[str, Any], list[str], str | None, float]:
    series = m.group(1)
    bore_code = int(m.group(2))

    _BORE_SPECIAL = {0: 10, 1: 12, 2: 15, 3: 17}
    if bore_code in _BORE_SPECIAL:
        bore_mm = _BORE_SPECIAL[bore_code]
    else:
        bore_mm = bore_code * 5

    series_key = f"{series}00"
    series_data = BEARING_SERIES.get(series_key)
    if not series_data:
        return {}, [], None, 0.0

    dims = series_data.get(bore_mm)
    if not dims:
        return {}, [], None, 0.0

    od, width = dims
    designation = f"{series_key}{bore_code:02d}"
    params = {
        "bore_diam": float(bore_mm),
        "outer_diam": float(od),
        "width": float(width),
    }
    return params, [f"ISO bearing {designation}"], None, 0.90


def _resolve_fit_class(m: re.Match) -> tuple[dict[str, Any], list[str], str | None, float]:
    hole = m.group(1)
    shaft = m.group(2)
    fit_key = f"{hole}/{shaft}"

    from scadgen.knowledge.standards import ISO_FITS
    fit = ISO_FITS.get(fit_key)
    if not fit:
        return {}, [], None, 0.0

    params = {"fit_class": fit_key, "fit_type": fit["type"]}
    return params, [f"ISO 286 {fit_key} ({fit['description']})"], None, 0.70


def _resolve_gear_module(m: re.Match) -> tuple[dict[str, Any], list[str], str | None, float]:
    raw = float(m.group(1))
    standard = nearest_gear_module(raw)
    params: dict[str, Any] = {"modul": standard}
    notes = []
    if abs(raw - standard) > 0.001:
        notes.append(f"Non-standard module {raw} snapped to ISO {standard}")
    return params, [f"ISO 54 module {standard}"] + notes, "gear_spur", 0.70


def _resolve_pressure_angle(m: re.Match) -> tuple[dict[str, Any], list[str], str | None, float]:
    angle = float(m.group(1))
    from scadgen.knowledge.standards import STANDARD_PRESSURE_ANGLES
    if angle not in STANDARD_PRESSURE_ANGLES:
        nearest = min(STANDARD_PRESSURE_ANGLES, key=lambda a: abs(a - angle))
        return {"pressure_angle": nearest}, [f"Pressure angle snapped to {nearest} deg"], "gear_spur", 0.60
    return {"pressure_angle": angle}, [f"Pressure angle {angle} deg"], "gear_spur", 0.60


def _resolve_inches_to_mm(m: re.Match) -> tuple[dict[str, Any], list[str], str | None, float]:
    raw = m.group(1)
    if "/" in raw:
        num, den = raw.split("/")
        mm = (float(num) / float(den)) * 25.4
    else:
        mm = float(raw) * 25.4
    return {"_inches_mm": mm}, [f"{raw} inch = {mm:.2f} mm"], None, 0.50


def _resolve_pipe(m: re.Match) -> tuple[dict[str, Any], list[str], str | None, float]:
    prefix = m.group(0).split()[0]
    designation = m.group(0).strip()

    # Try exact lookup
    data = NOMINAL_PIPE_SIZES.get(designation)
    if not data:
        # Try with cleaned key
        for key in NOMINAL_PIPE_SIZES:
            if key.lower().replace(" ", "") == designation.lower().replace(" ", ""):
                data = NOMINAL_PIPE_SIZES[key]
                designation = key
                break
    if not data:
        return {}, [], None, 0.0

    od, wall = data
    params = {"outer_diam": od, "wall_thickness": wall, "inner_diam": od - 2 * wall}
    return params, [f"Pipe {designation} (OD={od}mm, wall={wall}mm)"], None, 0.80


def _resolve_fit_keyword(m: re.Match) -> tuple[dict[str, Any], list[str], str | None, float]:
    keyword = m.group(0).lower().strip()
    fit_class = FIT_KEYWORDS.get(keyword)
    if not fit_class:
        return {}, [], None, 0.0

    from scadgen.knowledge.standards import ISO_FITS
    fit = ISO_FITS.get(fit_class, {})
    desc = fit.get("description", "")
    params = {"fit_class": fit_class, "fit_type": fit.get("type", "")}
    return params, [f"ISO 286 {fit_class} ({desc})"], None, 0.65


def _resolve_oring(m: re.Match) -> tuple[dict[str, Any], list[str], str | None, float]:
    cs = float(m.group(1))
    data = ORING_CROSS_SECTIONS.get(cs)
    if not data:
        nearest_cs = min(ORING_CROSS_SECTIONS.keys(), key=lambda c: abs(c - cs))
        data = ORING_CROSS_SECTIONS[nearest_cs]
        note = f"O-ring CS {cs}mm snapped to standard {nearest_cs}mm"
        cs = nearest_cs
    else:
        note = f"O-ring CS {cs}mm"

    params = {
        "oring_cs": cs,
        "groove_depth": data["groove_depth"],
        "groove_width": data["groove_width"],
    }
    return params, [f"ISO 3601 {note}"], None, 0.75


def _resolve_keyway(m: re.Match) -> tuple[dict[str, Any], list[str], str | None, float]:
    shaft_d = float(m.group(1))
    dims = lookup_keyway(shaft_d)
    if not dims:
        return {}, [], None, 0.0

    key_w, key_h, shaft_depth, hub_depth = dims
    params = {
        "shaft_diam": shaft_d,
        "key_width": key_w,
        "key_height": key_h,
        "shaft_keyway_depth": shaft_depth,
        "hub_keyway_depth": hub_depth,
    }
    return params, [f"DIN 6885 keyway for {shaft_d}mm shaft (w={key_w} h={key_h})"], None, 0.80


def _resolve_length_mm(m: re.Match) -> tuple[dict[str, Any], list[str], str | None, float]:
    value = float(m.group(1))
    return {"_length_mm": value}, [], None, 0.40


def _resolve_teeth(m: re.Match) -> tuple[dict[str, Any], list[str], str | None, float]:
    teeth = int(m.group(1))
    return {"teeth": teeth}, [], "gear_spur", 0.50


# Resolver function signature: Match -> (params, standards, suggested_template, confidence)
_ResolverFn = Callable[[re.Match], tuple[dict[str, Any], list[str], str | None, float]]

_PATTERNS: list[tuple[re.Pattern, _ResolverFn]] = [
    # ISO metric threads: M8, M8x1.0, M8x1.25, M10 x 1.5
    (re.compile(r"\bM(\d+(?:\.\d+)?)(?:\s*[xX]\s*([\d.]+))?\b", re.IGNORECASE),
     _resolve_iso_metric),

    # UNC threads: #10-24, #6-32, 1/4-20, 3/8-16, optionally followed by UNC/UNF
    (re.compile(r"\b(?:#(\d+)-(\d+)|(\d+/\d+)-(\d+))\s*(?:UNC|UNF)?\b"),
     _resolve_unc),

    # Bearing designations: 6205, 6305, 6010
    (re.compile(r"\b(6[0-3])(\d{2})\b"),
     _resolve_bearing),

    # ISO fit classes: H7/p6, H7/h6
    (re.compile(r"\b([A-Z]\d+)\s*/\s*([a-z]\d+)\b"),
     _resolve_fit_class),

    # Gear module: "module 2", "mod 2.5", "m2"
    (re.compile(r"\b(?:mod(?:ule)?)\s+(\d+(?:\.\d+)?)\b", re.IGNORECASE),
     _resolve_gear_module),

    # Pressure angle
    (re.compile(r"\b(?:PA|pressure\s*angle)\s*(\d+(?:\.\d+)?)\b", re.IGNORECASE),
     _resolve_pressure_angle),

    # Inch values: 2 inch, 2", 1/2 inch
    (re.compile(r"\b(\d+(?:/\d+)?(?:\.\d+)?)\s*(?:inch(?:es)?|in|\")\b", re.IGNORECASE),
     _resolve_inches_to_mm),

    # Pipe sizes: NPS 1/2, DN25, NPS 1-1/2
    (re.compile(r"\b(?:NPS|DN)\s*\d+(?:/\d+)?(?:-\d+/\d+)?\b", re.IGNORECASE),
     _resolve_pipe),

    # Fit keywords: press fit, sliding fit, etc.
    (re.compile(
        r"\b(?:press|interference|sliding|clearance|running|transition"
        r"|shrink|force|close|location|light\s+press|medium\s+press"
        r"|heavy\s+press)\s+fit\b",
        re.IGNORECASE,
    ), _resolve_fit_keyword),

    # O-ring cross section
    (re.compile(r"\bo-?ring\b.*?(\d+(?:\.\d+)?)\s*(?:mm)?\s*(?:CS|cross)", re.IGNORECASE),
     _resolve_oring),

    # Keyway for shaft diameter
    (re.compile(r"\bkeyway\b.*?(\d+(?:\.\d+)?)\s*(?:mm)?\s*shaft", re.IGNORECASE),
     _resolve_keyway),

    # Generic length: 40mm, 50 mm
    (re.compile(r"\b(\d+(?:\.\d+)?)\s*mm\b"),
     _resolve_length_mm),

    # Tooth count: "24 tooth", "32 teeth", "24t"
    (re.compile(r"\b(\d+)\s*(?:teeth|tooth|t)\b", re.IGNORECASE),
     _resolve_teeth),
]


class EngineeringResolver:
    """Resolve standard designations in free text into parameter values."""

    def __init__(self, registry=None):
        self._registry = registry

    def resolve(self, description: str) -> ResolvedInput:
        all_params: dict[str, Any] = {}
        all_standards: list[str] = []
        suggested_template: str | None = None
        max_confidence = 0.0

        for pattern, resolver_fn in _PATTERNS:
            for match in pattern.finditer(description):
                params, standards, template_hint, confidence = resolver_fn(match)
                # Merge params — first match wins for a given key
                for k, v in params.items():
                    if k not in all_params:
                        all_params[k] = v
                all_standards.extend(standards)
                if template_hint and confidence > max_confidence:
                    suggested_template = template_hint
                    max_confidence = confidence
                if confidence > max_confidence:
                    max_confidence = confidence

        # Infer template from matched standards when not explicitly suggested
        if not suggested_template:
            suggested_template = self._infer_template(description, all_params)
            if suggested_template:
                max_confidence = max(max_confidence, 0.60)

        # Resolve length parameter naming based on suggested template
        length_mm = all_params.pop("_length_mm", None)
        inches_mm = all_params.pop("_inches_mm", None)
        generic_length = length_mm or inches_mm

        if generic_length is not None:
            routed = False
            if suggested_template and self._registry:
                try:
                    tmpl = self._registry.get(suggested_template)
                    if tmpl.length_param:
                        all_params.setdefault(tmpl.length_param, generic_length)
                        routed = True
                except Exception:
                    pass
            if not routed:
                all_params.setdefault("_length_mm", generic_length)

        if suggested_template == "washer":
            self._map_bolt_params_to_washer(all_params)

        return ResolvedInput(
            original=description,
            standards_matched=all_standards,
            resolved_params=all_params,
            suggested_template=suggested_template,
            confidence=max_confidence,
        )

    def _map_bolt_params_to_washer(self, params: dict[str, Any]) -> None:
        """When template is washer, convert bolt params (shaft_diam) to washer params."""
        shaft_diam = params.pop("shaft_diam", None)
        params.pop("head_flat", None)
        params.pop("head_height", None)
        params.pop("thread_pitch", None)
        params.pop("pitch", None)
        if shaft_diam is not None and "inner_diam" not in params:
            from scadgen.knowledge.standards import ISO_METRIC_THREADS, ISO_WASHERS
            for key, data in ISO_METRIC_THREADS.items():
                if abs(data["shaft_diam"] - shaft_diam) < 0.01:
                    washer = ISO_WASHERS.get(key)
                    if washer:
                        params.setdefault("inner_diam", washer["inner_diam"])
                        params.setdefault("outer_diam", washer["outer_diam"])
                        params.setdefault("thickness", washer["thickness"])
                    break

    def _infer_template(self, description: str, params: dict[str, Any]) -> str | None:
        desc_lower = description.lower()

        # Fastener differentiation requires param-based routing (templates
        # can't self-describe "choose me when shaft_diam is present")
        if "shaft_diam" in params or "thread_pitch" in params or "pitch" in params:
            if any(w in desc_lower for w in ("socket head", "shcs", "allen bolt", "allen screw", "cap screw", "socket cap")):
                return "socket_head_cap_screw"
            if any(w in desc_lower for w in ("countersunk", "flat head", "flush", "csk")):
                return "countersunk_screw"
            if any(w in desc_lower for w in ("set screw", "grub screw", "headless")):
                return "set_screw"
            if any(w in desc_lower for w in ("bolt", "screw", "hex bolt", "hex head")):
                return "hex_bolt"
            if "nut" in desc_lower:
                return "hex_nut"

        if "modul" in params or "teeth" in params:
            return "gear_spur"

        if not self._registry:
            return None

        # Data-driven scoring: template metadata IS the routing table
        has_fastener_words = any(w in desc_lower for w in ("bolt", "screw", "nut"))
        best_tid, best_score = None, 0.0

        for tmpl in self._registry.list_templates():
            score = 0.0
            for alias in tmpl.aliases:
                a = alias.lower()
                if a in desc_lower:
                    score = max(score, 3.0 + len(a.split()))
            for kw in tmpl.keywords:
                if kw.lower() in desc_lower:
                    score += 1.0
            if has_fastener_words and not tmpl.category.startswith("fastener") and score < 5:
                score = 0.0
            if score > best_score:
                best_score = score
                best_tid = tmpl.template_id

        return best_tid if best_score > 0 else None
