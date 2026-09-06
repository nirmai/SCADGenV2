"""Prompt templates for each stage of the agentic assembly pipeline."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from scadgen.agentic.types import AssemblyPlan, PartSpec
    from scadgen.types import Template


def build_decomposition_prompt(
    description: str,
    templates: list[Template],
    has_image: bool = False,
) -> tuple[str, str]:
    """Build system + user prompt for the decomposition stage.

    Returns (system_prompt, user_prompt).
    """
    system = (
        "You are a mechanical CAD assembly planner. Given a description of an "
        "object, decompose it into individual parts that can be manufactured "
        "separately and assembled together. Each part should map to a parametric "
        "OpenSCAD template — either an existing one from the catalog, or a new "
        "one you propose."
    )
    if has_image:
        system += (
            " A reference image is provided. Study it carefully and make the "
            "assembly match what you see — the parts present, their shapes, "
            "their relative sizes, their vertical stacking order, and colors."
        )

    catalog = _build_template_catalog(templates)

    image_note = ""
    if has_image:
        image_note = (
            "\n## Reference Image\n"
            "A reference image is attached. Base the decomposition on it: "
            "identify each distinct part you see, estimate its proportions, "
            "and reproduce the stacking order and colors from the image.\n"
        )

    user = f"""{catalog}
{image_note}
## User Request
"{description}"

## Instructions
Decompose this object into individual parts. For each part:
- Choose an existing template from the catalog if one fits
- Otherwise INVENT a specific, descriptive new template_id (lowercase,
  underscored) that names the actual part — e.g. "cage_body", "bird_perch",
  "lamp_shade". This new template will be generated for you.
- NEVER use a vague placeholder as a template name: no "primitive",
  "part", "shape", "custom", "generic", "not_defined", "tbd", or similar.
  Every suggested_template must be either a real catalog id or a concrete
  new part name.
- Set reasonable parameter values based on the description
- Assign a functional role

Then define how the parts connect using their connector names.

## How connectors work (READ CAREFULLY)
Each connector has a position on the part and a direction facing outward.
To STACK part B on top of part A, connect A's TOP connector to B's BOTTOM
connector with type "mate":
  A.top_face -> B.bottom_face  (mate)
This places B's bottom exactly on A's top. Then stack C on B the same way:
  B.top_face -> C.bottom_face  (mate)

Rules for choosing connectors:
- To stack upward, always go TOP of the lower part -> BOTTOM of the upper part
- Use face connectors (top_face, bottom_face) for stacking, NOT center_axis
  (center_axis is the middle of a part — mating two centers overlaps them)
- Never attach something to a base's bottom_face unless it truly hangs below
- EVERY non-root part MUST have at least one connection, or it will be
  discarded. A 4-part assembly needs at least 3 connections forming a chain
  from the root outward.

Return ONLY a JSON object with this exact structure:
{{
  "assembly_name": "short_name",
  "root_part": "part_id_of_base_or_main_part",
  "parts": [
    {{
      "part_id": "unique_name",
      "description": "what this part is and does",
      "suggested_template": "template_id",
      "suggested_params": {{"param": value}},
      "role": "structural|decorative|mechanical|connector"
    }}
  ],
  "connections": [
    {{
      "from_part": "part_id",
      "from_connector": "connector_name",
      "to_part": "part_id",
      "to_connector": "connector_name",
      "type": "mate|coaxial",
      "offset": 0
    }}
  ],
  "colors": {{
    "part_id": "ColorName"
  }}
}}

Rules:
- "mate" means surfaces face each other (directions oppose)
- "coaxial" means axes align (directions match)
- The root_part is the part that rests on the ground / holds the assembly
  up (e.g. a base or block), NOT a part that hangs off another
- PARAMETERS: every value in suggested_params MUST fall within the
  [min..max] range shown for that param in the catalog. Never exceed a max
  or go below a min.
- CONSTRAINTS: honor every "must satisfy" expression listed under a
  template. If it says "bottom_diam > top_diam", make bottom_diam larger.
  If it says "curve_radius > stem_diam * 2", size them accordingly.
- When unsure of a good value, omit the param and the template default is used
- Use sensible engineering dimensions in mm
- COLORS: give all parts of a single object the SAME color unless the
  description calls for different ones. Every part_id in "colors" MUST map
  to a real OpenSCAD color name (Silver, Goldenrod, DarkGray, White, Red,
  etc.) — never "none", "not_applicable", or an empty string.
- Return ONLY the JSON, no other text"""

    return system, user


def build_template_generation_prompt(
    part: PartSpec,
    plan: AssemblyPlan,
    examples: list[Template],
) -> tuple[str, str]:
    """Build prompt for generating a missing .scad template.

    Returns (system_prompt, user_prompt).
    """
    system = (
        "You are an expert OpenSCAD programmer and mechanical engineer. "
        "Generate complete, valid OpenSCAD template files for the SCADgen "
        "parametric CAD system."
    )

    # Identify which connectors this part needs from the connection plan
    required_connectors = _extract_required_connectors(part, plan)

    example_blocks = []
    for tmpl in examples:
        example_blocks.append(
            f"### Example: {tmpl.template_id}\n```\n{tmpl.source_code.rstrip()}\n```"
        )
    examples_text = "\n\n".join(example_blocks)

    user = f"""## Task
Generate a complete OpenSCAD template file for the SCADgen system.

Template ID: {part.suggested_template}
Description: {part.description}
Role in assembly: {part.role}

{required_connectors}

## Example Templates (use this exact format)

{examples_text}

## SCADGEN_META Format Rules
1. YAML block between `// SCADGEN_META_BEGIN` and `// SCADGEN_META_END`
2. Every YAML line prefixed with `// ` (two slashes, one space)
3. Required fields: schema_version (1), template_id, module_name, description,
   category, tags, aliases, keywords, params, connectors
4. Each param: name, type (float/int/bool), default, min, max, unit, description
5. Connectors: name, type (axial/planar), origin (can use param name expressions),
   direction ([x,y,z] unit vector), optional diameter_ref
6. Add constraints where appropriate

## Connector Origin Expressions
Origins can reference parameter names. The assembly system evaluates them at build time.
Examples:
  origin: [0, 0, 0]                    # Fixed at origin
  origin: [0, 0, "height"]             # At top of part
  origin: [0, 0, "-shaft_len"]         # Below origin
  origin: ["diameter / 2", 0, "height / 2"]  # Side midpoint

Direction is always a fixed unit vector like [0, 0, 1] or [0, 0, -1].
String expressions ONLY go in origin fields, never in direction.

## OpenSCAD Rules
- Module name must match module_name in metadata
- All parameters must have defaults matching the metadata defaults
- Set `$fn = fn;` at the top of the module (fn is always a param)
- Use difference() for holes, union() for joining
- Available primitives: cube, cylinder, sphere, linear_extrude, rotate_extrude, hull
- Available transforms: translate, rotate, scale, mirror
- All dimensions in mm
- Make the geometry look professional — use chamfers, fillets, and detail features

## Suggested Parameters
{_format_suggested_params(part)}

## Output
Return ONLY the complete .scad file content. No markdown fences.
No explanation before or after. Start directly with `// SCADGEN_META_BEGIN`."""

    return system, user


def build_repair_prompt(
    original_code: str,
    errors: list[str],
) -> tuple[str, str]:
    """Build prompt for repairing a generated template that failed validation.

    Returns (system_prompt, user_prompt).
    """
    system = (
        "You are an expert OpenSCAD programmer fixing a template file that "
        "has validation errors."
    )

    error_list = "\n".join(f"  - {e}" for e in errors)

    user = f"""The following OpenSCAD template has validation errors.
Fix ALL errors and return the corrected complete .scad file.

## Errors Found
{error_list}

## Original Template
```
{original_code}
```

## Rules
- Fix every listed error
- Keep the same template_id and overall structure
- Return ONLY the complete corrected .scad file content
- No markdown fences. Start directly with `// SCADGEN_META_BEGIN`."""

    return system, user


def build_connection_refinement_prompt(
    plan: AssemblyPlan,
    mismatches: list[dict],
    template_connectors: dict[str, list[dict]],
) -> tuple[str, str]:
    """Build prompt for fixing connector name mismatches.

    Returns (system_prompt, user_prompt).
    """
    system = (
        "You are a mechanical CAD assembly planner fixing connector references "
        "in an assembly plan."
    )

    connector_info = []
    for part_id, connectors in template_connectors.items():
        conn_list = ", ".join(
            f"{c['name']} ({c['type']}, direction={c['direction']})"
            for c in connectors
        )
        connector_info.append(f"  Part '{part_id}': [{conn_list}]")
    connectors_text = "\n".join(connector_info)

    mismatch_lines = []
    for m in mismatches:
        mismatch_lines.append(
            f"  Connection {m['from_part']}.{m['from_connector']} → "
            f"{m['to_part']}.{m['to_connector']}: {m['error']}"
        )
    mismatch_text = "\n".join(mismatch_lines)

    user = f"""## Available Connectors Per Part
{connectors_text}

## Connections With Errors
{mismatch_text}

## Current Full Connection List
{_format_connections(plan)}

## Instructions
Fix the connector names so every connection references an actual connector
on the corresponding part. Keep connection types and offsets unchanged unless
they need fixing too.

Return ONLY a JSON object:
{{
  "connections": [
    {{
      "from_part": "part_id",
      "from_connector": "connector_name",
      "to_part": "part_id",
      "to_connector": "connector_name",
      "type": "mate|coaxial",
      "offset": 0
    }}
  ]
}}"""

    return system, user


# ── Helpers ──────────────────────────────────────────────────────────────


def _build_template_catalog(templates: list[Template]) -> str:
    """Compressed template catalog for the decomposition prompt.

    Shows each param with its default and [min..max] range plus the
    template's constraints, so the LLM can choose valid parameters.
    """
    by_category: dict[str, list[Template]] = {}
    for t in templates:
        cat = t.category or "other"
        by_category.setdefault(cat, []).append(t)

    sections = ["## Available Template Catalog"]
    for cat in sorted(by_category):
        sections.append(f"\n### {cat.title()}")
        for t in sorted(by_category[cat], key=lambda x: x.template_id):
            connectors = ", ".join(c.name for c in t.connectors) or "none"
            sections.append(
                f"- **{t.template_id}**: {t.description} [connectors: {connectors}]"
            )
            for p in t.parameters:
                if p.name == "fn":
                    continue
                rng = ""
                if p.min is not None and p.max is not None:
                    rng = f" [{_num(p.min)}..{_num(p.max)}]"
                sections.append(
                    f"    - {p.name}={_num(p.default)}{rng}"
                )
            for c in t.constraints:
                sections.append(f"    ! must satisfy: {c.check}")

    return "\n".join(sections)


def _num(v: object) -> str:
    """Format a numeric value compactly (drop trailing .0)."""
    if isinstance(v, float) and v.is_integer():
        return str(int(v))
    return str(v)


def _extract_required_connectors(part: PartSpec, plan: AssemblyPlan) -> str:
    """Identify which connectors this part needs from the connection plan."""
    needed = []
    for conn in plan.connections:
        if conn.from_part == part.part_id:
            needed.append(
                f"- {conn.from_connector}: connects to {conn.to_part}'s "
                f"{conn.to_connector} ({conn.type})"
            )
        elif conn.to_part == part.part_id:
            needed.append(
                f"- {conn.to_connector}: connects from {conn.from_part}'s "
                f"{conn.from_connector} ({conn.type})"
            )

    if needed:
        return "## Required Connectors (from assembly plan)\n" + "\n".join(needed)
    return "## Required Connectors\nDefine at least one connector for assembly use."


def _format_suggested_params(part: PartSpec) -> str:
    if not part.suggested_params:
        return "No specific parameters suggested — use reasonable engineering defaults."
    lines = []
    for k, v in part.suggested_params.items():
        lines.append(f"- {k}: {v}")
    return "\n".join(lines)


def _format_connections(plan: AssemblyPlan) -> str:
    lines = []
    for c in plan.connections:
        lines.append(
            f"  {c.from_part}.{c.from_connector} → "
            f"{c.to_part}.{c.to_connector} ({c.type}, offset={c.offset})"
        )
    return "\n".join(lines)
