from typing_extensions import final
from mypy.types import Type as MypyType, UnionType, Instance, union_items, TypeVarType
from typing import Sequence, List
from mypy.plugin import MethodContext


@final
class MetadataInjector(object):
    """
    Injects fake ``Supports[TypeClass]`` parent classes into ``mro``.

    Ok, this is wild. Why do we need this?
    Because, otherwise expressing ``Supports`` is not possible,
    here's an example:

    .. code:: python

        >>> from classes import AssociatedType, Supports, typeclass

        >>> class ToStr(AssociatedType):
        ...     ...

        >>> @typeclass(ToStr)
        ... def to_str(instance) -> str:
        ...     ...

        >>> @to_str.instance(int)
        ... def _to_str_int(instance: int) -> str:
        ...      return 'Number: {0}'.format(instance)

        >>> assert to_str(1) == 'Number: 1'

    Now, let's use ``Supports`` to only pass specific
    typeclass instances in a function:

    .. code:: python

        >>> def convert_to_string(arg: Supports[ToStr]) -> str:
        ...     return to_str(arg)

    This is possible, due to a fact that we insert ``Supports[ToStr]``
    into all classes that are mentioned as ``.instance()`` for ``ToStr``
    typeclass.

    So, we can call:

    .. code:: python

        >>> assert convert_to_string(1) == 'Number: 1'

    But, ``convert_to_string(None)`` will raise a type error.
    """

    __slots__ = ('_associated_type', '_instance_types', '_added_types')

    def __init__(
        self,
        associated_type: MypyType,
        instance_type: MypyType,
    ) -> None:
        self._associated_type = associated_type
        self._instance_types = union_items(instance_type)
        self._added_types: List[Instance] = []

    def add_supports_metadata(self) -> None:
        if not isinstance(self._associated_type, Instance):
            return

        for instance_type in self._instance_types:
            assert isinstance(instance_type, Instance)

            supports_spec = self._associated_type.copy_modified(args=[
                TypeVarType(var_def)
                for var_def in instance_type.type.defn.type_vars
            ])
            print('supports_spec', supports_spec)

            if supports_spec not in instance_type.type.bases:
                instance_type.type.bases.append(supports_spec)
            if supports_spec.type not in instance_type.type.mro:
                instance_type.type.mro.insert(0, supports_spec.type)

            self._added_types.append(supports_spec)

    def remove_supports_metadata(self) -> None:
        if not isinstance(self._associated_type, Instance):
            return

        for instance_type in self._instance_types:
            assert isinstance(instance_type, Instance)

            for added_type in self._added_types:
                if added_type in instance_type.type.bases:
                    instance_type.type.bases.remove(added_type)
                if added_type.type in instance_type.type.mro:
                    instance_type.type.mro.remove(added_type.type)

        self._added_types = []
