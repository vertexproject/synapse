.. _vtx_300_devops-python-version:

Minimum Python Version 3.14
===========================

Synapse 3.0.0 raises its minimum supported interpreter from Python 3.11 to Python 3.14, and pins to the 3.14 minor
release.

What changed
    Synapse 3.x requires Python 3.14. The package import guard in ``synapse/__init__.py`` now raises when running on
    Python earlier than 3.14 (the 2.x guard raised on versions earlier than 3.11), with the message
    ``synapse is not supported on Python versions < 3.14``.

    The ``pyproject.toml`` ``requires-python`` is now ``>=3.14,<3.15`` (2.x was ``>=3.11``), and the package
    classifiers list ``Programming Language :: Python :: 3.14`` (2.x listed 3.11).

Why
    Moving to the current CPython release lets the codebase rely on newer language and runtime features.

What you need to do
    Provision Python 3.14 (specifically the 3.14.x line) wherever you run Synapse or its client libraries;
    venvs, CI runners, and any host importing the ``synapse`` package. Rebuild any custom images on a 3.14 base.
    The official images already ship 3.14.

    .. code-block:: bash

        # 2.x
        $ python --version
        Python 3.11.x  # supported

        # 3.x
        $ python --version
        Python 3.14.x  # required (>=3.14,<3.15)
        # importing under 3.13 raises:
        #   Exception: synapse is not supported on Python versions < 3.14
