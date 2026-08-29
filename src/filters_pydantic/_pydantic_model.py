"""Applies a pydantic model as a phx-filters filter."""

from typing import Any

import pydantic
from filters.base import BaseFilter

__all__ = ["PydanticModel"]


# phx-filters ships no py.typed marker, so BaseFilter is untyped under mypy.
class PydanticModel(BaseFilter):  # type: ignore[misc]
    """Validates a value against a pydantic model.

    Use inside a phx-filters chain to validate a nested structure via a
    full pydantic model, rather than field-by-field filters — e.g. nested
    inside a ``FilterMapper``:

        f.Required | PydanticModel(Person)

    On success, returns a model instance. On failure, reports one error
    per ``pydantic.ValidationError`` entry, keyed by its dotted ``loc``
    path (see docs/adr/002-pydanticmodel-error-translation.md).
    """

    CODE_INVALID = "invalid"

    templates = {
        CODE_INVALID: "{message}",
    }

    def __init__(self, model: type[pydantic.BaseModel]) -> None:
        """
        Args:
            model: Validates the incoming value via ``model.model_validate``.
        """
        super().__init__()
        self.model = model

    def _apply(self, value: Any) -> Any:
        try:
            return self.model.model_validate(value)
        except pydantic.ValidationError as exc:
            for error in exc.errors():
                key = ".".join(str(part) for part in error["loc"])
                self._invalid_value(
                    value=error.get("input"),
                    reason=self.CODE_INVALID,
                    sub_key=key,
                    template_vars={"message": error["msg"]},
                )
            return None
