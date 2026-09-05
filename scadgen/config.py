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
    template_dirs: list[str] = field(default_factory=list)
    output_dir: str = ""
    openscad_path: str = ""

    @classmethod
    def load(cls) -> Config:
        pkg_templates = str(Path(__file__).parent / "templates")

        config = cls(
            provider=os.environ.get("SCADGEN_PROVIDER", "auto"),
            ollama_url=os.environ.get("OLLAMA_URL", "http://localhost:11434"),
            ollama_model=os.environ.get("OLLAMA_MODEL", "mistral"),
            openai_model=os.environ.get("OPENAI_MODEL", "gpt-4o-mini"),
            openai_api_key=os.environ.get("OPENAI_API_KEY", ""),
            template_dirs=[pkg_templates],
            output_dir=os.environ.get("SCADGEN_OUTPUT_DIR", ""),
            openscad_path=os.environ.get("OPENSCAD_PATH", ""),
        )

        extra_dirs = os.environ.get("SCADGEN_TEMPLATE_DIRS", "")
        if extra_dirs:
            config.template_dirs.extend(extra_dirs.split(os.pathsep))

        return config
