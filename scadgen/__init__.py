"""SCADgen — AI-powered parametric OpenSCAD generator with engineering knowledge."""

from scadgen.core.engine import SCADEngine
from scadgen.types import GenerationResult, Template

__version__ = "0.1.0"


def generate(
    description: str = "",
    *,
    template: str = "",
    params: dict | None = None,
    output: str = "",
    provider: str = "auto",
) -> GenerationResult:
    engine = SCADEngine(provider=provider)
    return engine.generate(
        description=description,
        template_id=template,
        params=params or {},
        output_path=output,
    )


def list_templates(category: str = "") -> list[Template]:
    engine = SCADEngine()
    return engine.registry.list_templates(category=category)


def get_template(template_id: str) -> Template:
    engine = SCADEngine()
    return engine.registry.get(template_id)


__all__ = [
    "generate",
    "list_templates",
    "get_template",
    "SCADEngine",
    "GenerationResult",
    "Template",
]
