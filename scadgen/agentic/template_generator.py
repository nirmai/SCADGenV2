"""Step 3: Generate missing .scad templates via LLM."""

from __future__ import annotations

import re
from pathlib import Path
from typing import TYPE_CHECKING

from scadgen.agentic.prompts import build_repair_prompt, build_template_generation_prompt
from scadgen.agentic.template_validator import validate_template
from scadgen.agentic.types import AssemblyPlan, PartSpec
from scadgen.core.template_registry import TemplateRegistry
from scadgen.exceptions import TemplateGenerationError
from scadgen.nlp.providers import LLMProvider

if TYPE_CHECKING:
    from scadgen.types import Template


class TemplateGenerator:
    def __init__(
        self,
        provider: LLMProvider,
        registry: TemplateRegistry,
        template_dir: Path,
        max_retries: int = 3,
    ):
        self._provider = provider
        self._registry = registry
        self._template_dir = template_dir
        self._max_retries = max_retries

    def generate_missing(
        self,
        plan: AssemblyPlan,
    ) -> list[str]:
        """Generate all missing templates. Returns list of created file paths.

        Failed templates are collected in self.failures; successfully generated
        templates are removed from plan.templates_needed.
        """
        created: list[str] = []
        self.failures: list[tuple[str, str]] = []
        still_needed: list[str] = []

        for tid in plan.templates_needed:
            part = self._find_part(plan, tid)
            if part is None:
                continue

            try:
                path = self._generate_one(part, plan)
                created.append(str(path))
            except TemplateGenerationError as e:
                self.failures.append((tid, str(e)))
                still_needed.append(tid)

        plan.templates_needed = still_needed
        return created

    def _generate_one(self, part: PartSpec, plan: AssemblyPlan) -> Path:
        """Generate a single template with validation + retry."""
        examples = self._select_examples(part)
        system, user = build_template_generation_prompt(part, plan, examples)

        code = self._provider.chat(user, system=system, max_tokens=8192)
        code = self._strip_fences(code)

        last_errors: list[str] = []
        for attempt in range(self._max_retries):
            errors = validate_template(code)
            if not errors:
                return self._save_and_register(part.suggested_template, code)

            last_errors = errors

            if attempt < self._max_retries - 1:
                repair_system, repair_user = build_repair_prompt(code, errors)
                code = self._provider.chat(repair_user, system=repair_system, max_tokens=8192)
                code = self._strip_fences(code)

        raise TemplateGenerationError(
            part.suggested_template, self._max_retries, last_errors
        )

    def _save_and_register(self, template_id: str, code: str) -> Path:
        """Write .scad file and register in the template registry."""
        self._template_dir.mkdir(parents=True, exist_ok=True)
        path = self._template_dir / f"{template_id}.scad"
        path.write_text(code, encoding="utf-8")
        self._registry.register_template(path)
        return path

    def _select_examples(self, part: PartSpec) -> list[Template]:
        """Pick 2 example templates most relevant to the part."""
        all_templates = self._registry.list_templates()
        if not all_templates:
            return []

        desc_words = set(re.findall(r"\b\w+\b", part.description.lower()))
        tmpl_words = set(
            re.findall(r"\b\w+\b", part.suggested_template.replace("_", " ").lower())
        )
        search_words = desc_words | tmpl_words

        scores: dict[str, float] = {}
        for t in all_templates:
            score = 0.0
            if t.category and any(
                w in t.category.lower() for w in search_words
            ):
                score += 5.0
            for kw in t.keywords:
                if kw.lower() in search_words:
                    score += 1.0
            if t.connectors:
                score += 2.0
            scores[t.template_id] = score

        ranked = sorted(scores.items(), key=lambda x: -x[1])

        examples = []
        if ranked:
            examples.append(self._registry.get(ranked[0][0]))

        # Add a simple template as format baseline
        for simple_id in ("cylinder", "cone", "bushing", "cube"):
            try:
                t = self._registry.get(simple_id)
                if not examples or t.template_id != examples[0].template_id:
                    examples.append(t)
                    break
            except Exception:
                pass

        return examples[:2]

    def _find_part(self, plan: AssemblyPlan, template_id: str) -> PartSpec | None:
        for p in plan.parts:
            if p.suggested_template == template_id:
                return p
        return None

    @staticmethod
    def _strip_fences(text: str) -> str:
        """Remove markdown fences and any prose the LLM wrapped around the file.

        The real template always starts at `// SCADGEN_META_BEGIN`, so trim
        everything before it and any trailing fence after the module.
        """
        text = text.strip()
        text = re.sub(r"^```(?:scad|openscad)?\s*\n?", "", text)
        text = re.sub(r"\n?```\s*$", "", text)

        # Drop any preamble prose before the metadata block.
        begin = text.find("// SCADGEN_META_BEGIN")
        if begin > 0:
            text = text[begin:]

        # Drop a trailing fence or trailing prose after the last closing brace.
        text = re.sub(r"\n?```[\s\S]*$", "", text)

        return text.strip()
