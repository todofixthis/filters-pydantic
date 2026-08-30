"""Tests for filters_pydantic.FilterField."""

import time
from concurrent.futures import ThreadPoolExecutor
from typing import Annotated, Optional

import filters as f
import pytest
from pydantic import BaseModel, Field, ValidationError

from filters_pydantic import FilterField


class Person(BaseModel):
    name: Annotated[str, FilterField(f.Required | f.Unicode | f.NotEmpty)]
    age: Annotated[int, FilterField(f.Required | f.Int | f.Min(0))]
    nickname: Annotated[Optional[str], FilterField(f.Unicode)] = None


def test_filter_field_pass_applies_chain() -> None:
    """The chain's own transformation reaches the field — pydantic's plain
    ``str`` schema has no such effect, so it must be the chain that produced
    the stripped value.
    """

    class Contact(BaseModel):
        name: Annotated[str, FilterField(f.Unicode | f.Strip)]

    assert Contact(name="  Phoenix  ").name == "Phoenix"


def test_filter_field_pass_coerces_before_pydantic_validates() -> None:
    """A numeric string for an int field is coerced by the chain before
    pydantic's own int schema runs, so it's accepted and yields a real int.
    """
    # Validate via a dict, the way data from an external source (e.g. a
    # JSON request body) would arrive — ``Person(age="7")`` is typed
    # against the annotation and fails mypy even though it's valid here.
    person = Person.model_validate({"name": "Phoenix", "age": "7"})

    assert person.age == 7
    assert isinstance(person.age, int)


def test_filter_field_pass_none_short_circuits_chain() -> None:
    """``None`` passes through a chain with no ``f.Required``, since
    ``BaseFilter`` short-circuits every filter on ``None`` before ``_apply``
    runs.
    """
    person = Person(name="Phoenix", age=1, nickname=None)

    assert person.nickname is None


def test_filter_field_pass_composes_with_field_default() -> None:
    """A ``pydantic.Field`` constraint in the same ``Annotated`` slot still
    applies after the chain runs, rejecting a value the chain alone would
    accept — ``f.Min(0)`` only bounds below, so ``Field(le=10)`` is the one
    stopping ``11``.
    """

    class Config(BaseModel):
        retries: Annotated[int, FilterField(f.Int | f.Min(0)), Field(le=10)] = 3

    assert Config(retries=5).retries == 5

    with pytest.raises(ValidationError):
        Config(retries=11)


def test_filter_field_fail_reports_single_filter_error() -> None:
    """A single chain failure surfaces as one ``value_error`` located at the
    failing field.
    """
    with pytest.raises(ValidationError) as exc_info:
        Person(name="", age=1)

    (error,) = exc_info.value.errors()
    assert error["type"] == "value_error"
    assert error["loc"] == ("name",)


def test_filter_field_fail_reports_none_as_required_violation() -> None:
    """``None`` reaching an ``f.Required`` chain fails as the chain's own
    ``value_error``, not pydantic's unrelated ``string_type`` rejection of
    ``None`` for a plain ``str`` field.
    """
    with pytest.raises(ValidationError) as exc_info:
        Person.model_validate({"name": None, "age": 1})

    (error,) = exc_info.value.errors()
    assert error["type"] == "value_error"
    assert "This value is required." in error["msg"]


def test_filter_field_fail_joins_multiple_chain_errors() -> None:
    """Multiple ``FilterMapper`` sub-key failures collapse into one
    ``value_error`` whose message names every failing sub-key.
    """

    class Point(BaseModel):
        coords: Annotated[
            dict[str, int],
            FilterField(
                f.FilterMapper(
                    {"x": f.Required | f.Int, "y": f.Required | f.Int},
                )
            ),
        ]

    with pytest.raises(ValidationError) as exc_info:
        Point(coords={})

    (error,) = exc_info.value.errors()
    assert error["type"] == "value_error"
    assert "x: This value is required." in error["msg"]
    assert "y: This value is required." in error["msg"]


def test_filter_field_pass_str_names_the_chain() -> None:
    """``str()`` names the wrapped chain, since the default object repr
    pydantic shows in ``model_fields[...].metadata`` identifies nothing
    about what actually validates the field.
    """
    field = FilterField(f.Required | f.Unicode | f.NotEmpty)

    assert "Required" in str(field)
    assert "NotEmpty" in str(field)


def test_filter_field_fail_propagates_unexpected_exception() -> None:
    """An exception raised inside a filter propagates as itself, rather than
    being reported as a generic pydantic ``value_error``.
    """

    # phx-filters ships no py.typed marker, so BaseFilter is untyped under mypy.
    class Boom(f.BaseFilter):  # type: ignore[misc]
        def _apply(self, value: object) -> object:
            raise RuntimeError("boom")

    class Ticket(BaseModel):
        number: Annotated[int, FilterField(Boom())]

    with pytest.raises(RuntimeError, match="boom"):
        Ticket.model_validate({"number": 1})


def test_filter_field_fail_rejects_none_chain_at_construction() -> None:
    """A ``None`` filter chain is rejected when ``FilterField`` is built, not
    left to crash the first time a field using it is validated.
    """
    with pytest.raises(TypeError, match="filter_chain"):
        FilterField(None)


def test_filter_field_fail_chain_output_mismatched_type_is_pydantic_error() -> None:
    """A chain output that doesn't satisfy the annotated type fails as a
    plain pydantic error, not as a ``value_error`` from the chain.
    """

    # The chain itself passes (``f.Unicode`` accepts anything); it's the
    # output that fails the annotated ``int``.
    class Ticket(BaseModel):
        number: Annotated[int, FilterField(f.Unicode)]

    with pytest.raises(ValidationError) as exc_info:
        Ticket.model_validate({"number": "not-a-number"})

    (error,) = exc_info.value.errors()
    assert error["type"] != "value_error"


def test_filter_field_pass_concurrent_validation_does_not_corrupt_other_calls() -> None:
    """Two threads validating the same field's shared chain at once don't
    clobber each other's result (ADR 005) — every valid input is still
    accepted and every invalid input is still rejected, regardless of what
    other threads are doing concurrently.
    """

    # phx-filters ships no py.typed marker, so BaseFilter is untyped under mypy.
    class SlowUnicode(f.BaseFilter):  # type: ignore[misc]
        """Widens the race window so concurrent full_clean() calls overlap."""

        def _apply(self, value: object) -> object:
            time.sleep(0.005)
            return self._filter(value, f.Unicode)

    class Widget(BaseModel):
        name: Annotated[str, FilterField(SlowUnicode() | f.NotEmpty)]

    def validate(index: int) -> tuple[int, bool]:
        value = "ok" if index % 2 == 0 else ""
        try:
            Widget(name=value)
            return index, True
        except ValidationError:
            return index, False

    with ThreadPoolExecutor(max_workers=40) as executor:
        results = list(executor.map(validate, range(40)))

    for index, passed in results:
        assert passed == (index % 2 == 0), f"input {index} got the wrong result"
