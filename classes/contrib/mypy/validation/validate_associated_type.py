from mypy.plugin import MethodContext
from mypy.types import Instance
from typing_extensions import Final

#: Fullname of the `AssociatedType` class.
_ASSOCIATED_TYPE_FULLNAME: Final = 'classes._typeclass.AssociatedType'

# Messages:
_WRONG_SUBCLASS_MSG: Final = (
    'Single direct subclass of "{0}" required; got "{1}"'
)

_TYPE_REUSE_MSG: Final = (
    'AssociatedType "{0}" must not be reused, originally associated with "{1}"'
)


def check_type(
    associated_type: Instance,
    typeclass: Instance,
    ctx: MethodContext,
) -> bool:
    """
    Checks passed ``AssociatedType`` instance.

    Right now, we only check that
    it is a subtype of our ``AssociatedType`` instance.
    In the future, it will do way more.
    """
    return all([
        _check_base_class(associated_type, ctx),
        _check_type_reuse(associated_type, typeclass, ctx),
        # TODO: check_body
        # TODO: check_generics_match_definition
        # TODO: we also need to check type vars used on definition:
        # no values, no bounds (?)
    ])


def _check_base_class(
    associated_type: Instance,
    ctx: MethodContext,
) -> bool:
    bases = associated_type.type.bases
    has_correct_base = (
        len(bases) == 1 and
        _ASSOCIATED_TYPE_FULLNAME == bases[0].type.fullname
    )
    if not has_correct_base:
        ctx.api.fail(
            _WRONG_SUBCLASS_MSG.format(
                _ASSOCIATED_TYPE_FULLNAME,
                associated_type,
            ),
            ctx.context,
        )
    return has_correct_base


def _check_type_reuse(
    associated_type: Instance,
    typeclass: Instance,
    ctx: MethodContext,
) -> bool:
    fullname = getattr(typeclass.args[3], 'value', None)
    metadata = associated_type.type.metadata.setdefault('classes', {})

    has_reuse = (
        fullname is not None and
        'typeclass' in metadata and
        metadata['typeclass'] != fullname
    )
    if has_reuse:
        ctx.api.fail(
            _TYPE_REUSE_MSG.format(associated_type.type.fullname, fullname),
            ctx.context,
        )

    metadata['typeclass'] = fullname
    return has_reuse
