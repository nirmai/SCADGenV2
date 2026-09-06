"""Step 2: Check which templates exist and which need to be generated."""

from __future__ import annotations

import re

from scadgen.agentic.types import AssemblyPlan
from scadgen.core.template_registry import TemplateRegistry


class TemplateInventory:
    def __init__(self, registry: TemplateRegistry):
        self._registry = registry

    def check(self, plan: AssemblyPlan) -> AssemblyPlan:
        """Classify each part's template as found or needed.

        Also attempts fuzzy matching when the exact template_id is not found.
        Mutates and returns the same plan object.
        """
        found: list[str] = []
        needed: list[str] = []

        for part in plan.parts:
            tid = part.suggested_template

            # Exact match (includes alias lookup)
            try:
                tmpl = self._registry.get(tid)
                part.suggested_template = tmpl.template_id
                if tmpl.template_id not in found:
                    found.append(tmpl.template_id)
                continue
            except Exception:
                pass

            # Fuzzy match: score all templates by keyword overlap
            best_id = self._fuzzy_match(part.description, tid)
            if best_id:
                part.suggested_template = best_id
                if best_id not in found:
                    found.append(best_id)
            else:
                if tid not in needed:
                    needed.append(tid)

        plan.templates_found = found
        plan.templates_needed = needed
        return plan

    def _fuzzy_match(self, description: str, suggested_id: str) -> str | None:
        """Try to find a matching template by keyword overlap."""
        tokens = set(re.findall(r"\b\w+\b", description.lower()))
        tokens.update(re.findall(r"\b\w+\b", suggested_id.replace("_", " ").lower()))

        best_score = 0.0
        best_id = None

        for tid in self._registry.all_ids():
            tmpl = self._registry.get(tid)
            score = 0.0
            for alias in tmpl.aliases:
                if alias.lower() in description.lower():
                    score += 5.0
            for kw in tmpl.keywords:
                if kw.lower() in tokens:
                    score += 1.0
            for tag in tmpl.tags:
                if tag.lower() in tokens:
                    score += 0.5
            if tid in suggested_id or suggested_id in tid:
                score += 3.0

            if score > best_score:
                best_score = score
                best_id = tid

        if best_score >= 3.0:
            return best_id
        return None
