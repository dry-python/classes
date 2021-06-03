from typing import Optional

from mypy.checker import detach_callable
from mypy.nodes import ARG_POS, Decorator, MemberExpr
from mypy.plugin import FunctionContext, MethodContext, MethodSigContext
from mypy.typeops import bind_self
from mypy.types import AnyType, CallableType, Instance
from mypy.types import Type as MypyType
from mypy.types import (
    TypeOfAny,
    TypeVarType,
    UninhabitedType,
    UnionType,
    get_proper_type,
)
from typing_extensions import final

from classes.contrib.mypy.typeops import (
    instance_signature,
    type_loader,
    typecheck,
)


@final
class ConstructorReturnType(object):
    """
    Adjust argument types when we define typeclasses via ``typeclass`` function.

    It has two modes:
    1. As a decorator ``@typeclass``
    2. As a regular call with a class definition: ``typeclass(SomeProtocol)``

    It also checks how typeclasses are defined.
    """

    def __call__(self, ctx: FunctionContext) -> MypyType:
        defn = ctx.arg_types[0][0]
        is_defined_by_class = (
            isinstance(defn, CallableType) and
            not defn.arg_types and
            isinstance(defn.ret_type, Instance)
        )

        if is_defined_by_class:
            return self._adjust_protocol_arguments(ctx)
        elif isinstance(defn, CallableType):
            return self._adjust_typeclass(defn, ctx)
        return ctx.default_return_type

    def _adjust_protocol_arguments(self, ctx: FunctionContext) -> MypyType:
        assert isinstance(ctx.arg_types[0][0], CallableType)
        assert isinstance(ctx.arg_types[0][0].ret_type, Instance)

        instance = ctx.arg_types[0][0].ret_type
        type_info = instance.type
        signature = type_info.get_method('__call__')
        if not signature:
            ctx.api.fail(
                'Typeclass definition must have `__call__` method',
                ctx.context,
            )
            return AnyType(TypeOfAny.from_error)

        signature_type = get_proper_type(signature.type)
        assert isinstance(signature_type, CallableType)
        return self._adjust_typeclass(
            bind_self(signature_type),
            ctx,
            class_definition=instance,
        )

    def _adjust_typeclass(
        self,
        typeclass_def: MypyType,
        ctx: FunctionContext,
        class_definition: Optional[Instance] = None,
    ) -> MypyType:
        assert isinstance(typeclass_def, CallableType)
        assert isinstance(ctx.default_return_type, Instance)

        ctx.default_return_type.args = (
            UninhabitedType(),  # We start with empty set of instances
            typeclass_def,
            class_definition if class_definition else UninhabitedType(),
        )
        return ctx.default_return_type


@final
class InstanceReturnType(object):
    """
    Adjusts the typing signature after ``.instance(type)`` call.

    We need this to get typing match working:
    so the type mentioned in ``.instance()`` call
    will be the same as the one in a function later on.

    We use ``ctx.arg_names[0]`` to determine which mode is used:
    1. If it is empty, than annotation-based dispatch method is used
    2. If it is not empty, that means that decorator with arguments is used,
       like ``@some.instance(MyType)``

    """

    def __call__(self, ctx: MethodContext) -> MypyType:
        """"""
        if not isinstance(ctx.type, Instance):
            return ctx.default_return_type
        if not isinstance(ctx.default_return_type, CallableType):
            # We need this line to trigger
            # `OverloadedDef` proper branch detection,
            # without it would consider this return type as the correct one
            # (usually it is `NoReturn` here when wrong overload is used):
            ctx.api.fail('Bad return type', ctx.context)  # Not shown to user
            return ctx.default_return_type

        signature = self._adjust_typeclass_callable(ctx)
        if not typecheck.check_typeclass(signature, ctx):
            return ctx.default_return_type

        instance_type = self._add_new_instance_type(ctx)
        self._add_supports_metadata(ctx, instance_type)
        return detach_callable(ctx.default_return_type)

    @classmethod
    def from_function_decorator(cls, ctx: FunctionContext) -> MypyType:
        """
        It is used when ``.instance`` is used without params as a decorator.

        Like:

        .. code:: python

           @some.instance
           def _some_str(instance: str) -> str:
               ...

        """
        is_decorator = (
            isinstance(ctx.context, Decorator) and
            len(ctx.context.decorators) == 1 and
            isinstance(ctx.context.decorators[0], MemberExpr) and
            ctx.context.decorators[0].name == 'instance'
        )
        if not is_decorator:
            return ctx.default_return_type

        passed_function = ctx.arg_types[0][0]
        assert isinstance(passed_function, CallableType)

        if not passed_function.arg_types:
            return ctx.default_return_type

        annotation_type = passed_function.arg_types[0]
        if isinstance(annotation_type, Instance):
            if annotation_type.type and annotation_type.type.is_protocol:
                ctx.api.fail(
                    'Protocols must be passed with `is_protocol=True`',
                    ctx.context,
                )
                return ctx.default_return_type
        else:
            ctx.api.fail(
                'Only simple instance types are allowed, got: {0}'.format(
                    annotation_type,
                ),
                ctx.context,
            )
            return ctx.default_return_type

        ret_type = CallableType(
            arg_types=[passed_function],
            arg_kinds=[ARG_POS],
            arg_names=[None],
            ret_type=AnyType(TypeOfAny.implementation_artifact),
            fallback=passed_function.fallback,
        )
        instance_type = ctx.api.expr_checker.accept(  # type: ignore
            ctx.context.decorators[0].expr,  # type: ignore
        )

        # We need to change the `ctx` type from `Function` to `Method`:
        return cls()(MethodContext(
            type=instance_type,
            arg_types=ctx.arg_types,
            arg_kinds=ctx.arg_kinds,
            arg_names=ctx.arg_names,
            args=ctx.args,
            callee_arg_names=ctx.callee_arg_names,
            default_return_type=ret_type,
            context=ctx.context,
            api=ctx.api,
        ))

    def _adjust_typeclass_callable(
        self,
        ctx: MethodContext,
    ) -> CallableType:
        """Prepares callback"""
        assert isinstance(ctx.default_return_type, CallableType)
        assert isinstance(ctx.type, Instance)

        if not ctx.arg_names[0]:
            # We only need to adjust callables
            # that are passed via a decorator with params,
            # annotations-only are ignored:
            return ctx.default_return_type

        real_signature = ctx.type.args[1].copy_modified()
        to_adjust = ctx.default_return_type.arg_types[0]
        assert isinstance(real_signature, CallableType)
        assert isinstance(to_adjust, CallableType)

        ctx.default_return_type.arg_types[0] = instance_signature.prepare(
            real_signature,
            to_adjust.arg_types[0],
            ctx,
        )
        return ctx.default_return_type.arg_types[0]

    def _add_new_instance_type(
        self,
        ctx: MethodContext,
    ) -> MypyType:
        """Adds new types into type argument 0 by unifing unique types."""
        assert isinstance(ctx.type, Instance)
        assert isinstance(ctx.default_return_type, CallableType)
        assert isinstance(ctx.default_return_type.arg_types[0], CallableType)

        instance_type = ctx.default_return_type.arg_types[0].arg_types[0]
        unified = list(set(filter(
            # It means that function was defined without annotation
            # or with explicit `Any`, we prevent our Union from pollution.
            # Because `Union[Any, int]` is just `Any`.
            # We also clear accidental type vars.
            lambda type_: not isinstance(type_, (TypeVarType, UninhabitedType)),
            [instance_type, ctx.type.args[0]],
        )))

        ctx.type.args = (
            UnionType.make_union(unified),
            *ctx.type.args[1:],
        )
        return instance_type

    def _add_supports_metadata(
        self,
        ctx: MethodContext,
        instance_type: MypyType,
    ) -> None:
        """
        Injects fake ``Supports[TypeClass]`` parent classes into ``mro``.

        Ok, this is wild. Why do we need this?
        Because, otherwise expressing ``Supports`` is not possible,
        here's an example:

        .. code:: python

          >>> from classes import Supports, typeclass
          >>> from typing_extensions import Protocol

          >>> class ToStr(Protocol):
          ...     def __call__(self, instance) -> str:
          ...         ...

          >>> to_str = typeclass(ToStr)
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
        if not isinstance(instance_type, Instance):
            return

        assert isinstance(ctx.type, Instance)

        supports_spec = type_loader.load_supports_type(ctx.type.args[2], ctx)
        if supports_spec not in instance_type.type.bases:
            instance_type.type.bases.append(supports_spec)
        if supports_spec.type not in instance_type.type.mro:
            instance_type.type.mro.insert(0, supports_spec.type)


def call_signature(ctx: MethodSigContext) -> CallableType:
    """Returns proper ``__call__`` signature of a typeclass."""
    assert isinstance(ctx.type, Instance)

    real_signature = ctx.type.args[1]
    if not isinstance(real_signature, CallableType):
        return ctx.default_signature

    real_signature.arg_types[0] = ctx.type.args[0]

    if isinstance(ctx.type.args[2], Instance):
        # Why do we need this check?
        # Let's see what will happen without it:
        # For example, typeclass `ToJson` with `int` and `str` have will have
        # `Union[str, int]` as the first argument type.
        # But, we need `Union[str, int, Supports[ToJson]]`
        # That's why we are loading this type if the definition is there.
        supports_spec = type_loader.load_supports_type(ctx.type.args[2], ctx)
        real_signature.arg_types[0] = UnionType.make_union([
            real_signature.arg_types[0],
            supports_spec,
        ])
    return real_signature
