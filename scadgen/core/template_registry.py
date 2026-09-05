from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml

from scadgen.exceptions import TemplateNotFoundError, TemplateParseError
from scadgen.types import ConnectorDef, ConstraintDef, ParameterDef, Template

_META_PATTERN = re.compile(
    r"//\s*SCADGEN_META_BEGIN\s*\n(.*?)//\s*SCADGEN_META_END",
    re.DOTALL,
)


class TemplateRegistry:
    def __init__(self, template_dirs: list[str]):
        self._templates: dict[str, Template] = {}
        self._alias_map: dict[str, str] = {}
        for d in template_dirs:
            self._scan_directory(Path(d))

    def get(self, template_id: str) -> Template:
        key = template_id.lower().strip()
        if key in self._templates:
            return self._templates[key]
        if key in self._alias_map:
            return self._templates[self._alias_map[key]]
        raise TemplateNotFoundError(f"Template not found: {template_id}")

    def list_templates(self, category: str = "") -> list[Template]:
        templates = list(self._templates.values())
        if category:
            cat = category.lower()
            templates = [t for t in templates if cat in t.category.lower()]
        return sorted(templates, key=lambda t: t.template_id)

    def all_ids(self) -> list[str]:
        return sorted(self._templates.keys())

    def _scan_directory(self, directory: Path) -> None:
        if not directory.is_dir():
            return
        for scad_file in sorted(directory.glob("*.scad")):
            try:
                template = self._parse_template(scad_file)
                self._templates[template.template_id] = template
                for alias in template.aliases:
                    self._alias_map[alias.lower()] = template.template_id
            except TemplateParseError:
                pass

    def _parse_template(self, path: Path) -> Template:
        source = path.read_text(encoding="utf-8")
        match = _META_PATTERN.search(source)
        if not match:
            raise TemplateParseError(f"No SCADGEN_META block in {path.name}")

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
            raise TemplateParseError(f"Invalid YAML in {path.name}: {e}") from e

        if not isinstance(meta, dict):
            raise TemplateParseError(f"Meta block in {path.name} is not a mapping")

        params = []
        for p in meta.get("params", []):
            params.append(
                ParameterDef(
                    name=p["name"],
                    type=p.get("type", "float"),
                    default=p.get("default"),
                    min=p.get("min"),
                    max=p.get("max"),
                    unit=p.get("unit"),
                    description=p.get("description", ""),
                )
            )

        connectors = []
        for c in meta.get("connectors", []):
            connectors.append(
                ConnectorDef(
                    name=c["name"],
                    type=c.get("type", "axial"),
                    origin=c.get("origin", [0, 0, 0]),
                    direction=c.get("direction", [0, 0, 1]),
                    diameter_ref=c.get("diameter_ref", ""),
                )
            )

        derived = {}
        for entry in meta.get("derived", []):
            if isinstance(entry, dict):
                derived.update(entry)

        constraints = []
        for c in meta.get("constraints", []):
            constraints.append(
                ConstraintDef(
                    check=c["check"],
                    message=c.get("message", ""),
                    severity=c.get("severity", "error"),
                )
            )

        return Template(
            template_id=meta.get("template_id", path.stem),
            file_path=str(path),
            module_name=meta.get("module_name", meta.get("template_id", path.stem)),
            description=meta.get("description", ""),
            category=meta.get("category", ""),
            tags=meta.get("tags", []),
            parameters=params,
            connectors=connectors,
            derived_expressions=derived,
            source_code=source,
            aliases=meta.get("aliases", []),
            keywords=meta.get("keywords", []),
            constraints=constraints,
        )
