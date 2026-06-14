"""Repository-root compatibility shim for Energy Aware Code.

The implementation lives in ``estimador-cag/energy_core`` because this
incubator branch still shares the AI Engineering course repository. This shim
keeps the developer command ergonomic from the repository root:

    python -m energy_core.cli ...

It should stay tiny. Product code belongs in ``estimador-cag/energy_core`` until
Energy Aware Code is extracted into its own repository.
"""

from pathlib import Path

_ACTUAL_PACKAGE = Path(__file__).resolve().parents[1] / "estimador-cag" / "energy_core"

if not _ACTUAL_PACKAGE.is_dir():
    msg = f"Energy Core implementation package not found at {_ACTUAL_PACKAGE}"
    raise ImportError(msg)

__path__ = [str(_ACTUAL_PACKAGE)]
