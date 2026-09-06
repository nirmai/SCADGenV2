from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class ParameterDef:
    name: str
    type: str  # "int", "float", "bool", "string"
    default: Any
    min: Optional[float] = None
    max: Optional[float] = None
    unit: Optional[str] = None
    description: str = ""

    def validate(self, value: Any) -> Any:
        coerced = self._coerce(value)
        if self.min is not None and coerced < self.min:
            raise ParameterValidationError(
                f"{self.name}: {coerced} below minimum {self.min}"
            )
        if self.max is not None and coerced > self.max:
            raise ParameterValidationError(
                f"{self.name}: {coerced} above maximum {self.max}"
            )
        return coerced

    def _coerce(self, value: Any) -> Any:
        try:
            if self.type == "int":
                return int(float(value))
            if self.type == "float":
                return float(value)
            if self.type == "bool":
                if isinstance(value, str):
                    return value.lower() in ("true", "1", "yes")
                return bool(value)
            return str(value)
        except (ValueError, TypeError) as e:
            raise ParameterValidationError(
                f"{self.name}: cannot convert {value!r} to {self.type}"
            ) from e


@dataclass
class ConstraintDef:
    check: str        # Python expression evaluated against params; True = OK
    message: str      # Format string with {param_name} placeholders
    severity: str     # "error" or "warning"


@dataclass
class ConnectorDef:
    name: str
    type: str  # "axial", "planar", "threaded", "snap"
    origin: list[float | str] = field(default_factory=lambda: [0.0, 0.0, 0.0])
    direction: list[float | str] = field(default_factory=lambda: [0.0, 0.0, 1.0])
    diameter_ref: str = ""


@dataclass
class Template:
    template_id: str
    file_path: str
    module_name: str
    description: str
    category: str
    tags: list[str] = field(default_factory=list)
    parameters: list[ParameterDef] = field(default_factory=list)
    connectors: list[ConnectorDef] = field(default_factory=list)
    derived_expressions: dict[str, str] = field(default_factory=dict)
    source_code: str = ""
    aliases: list[str] = field(default_factory=list)
    keywords: list[str] = field(default_factory=list)
    length_param: str = ""
    constraints: list[ConstraintDef] = field(default_factory=list)

    def validate_params(self, params: dict[str, Any]) -> dict[str, Any]:
        validated = {}
        param_defs = {p.name: p for p in self.parameters}
        for name, value in params.items():
            if name not in param_defs:
                continue
            validated[name] = param_defs[name].validate(value)
        return validated

    def apply_defaults(self, params: dict[str, Any]) -> dict[str, Any]:
        result = {}
        for p in self.parameters:
            if p.name in params:
                result[p.name] = params[p.name]
            else:
                result[p.name] = p.default
        return result

    def compute_derived(self, params: dict[str, Any]) -> dict[str, float]:
        results = {}
        for name, expr in self.derived_expressions.items():
            try:
                results[name] = eval(expr, {"__builtins__": {}}, params)  # noqa: S307
            except Exception:
                pass
        return results


@dataclass
class ResolvedStandard:
    standard_name: str
    resolved_params: dict[str, Any]
    confidence: float = 0.0


@dataclass
class ResolvedInput:
    original: str
    standards_matched: list[str] = field(default_factory=list)
    resolved_params: dict[str, Any] = field(default_factory=dict)
    suggested_template: Optional[str] = None
    confidence: float = 0.0


@dataclass
class ExtractionResult:
    template: Template
    parameters: dict[str, Any]
    confidence: float
    notes: str = ""
    resolved_standards: Optional[ResolvedInput] = None


@dataclass
class GenerationResult:
    scad_code: str
    output_path: str
    template: Template
    parameters: dict[str, Any]
    derived_values: dict[str, float] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)


from scadgen.exceptions import ParameterValidationError  # noqa: E402

__all__ = ["ParameterValidationError"]
