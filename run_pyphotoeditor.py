"""Convenience launcher so users can run `python run_pyphotoeditor.py`
instead of `python -m pyphotoeditor.main`."""
from pyphotoeditor.main import main

if __name__ == "__main__":
    raise SystemExit(main())
