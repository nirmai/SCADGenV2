"""Validate LLM-generated .scad template files before registering them."""

from __future__ import annotations

import re

import yaml


_META_PATTERN = re.compile(
    r"//\s*SCADGEN_META_BEGIN\s*\n(.*?)//\s*SCADGEN_META_END",
    re.DOTALL,
)

_MODULE_PATTERN = re.compile(r"module\s+(\w+)\s*\(")

# Any OpenSCAD construct that yields geometry — used to reject empty bodies.
_GEOMETRY_PATTERN = re.compile(
    r"\b(cube|cylinder|sphere|polyhedron|circle|square|polygon|text|surface|"
    r"import|linear_extrude|rotate_extrude|hull|minkowski|offset|union|"
    r"difference|intersection|translate|rotate|scale|mirror|resize|color|"
    r"children)\s*\("
)


def validate_template(source: str) -> list[str]:
    """Validate a generated .scad template. Returns a list of error messages (empty = valid)."""
    errors: list[str] = []

    # 1. META block present
    match = _META_PATTERN.search(source)
    if not match:
        errors.append("Missing SCADGEN_META_BEGIN / SCADGEN_META_END block")
        return errors

    # 2. Parse YAML
    raw_yaml = match.group(1)
    cleaned_lines = []
    for line in raw_yaml.splitlines():
        stripped = line.lstrip()
        if stripped.startswith("//"):
            stripped = stripped[2:]
            if stripped.startswith(" "):
                stripped = stripped[1:]
        cleaned_lines.append(stripped)
    cleaned = "\n".join(cleaned_lines)

    try:
        meta = yaml.safe_load(cleaned)
    except yaml.YAMLError as e:
        errors.append(f"YAML parse error: {e}")
        return errors

    if not isinstance(meta, dict):
        errors.append("META block is not a YAML mapping")
        return errors

    # 3. Required fields
    for field in ("template_id", "module_name", "params"):
        if field not in meta:
            errors.append(f"Missing required field: {field}")

    if errors:
        return errors

    template_id = meta["template_id"]
    module_name = meta["module_name"]

    # 4. Module definition exists
    module_match = _MODULE_PATTERN.search(source)
    if not module_match:
        errors.append(f"No module definition found (expected 'module {module_name}(...)')")
    elif module_match.group(1) != module_name:
        errors.append(
            f"Module name mismatch: YAML says '{module_name}', "
            f"code defines '{module_match.group(1)}'"
        )

    # 4b. Body must actually produce geometry (cheap pre-filter before render)
    body = source[match.end():]  # everything after SCADGEN_META_END
    if not _GEOMETRY_PATTERN.search(body):
        errors.append(
            "Module body produces no geometry (no primitive/transform call found)"
        )

    # 5. Params consistency
    yaml_params = {p["name"] for p in meta.get("params", [])}
    if module_match:
        # Extract param names from module signature
        sig_start = module_match.end() - 1  # position of '('
        depth = 0
        sig_end = sig_start
        for i in range(sig_start, len(source)):
            if source[i] == "(":
                depth += 1
            elif source[i] == ")":
                depth -= 1
                if depth == 0:
                    sig_end = i
                    break
        signature = source[sig_start + 1 : sig_end]
        sig_params = set(re.findall(r"(\w+)\s*=", signature))
        missing_in_sig = yaml_params - sig_params
        if missing_in_sig:
            errors.append(
                f"Params in YAML but not in module signature: {', '.join(sorted(missing_in_sig))}"
            )

    # 6. Param defaults within declared ranges
    for p in meta.get("params", []):
        default = p.get("default")
        pmin = p.get("min")
        pmax = p.get("max")
        if default is not None and pmin is not None:
            try:
                if float(default) < float(pmin):
                    errors.append(
                        f"Param '{p['name']}': default {default} below min {pmin}"
                    )
            except (ValueError, TypeError):
                pass
        if default is not None and pmax is not None:
            try:
                if float(default) > float(pmax):
                    errors.append(
                        f"Param '{p['name']}': default {default} above max {pmax}"
                    )
            except (ValueError, TypeError):
                pass

    # 7. Connector expressions reference declared params
    for c in meta.get("connectors", []):
        for component in c.get("origin", []):
            if isinstance(component, str):
                idents = set(re.findall(r"[a-zA-Z_]\w*", component))
                unknown = idents - yaml_params
                if unknown:
                    errors.append(
                        f"Connector '{c['name']}' origin references unknown param(s): "
                        f"{', '.join(sorted(unknown))}"
                    )

    # 8. Balanced braces
    open_braces = source.count("{")
    close_braces = source.count("}")
    if open_braces != close_braces:
        errors.append(
            f"Unbalanced braces: {open_braces} opening vs {close_braces} closing"
        )

    open_parens = source.count("(")
    close_parens = source.count(")")
    if open_parens != close_parens:
        errors.append(
            f"Unbalanced parentheses: {open_parens} opening vs {close_parens} closing"
        )

    return errors
