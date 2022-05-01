"""Base classes."""
from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar, TypeVar

CachedInstanceT_co = TypeVar(
    "CachedInstanceT_co",
    bound="CachedInstance",
    covariant=True,
)


@dataclass(frozen=True)
class CachedInstance:
    _cache: ClassVar[dict[str, CachedInstance]] = {}

    instance_id: str

    @classmethod
    def get_by_id(
        cls: type[CachedInstanceT_co], id_field_value: str | None
    ) -> CachedInstanceT_co:
        if id_field_value is None:
            return next(iter(cls._cache.values()))  # type: ignore

        return cls._cache[id_field_value]  # type: ignore

    def __post_init__(self) -> None:
        """Store the created instance to cache."""
        self._cache[self.instance_id] = self
