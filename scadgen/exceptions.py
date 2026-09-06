class SCADGenError(Exception):
    pass


class TemplateNotFoundError(SCADGenError):
    pass


class TemplateParseError(SCADGenError):
    pass


class ParameterValidationError(SCADGenError, ValueError):
    pass


class ProviderError(SCADGenError):
    pass


class ProviderUnavailableError(ProviderError):
    pass


class ExtractionError(SCADGenError):
    pass


class RenderError(SCADGenError):
    pass


class ConstraintViolationError(SCADGenError):
    def __init__(self, violations: list[str]):
        self.violations = violations
        super().__init__("Constraint violations:\n" + "\n".join(f"  - {v}" for v in violations))


class AgenticError(SCADGenError):
    pass


class DecompositionError(AgenticError):
    pass


class TemplateGenerationError(AgenticError):
    def __init__(self, template_id: str, attempts: int, last_errors: list[str]):
        self.template_id = template_id
        self.attempts = attempts
        self.last_errors = last_errors
        super().__init__(
            f"Failed to generate template '{template_id}' after {attempts} attempts: "
            + "; ".join(last_errors)
        )


class ConnectionPlanError(AgenticError):
    pass


class AssemblyExecutionError(AgenticError):
    pass
