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
