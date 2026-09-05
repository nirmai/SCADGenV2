from __future__ import annotations

from scadgen.types import ResolvedInput, Template


def build_extraction_prompt(
    candidates: list[Template],
    resolved: ResolvedInput,
    user_input: str,
) -> str:
    sections = [
        "You are a mechanical engineering CAD assistant. "
        "Given a part description, select the correct template and extract parameter values.\n"
    ]

    sections.append("## Available Templates\n")
    for tmpl in candidates:
        sections.append(f"### {tmpl.template_id}")
        sections.append(f"Description: {tmpl.description}")
        sections.append("Parameters:")
        for p in tmpl.parameters:
            range_str = ""
            if p.min is not None and p.max is not None:
                range_str = f", range=[{p.min}, {p.max}]"
            unit_str = f", {p.unit}" if p.unit else ""
            sections.append(
                f"  {p.name} ({p.type}, default={p.default}{range_str}{unit_str}): "
                f"{p.description}"
            )
        sections.append("")

    if resolved.standards_matched:
        sections.append("## Engineering Context (from standards resolver)")
        sections.append(f"Standards matched: {', '.join(resolved.standards_matched)}")
        if resolved.resolved_params:
            params_str = ", ".join(
                f"{k}={v}" for k, v in resolved.resolved_params.items()
            )
            sections.append(f"Pre-resolved values: {params_str}")
        sections.append("")

    sections.append(f'## User Request\n"{user_input}"\n')

    sections.append(
        "## Instructions\n"
        "Return ONLY a JSON object with these fields:\n"
        "{\n"
        '  "template_id": "<exact template_id from the list above>",\n'
        '  "parameters": {"param_name": value, ...},\n'
        '  "confidence": 0.0 to 1.0,\n'
        '  "notes": "brief explanation of any inferences made"\n'
        "}\n\n"
        "Rules:\n"
        "- Use pre-resolved values when available\n"
        "- Infer reasonable values for unspecified parameters based on engineering context\n"
        "- Use standard engineering defaults when no information is given\n"
        "- Return numeric values as numbers, not strings\n"
        "- Return ONLY the JSON object, no other text"
    )

    return "\n".join(sections)
