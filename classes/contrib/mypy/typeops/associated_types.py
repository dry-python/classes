from mypy.plugin import MethodContext
from mypy.types import Instance
from typing_extensions import Final

#: Fullname of the `AssociatedType` class.
_ASSOCIATED_TYPE_FULLNAME: Final = 'classes._typeclass.AssociatedType'

# Messages:
_WRONG_SUBCLASS_MSG: Final = (
    'Single direct subclass of "{0}" required; got "{1}"'
)


def check_type(
    associated_type: Instance,
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
        # TODO: check_type_reuse
        # TODO: check_body
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
