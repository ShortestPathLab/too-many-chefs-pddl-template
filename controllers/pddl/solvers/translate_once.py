"""Run a Fast Downward translator once, as a script in its own process.

Usage: ``python translate_once.py TRANSLATOR_DIR DOMAIN TASK [OPTIONS...]``,
where ``TRANSLATOR_DIR`` holds the ``translate`` package.

This does what the translator's ``python -m translate`` entry point does, with
the same exit codes. That entry point in up-fast-downward 0.5.2 calls ``main()``
a second time after the first returns, so every task was translated twice.
"""

import sys

TRANSLATE_OUT_OF_MEMORY = 20
TRANSLATE_INPUT_ERROR = 31

if __name__ == "__main__":
    sys.path.insert(0, sys.argv.pop(1))

    from translate import pddl_parser  # ty: ignore[unresolved-import]
    from translate.main import main  # ty: ignore[unresolved-import]
    from translate.options import set_options  # ty: ignore[unresolved-import]

    set_options(sys.argv[1:])
    try:
        main()
    except MemoryError:
        print("Translator ran out of memory")
        sys.exit(TRANSLATE_OUT_OF_MEMORY)
    except pddl_parser.ParseError as error:
        print(error)
        sys.exit(TRANSLATE_INPUT_ERROR)
