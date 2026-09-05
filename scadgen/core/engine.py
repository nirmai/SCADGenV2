from __future__ import annotations

from pathlib import Path
from typing import Any

from scadgen.config import Config
from scadgen.core.renderer import SCADRenderer
from scadgen.core.template_registry import TemplateRegistry
from scadgen.exceptions import SCADGenError
from scadgen.knowledge.resolver import EngineeringResolver
from scadgen.types import GenerationResult


class SCADEngine:
    def __init__(self, provider: str = "auto", template_dirs: list[str] | None = None):
        self.config = Config.load()
        if provider != "auto":
            self.config.provider = provider
        if template_dirs:
            self.config.template_dirs = template_dirs

        self.registry = TemplateRegistry(self.config.template_dirs)
        self.renderer = SCADRenderer()
        self.resolver = EngineeringResolver()
        self._extractor = None

    @property
    def extractor(self):
        if self._extractor is None:
            from scadgen.nlp.extractor import ParameterExtractor

            self._extractor = ParameterExtractor(
                registry=self.registry,
                resolver=self.resolver,
                config=self.config,
            )
        return self._extractor

    def generate(
        self,
        description: str = "",
        template_id: str = "",
        params: dict[str, Any] | None = None,
        output_path: str = "",
    ) -> GenerationResult:
        params = params or {}

        if description:
            extraction = self.extractor.extract(description)
            template = extraction.template
            merged = {**extraction.parameters, **params}
        elif template_id:
            template = self.registry.get(template_id)
            merged = params
        else:
            raise SCADGenError("Provide either 'description' or 'template_id'")

        validated = template.validate_params(merged)
        final_params = template.apply_defaults(validated)
        scad_code = self.renderer.render(template, final_params)
        derived = template.compute_derived(final_params)

        warnings: list[str] = []
        out_path = ""
        if output_path:
            out = Path(output_path)
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(scad_code, encoding="utf-8")
            out_path = str(out)

        return GenerationResult(
            scad_code=scad_code,
            output_path=out_path,
            template=template,
            parameters=final_params,
            derived_values=derived,
            warnings=warnings,
        )
