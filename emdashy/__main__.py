"""Allow ``python -m emdashy`` as an alias for the ``emdash`` CLI."""

from .cli import main

if __name__ == "__main__":
    raise SystemExit(main())
