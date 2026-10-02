from collections.abc import Iterator, Mapping
from types import UnionType
from typing import Annotated, Any, Union, get_args, get_origin

from fastapi import Request
from pydantic import AliasChoices, AliasPath, BaseModel


def _variants(annotation: Any) -> tuple[Any, ...]:
    if get_origin(annotation) is Annotated:
        return _variants(get_args(annotation)[0])
    if get_origin(annotation) in (Union, UnionType):
        return tuple(item for branch in get_args(annotation) for item in _variants(branch))
    return (annotation,)


def _alias_paths(alias: Any) -> list[tuple[str | int, ...]]:
    if isinstance(alias, AliasChoices):
        return [path for choice in alias.choices for path in _alias_paths(choice)]
    if isinstance(alias, AliasPath):
        return [tuple(alias.path)]
    return [(alias,)]


def _model_paths(model: type[BaseModel]) -> Iterator[tuple[tuple[str | int, ...], Any]]:
    for name, field in model.model_fields.items():
        paths = _alias_paths(field.validation_alias or field.alias or name)
        if model.model_config.get("validate_by_name") or model.model_config.get("loc_by_alias") is False:
            paths.append((name,))
        for path in paths:
            yield path, field.annotation


def _safe_parts(annotation: Any, parts: tuple) -> list[str | int]:
    if not parts:
        return []
    part, *remaining = parts
    variants = _variants(annotation)
    if len(variants) > 1:
        for variant in variants:
            if isinstance(variant, type) and issubclass(variant, BaseModel) and part == variant.__name__:
                # Pydantic inserts a branch label; it is not part of the submitted path.
                return _safe_parts(variant, tuple(remaining))
    for variant in variants:
        origin, args = get_origin(variant), get_args(variant)
        if isinstance(variant, type) and issubclass(variant, BaseModel):
            matches = []
            for path, next_type in _model_paths(variant):
                if parts[:len(path)] == path:
                    matches.append((path, next_type))
            if matches:
                # Aliases may share a prefix; consume the most specific declared path.
                path, next_type = max(matches, key=lambda match: len(match[0]))
                return [*path, *_safe_parts(next_type, parts[len(path):])]
        elif origin in (list, tuple, set, frozenset) and isinstance(part, int):
            next_type = args[0] if args else Any
            if origin is tuple and args and args[-1] is not Ellipsis:
                next_type = args[part] if 0 <= part < len(args) else Any
            return [part, *_safe_parts(next_type, tuple(remaining))]
        elif origin in (dict, Mapping):
            # Mapping keys originate in submitted data, even when they are integers.
            next_type = args[1] if len(args) == 2 else Any
            return ["[key]" if part == "[key]" else "[redacted]",
                    *_safe_parts(next_type, tuple(remaining))]
    return ["[key]" if part == "[key]" else "[redacted]",
            *_safe_parts(Any, tuple(remaining))]


def _input_fields(dependant: Any, group: str) -> Iterator[Any]:
    yield from getattr(dependant, group, [])
    for dependency in getattr(dependant, "dependencies", []):
        yield from _input_fields(dependency, group)


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
        fields = _input_fields(dependant, groups[source])
        for field in fields:
            annotation = field.field_info.annotation
            for variant in _variants(annotation):
                if isinstance(variant, type) and issubclass(variant, BaseModel):
                    # Parameter models are flattened: their outer argument name is absent from loc.
                    if any(tuple(parts[:len(path)]) == path for path, _ in _model_paths(variant)):
                        return [source, *_safe_parts(annotation, tuple(parts))]
            if parts and field.alias == parts[0]:
                return [source, field.alias, *_safe_parts(annotation, tuple(parts[1:]))]
        return [source, *("[redacted]" for _ in parts)]
    return ["input", *("[redacted]" for _ in parts)]
