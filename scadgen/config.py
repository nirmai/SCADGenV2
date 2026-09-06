from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Config:
    provider: str = "auto"
    ollama_url: str = "http://localhost:11434"
    ollama_model: str = "mistral"
    openai_model: str = "gpt-4o-mini"
    openai_api_key: str = ""
    anthropic_model: str = "claude-sonnet-5"
    anthropic_api_key: str = ""
    template_dirs: list[str] = field(default_factory=list)
    generated_templates_dir: str = ""
    output_dir: str = ""
    openscad_path: str = ""

    @classmethod
    def load(cls) -> Config:
        pkg_templates = str(Path(__file__).parent / "templates")
        default_generated_dir = str(Path(__file__).parent.parent / "generated_templates")

        config = cls(
            provider=os.environ.get("SCADGEN_PROVIDER", "auto"),
            ollama_url=os.environ.get("OLLAMA_URL", "http://localhost:11434"),
            ollama_model=os.environ.get("OLLAMA_MODEL", "mistral"),
            openai_model=os.environ.get("OPENAI_MODEL", "gpt-4o-mini"),
            openai_api_key=os.environ.get("OPENAI_API_KEY", ""),
            anthropic_model=os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-5"),
            anthropic_api_key=os.environ.get("ANTHROPIC_API_KEY", ""),
            template_dirs=[pkg_templates],
            generated_templates_dir=os.environ.get(
                "SCADGEN_GENERATED_DIR", default_generated_dir
            ),
            output_dir=os.environ.get("SCADGEN_OUTPUT_DIR", ""),
            openscad_path=os.environ.get("OPENSCAD_PATH", ""),
        )

        extra_dirs = os.environ.get("SCADGEN_TEMPLATE_DIRS", "")
        if extra_dirs:
            config.template_dirs.extend(extra_dirs.split(os.pathsep))

        # Generated templates persist across runs in their own cache dir,
        # always scanned last so curated templates take precedence on any
        # id collision (see TemplateRegistry._scan_directory).
        config.template_dirs.append(config.generated_templates_dir)

        return config
