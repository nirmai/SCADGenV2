"""Engineering standards database.

Pure-Python lookup tables derived from published ISO/ASME/DIN standards.
No external database, no ML.
"""

# ---------------------------------------------------------------------------
# ISO Metric Threads (ISO 261/262, ISO 4014/4017, ISO 4032)
# ---------------------------------------------------------------------------

ISO_METRIC_THREADS: dict[str, dict] = {
    "M1.6": {"shaft_diam": 1.6,  "pitch_coarse": 0.35, "head_flat": 3.2,   "head_height": 1.1,  "nut_flat": 3.2,   "nut_height": 1.3},
    "M2":   {"shaft_diam": 2.0,  "pitch_coarse": 0.4,  "head_flat": 4.0,   "head_height": 1.4,  "nut_flat": 4.0,   "nut_height": 1.6},
    "M2.5": {"shaft_diam": 2.5,  "pitch_coarse": 0.45, "head_flat": 5.0,   "head_height": 1.7,  "nut_flat": 5.0,   "nut_height": 2.0},
    "M3":   {"shaft_diam": 3.0,  "pitch_coarse": 0.5,  "head_flat": 5.5,   "head_height": 2.0,  "nut_flat": 5.5,   "nut_height": 2.4},
    "M4":   {"shaft_diam": 4.0,  "pitch_coarse": 0.7,  "head_flat": 7.0,   "head_height": 2.8,  "nut_flat": 7.0,   "nut_height": 3.2},
    "M5":   {"shaft_diam": 5.0,  "pitch_coarse": 0.8,  "head_flat": 8.0,   "head_height": 3.5,  "nut_flat": 8.0,   "nut_height": 4.7},
    "M6":   {"shaft_diam": 6.0,  "pitch_coarse": 1.0,  "head_flat": 10.0,  "head_height": 4.0,  "nut_flat": 10.0,  "nut_height": 5.2},
    "M8":   {"shaft_diam": 8.0,  "pitch_coarse": 1.25, "head_flat": 13.0,  "head_height": 5.3,  "nut_flat": 13.0,  "nut_height": 6.8},
    "M10":  {"shaft_diam": 10.0, "pitch_coarse": 1.5,  "head_flat": 16.0,  "head_height": 6.4,  "nut_flat": 16.0,  "nut_height": 8.4},
    "M12":  {"shaft_diam": 12.0, "pitch_coarse": 1.75, "head_flat": 18.0,  "head_height": 7.5,  "nut_flat": 18.0,  "nut_height": 10.8},
    "M14":  {"shaft_diam": 14.0, "pitch_coarse": 2.0,  "head_flat": 21.0,  "head_height": 8.8,  "nut_flat": 21.0,  "nut_height": 12.8},
    "M16":  {"shaft_diam": 16.0, "pitch_coarse": 2.0,  "head_flat": 24.0,  "head_height": 10.0, "nut_flat": 24.0,  "nut_height": 14.8},
    "M18":  {"shaft_diam": 18.0, "pitch_coarse": 2.5,  "head_flat": 27.0,  "head_height": 11.5, "nut_flat": 27.0,  "nut_height": 15.8},
    "M20":  {"shaft_diam": 20.0, "pitch_coarse": 2.5,  "head_flat": 30.0,  "head_height": 12.5, "nut_flat": 30.0,  "nut_height": 18.0},
    "M22":  {"shaft_diam": 22.0, "pitch_coarse": 2.5,  "head_flat": 32.0,  "head_height": 14.0, "nut_flat": 34.0,  "nut_height": 19.4},
    "M24":  {"shaft_diam": 24.0, "pitch_coarse": 3.0,  "head_flat": 36.0,  "head_height": 15.0, "nut_flat": 36.0,  "nut_height": 21.5},
    "M27":  {"shaft_diam": 27.0, "pitch_coarse": 3.0,  "head_flat": 41.0,  "head_height": 17.0, "nut_flat": 41.0,  "nut_height": 23.8},
    "M30":  {"shaft_diam": 30.0, "pitch_coarse": 3.5,  "head_flat": 46.0,  "head_height": 18.7, "nut_flat": 46.0,  "nut_height": 25.6},
    "M33":  {"shaft_diam": 33.0, "pitch_coarse": 3.5,  "head_flat": 50.0,  "head_height": 21.0, "nut_flat": 50.0,  "nut_height": 28.7},
    "M36":  {"shaft_diam": 36.0, "pitch_coarse": 4.0,  "head_flat": 55.0,  "head_height": 22.5, "nut_flat": 55.0,  "nut_height": 31.0},
    "M42":  {"shaft_diam": 42.0, "pitch_coarse": 4.5,  "head_flat": 65.0,  "head_height": 26.0, "nut_flat": 65.0,  "nut_height": 34.0},
    "M48":  {"shaft_diam": 48.0, "pitch_coarse": 5.0,  "head_flat": 75.0,  "head_height": 30.0, "nut_flat": 75.0,  "nut_height": 38.0},
    "M56":  {"shaft_diam": 56.0, "pitch_coarse": 5.5,  "head_flat": 85.0,  "head_height": 35.0, "nut_flat": 85.0,  "nut_height": 45.0},
    "M64":  {"shaft_diam": 64.0, "pitch_coarse": 6.0,  "head_flat": 95.0,  "head_height": 40.0, "nut_flat": 95.0,  "nut_height": 51.0},
}

ISO_METRIC_FINE_PITCH: dict[str, list[float]] = {
    "M8":  [1.0, 0.75],
    "M10": [1.25, 1.0, 0.75],
    "M12": [1.5, 1.25, 1.0],
    "M14": [1.5, 1.25, 1.0],
    "M16": [1.5, 1.0],
    "M18": [2.0, 1.5, 1.0],
    "M20": [2.0, 1.5, 1.0],
    "M22": [2.0, 1.5, 1.0],
    "M24": [2.0, 1.5, 1.0],
    "M27": [2.0, 1.5, 1.0],
    "M30": [2.0, 1.5, 1.0],
    "M33": [2.0, 1.5],
    "M36": [3.0, 2.0, 1.5],
    "M42": [3.0, 2.0, 1.5],
    "M48": [3.0, 2.0, 1.5],
}

# ---------------------------------------------------------------------------
# UNC/UNF Threads (ASME B1.1)
# ---------------------------------------------------------------------------

UNC_THREADS: dict[str, dict] = {
    "#0-80":   {"shaft_diam": 1.524, "pitch_mm": 0.317},
    "#1-64":   {"shaft_diam": 1.854, "pitch_mm": 0.397},
    "#2-56":   {"shaft_diam": 2.184, "pitch_mm": 0.454},
    "#3-48":   {"shaft_diam": 2.515, "pitch_mm": 0.529},
    "#4-40":   {"shaft_diam": 2.845, "pitch_mm": 0.635},
    "#5-40":   {"shaft_diam": 3.175, "pitch_mm": 0.635},
    "#6-32":   {"shaft_diam": 3.505, "pitch_mm": 0.794},
    "#8-32":   {"shaft_diam": 4.166, "pitch_mm": 0.794},
    "#10-24":  {"shaft_diam": 4.826, "pitch_mm": 1.058},
    "#12-24":  {"shaft_diam": 5.486, "pitch_mm": 1.058},
    "1/4-20":  {"shaft_diam": 6.350,  "pitch_mm": 1.270},
    "5/16-18": {"shaft_diam": 7.938,  "pitch_mm": 1.411},
    "3/8-16":  {"shaft_diam": 9.525,  "pitch_mm": 1.588},
    "7/16-14": {"shaft_diam": 11.112, "pitch_mm": 1.814},
    "1/2-13":  {"shaft_diam": 12.700, "pitch_mm": 1.954},
    "9/16-12": {"shaft_diam": 14.288, "pitch_mm": 2.117},
    "5/8-11":  {"shaft_diam": 15.875, "pitch_mm": 2.309},
    "3/4-10":  {"shaft_diam": 19.050, "pitch_mm": 2.540},
    "7/8-9":   {"shaft_diam": 22.225, "pitch_mm": 2.822},
    "1-8":     {"shaft_diam": 25.400, "pitch_mm": 3.175},
}

# ---------------------------------------------------------------------------
# ISO Gear Module Series (ISO 54)
# ---------------------------------------------------------------------------

ISO_GEAR_MODULES: list[float] = [
    0.3, 0.4, 0.5, 0.6, 0.8, 1.0, 1.25, 1.5,
    2.0, 2.5, 3.0, 4.0, 5.0, 6.0, 8.0, 10.0,
]

STANDARD_PRESSURE_ANGLES: list[float] = [14.5, 20.0, 25.0]

# ---------------------------------------------------------------------------
# Bearings (ISO 15, ISO 492) — bore: (OD, width)
# ---------------------------------------------------------------------------

BEARING_SERIES: dict[str, dict[int, tuple[int, int]]] = {
    "6000": {
        3: (10, 4), 4: (12, 4), 5: (13, 4), 6: (15, 5), 7: (19, 6),
        8: (22, 7), 9: (24, 7), 10: (26, 8), 12: (28, 8), 15: (32, 9),
        17: (35, 10), 20: (42, 12), 25: (47, 12), 30: (55, 13),
        35: (62, 14), 40: (68, 15), 45: (75, 16), 50: (80, 16),
    },
    "6200": {
        10: (30, 9), 12: (32, 10), 15: (35, 11), 17: (40, 12),
        20: (47, 14), 25: (52, 15), 30: (62, 16), 35: (72, 17),
        40: (80, 18), 45: (85, 19), 50: (90, 20),
    },
    "6300": {
        10: (35, 11), 12: (37, 12), 15: (42, 13), 17: (47, 14),
        20: (52, 15), 25: (62, 17), 30: (72, 19), 35: (80, 21),
        40: (90, 23), 45: (100, 25), 50: (110, 27),
    },
}

# ---------------------------------------------------------------------------
# ISO Fits (ISO 286-1/2)
# ---------------------------------------------------------------------------

ISO_FITS: dict[str, dict] = {
    "H7/f6":  {"description": "sliding fit (lubricated)", "type": "clearance"},
    "H7/g6":  {"description": "close running fit", "type": "clearance"},
    "H7/h6":  {"description": "location/sliding fit", "type": "clearance"},
    "H7/js6": {"description": "location fit (either way)", "type": "transition"},
    "H7/k6":  {"description": "location fit (light press)", "type": "transition"},
    "H7/m6":  {"description": "location fit (medium press)", "type": "transition"},
    "H7/n6":  {"description": "location fit (heavy press)", "type": "transition"},
    "H7/p6":  {"description": "press fit (light)", "type": "interference"},
    "H7/r6":  {"description": "press fit (medium)", "type": "interference"},
    "H7/s6":  {"description": "press fit (heavy)", "type": "interference"},
}

FIT_KEYWORDS: dict[str, str] = {
    "clearance fit": "H7/h6",
    "sliding fit": "H7/f6",
    "running fit": "H7/g6",
    "close fit": "H7/js6",
    "location fit": "H7/k6",
    "transition fit": "H7/k6",
    "press fit": "H7/p6",
    "interference fit": "H7/s6",
    "light press": "H7/p6",
    "medium press": "H7/r6",
    "heavy press": "H7/s6",
    "shrink fit": "H7/s6",
    "force fit": "H7/s6",
}

# ---------------------------------------------------------------------------
# Keyways (DIN 6885 / ISO 2491) — shaft range: (key_w, key_h, shaft_depth, hub_depth)
# ---------------------------------------------------------------------------

KEYWAY_STANDARDS: dict[tuple[int, int], tuple[float, float, float, float]] = {
    (6, 8):     (2, 2, 1.2, 1.0),
    (8, 10):    (3, 3, 1.8, 1.4),
    (10, 12):   (4, 4, 2.5, 1.8),
    (12, 17):   (5, 5, 3.0, 2.3),
    (17, 22):   (6, 6, 3.5, 2.8),
    (22, 30):   (8, 7, 4.0, 3.3),
    (30, 38):   (10, 8, 5.0, 3.3),
    (38, 44):   (12, 8, 5.0, 3.3),
    (44, 50):   (14, 9, 5.5, 3.8),
    (50, 58):   (16, 10, 6.0, 4.3),
    (58, 65):   (18, 11, 7.0, 4.4),
    (65, 75):   (20, 12, 7.5, 4.9),
    (75, 85):   (22, 14, 9.0, 5.4),
    (85, 95):   (25, 14, 9.0, 5.4),
}

# ---------------------------------------------------------------------------
# O-Ring Grooves (ISO 3601) — CS mm: {groove_depth, groove_width, squeeze %}
# ---------------------------------------------------------------------------

ORING_CROSS_SECTIONS: dict[float, dict] = {
    1.02: {"groove_depth": 0.70, "groove_width": 1.40, "squeeze": 0.31},
    1.27: {"groove_depth": 0.90, "groove_width": 1.70, "squeeze": 0.29},
    1.78: {"groove_depth": 1.32, "groove_width": 2.50, "squeeze": 0.26},
    2.62: {"groove_depth": 2.00, "groove_width": 3.55, "squeeze": 0.24},
    3.53: {"groove_depth": 2.77, "groove_width": 4.70, "squeeze": 0.22},
    5.33: {"groove_depth": 4.27, "groove_width": 7.00, "squeeze": 0.20},
    6.99: {"groove_depth": 5.64, "groove_width": 9.10, "squeeze": 0.19},
}

# ---------------------------------------------------------------------------
# Pipe Sizes (ASME B36.10M / ISO 4200)
# ---------------------------------------------------------------------------

NOMINAL_PIPE_SIZES: dict[str, tuple[float, float]] = {
    # NPS designation: (OD_mm, wall_schedule_40_mm)
    "NPS 1/8":   (10.3, 1.73),
    "NPS 1/4":   (13.7, 2.24),
    "NPS 3/8":   (17.1, 2.31),
    "NPS 1/2":   (21.3, 2.77),
    "NPS 3/4":   (26.7, 2.87),
    "NPS 1":     (33.4, 3.38),
    "NPS 1-1/4": (42.2, 3.56),
    "NPS 1-1/2": (48.3, 3.68),
    "NPS 2":     (60.3, 3.91),
    "NPS 2-1/2": (73.0, 5.16),
    "NPS 3":     (88.9, 5.49),
    "NPS 4":     (114.3, 6.02),
    # DN equivalents
    "DN6":  (10.2, 1.6),
    "DN8":  (13.5, 2.0),
    "DN10": (17.2, 2.0),
    "DN15": (21.3, 2.6),
    "DN20": (26.9, 2.6),
    "DN25": (33.7, 3.2),
    "DN32": (42.4, 3.2),
    "DN40": (48.3, 3.2),
    "DN50": (60.3, 3.6),
    "DN65": (76.1, 3.6),
    "DN80": (88.9, 4.0),
    "DN100": (114.3, 4.5),
}


# ──────────────────────────────────────────────
# Socket Head Cap Screws (ISO 4762 / DIN 912)
# ──────────────────────────────────────────────

ISO_SHCS: dict[str, dict] = {
    "M2":   {"shaft_diam": 2.0,  "head_diam": 3.8,  "head_height": 2.0,  "socket_size": 1.5,  "socket_depth": 1.0},
    "M2.5": {"shaft_diam": 2.5,  "head_diam": 4.5,  "head_height": 2.5,  "socket_size": 2.0,  "socket_depth": 1.1},
    "M3":   {"shaft_diam": 3.0,  "head_diam": 5.5,  "head_height": 3.0,  "socket_size": 2.5,  "socket_depth": 1.3},
    "M4":   {"shaft_diam": 4.0,  "head_diam": 7.0,  "head_height": 4.0,  "socket_size": 3.0,  "socket_depth": 2.0},
    "M5":   {"shaft_diam": 5.0,  "head_diam": 8.5,  "head_height": 5.0,  "socket_size": 4.0,  "socket_depth": 2.5},
    "M6":   {"shaft_diam": 6.0,  "head_diam": 10.0, "head_height": 6.0,  "socket_size": 5.0,  "socket_depth": 3.0},
    "M8":   {"shaft_diam": 8.0,  "head_diam": 13.0, "head_height": 8.0,  "socket_size": 6.0,  "socket_depth": 4.0},
    "M10":  {"shaft_diam": 10.0, "head_diam": 16.0, "head_height": 10.0, "socket_size": 8.0,  "socket_depth": 5.0},
    "M12":  {"shaft_diam": 12.0, "head_diam": 18.0, "head_height": 12.0, "socket_size": 10.0, "socket_depth": 6.0},
    "M14":  {"shaft_diam": 14.0, "head_diam": 21.0, "head_height": 14.0, "socket_size": 12.0, "socket_depth": 7.0},
    "M16":  {"shaft_diam": 16.0, "head_diam": 24.0, "head_height": 16.0, "socket_size": 14.0, "socket_depth": 8.0},
    "M20":  {"shaft_diam": 20.0, "head_diam": 30.0, "head_height": 20.0, "socket_size": 17.0, "socket_depth": 10.0},
    "M24":  {"shaft_diam": 24.0, "head_diam": 36.0, "head_height": 24.0, "socket_size": 19.0, "socket_depth": 12.0},
}

# ──────────────────────────────────────────────
# Countersunk Screws (ISO 10642)
# head_angle is always 90 degrees for metric
# ──────────────────────────────────────────────

ISO_COUNTERSUNK: dict[str, dict] = {
    "M3":   {"shaft_diam": 3.0,  "head_diam": 6.72,  "head_height": 1.86, "socket_size": 2.0},
    "M4":   {"shaft_diam": 4.0,  "head_diam": 8.96,  "head_height": 2.48, "socket_size": 2.5},
    "M5":   {"shaft_diam": 5.0,  "head_diam": 11.20, "head_height": 3.10, "socket_size": 3.0},
    "M6":   {"shaft_diam": 6.0,  "head_diam": 13.44, "head_height": 3.72, "socket_size": 4.0},
    "M8":   {"shaft_diam": 8.0,  "head_diam": 17.92, "head_height": 4.96, "socket_size": 5.0},
    "M10":  {"shaft_diam": 10.0, "head_diam": 22.40, "head_height": 6.20, "socket_size": 6.0},
    "M12":  {"shaft_diam": 12.0, "head_diam": 26.88, "head_height": 7.44, "socket_size": 8.0},
    "M16":  {"shaft_diam": 16.0, "head_diam": 33.60, "head_height": 8.80, "socket_size": 10.0},
    "M20":  {"shaft_diam": 20.0, "head_diam": 40.32, "head_height": 10.16, "socket_size": 12.0},
}

# ──────────────────────────────────────────────
# Flat Washers (ISO 7089 - normal series)
# ──────────────────────────────────────────────

ISO_WASHERS: dict[str, dict] = {
    "M2":   {"inner_diam": 2.2,  "outer_diam": 5.0,   "thickness": 0.3},
    "M2.5": {"inner_diam": 2.7,  "outer_diam": 6.0,   "thickness": 0.5},
    "M3":   {"inner_diam": 3.2,  "outer_diam": 7.0,   "thickness": 0.5},
    "M4":   {"inner_diam": 4.3,  "outer_diam": 9.0,   "thickness": 0.8},
    "M5":   {"inner_diam": 5.3,  "outer_diam": 10.0,  "thickness": 1.0},
    "M6":   {"inner_diam": 6.4,  "outer_diam": 12.0,  "thickness": 1.6},
    "M8":   {"inner_diam": 8.4,  "outer_diam": 16.0,  "thickness": 1.6},
    "M10":  {"inner_diam": 10.5, "outer_diam": 20.0,  "thickness": 2.0},
    "M12":  {"inner_diam": 13.0, "outer_diam": 24.0,  "thickness": 2.5},
    "M14":  {"inner_diam": 15.0, "outer_diam": 28.0,  "thickness": 2.5},
    "M16":  {"inner_diam": 17.0, "outer_diam": 30.0,  "thickness": 3.0},
    "M20":  {"inner_diam": 21.0, "outer_diam": 37.0,  "thickness": 3.0},
    "M24":  {"inner_diam": 25.0, "outer_diam": 44.0,  "thickness": 4.0},
}


def lookup_keyway(shaft_diam: float) -> tuple[float, float, float, float] | None:
    for (lo, hi), dims in KEYWAY_STANDARDS.items():
        if lo <= shaft_diam < hi:
            return dims
    return None


def nearest_gear_module(value: float) -> float:
    return min(ISO_GEAR_MODULES, key=lambda m: abs(m - value))


def lookup_bearing(series: str, bore: int) -> tuple[int, int] | None:
    s = BEARING_SERIES.get(series)
    if s:
        return s.get(bore)
    return None
