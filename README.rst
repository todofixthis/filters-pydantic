.. image:: https://github.com/todofixthis/filters-pydantic/actions/workflows/build.yml/badge.svg
   :target: https://github.com/todofixthis/filters-pydantic/actions/workflows/build.yml
.. image:: https://readthedocs.org/projects/phx-filters-pydantic/badge/?version=latest
   :target: http://phx-filters-pydantic.readthedocs.io/

Pydantic Filters
================

Pydantic integration for Filters

Getting Started
---------------
TODO

Requirements
------------
Pydantic Filters is known to be compatible with the following Python versions:

- 3.12
- 3.11
- 3.10

.. note::

   I'm only one person, so to keep from getting overwhelmed, I'm only committing to
   supporting the 3 most recent versions of Python.

Maintainers
-----------
To install the distribution for local development, some additional setup is required:

#. `Install poetry <https://python-poetry.org/docs/#installation>`_ (only needs to be
   done once).

#. Run the following command to install additional dependencies::

      poetry install --with=dev

#. Activate pre-commit hook::

      poetry run autohooks activate --mode=poetry

Running Unit Tests and Type Checker
-----------------------------------
Run the tests for all supported versions of Python using
`tox <https://tox.readthedocs.io/>`_::

   poetry run tox -p

.. note::

   The first time this runs, it will take awhile, as mypy needs to build up its cache.
   Subsequent runs should be much faster.

If you just want to run unit tests in the current virtualenv (using
`pytest <https://docs.pytest.org>`_)::

   poetry run pytest

If you just want to run type checking in the current virtualenv (using
`mypy <https://mypy.readthedocs.io>`_)::

   poetry run mypyc src test

Documentation
-------------
To build the documentation locally:

#. Switch to the ``docs`` directory::

    cd docs

#. Build the documentation::

    make html

Releases
--------
Steps to build releases are based on
`Packaging Python Projects Tutorial <https://packaging.python.org/en/latest/tutorials/packaging-projects/>`_.

.. important::

   Make sure to build releases off of the ``main`` branch, and check that all changes
   from ``develop`` have been merged before creating the release!

1. Build the Project
~~~~~~~~~~~~~~~~~~~~
#. Delete artefacts from previous builds, if applicable::

    rm dist/*

#. Run the build::

    poetry build

#. The build artefacts will be located in the ``dist`` directory at the top level of the
   project.

2. Upload to PyPI
~~~~~~~~~~~~~~~~~
#. `Create a PyPI API token <https://pypi.org/manage/account/token/>`_ (you only have to
   do this once).
#. Increment the version number in ``pyproject.toml``.
#. Upload build artefacts to PyPI::

    poetry publish

3. Create GitHub Release
~~~~~~~~~~~~~~~~~~~~~~~~
#. Create a tag and push to GitHub::

      git tag <version>
      git push <version>

   ``<version>`` must match the updated version number in ``pyproject.toml``.

#. Go to the `Releases page for the repo`_.
#. Click ``Draft a new release``.
#. Select the tag that you created in step 1.
#. Specify the title of the release (e.g., ``Pydantic Filters v1.2.3``).
#. Write a description for the release.  Make sure to include:
   - Credit for code contributed by community members.
   - Significant functionality that was added/changed/removed.
   - Any backwards-incompatible changes and/or migration instructions.
   - SHA256 hashes of the build artefacts.
#. GPG-sign the description for the release (ASCII-armoured).
#. Attach the build artefacts to the release.
#. Click ``Publish release``.

.. _Releases page for the repo: https://github.com/todofixthis/filters-pydantic/releases
