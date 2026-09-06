from scadgen.agentic.types import AssemblyPlan, AssemblyResult, ConnectionSpec, PartSpec

__all__ = [
    "AssemblyPlan",
    "AssemblyResult",
    "ConnectionSpec",
    "PartSpec",
    "assemble",
]


def assemble(
    description: str,
    engine: "SCADEngine",  # noqa: F821
    output_path: str = "",
    output_dir: str = "output",
    max_retries: int = 3,
    dry_run: bool = False,
    verbose: bool = False,
) -> AssemblyResult:
    """Full agentic assembly pipeline: NL description → .scad assembly file."""
    from scadgen.agentic.pipeline import run_pipeline

    return run_pipeline(
        description=description,
        engine=engine,
        output_path=output_path,
        output_dir=output_dir,
        max_retries=max_retries,
        dry_run=dry_run,
        verbose=verbose,
    )
