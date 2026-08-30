"""Local unit tests for `pipeline/`.

Only modules that hold no data and open no BigQuery client are testable here, which today
means four of them: `disclosure.py` and `cs_spine.py`, which this package covers, and
`01_probe.py` and `02_pregate.py`, which it does not.  Both of the latter run to completion
on a laptop with no cloud access and no credentials (`python3 01_probe.py --self-test` and
`python3 02_pregate.py`) and both carry substantial in-module self-tests.  Everything else
in `pipeline/` needs a Workbench session, so its checking happens as in-module assertions
that are stop conditions at runtime.

THE GAP, WRITTEN DOWN SO IT IS NOT MISTAKEN FOR A DESIGN CHOICE.  The two largest modules
in `pipeline/`, over five thousand lines together, are covered by their own self-tests and
by nothing else: there is no `test_probe.py` and no `test_pregate.py` in this package.  A
self-test that ships inside the module it tests runs only when somebody remembers to run
it, and it cannot fail for a module that was deleted or never imported.  Both filenames
begin with a digit, so a test file cannot `import` them by name and must load them through
`importlib.util.spec_from_file_location`.  `02_pregate.py` already does exactly that for
its own import of `01_probe.py`; copy that pattern rather than inventing a second one.

This file exists so pytest imports the suite as a package and puts `pipeline/` itself on the
path, which is what makes `import disclosure` resolve when the suite is run from `pipeline/`.
"""
