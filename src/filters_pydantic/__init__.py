"""Pydantic integration for phx-filters.

``FilterField`` runs a filters chain as a pydantic field's validator;
``PydanticModel`` runs a pydantic model as a step inside a filters chain.
"""

__version__ = "1.0.0a1"

__all__ = ["FilterField", "PydanticModel"]

from ._filter_field import FilterField
from ._pydantic_model import PydanticModel
