"""Tests for filters_pydantic.PydanticModel."""

from typing import Any, Callable

import filters as f
import pydantic

from filters_pydantic import PydanticModel

AssertFilterPasses = Callable[..., Any]
AssertFilterErrors = Callable[..., Any]


class Address(pydantic.BaseModel):
    postcode: str


class Person(pydantic.BaseModel):
    name: str
    age: int


class Contact(pydantic.BaseModel):
    address: Address


class Ticket(pydantic.BaseModel):
    priority: int

    @pydantic.model_validator(mode="after")
    def _check_priority(self) -> "Ticket":
        if self.priority > 10:
            raise ValueError("Priority must not exceed 10.")
        return self


def test_pydantic_model_pass_none(assert_filter_passes: AssertFilterPasses) -> None:
    """``None`` bypasses the wrapped model entirely and passes through
    unchanged.
    """
    assert_filter_passes(PydanticModel(Person), None)


def test_pydantic_model_pass_returns_model_instance(
    assert_filter_passes: AssertFilterPasses,
) -> None:
    """A valid mapping is validated into a model instance, not returned as
    the raw dict.
    """
    assert_filter_passes(
        PydanticModel(Person),
        {"name": "Phoenix", "age": 42},
        Person(name="Phoenix", age=42),
    )


def test_pydantic_model_fail_reports_error_per_field(
    assert_filter_errors: AssertFilterErrors,
) -> None:
    """Each invalid or missing field produces its own ``CODE_INVALID`` entry
    keyed by that field's name.
    """
    assert_filter_errors(
        PydanticModel(Person),
        {"age": "not-a-number"},
        {
            "name": [PydanticModel.CODE_INVALID],
            "age": [PydanticModel.CODE_INVALID],
        },
    )


def test_pydantic_model_fail_nested_field_uses_dotted_key(
    assert_filter_errors: AssertFilterErrors,
) -> None:
    """A failing field on a nested model is keyed by the dotted path to
    that field, not the outer field alone.
    """
    assert_filter_errors(
        PydanticModel(Contact),
        {"address": {}},
        {"address.postcode": [PydanticModel.CODE_INVALID]},
    )


def test_pydantic_model_fail_model_level_error_reports_at_own_key(
    assert_filter_errors: AssertFilterErrors,
) -> None:
    """A whole-model ``model_validator`` failure — whose ``loc`` is empty —
    lands at this filter's own key rather than a sub-key.
    """
    assert_filter_errors(
        PydanticModel(Ticket),
        {"priority": 20},
        [PydanticModel.CODE_INVALID],
    )


def test_pydantic_model_fail_nested_in_filter_mapper_scopes_key() -> None:
    """Nesting ``PydanticModel`` inside a ``FilterMapper`` scopes its field
    errors under the mapper's own key, e.g. ``person.name``.
    """
    schema = f.FilterMapper({"person": PydanticModel(Person)})
    runner = f.FilterRunner(schema, {"person": {"age": 1}})

    assert not runner.is_valid()
    (error,) = runner.get_errors()["person.name"]
    assert error["code"] == PydanticModel.CODE_INVALID
