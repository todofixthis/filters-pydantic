"""Tests for filters_pydantic.FilterField."""

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
    """The filter chain, not pydantic, produces the field's final value."""
    person = Person(name="  Phoenix  ", age=42)

    # ``f.Unicode`` on its own doesn't strip whitespace; the point here is
    # that the filter chain — not pydantic — produced the value.
    assert person.name == "  Phoenix  "
    assert person.age == 42


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
    """``FilterField`` and ``pydantic.Field`` in the same ``Annotated`` slot
    both apply — the field's default and its ``ge=0`` constraint still hold.
    """

    class Config(BaseModel):
        retries: Annotated[int, FilterField(f.Int | f.Min(0)), Field(ge=0)] = 3

    assert Config().retries == 3
    assert Config(retries=5).retries == 5


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
    """``None`` reaching an ``f.Required`` chain is reported as a failure at
    that field, not treated as a value to pass through.
    """
    with pytest.raises(ValidationError) as exc_info:
        Person.model_validate({"name": None, "age": 1})

    (error,) = exc_info.value.errors()
    assert error["loc"] == ("name",)


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
