"""Step 2: Check which templates exist and which need to be generated."""

from __future__ import annotations

import re

from scadgen.agentic.types import AssemblyPlan
from scadgen.core.template_registry import TemplateRegistry

_PRIMITIVES = {"cube", "cylinder", "sphere", "cone", "torus"}


class TemplateInventory:
    def __init__(self, registry: TemplateRegistry):
        self._registry = registry

    def check(self, plan: AssemblyPlan) -> AssemblyPlan:
        """Classify each part's template as found or needed.

        Custom parts (flagged by the decomposer) are forced to generation
        unless they exactly match a non-primitive catalog template — this
        keeps complex parts from being fuzzy-matched down to a bare primitive.
        Otherwise, exact match then fuzzy match, else mark for generation.
        Mutates and returns the same plan object.
        """
        found: list[str] = []
        needed: list[str] = []

        for part in plan.parts:
            tid = part.suggested_template

            # Complex parts must be generated, not collapsed onto a primitive.
            if part.custom:
                resolved = self._resolve_id(tid)
                if resolved is not None and resolved not in _PRIMITIVES:
                    part.suggested_template = resolved
                    if resolved not in found:
                        found.append(resolved)
                else:
                    gen_id = self._dedupe_generated_id(tid, part.part_id)
                    part.suggested_template = gen_id
                    if gen_id not in needed:
                        needed.append(gen_id)
                continue

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

    def _resolve_id(self, tid: str) -> str | None:
        """Return the canonical template_id if `tid` matches one, else None."""
        try:
            return self._registry.get(tid).template_id
        except Exception:
            return None

    def _dedupe_generated_id(self, tid: str, part_id: str) -> str:
        """Pick a template id to generate under, avoiding primitive collisions."""
        if tid and tid not in _PRIMITIVES:
            return tid
        base = part_id if part_id and part_id not in _PRIMITIVES else f"{tid}_custom"
        return base

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
