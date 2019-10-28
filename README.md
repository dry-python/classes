# classes

[![classes logo](https://raw.githubusercontent.com/dry-python/brand/master/logo/classes.png)](https://github.com/dry-python/classes)

-----

[![Build Status](https://travis-ci.org/dry-python/classes.svg?branch=master)](https://travis-ci.org/dry-python/classes)
[![Coverage Status](https://coveralls.io/repos/github/dry-python/classes/badge.svg?branch=master)](https://coveralls.io/github/dry-python/classes?branch=master)
[![Documentation Status](https://readthedocs.org/projects/classes/badge/?version=latest)](https://classes.readthedocs.io/en/latest/?badge=latest)
[![Python Version](https://img.shields.io/pypi/pyversions/classes.svg)](https://pypi.org/project/classes/)
[![wemake-python-styleguide](https://img.shields.io/badge/style-wemake-000000.svg)](https://github.com/wemake-services/wemake-python-styleguide)
[![Checked with mypy](http://www.mypy-lang.org/static/mypy_badge.svg)](http://mypy-lang.org/)

-----

Smart, pythonic, ad-hoc, typed polymorphism for Python.


## Features

- Provides a bunch of primitives to write declarative business logic
- Enforces better architecture
- Fully typed with annotations and checked with `mypy`, [PEP561 compatible](https://www.python.org/dev/peps/pep-0561/)
- Allows to write a lot of simple code without inheritance or interfaces
- Pythonic and pleasant to write and to read (!)
- Easy to start: has lots of docs, tests, and tutorials


## Installation

```bash
pip install classes
```

You might also want to [configure](https://classes.readthedocs.io/en/latest/pages/container.html#type-safety)
`mypy` correctly and install our plugin
to fix [this existing issue](https://github.com/python/mypy/issues/3157):

```ini
# In setup.cfg or mypy.ini:
[mypy]
plugins =
  classes.contrib.mypy.typeclass_plugin
```

We also recommend to use the same `mypy` settings [we use](https://github.com/wemake-services/wemake-python-styleguide/blob/master/styles/mypy.toml).

Make sure you know how to get started, [check out our docs](https://classes.readthedocs.io/en/latest/)!

