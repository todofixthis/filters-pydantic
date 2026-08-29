.. image:: https://github.com/todofixthis/filters-pydantic/actions/workflows/build.yml/badge.svg
   :target: https://github.com/todofixthis/filters-pydantic/actions/workflows/build.yml
.. image:: https://readthedocs.org/projects/phx-filters-pydantic/badge/?version=latest
   :target: http://phx-filters-pydantic.readthedocs.io/

Pydantic Filters
================

Pydantic integration for Filters

Getting Started
---------------
Install alongside `pydantic <https://docs.pydantic.dev/>`_ and
`filters <https://filters.readthedocs.io/>`_::

   pip install phx-filters-pydantic

``filters`` chains have no generic typing, so wrap one in ``FilterField`` and
attach it as ``Annotated`` metadata next to an ordinary type hint. The hint
tells pydantic (and your type checker) what to expect; the chain runs first
and does the actual validation::

   from typing import Annotated

   import filters as f
   from pydantic import BaseModel

   from filters_pydantic import FilterField


   class Person(BaseModel):
       name: Annotated[str, FilterField(f.Required | f.Unicode | f.NotEmpty)]
       age: Annotated[int, FilterField(f.Required | f.Int | f.Min(0))]


   Person(name="Phoenix", age="42")
   # Person(name='Phoenix', age=42)

A value the chain rejects raises the model's usual ``pydantic.ValidationError``,
with every filter error message for that field joined into one.

Validating a Model Inside a Filter Chain
-----------------------------------------
Going the other direction, wrap a pydantic model in ``PydanticModel`` to validate a
value against it from *inside* a ``filters`` chain — e.g. nested inside a
``FilterMapper`` or ``FilterRepeater``::

   import filters as f
   from pydantic import BaseModel

   from filters_pydantic import PydanticModel


   class Address(BaseModel):
       postcode: str


   schema = f.FilterMapper({"address": PydanticModel(Address)})
   runner = f.FilterRunner(schema, {"address": {}})
   runner.is_valid()
   # False
   runner.get_errors()
   # {'address.postcode': [{'code': 'invalid', 'message': 'Field required'}]}

Unlike ``FilterField``, which joins every chain error into one message,
``PydanticModel`` reports each pydantic validation error individually, keyed by
its dotted field path.

See the `full documentation <https://phx-filters-pydantic.readthedocs.io/>`_ for
more.

Requirements
------------
Pydantic Filters is known to be compatible with the following Python versions:

- 3.14
- 3.13
- 3.12

.. note::

   I'm only one person, so to keep from getting overwhelmed, I'm only committing to
   supporting the 3 most recent versions of Python.

Maintainers
-----------
To install the distribution for local development, some additional setup is required:

#. `Install uv <https://docs.astral.sh/uv/getting-started/installation/>`_ (only needs
   to be done once).

#. Run the following command to install additional dependencies::

      uv sync --group=dev

#. Activate pre-commit hook::

      uv run autohooks activate --mode=pythonpath

Running Unit Tests and Type Checker
-----------------------------------
Run the tests for all supported versions of Python using
`tox <https://tox.readthedocs.io/>`_::

   uv run tox -p

.. note::

   The first time this runs, it will take awhile, as mypy needs to build up its cache.
   Subsequent runs should be much faster.

If you just want to run unit tests in the current virtualenv (using
`pytest <https://docs.pytest.org>`_)::

   uv run pytest

If you just want to run type checking in the current virtualenv (using
`mypy <https://mypy.readthedocs.io>`_)::

   uv run mypy src test

Documentation
-------------
To build the documentation locally:

#. Switch to the ``docs`` directory::

    cd docs

#. Build the documentation::

    make html

Releases
--------
Releases are cut from a ``release/<version>`` branch off ``main``, merged via pull
request, then built, GPG-signed, tagged, and published to `PyPI
<https://pypi.org/project/phx-filters-pydantic/>`_ and the `GitHub Releases page
<https://github.com/todofixthis/filters-pydantic/releases>`_. See
``.agents/skills/release/SKILL.md`` for the full, current procedure — that file is
the source of truth; this section only summarises it.
