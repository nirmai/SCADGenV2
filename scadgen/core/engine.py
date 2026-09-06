from __future__ import annotations

from pathlib import Path
from typing import Any

from scadgen.config import Config
from scadgen.core.renderer import SCADRenderer
from scadgen.core.template_registry import TemplateRegistry
from scadgen.exceptions import ConstraintViolationError, SCADGenError
from scadgen.knowledge.constraints import harmonize_linked_params, validate_constraints
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
        self.resolver = EngineeringResolver(registry=self.registry)
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
        user_explicit = set(params.keys())

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

        final_params, link_messages = harmonize_linked_params(
            template, final_params, user_explicit,
        )

        warnings: list[str] = list(link_messages)
        errors, constraint_warnings = validate_constraints(template, final_params)
        if errors:
            raise ConstraintViolationError(errors)
        warnings.extend(constraint_warnings)

        scad_code = self.renderer.render(template, final_params)
        derived = template.compute_derived(final_params)

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
