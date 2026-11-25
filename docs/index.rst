Pydantic Filters
================

.. toctree::
   :maxdepth: 1
   :caption: Contents:

   api

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

   text_chain = f.Unicode | f.Strip


   class Article(BaseModel):
       # Unsafe: both chains hold text_chain's own Unicode and Strip filters
       title: Annotated[str, FilterField(text_chain | f.MaxLength(50))]
       body: Annotated[str, FilterField(text_chain | f.MaxLength(2000))]

For those cases, or for an expensive chain (I/O, a slow computation) under
concurrent load, pass a zero-argument callable that builds every filter each time
it runs. A filter class, such as ``FilterField(f.Unicode)``, counts as one. Each
validation then gets its own independent chain and skips the lock entirely.

To share a base chain, make it a filter macro. A macro builds new filters each
time a chain uses it::

   @f.filter_macro
   def Text() -> f.FilterChain[str]:
       return f.Unicode | f.Strip


   class Article(BaseModel):
       title: Annotated[str, FilterField(lambda: Text | f.MaxLength(50))]
       body: Annotated[str, FilterField(lambda: Text | f.MaxLength(2000))]

Without the lambdas, ``FilterField(Text | f.MaxLength(50))`` is safe too: each
field owns the chain its ``|`` builds, and its lock covers it.

A callable that uses an existing filter or chain anywhere, such as
``lambda: text_chain | f.MaxLength(50)`` or ``lambda: f.Required | text_chain``,
is unsafe, because every call reuses that chain's filter instances.

Sharing a filter with a ``FilterMapper`` or ``FilterRepeater`` also mislabels its
errors, even on one thread. Once a ``FilterMapper`` holds a filter, that filter's
errors carry the mapper's key wherever else it runs, so a ``title`` field using a
chain that a ``FilterMapper`` also holds under ``name`` reports ``name: Non-empty
value expected.`` A ``FilterRepeater`` does the same once it has run, with the
last list index it processed, such as ``1:``. A callable that builds every filter
avoids this too (see
`todofixthis/filters#175 <https://github.com/todofixthis/filters/issues/175>`_).

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

Requirements
------------
Pydantic Filters is known to be compatible with the following Python versions:

- 3.14
- 3.13
- 3.12

I'm only one person, so to keep from getting overwhelmed, I'm only committing to
supporting the 3 most recent versions of Python.
