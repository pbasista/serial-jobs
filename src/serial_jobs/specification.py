"""Functionality for instantiating classes from specification."""
from dataclasses import dataclass
from typing import ClassVar, Generator, Optional, TypeVar

SpecT = TypeVar("SpecT", bound="SpecMixin")


@dataclass(frozen=True)
class SpecMixin:
    """A mixin class which stores the specifications of its instances."""

    # This cache of specifications needs to be provided
    # by the class to which this class is mixed-in.
    # It allows every derived class to have its own cache.
    specs_by_id: ClassVar[dict[str, dict]]

    spec_id: str
    name: Optional[str]

    @classmethod
    def load_specifications(cls: type[SpecT], specifications: list[dict]) -> None:
        for specification in specifications:
            specification_id = specification["id"]
            cls.specs_by_id[specification_id] = specification

    @classmethod
    def from_spec(cls: type[SpecT], spec: dict) -> SpecT:
        raise NotImplementedError

    @classmethod
    def from_all_specs(cls: type[SpecT]) -> Generator[SpecT, None, None]:
        for spec in cls.specs_by_id.values():
            yield cls.from_spec(spec)

    @classmethod
    def from_id(cls: type[SpecT], spec_id: str) -> SpecT:
        return cls.from_spec(cls.specs_by_id[spec_id])

    @classmethod
    def default_id(cls: type[SpecT]) -> str:
        return next(iter(cls.specs_by_id.keys()))
