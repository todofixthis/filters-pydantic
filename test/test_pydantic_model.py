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


class Tag(pydantic.BaseModel):
    n: str


class Catalog(pydantic.BaseModel):
    tags: list[Tag]


class Employee(pydantic.BaseModel):
    real_name: str = pydantic.Field(alias="realName")


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


def test_pydantic_model_fail_list_index_uses_dotted_key(
    assert_filter_errors: AssertFilterErrors,
) -> None:
    """A failing field inside a list item is keyed by its numeric index,
    dotted the same way a nested model's own field is (ADR 002).
    """
    assert_filter_errors(
        PydanticModel(Catalog),
        {"tags": [{"n": "ok"}, {}]},
        {"tags.1.n": [PydanticModel.CODE_INVALID]},
    )


def test_pydantic_model_fail_non_mapping_input_reports_at_own_key(
    assert_filter_errors: AssertFilterErrors,
) -> None:
    """An input that isn't a mapping at all fails with an empty ``loc``,
    landing at this filter's own key the same way a whole-model
    ``model_validator`` failure does (ADR 002).
    """
    assert_filter_errors(
        PydanticModel(Person),
        "not-a-mapping",
        [PydanticModel.CODE_INVALID],
    )


def test_pydantic_model_fail_uses_the_fields_alias_in_its_key(
    assert_filter_errors: AssertFilterErrors,
) -> None:
    """A missing aliased field is keyed by its alias, since that's what
    ``pydantic.ValidationError.errors()`` itself reports in ``loc`` — not
    the attribute name a caller matching on field names might expect.
    """
    assert_filter_errors(
        PydanticModel(Employee),
        {},
        {"realName": [PydanticModel.CODE_INVALID]},
    )


def test_pydantic_model_pass_str_names_the_wrapped_model() -> None:
    """``str()`` names the wrapped model, since it feeds into phx-filters'
    own debug context (``BaseFilter._invalid_value``'s ``context["filter"]``)
    and a bare default object repr can't identify which model rejected a
    value.
    """
    assert "Person" in str(PydanticModel(Person))


def test_pydantic_model_fail_nested_in_filter_mapper_scopes_key() -> None:
    """Nesting ``PydanticModel`` inside a ``FilterMapper`` scopes its field
    errors under the mapper's own key, e.g. ``person.name``.
    """
    schema = f.FilterMapper({"person": PydanticModel(Person)})
    runner = f.FilterRunner(schema, {"person": {"age": 1}})

    assert not runner.is_valid()
    (error,) = runner.get_errors()["person.name"]
    assert error["code"] == PydanticModel.CODE_INVALID


def test_pydantic_model_fail_nested_in_filter_repeater_scopes_key() -> None:
    """Nesting ``PydanticModel`` inside a ``FilterRepeater`` scopes its
    field errors under each item's own index, e.g. ``1.name``.
    """
    schema = f.FilterRepeater(PydanticModel(Person))
    runner = f.FilterRunner(schema, {0: {"name": "Phoenix", "age": 1}, 1: {"age": 2}})

    assert not runner.is_valid()
    (error,) = runner.get_errors()["1.name"]
    assert error["code"] == PydanticModel.CODE_INVALID
