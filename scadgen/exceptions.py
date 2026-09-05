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
