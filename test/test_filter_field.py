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
    person = Person(name="  Phoenix  ", age=42)

    # ``f.Unicode`` on its own doesn't strip whitespace; the point here is
    # that the filter chain — not pydantic — produced the value.
    assert person.name == "  Phoenix  "
    assert person.age == 42


def test_filter_field_pass_coerces_before_pydantic_validates() -> None:
    # ``f.Int`` coerces the incoming str to an int before pydantic's own
    # ``int`` schema runs, so a numeric string is accepted — a shape that
    # doesn't fit ``Person``'s own ``__init__`` typing, so validate via a
    # dict, the way data from an external source (e.g. a JSON request body)
    # would arrive.
    person = Person.model_validate({"name": "Phoenix", "age": "7"})

    assert person.age == 7
    assert isinstance(person.age, int)


def test_filter_field_pass_none_short_circuits_chain() -> None:
    # ``None`` passes through every filter automatically (handled by
    # ``BaseFilter`` before ``_apply`` runs), so a chain without
    # ``f.Required`` never rejects it.
    person = Person(name="Phoenix", age=1, nickname=None)

    assert person.nickname is None


def test_filter_field_pass_composes_with_field_default() -> None:
    class Config(BaseModel):
        retries: Annotated[int, FilterField(f.Int | f.Min(0)), Field(ge=0)] = 3

    assert Config().retries == 3
    assert Config(retries=5).retries == 5


def test_filter_field_fail_reports_single_filter_error() -> None:
    with pytest.raises(ValidationError) as exc_info:
        Person(name="", age=1)

    (error,) = exc_info.value.errors()
    assert error["type"] == "value_error"
    assert error["loc"] == ("name",)


def test_filter_field_fail_reports_none_as_required_violation() -> None:
    with pytest.raises(ValidationError) as exc_info:
        Person.model_validate({"name": None, "age": 1})

    (error,) = exc_info.value.errors()
    assert error["loc"] == ("name",)


def test_filter_field_fail_joins_multiple_chain_errors() -> None:
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
    # The chain itself passes (``f.Unicode`` accepts anything), but its
    # output doesn't satisfy the annotated ``int`` — that's reported by
    # pydantic's own schema, not as a ``value_error`` from the chain.
    class Ticket(BaseModel):
        number: Annotated[int, FilterField(f.Unicode)]

    with pytest.raises(ValidationError) as exc_info:
        Ticket.model_validate({"number": "not-a-number"})

    (error,) = exc_info.value.errors()
    assert error["type"] != "value_error"
