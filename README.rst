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

pydantic can't read a field's type from a ``filters`` chain, so wrap one in
``FilterField`` and attach it as ``Annotated`` metadata next to an ordinary
type hint. The hint tells pydantic (and your type checker) what to expect;
the chain runs first and does the actual validation::

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

A chain built inline like this is shared across every validation of that field,
so ``FilterField`` serialises concurrent access to it with a lock (see
`ADR 005 <https://github.com/todofixthis/filters-pydantic/blob/main/docs/adr/005-serialise-shared-filter-chains.md>`_).
The lock belongs to the ``FilterField``, so reusing one ``Annotated`` alias across
fields and models is safe: every use shares that one lock.

The lock can't protect a filter that is also used outside its ``FilterField``. That
happens when two ``FilterField`` instances are built from the same chain, when code
outside pydantic runs the chain directly, or when a shared chain is combined into
two others with ``|`` (on either side), or nested in a ``FilterMapper`` or
``FilterRepeater``. Each of these reuses the shared chain's filters rather than
copying them::

   Text = f.Unicode | f.Strip


   class Article(BaseModel):
       # Unsafe: both chains hold Text's own Unicode and Strip filters
       title: Annotated[str, FilterField(Text | f.MaxLength(50))]
       body: Annotated[str, FilterField(Text | f.MaxLength(2000))]

For those cases, or for an expensive chain (I/O, a slow computation) under
concurrent load, pass a zero-argument callable that builds every filter each time
it runs. A filter class, such as ``FilterField(f.Unicode)``, counts as one. Each
validation then gets its own independent chain and skips the lock entirely. To
share a base chain, build it in a function::

   def text() -> f.FilterChain[str]:
       return f.Unicode | f.Strip


   class Article(BaseModel):
       title: Annotated[str, FilterField(lambda: text() | f.MaxLength(50))]
       body: Annotated[str, FilterField(lambda: text() | f.MaxLength(2000))]

A callable that uses an existing filter or chain anywhere, such as
``lambda: Text | f.MaxLength(50)`` or ``lambda: f.Required | Text``, is unsafe for
the same reason.

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

``PydanticModel`` is also registered as a `filters extension
<https://filters.readthedocs.io/en/latest/extensions.html>`_, so it's reachable as
``f.ext.PydanticModel`` without importing this package directly::

   import filters as f


   schema = f.FilterMapper({"address": f.ext.PydanticModel(Address)})

``FilterField`` isn't a ``filters.base.BaseFilter``, so it stays a plain import.

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

    uv run make html SPHINXOPTS=-W

Releases
--------
Releases are cut from a ``release/<version>`` branch off ``main``, merged via pull
request, then built, GPG-signed, tagged, and published to `PyPI
<https://pypi.org/project/phx-filters-pydantic/>`_ and the `GitHub Releases page
<https://github.com/todofixthis/filters-pydantic/releases>`_. See
``.agents/skills/release/SKILL.md`` for the full, current procedure — that file is
the source of truth; this section only summarises it.
