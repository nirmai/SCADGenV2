from __future__ import annotations

import re
from typing import Any

from scadgen.config import Config
from scadgen.core.template_registry import TemplateRegistry
from scadgen.exceptions import ExtractionError
from scadgen.knowledge.resolver import EngineeringResolver
from scadgen.nlp.prompts import build_extraction_prompt
from scadgen.nlp.json_utils import parse_json_response
from scadgen.nlp.providers import LLMProvider, create_provider
from scadgen.types import ExtractionResult, ResolvedInput, Template


class ParameterExtractor:
    def __init__(
        self,
        registry: TemplateRegistry,
        resolver: EngineeringResolver,
        config: Config,
    ):
        self.registry = registry
        self.resolver = resolver
        self.config = config
        self._provider: LLMProvider | None = None

    @property
    def provider(self) -> LLMProvider:
        if self._provider is None:
            self._provider = create_provider(self.config)
        return self._provider

    def extract(self, description: str) -> ExtractionResult:
        resolved = self.resolver.resolve(description)
        candidates = self._pre_classify(description, resolved)

        if resolved.confidence >= 0.9 and resolved.suggested_template:
            template = self.registry.get(resolved.suggested_template)
            all_covered = all(
                p.name in resolved.resolved_params
                for p in template.parameters
                if p.default is None
            )
            if all_covered:
                return ExtractionResult(
                    template=template,
                    parameters=resolved.resolved_params,
                    confidence=resolved.confidence,
                    notes="Resolved entirely from engineering standards (no LLM call)",
                    resolved_standards=resolved,
                )

        prompt = build_extraction_prompt(candidates, resolved, description)
        response = self.provider.chat(prompt)
        parsed = self._parse_response(response)

        template_id = parsed.get("template_id", "")
        template = self._resolve_template(template_id, candidates)
        raw_params = parsed.get("parameters", {})
        merged = {**resolved.resolved_params, **raw_params}

        return ExtractionResult(
            template=template,
            parameters=merged,
            confidence=parsed.get("confidence", 0.5),
            notes=parsed.get("notes", ""),
            resolved_standards=resolved,
        )

    def _pre_classify(
        self, description: str, resolved: ResolvedInput
    ) -> list[Template]:
        tokens = set(re.findall(r"\b\w+\b", description.lower()))
        scores: dict[str, float] = {}

        for tid in self.registry.all_ids():
            tmpl = self.registry.get(tid)
            score = 0.0
            for alias in tmpl.aliases:
                if alias.lower() in description.lower():
                    score += 3.0
            for kw in tmpl.keywords:
                if kw.lower() in tokens:
                    score += 1.0
            for tag in tmpl.tags:
                if tag.lower() in tokens:
                    score += 0.5
            scores[tid] = score

        if resolved.suggested_template and resolved.suggested_template in scores:
            scores[resolved.suggested_template] += 5.0

        ranked = sorted(scores.items(), key=lambda x: -x[1])
        top_score = ranked[0][1] if ranked else 0
        if top_score == 0:
            return [self.registry.get(tid) for tid, _ in ranked[:5]]

        threshold = max(top_score * 0.3, 1.0)
        candidates = [
            self.registry.get(tid) for tid, s in ranked if s >= threshold
        ]
        return candidates[:5]

    def _resolve_template(
        self, template_id: str, candidates: list[Template]
    ) -> Template:
        try:
            return self.registry.get(template_id)
        except Exception:
            pass
        for c in candidates:
            if template_id.lower() in c.template_id.lower():
                return c
            if any(template_id.lower() in a.lower() for a in c.aliases):
                return c
        if candidates:
            return candidates[0]
        raise ExtractionError(f"Cannot resolve template: {template_id}")

    def _parse_response(self, text: str) -> dict[str, Any]:
        try:
            return parse_json_response(text)
        except ValueError as e:
            raise ExtractionError(str(e)) from e
