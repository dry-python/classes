dry-python ecosystem
====================

We support other ``dry-python`` projects.

returns
-------

This project is designed to work together with `returns <https://github.com/dry-python/returns>`_:

.. code:: python

  from classes import typeclass
  from returns.result import Result

  @typeclass
  def result_to_str(instance) -> str:
      """This is a typeclass definition to convert Result container to str."""

  @result_to_str.instance(Result.success_type)
  def _result_to_str_success(instance: Result) -> str:
      """The sad part is that we cannot make this case generic..."""
      return str(instance.unwrap())  # will always receive `Success` types

  @result_to_str.instance(Result.failure_type)
  def _result_to_str_failure(instance: Result) -> str:
      """But we can still use cases to work with top-level types!"""
      return str(instance.failure())  # will always receive `Failure` types

Combining ``classes`` and ``returns`` allows you
to write typed and declaratice business logic
without almost any ``isintance`` calls.

It also helps you with the value unwrapping from the ``Result`` container.
