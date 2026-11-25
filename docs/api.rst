API Documentation
=================

.. automodule:: filters_pydantic

..
   autodoc can't document a PEP 695 class type parameter, which isn't a
   module attribute, yet ``PydanticModel``'s signature references it.

.. py:data:: PydanticModel.T_model
   :module: filters_pydantic

   Type parameter of :py:class:`PydanticModel`: the pydantic model it validates
   against, and so the type of the instance it returns.
