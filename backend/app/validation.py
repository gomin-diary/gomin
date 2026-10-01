from collections.abc import Mapping
from types import UnionType
from typing import Annotated, Any, Union, get_args, get_origin

from fastapi import Request
from pydantic import BaseModel


def _variants(annotation: Any) -> tuple[Any, ...]:
    if get_origin(annotation) is Annotated:
        return _variants(get_args(annotation)[0])
    if get_origin(annotation) in (Union, UnionType):
        return tuple(item for branch in get_args(annotation) for item in _variants(branch))
    return (annotation,)


def _safe_parts(annotation: Any, parts: tuple) -> list[str | int]:
    safe: list[str | int] = []
    for part in parts:
        next_type: Any = Any
        label: str | int = "[redacted]"
        for variant in _variants(annotation):
            origin, args = get_origin(variant), get_args(variant)
            if isinstance(variant, type) and issubclass(variant, BaseModel):
                field = next((field for name, field in variant.model_fields.items()
                              if part == (field.validation_alias or field.alias or name)), None)
                if field is not None:
                    label, next_type = part, field.annotation
                    break
            elif origin in (list, tuple, set, frozenset) and isinstance(part, int):
                label = part
                next_type = args[0] if args else Any
                if origin is tuple and args and args[-1] is not Ellipsis:
                    next_type = args[part] if 0 <= part < len(args) else Any
                break
            elif origin in (dict, Mapping):
                # Mapping keys originate in submitted data, even when they are integers.
                next_type = args[1] if len(args) == 2 else Any
                break
        if part == "[key]":
            label = "[key]"
        safe.append(label)
        annotation = next_type
    return safe


def safe_validation_path(request: Request, location: tuple) -> list[str | int]:
    """Keep declared input fields and sequence indices; hide dynamic map keys."""
    if not location:
        return []
    source, *parts = location
    route = request.scope.get("route")
    if source == "body":
        field = getattr(route, "body_field", None)
        annotation = field.field_info.annotation if field else Any
        return ["body", *_safe_parts(annotation, tuple(parts))]
    groups = {"query": "query_params", "path": "path_params", "header": "header_params", "cookie": "cookie_params"}
    if source in groups:
        dependant = getattr(route, "dependant", None)
        fields = getattr(dependant, groups[source], [])
        field = next((field for field in fields if parts and field.alias == parts[0]), None)
        if field:
            return [source, field.alias, *_safe_parts(field.field_info.annotation, tuple(parts[1:]))]
        return [source, *("[redacted]" for _ in parts)]
    return ["input", *("[redacted]" for _ in parts)]
