"""Tests confirming this package's filters.extensions entry points."""

from importlib.metadata import entry_points

from filters_pydantic import PydanticModel


def test_entry_points_pydantic_model_is_discoverable() -> None:
    """PydanticModel is registered under the filters.extensions entry-point
    group, so f.ext.PydanticModel resolves to it without an explicit import
    (ADR 006).
    """
    (matched,) = [
        target
        for target in entry_points(group="filters.extensions")
        if target.name == "PydanticModel"
    ]

    assert matched.load() is PydanticModel
