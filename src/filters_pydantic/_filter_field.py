"""Applies a phx-filters chain to a pydantic model field."""

from typing import Any

import filters as f
from pydantic import GetCoreSchemaHandler
from pydantic_core import core_schema

__all__ = ["FilterField"]


class FilterField:
    """Runs a filters chain as a pydantic field's validation logic.

    ``phx-filters`` chains have no generic typing, so attach ``FilterField``
    as ``Annotated`` metadata alongside an ordinary type hint — the hint
    tells pydantic (and static type checkers) what to expect; the chain
    does the actual validation:

        Name = Annotated[str, FilterField(f.Required | f.Unicode | f.NotEmpty)]

    The chain runs before pydantic's own validation of the annotated type,
    so its output still has to satisfy that type.
    """

    def __init__(self, filter_chain: f.FilterCompatible) -> None:
        """
        Args:
            filter_chain: Applied to the incoming value before pydantic
                validates it against the field's annotated type.

        Raises:
            TypeError: If ``filter_chain`` is ``None`` — a valid value for
                ``FilterCompatible`` elsewhere in phx-filters (e.g. an
                unfiltered ``FilterMapper`` key), but never a sensible chain
                for a field to run.
        """
        if filter_chain is None:
            raise TypeError("filter_chain must not be None")
        self.filter_chain = filter_chain

    def __str__(self) -> str:
        return f"{type(self).__name__}({self.filter_chain})"

    def __get_pydantic_core_schema__(
        self,
        source_type: Any,
        handler: GetCoreSchemaHandler,
    ) -> core_schema.CoreSchema:
        return core_schema.no_info_before_validator_function(
            self._run_filter_chain,
            handler(source_type),
        )

    def _run_filter_chain(self, value: Any) -> Any:
        """Runs the filter chain, raising on failure.

        Returns:
            The chain's cleaned value.

        Raises:
            ValueError: If the chain rejects ``value`` as invalid.
            Exception: Whatever a filter itself raised, if the failure was
                an unexpected exception rather than a validation rejection —
                ``BaseFilter.apply`` catches every exception internally, so
                without this it would otherwise be misreported as a generic
                ``value_error`` with the real cause discarded.
        """
        runner = f.FilterRunner(self.filter_chain, value, capture_exc_info=True)
        if runner.is_valid():
            return runner.cleaned_data

        if runner.has_exceptions:
            _, exc, tb = runner.exc_info[0]
            raise exc.with_traceback(tb)

        messages = [
            f"{key}: {message['message']}" if key else message["message"]
            for key, key_messages in runner.get_errors().items()
            for message in key_messages
        ]
        raise ValueError("; ".join(messages))
