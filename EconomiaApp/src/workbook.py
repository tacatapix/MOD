"""Workbook loader for the Economia app.

Loads the bundled ``Economia.xlsm`` and exposes every sheet as an in-memory
list of rows (each row is a list of cell values).  Cell values are kept as
strings when they came from VBA-generated labels and as their original
Python scalar otherwise.  Sheets are loaded lazily on first access because
the ``Types`` sheet alone has ~55 555 rows.

The class mimics a very small subset of Excel's API used by the original
VBA macros:

* ``ws.cell(row, col)``  -- 1-based cell access, returns ``""`` for empty.
* ``ws.set(row, col, v)``
* ``ws.last_row_from_bottom(col)`` -- equivalent to ``Range("Xm").End(xlUp).Row``.
* ``ws.find(value, start_row=1, start_col=1)`` -- equivalent to ``Cells.Find``.
* ``ws.clear()`` / ``ws.clear_column(col)``
* iteration helpers ``rows`` / ``enumerate_rows``.

The module also exposes :func:`bundled_xlsm_path` which resolves the
embedded workbook whether the app is running from source or from a
PyInstaller bundle.
"""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional, Tuple


def bundled_xlsm_path() -> str:
    """Return the absolute path to the bundled ``Economia.xlsm``.

    Works both from source and when frozen by PyInstaller.
    """
    candidates: List[str] = []

    if hasattr(sys, "_MEIPASS"):
        # PyInstaller extracts resources here at runtime.
        candidates.append(os.path.join(sys._MEIPASS, "resources", "Economia.xlsm"))  # type: ignore[attr-defined]

    here = os.path.dirname(os.path.abspath(__file__))
    candidates.append(os.path.join(here, "..", "resources", "Economia.xlsm"))
    candidates.append(os.path.join(here, "resources", "Economia.xlsm"))

    cwd_local = os.path.join(os.getcwd(), "Economia.xlsm")
    candidates.append(cwd_local)

    for c in candidates:
        if os.path.isfile(c):
            return os.path.abspath(c)

    raise FileNotFoundError(
        "Economia.xlsm não encontrado. Caminhos testados:\n  - "
        + "\n  - ".join(candidates)
    )


def _cell_to_str(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, float):
        if value.is_integer():
            return str(int(value))
        return repr(value)
    return str(value)


@dataclass
class Sheet:
    """A mutable 2-D grid modelling an Excel worksheet (1-based)."""

    name: str
    data: List[List[Any]] = field(default_factory=list)

    # ------------------------------------------------------------------
    # Core accessors
    # ------------------------------------------------------------------
    @property
    def max_row(self) -> int:
        return len(self.data)

    @property
    def max_col(self) -> int:
        return max((len(r) for r in self.data), default=0)

    def _ensure(self, row: int, col: int) -> None:
        while len(self.data) < row:
            self.data.append([])
        r = self.data[row - 1]
        if len(r) < col:
            r.extend([None] * (col - len(r)))

    def cell(self, row: int, col: int) -> Any:
        if row < 1 or col < 1:
            return ""
        if row > len(self.data):
            return ""
        r = self.data[row - 1]
        if col > len(r):
            return ""
        v = r[col - 1]
        return "" if v is None else v

    def cell_str(self, row: int, col: int) -> str:
        return _cell_to_str(self.cell(row, col))

    def set(self, row: int, col: int, value: Any) -> None:
        self._ensure(row, col)
        self.data[row - 1][col - 1] = value

    # ------------------------------------------------------------------
    # VBA-like helpers
    # ------------------------------------------------------------------
    def last_row_from_bottom(self, col: int) -> int:
        """Equivalent to ``Range(col & "1048576").End(xlUp).Row``."""
        for i in range(self.max_row, 0, -1):
            if self.cell(i, col) not in ("", None):
                return i
        return 1

    def last_col_from_right(self, row: int) -> int:
        """Equivalent to ``Cells(row, 16384).End(xlToLeft).Column``."""
        row_data = self.data[row - 1] if row <= self.max_row else []
        for i in range(len(row_data), 0, -1):
            if row_data[i - 1] not in ("", None):
                return i
        return 1

    def end_down(self, row: int, col: int) -> int:
        """Equivalent to ``Cells(row, col).End(xlDown).Row``."""
        max_r = self.max_row
        if self.cell(row, col) in ("", None):
            for i in range(row + 1, max_r + 1):
                if self.cell(i, col) not in ("", None):
                    return i
            return max_r
        # starting at a filled cell: descend while next is filled, else jump to next filled
        if row + 1 <= max_r and self.cell(row + 1, col) in ("", None):
            for i in range(row + 1, max_r + 1):
                if self.cell(i, col) not in ("", None):
                    return i
            return max_r
        for i in range(row + 1, max_r + 1):
            if self.cell(i, col) in ("", None):
                return i - 1
        return max_r

    def end_up(self, row: int, col: int) -> int:
        """Equivalent to ``Cells(row, col).End(xlUp).Row``."""
        if self.cell(row, col) in ("", None):
            for i in range(row - 1, 0, -1):
                if self.cell(i, col) not in ("", None):
                    return i
            return 1
        if row - 1 >= 1 and self.cell(row - 1, col) in ("", None):
            for i in range(row - 1, 0, -1):
                if self.cell(i, col) not in ("", None):
                    return i
            return 1
        for i in range(row - 1, 0, -1):
            if self.cell(i, col) in ("", None):
                return i + 1
        return 1

    def find(
        self,
        what: str,
        start_row: int = 1,
        start_col: int = 1,
        exact: bool = False,
    ) -> Optional[Tuple[int, int]]:
        """Equivalent to ``Cells.Find`` (case-insensitive partial match)."""
        needle = str(what).lower() if not exact else str(what)
        total_rows = self.max_row
        for r in range(start_row, total_rows + 1):
            row = self.data[r - 1]
            start = start_col if r == start_row else 1
            for c in range(start, len(row) + 1):
                v = row[c - 1]
                if v in ("", None):
                    continue
                s = _cell_to_str(v)
                if exact:
                    if s == what:
                        return (r, c)
                else:
                    if needle in s.lower():
                        return (r, c)
        return None

    def find_header(self, header: str, row: int = 1) -> Optional[int]:
        """Find ``header`` on ``row``, returning its column (1-based)."""
        r = self.data[row - 1] if row <= self.max_row else []
        for c, v in enumerate(r, 1):
            if _cell_to_str(v).strip() == header:
                return c
        return None

    def clear(self) -> None:
        self.data = []

    def clear_column(self, col: int) -> None:
        for row in self.data:
            if len(row) >= col:
                row[col - 1] = None

    def replace_in_column(
        self, col: int, what: str, replacement: str, *, whole_cell: bool = False
    ) -> None:
        for row in self.data:
            if len(row) >= col and row[col - 1] not in ("", None):
                s = _cell_to_str(row[col - 1])
                if whole_cell:
                    if s == what:
                        row[col - 1] = replacement
                else:
                    if what in s:
                        row[col - 1] = s.replace(what, replacement)

    def replace_all(self, what: str, replacement: str) -> None:
        for row in self.data:
            for i, v in enumerate(row):
                if v in ("", None):
                    continue
                s = _cell_to_str(v)
                if what in s:
                    row[i] = s.replace(what, replacement)

    # ------------------------------------------------------------------
    # Iteration helpers
    # ------------------------------------------------------------------
    def rows(self) -> Iterable[List[Any]]:
        return iter(self.data)

    def text_rows(self) -> List[List[str]]:
        return [[_cell_to_str(v) for v in row] for row in self.data]

    def to_tsv(self) -> str:
        """Return a TSV string of the current sheet contents."""
        return "\n".join("\t".join(_cell_to_str(c) for c in r) for r in self.data)

    # ------------------------------------------------------------------
    # Row / column edits (for the interactive spreadsheet editor)
    # ------------------------------------------------------------------
    def insert_row(self, row: int) -> None:
        """Insert a blank row *before* ``row`` (1-based)."""
        row = max(1, min(row, self.max_row + 1))
        self.data.insert(row - 1, [])

    def delete_row(self, row: int) -> None:
        if 1 <= row <= self.max_row:
            del self.data[row - 1]

    def insert_col(self, col: int) -> None:
        """Insert a blank column *before* ``col`` (1-based)."""
        for r in self.data:
            if len(r) >= col - 1:
                r.insert(col - 1, None)

    def delete_col(self, col: int) -> None:
        for r in self.data:
            if len(r) >= col:
                del r[col - 1]


class Workbook:
    """In-memory workbook loaded from an .xlsm file."""

    def __init__(self, path: str) -> None:
        self.path = path
        self.sheets: Dict[str, Sheet] = {}
        self._loaded = False

    @classmethod
    def from_bundled(cls) -> "Workbook":
        return cls(bundled_xlsm_path())

    def load(self, progress_cb: Optional[callable] = None) -> None:
        """Load every sheet using openpyxl read-only mode."""
        if self._loaded:
            return

        import openpyxl  # lazy import keeps startup fast

        wb = openpyxl.load_workbook(
            self.path, data_only=True, read_only=True, keep_vba=False
        )
        names = wb.sheetnames
        total = len(names)

        for i, name in enumerate(names, 1):
            if progress_cb:
                progress_cb(i, total, name)
            src = wb[name]
            grid: List[List[Any]] = []
            for row in src.iter_rows(values_only=True):
                grid.append(list(row))
            # Strip fully-empty trailing rows.
            while grid and all(v in ("", None) for v in grid[-1]):
                grid.pop()
            self.sheets[name] = Sheet(name=name, data=grid)
        wb.close()
        self._loaded = True

    # ------------------------------------------------------------------
    # Case-insensitive access (VBA is case-insensitive for sheet names)
    # ------------------------------------------------------------------
    def sheet(self, name: str) -> Sheet:
        if name in self.sheets:
            return self.sheets[name]
        lname = name.lower()
        for k, v in self.sheets.items():
            if k.lower() == lname:
                return v
        raise KeyError(f"Planilha '{name}' não encontrada")

    def __contains__(self, name: str) -> bool:  # noqa: D401
        try:
            self.sheet(name)
            return True
        except KeyError:
            return False

    def __iter__(self):
        return iter(self.sheets.values())

    def names(self) -> List[str]:
        return list(self.sheets.keys())

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------
    def save_as(self, dest_path: str) -> str:
        """Write every in-memory sheet to an .xlsx file.

        Returns the absolute path written.  ``.xlsx`` is used regardless
        of the extension given, so VBA code is never shipped back.
        """
        import openpyxl
        from openpyxl.utils.exceptions import IllegalCharacterError

        wb = openpyxl.Workbook()
        # Remove the default sheet.
        default = wb.active
        wb.remove(default)

        for name, sheet in self.sheets.items():
            # openpyxl sheet names are limited to 31 chars and cannot
            # contain ``[]:*?/\\``.  Trim instead of failing.
            safe = name
            for bad in "[]:*?/\\":
                safe = safe.replace(bad, " ")
            safe = safe[:31] or "Sheet"
            ws = wb.create_sheet(title=safe)
            for row in sheet.data:
                try:
                    ws.append([_cell_to_str(v) if v is not None else None for v in row])
                except IllegalCharacterError:
                    ws.append([
                        (_cell_to_str(v).replace("\x00", "") if v is not None else None)
                        for v in row
                    ])

        if not dest_path.lower().endswith(".xlsx"):
            dest_path += ".xlsx"
        os.makedirs(os.path.dirname(os.path.abspath(dest_path)) or ".", exist_ok=True)
        wb.save(dest_path)
        wb.close()
        return os.path.abspath(dest_path)

    def save_sheet_as(self, sheet_name: str, dest_path: str) -> str:
        """Save a single sheet to its own .xlsx file."""
        import openpyxl
        from openpyxl.utils.exceptions import IllegalCharacterError

        sheet = self.sheet(sheet_name)
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = sheet_name[:31] or "Sheet"
        for row in sheet.data:
            try:
                ws.append([_cell_to_str(v) if v is not None else None for v in row])
            except IllegalCharacterError:
                ws.append([
                    (_cell_to_str(v).replace("\x00", "") if v is not None else None)
                    for v in row
                ])
        if not dest_path.lower().endswith(".xlsx"):
            dest_path += ".xlsx"
        os.makedirs(os.path.dirname(os.path.abspath(dest_path)) or ".", exist_ok=True)
        wb.save(dest_path)
        wb.close()
        return os.path.abspath(dest_path)
