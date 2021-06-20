# Version history

We follow Semantic Versions since the `0.1.0` release.


## Version 0.3.0

### Features

- **Breaking**: drops `python3.6` support
- **Breaking**: now requires `typing_extensions>=3.10` and `mypy>=0.902`
- **Breaking**: now `classes` traverses `mro` of registered types
  and fallbacks to super-types if some type is not registered
- Adds generic typeclasses
- Adds caching to runtime type dispatch,
  it allows to call already resolved instances way faster
- Adds better typeclass validation during `mypy` typechecking
- Adds `.supports()` method to typeclass to check
  if some instance is supported in runtime
- Makes `.supports()` a typeguard
- Adds `Supports` type
- Adds `AssociatedType` variadic type

### Misc

- Improves docs


## Version 0.2.0

### Features

- **Breaking**: renames mypy `typeclass_plugin` to `classes_plugin`
- Adds `python3.9` support

### Misc

- Updates dependencies


## Version 0.1.0

- Initial release
