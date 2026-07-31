"""Generic, dependency-free (de)serialization for the domain's dataclasses.

CLAUDE.md reserves Pydantic for I/O-boundary schemas and forbids the
domain package from depending on it. Every domain dataclass is plain
enough (dataclasses, StrEnum, NewType(str), list/dict/tuple, `X | None`)
that a small reflection-based codec covers all of it without needing a
per-class `to_dict`/`from_dict`.
"""

from __future__ import annotations

import dataclasses
import types
from collections.abc import Mapping as MappingABC
from enum import Enum
from typing import Any, Union, get_args, get_origin, get_type_hints

JsonValue = Any

_UNION_ORIGINS = {Union, types.UnionType}
_DICT_ORIGINS = {dict, MappingABC}


def to_json_dict(obj: Any) -> JsonValue:
    """Recursively convert a dataclass tree into plain JSON-safe values."""
    if obj is None or isinstance(obj, str | int | float | bool):
        return obj
    if isinstance(obj, Enum):
        return obj.value
    if dataclasses.is_dataclass(obj) and not isinstance(obj, type):
        return {f.name: to_json_dict(getattr(obj, f.name)) for f in dataclasses.fields(obj)}
    if isinstance(obj, MappingABC):
        return {str(k): to_json_dict(v) for k, v in obj.items()}
    if isinstance(obj, list | tuple):
        return [to_json_dict(v) for v in obj]
    raise TypeError(f"serialization.to_json_dict: cannot serialize {type(obj)!r}")


def from_json_dict(target_type: Any, data: JsonValue) -> Any:
    """Reconstruct a value of `target_type` from JSON-safe `data`.

    `target_type` is a type hint (a dataclass, an Enum, `list[X]`,
    `dict[str, X]`, `X | None`, or a primitive/NewType).
    """
    origin = get_origin(target_type)

    if origin in _UNION_ORIGINS:
        args = [a for a in get_args(target_type) if a is not type(None)]
        if data is None:
            return None
        # Only Optional[X] (a single non-None branch) is supported: real
        # sum types would need a discriminator field, not needed here.
        return from_json_dict(args[0], data)

    if data is None:
        return None

    if origin is list:
        (item_type,) = get_args(target_type)
        return [from_json_dict(item_type, v) for v in data]

    if origin is tuple:
        item_types = get_args(target_type)
        if len(item_types) == 2 and item_types[1] is Ellipsis:
            # Homogeneous, variable-length tuple: `tuple[X, ...]`.
            (item_type, _) = item_types
            return tuple(from_json_dict(item_type, v) for v in data)
        return tuple(from_json_dict(t, v) for t, v in zip(item_types, data, strict=True))

    if origin in _DICT_ORIGINS:
        key_type, val_type = get_args(target_type)
        return {from_json_dict(key_type, k): from_json_dict(val_type, v) for k, v in data.items()}

    if isinstance(target_type, type) and issubclass(target_type, Enum):
        return target_type(data)

    if dataclasses.is_dataclass(target_type):
        hints = get_type_hints(target_type)
        kwargs = {}
        for field in dataclasses.fields(target_type):
            if field.name in data:
                kwargs[field.name] = from_json_dict(hints[field.name], data[field.name])
        # typeshed's TypeGuard for is_dataclass() narrows to the *instance*
        # protocol even here, where target_type is still the class itself.
        return target_type(**kwargs)  # type: ignore[operator]

    if target_type in (int, float, str):
        # Covers e.g. `dict[int, X]` keys, which JSON always round-trips
        # as strings.
        return target_type(data)

    # NewType(str)-style aliases and anything untyped (e.g. `Any`): JSON
    # already has the right runtime representation, nothing to reconstruct.
    return data
