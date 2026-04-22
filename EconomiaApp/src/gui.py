"""Tkinter GUI for the Economia app.

Replicates the ``UserForm1`` menu of the original workbook: one button
per macro plus buttons that open the underlying sheets in a lightweight
viewer/editor.  Generated output is written to ``Saida/`` next to the
executable AND copied to the clipboard exactly like the VBA did.
"""

from __future__ import annotations

import os
import sys
import threading
import tkinter as tk
import traceback
from tkinter import filedialog, messagebox, ttk
from typing import Callable, Dict, List, Optional

import macros
from workbook import Sheet, Workbook, bundled_xlsm_path


APP_TITLE = "Economia DayZ — Gerador de Configurações"
APP_VERSION = "1.0.0"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _output_dir() -> str:
    """Resolve the directory where generated files are saved.

    When running frozen we save next to the executable in ``Saida/``; in
    development we save to ``EconomiaApp/Saida/``.
    """
    if getattr(sys, "frozen", False):
        base = os.path.dirname(os.path.abspath(sys.executable))
    else:
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    out = os.path.join(base, "Saida")
    os.makedirs(out, exist_ok=True)
    return out


def _copy_to_clipboard(root: tk.Tk, text: str) -> None:
    try:
        root.clipboard_clear()
        root.clipboard_append(text)
        root.update()
    except tk.TclError:
        pass


def _save_text(filename: str, text: str) -> str:
    path = os.path.join(_output_dir(), filename)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)
    return path


# ---------------------------------------------------------------------------
# Sheet viewer / editor
# ---------------------------------------------------------------------------
class SheetViewer(tk.Toplevel):
    """Excel-style read/edit view of a :class:`Sheet`.

    Navigation and editing shortcuts (same as Excel/LibreOffice):

    * click a cell to select it;
    * double-click, ``F2`` or ``Enter`` to edit;
    * start typing to replace the contents;
    * ``Enter`` commits and moves down, ``Tab`` commits and moves right,
      ``Escape`` cancels;
    * arrow keys move the selection;
    * ``Ctrl+Z`` undoes the last change;
    * ``Delete`` clears the selected cell;
    * the toolbar has insert/remove row, insert/remove column and
      ``Salvar planilha`` (writes to ``Saida\\Economia_editada.xlsx``).
    """

    MAX_ROWS = 20000  # safety cap; big sheets are paginated

    def __init__(self, master: tk.Tk, sheet: Sheet, on_save_all=None) -> None:
        super().__init__(master)
        self.title(f"{APP_TITLE} — {sheet.name}")
        self.geometry("1200x700")
        self.sheet = sheet
        self._on_save_all = on_save_all
        self._undo_stack: List[tuple] = []  # (row, col, old_value)
        self._selected: Optional[tuple] = None  # (row, col) 1-based
        self._editing = False
        self._build()

    # -- UI ----------------------------------------------------------------
    def _build(self) -> None:
        tb = tk.Frame(self, bg="#eceff1")
        tb.pack(fill="x")
        self._mk_tb_btn(tb, "Salvar planilha", self._save_sheet, "#2e7d32")
        self._mk_tb_btn(tb, "Inserir linha ↑", self._insert_row_above)
        self._mk_tb_btn(tb, "Inserir linha ↓", self._insert_row_below)
        self._mk_tb_btn(tb, "Excluir linha", self._delete_row, "#c62828")
        self._mk_tb_btn(tb, "Inserir coluna ←", self._insert_col_left)
        self._mk_tb_btn(tb, "Inserir coluna →", self._insert_col_right)
        self._mk_tb_btn(tb, "Excluir coluna", self._delete_col, "#c62828")
        self._mk_tb_btn(tb, "Desfazer (Ctrl+Z)", self._undo)

        info = tk.Frame(self)
        info.pack(fill="x", padx=6, pady=(4, 2))
        self._info = tk.StringVar()
        tk.Label(info, textvariable=self._info, font=("Segoe UI", 10)).pack(
            side="left"
        )
        self._cell_label = tk.StringVar(value="-")
        tk.Label(info, textvariable=self._cell_label, font=("Segoe UI", 10, "bold")).pack(
            side="left", padx=16
        )

        # Formula bar.
        fb = tk.Frame(self)
        fb.pack(fill="x", padx=6, pady=(0, 4))
        tk.Label(fb, text="Conteúdo:", font=("Segoe UI", 10)).pack(side="left")
        self._formula_var = tk.StringVar()
        fe = tk.Entry(fb, textvariable=self._formula_var, font=("Segoe UI", 10))
        fe.pack(side="left", fill="x", expand=True, padx=6)
        fe.bind("<Return>", self._commit_formula_bar)
        self._formula_entry = fe

        ncols = max(self.sheet.max_col, 1)
        cols = [f"c{i+1}" for i in range(ncols)]

        tree_frame = tk.Frame(self)
        tree_frame.pack(fill="both", expand=True, padx=4, pady=4)

        self.tree = ttk.Treeview(
            tree_frame,
            columns=cols,
            show="tree headings",
            height=30,
            selectmode="browse",
        )
        self.tree.heading("#0", text="#")
        self.tree.column("#0", width=60, stretch=False, anchor="e")
        for i, c in enumerate(cols, 1):
            self.tree.heading(c, text=self._column_letter(i))
            self.tree.column(c, width=110, stretch=False)

        vsb = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        hsb = ttk.Scrollbar(tree_frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscroll=vsb.set, xscroll=hsb.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")
        tree_frame.rowconfigure(0, weight=1)
        tree_frame.columnconfigure(0, weight=1)

        # Populate rows (capped).
        self._populate_rows()

        # Event bindings.
        self.tree.bind("<Button-1>", self._on_click)
        self.tree.bind("<Double-1>", self._on_dbl_click)
        self.tree.bind("<Key>", self._on_key)
        self.tree.bind("<F2>", self._edit_selected)
        self.tree.bind("<Return>", self._edit_selected)
        self.tree.bind("<Delete>", self._delete_cell)
        self.tree.bind("<BackSpace>", self._delete_cell)
        self.tree.bind("<Up>", lambda e: self._move(-1, 0))
        self.tree.bind("<Down>", lambda e: self._move(1, 0))
        self.tree.bind("<Left>", lambda e: self._move(0, -1))
        self.tree.bind("<Right>", lambda e: self._move(0, 1))
        self.tree.bind("<Tab>", lambda e: self._move(0, 1) or "break")
        self.tree.bind("<Control-z>", lambda e: self._undo())
        self.tree.bind("<Control-Z>", lambda e: self._undo())

        self.tree.tag_configure("sel", background="#ffe082")
        self._refresh_info()
        self._select(1, 1)
        self.tree.focus_set()

    def _mk_tb_btn(self, parent, text, cmd, bg="#546e7a"):
        b = tk.Button(
            parent,
            text=text,
            command=cmd,
            bg=bg,
            fg="white",
            activebackground="#263238",
            activeforeground="white",
            font=("Segoe UI", 9, "bold"),
            bd=0,
            padx=10,
            pady=4,
        )
        b.pack(side="left", padx=2, pady=4)
        return b

    def _populate_rows(self) -> None:
        self.tree.delete(*self.tree.get_children())
        ncols = max(self.sheet.max_col, 1)
        limit = min(self.sheet.max_row, self.MAX_ROWS)
        for i in range(limit):
            row = self.sheet.data[i]
            vals = [(row[j] if j < len(row) else "") for j in range(ncols)]
            vals = ["" if v is None else str(v) for v in vals]
            self.tree.insert("", "end", iid=str(i + 1), text=str(i + 1), values=vals)

        # Ensure there are columns matching the underlying data.
        current = list(self.tree["columns"])
        needed = [f"c{i+1}" for i in range(ncols)]
        if current != needed:
            self.tree["columns"] = needed
            self.tree.heading("#0", text="#")
            self.tree.column("#0", width=60, stretch=False, anchor="e")
            for i, c in enumerate(needed, 1):
                self.tree.heading(c, text=self._column_letter(i))
                self.tree.column(c, width=110, stretch=False)

    @staticmethod
    def _column_letter(col: int) -> str:
        s = ""
        while col > 0:
            col, rem = divmod(col - 1, 26)
            s = chr(65 + rem) + s
        return s

    # -- selection helpers ---------------------------------------------
    def _refresh_info(self) -> None:
        trunc = ""
        if self.sheet.max_row > self.MAX_ROWS:
            trunc = f"  (mostrando {self.MAX_ROWS}/{self.sheet.max_row} linhas)"
        self._info.set(
            f"Planilha: {self.sheet.name}  |  Linhas: {self.sheet.max_row}  "
            f"Colunas: {self.sheet.max_col}{trunc}"
        )

    def _select(self, row: int, col: int) -> None:
        row = max(1, min(row, min(self.sheet.max_row, self.MAX_ROWS)))
        col = max(1, min(col, self.sheet.max_col or 1))
        prev = self._selected
        self._selected = (row, col)
        # Update tags to highlight the row.
        if prev:
            try:
                self.tree.item(str(prev[0]), tags=())
            except tk.TclError:
                pass
        try:
            self.tree.item(str(row), tags=("sel",))
        except tk.TclError:
            pass
        self.tree.selection_set(str(row))
        self.tree.focus(str(row))
        self.tree.see(str(row))
        self._cell_label.set(f"{self._column_letter(col)}{row}")
        self._formula_var.set(self.sheet.cell_str(row, col))

    def _move(self, dr: int, dc: int) -> None:
        if self._editing or not self._selected:
            return
        r, c = self._selected
        self._select(r + dr, c + dc)

    # -- event handlers ------------------------------------------------
    def _on_click(self, event) -> None:
        row_id = self.tree.identify_row(event.y)
        col_id = self.tree.identify_column(event.x)
        if not row_id:
            return
        col_index = int(col_id.replace("#", "")) if col_id else 1
        # column #0 is the row-number pseudo-column
        if col_index <= 0:
            col_index = 1
        self._select(int(row_id), col_index)

    def _on_dbl_click(self, event) -> None:
        self._on_click(event)
        self._edit_selected(event)

    def _on_key(self, event) -> None:
        if self._editing or not self._selected:
            return
        # Printable character starts edit.
        if event.char and event.char.isprintable() and not (event.state & 0x4):  # no Ctrl
            self._edit_selected(event, prefill=event.char)
            return "break"

    def _edit_selected(self, _event=None, *, prefill: Optional[str] = None) -> None:
        if not self._selected:
            return
        row, col = self._selected
        col_id = f"#{col}"
        try:
            bbox = self.tree.bbox(str(row), col_id)
        except tk.TclError:
            bbox = None
        if not bbox:
            # scroll and retry
            self.tree.see(str(row))
            self.update_idletasks()
            bbox = self.tree.bbox(str(row), col_id)
            if not bbox:
                return
        x, y, w, h = bbox
        current = self.sheet.cell_str(row, col)
        entry = tk.Entry(self.tree, font=("Segoe UI", 10))
        entry.place(x=x, y=y, width=max(w, 80), height=h)
        if prefill is not None:
            entry.insert(0, prefill)
        else:
            entry.insert(0, current)
            entry.select_range(0, "end")
        entry.focus()
        self._editing = True

        def commit(_evt=None, advance: tuple = (1, 0)):
            new = entry.get()
            if new != current:
                self._push_undo(row, col, self.sheet.cell(row, col))
                self.sheet.set(row, col, new)
                cols = list(self.tree["columns"])
                if col - 1 < len(cols):
                    self.tree.set(str(row), cols[col - 1], new)
            entry.destroy()
            self._editing = False
            self._move(*advance)

        def cancel(_evt=None):
            entry.destroy()
            self._editing = False
            self.tree.focus_set()

        entry.bind("<Return>", lambda e: commit(advance=(1, 0)))
        entry.bind("<Tab>", lambda e: commit(advance=(0, 1)) or "break")
        entry.bind("<Shift-Tab>", lambda e: commit(advance=(0, -1)) or "break")
        entry.bind("<Escape>", cancel)
        entry.bind("<FocusOut>", lambda e: commit(advance=(0, 0)))

    def _commit_formula_bar(self, _evt=None) -> None:
        if not self._selected:
            return
        row, col = self._selected
        new = self._formula_var.get()
        old = self.sheet.cell(row, col)
        if _cell_to_str_equivalent(old, new):
            return
        self._push_undo(row, col, old)
        self.sheet.set(row, col, new)
        cols = list(self.tree["columns"])
        if col - 1 < len(cols):
            self.tree.set(str(row), cols[col - 1], new)
        self.tree.focus_set()

    def _delete_cell(self, _evt=None) -> None:
        if self._editing or not self._selected:
            return
        row, col = self._selected
        old = self.sheet.cell(row, col)
        if old in ("", None):
            return
        self._push_undo(row, col, old)
        self.sheet.set(row, col, "")
        cols = list(self.tree["columns"])
        if col - 1 < len(cols):
            self.tree.set(str(row), cols[col - 1], "")
        self._formula_var.set("")

    # -- row / column ops ---------------------------------------------
    def _insert_row_above(self) -> None:
        if not self._selected:
            return
        row, _ = self._selected
        self.sheet.insert_row(row)
        self._push_undo("insert_row", row)
        self._populate_rows()
        self._refresh_info()
        self._select(row, self._selected[1] if self._selected else 1)

    def _insert_row_below(self) -> None:
        if not self._selected:
            return
        row, _ = self._selected
        self.sheet.insert_row(row + 1)
        self._push_undo("insert_row", row + 1)
        self._populate_rows()
        self._refresh_info()
        self._select(row + 1, self._selected[1] if self._selected else 1)

    def _delete_row(self) -> None:
        if not self._selected:
            return
        row, _ = self._selected
        if not messagebox.askyesno(APP_TITLE, f"Excluir linha {row}?"):
            return
        old_row = list(self.sheet.data[row - 1]) if row <= self.sheet.max_row else []
        self.sheet.delete_row(row)
        self._push_undo("delete_row", row, old_row)
        self._populate_rows()
        self._refresh_info()
        self._select(min(row, self.sheet.max_row), self._selected[1])

    def _insert_col_left(self) -> None:
        if not self._selected:
            return
        _, col = self._selected
        self.sheet.insert_col(col)
        self._push_undo("insert_col", col)
        self._populate_rows()
        self._refresh_info()

    def _insert_col_right(self) -> None:
        if not self._selected:
            return
        _, col = self._selected
        self.sheet.insert_col(col + 1)
        self._push_undo("insert_col", col + 1)
        self._populate_rows()
        self._refresh_info()

    def _delete_col(self) -> None:
        if not self._selected:
            return
        _, col = self._selected
        letter = self._column_letter(col)
        if not messagebox.askyesno(APP_TITLE, f"Excluir coluna {letter}?"):
            return
        old_col = [
            (r[col - 1] if len(r) >= col else None) for r in self.sheet.data
        ]
        self.sheet.delete_col(col)
        self._push_undo("delete_col", col, old_col)
        self._populate_rows()
        self._refresh_info()

    # -- undo ---------------------------------------------------------
    def _push_undo(self, *args) -> None:
        self._undo_stack.append(args)
        if len(self._undo_stack) > 500:
            self._undo_stack = self._undo_stack[-500:]

    def _undo(self, _evt=None) -> None:
        if self._editing or not self._undo_stack:
            return
        action = self._undo_stack.pop()
        kind = action[0]
        if isinstance(kind, int):  # cell edit: (row, col, old_value)
            r, c, old = action
            self.sheet.set(r, c, old)
            cols = list(self.tree["columns"])
            if c - 1 < len(cols):
                self.tree.set(
                    str(r), cols[c - 1], "" if old in ("", None) else str(old)
                )
            self._select(r, c)
        elif kind == "insert_row":
            _, r = action
            self.sheet.delete_row(r)
            self._populate_rows()
            self._refresh_info()
        elif kind == "delete_row":
            _, r, old = action
            self.sheet.insert_row(r)
            for i, v in enumerate(old, 1):
                if v not in ("", None):
                    self.sheet.set(r, i, v)
            self._populate_rows()
            self._refresh_info()
        elif kind == "insert_col":
            _, c = action
            self.sheet.delete_col(c)
            self._populate_rows()
            self._refresh_info()
        elif kind == "delete_col":
            _, c, old = action
            self.sheet.insert_col(c)
            for i, v in enumerate(old, 1):
                if v not in ("", None):
                    self.sheet.set(i, c, v)
            self._populate_rows()
            self._refresh_info()

    # -- save ---------------------------------------------------------
    def _save_sheet(self) -> None:
        if self._on_save_all is None:
            messagebox.showinfo(APP_TITLE, "Salve a partir da janela principal.")
            return
        self._on_save_all()


def _cell_to_str_equivalent(a, b) -> bool:
    def norm(x):
        if x is None:
            return ""
        return str(x)
    return norm(a) == norm(b)


# ---------------------------------------------------------------------------
# Main window
# ---------------------------------------------------------------------------
class EconomiaApp:
    def __init__(self) -> None:
        self.root = tk.Tk()
        self.root.title(f"{APP_TITLE}  v{APP_VERSION}")
        self.root.geometry("1000x720")

        self.wb: Optional[Workbook] = None
        self.status_var = tk.StringVar(value="Carregando planilha...")

        self._build_ui()
        self.root.after(200, self._load_async)

    # ------------------------------------------------------------------
    # UI layout
    # ------------------------------------------------------------------
    def _build_ui(self) -> None:
        header = tk.Frame(self.root, bg="#1b5e20", height=70)
        header.pack(fill="x")
        tk.Label(
            header,
            text="ECONOMIA DAYZ",
            font=("Segoe UI", 20, "bold"),
            fg="white",
            bg="#1b5e20",
        ).pack(side="left", padx=16, pady=14)
        tk.Label(
            header,
            text=APP_VERSION,
            fg="#c8e6c9",
            bg="#1b5e20",
            font=("Segoe UI", 10),
        ).pack(side="left", pady=20)

        notebook = ttk.Notebook(self.root)
        notebook.pack(fill="both", expand=True, padx=10, pady=10)

        # -- Tab: Geração -------------------------------------------------
        tab_gen = tk.Frame(notebook)
        notebook.add(tab_gen, text="Geração")

        actions: List[tuple] = [
            ("Gerar Types.xml", self._run_gerar_types, "types.xml"),
            ("Tratar Types (limpeza)", self._run_tratamento, "trata_types.txt"),
            ("Identificação MOD", self._run_identif, None),
            ("Gerar TraderConfig", self._run_traderconfig, "TraderConfig.txt"),
            ("Gerar TraderObjects", self._run_traderobjects, "TraderObjects.txt"),
            ("Gerar TP_General", self._run_tp_general, "TP_General.txt"),
            ("Gerar TP_IDs (TraderPlus)", self._run_tp_ids, "TP_IDs.json"),
            ("Gerar TP_Price (TraderPlus)", self._run_tp_price, "TP_Price.json"),
            ("Gerar SpawnableTypes", self._run_spawnable, "SpawnableTypes.xml"),
            ("Armas Duplicadas", self._run_armas_dup, None),
        ]
        self._make_button_grid(tab_gen, actions, title="Geração principal")

        # -- Tab: Eventos -------------------------------------------------
        tab_ev = tk.Frame(notebook)
        notebook.add(tab_ev, text="Eventos")
        events = [
            ("Sorteio de itens (SORTEIO)", self._run_sorteio, None),
            ("Categorias do Sorteio", self._run_cat_sorteio, None),
            ("Evento CJ187", lambda: self._run_evento("cj187"), "EventosCJ187.txt"),
            (
                "Evento Airdrop",
                lambda: self._run_evento("airdrop"),
                "EventosAirdrop.txt",
            ),
            (
                "Evento Treasure",
                lambda: self._run_evento("treasure"),
                "EventosTreasure.txt",
            ),
            ("Evento KOTH", lambda: self._run_evento("koth"), "EventosKOTH.txt"),
        ]
        self._make_button_grid(tab_ev, events, title="Eventos / sorteios")

        # -- Tab: Planilhas ----------------------------------------------
        tab_sh = tk.Frame(notebook)
        notebook.add(tab_sh, text="Planilhas")
        tk.Label(
            tab_sh,
            text="Abrir planilhas do workbook (visualizar e editar)",
            font=("Segoe UI", 11, "bold"),
        ).pack(anchor="w", padx=10, pady=(10, 4))
        self.sheet_list = tk.Listbox(tab_sh, height=20)
        self.sheet_list.pack(fill="both", expand=True, padx=10, pady=6)
        btns = tk.Frame(tab_sh)
        btns.pack(fill="x", padx=10, pady=6)
        tk.Button(
            btns, text="Abrir planilha", command=self._open_selected_sheet
        ).pack(side="left")
        tk.Button(btns, text="Exportar CSV", command=self._export_csv).pack(
            side="left", padx=8
        )
        tk.Button(
            btns,
            text="Salvar tudo (XLSX)",
            command=self._save_workbook,
            bg="#2e7d32",
            fg="white",
        ).pack(side="left", padx=8)
        tk.Button(
            btns,
            text="Salvar planilha atual",
            command=self._save_current_sheet,
        ).pack(side="left", padx=8)

        self.sheet_list.bind(
            "<Double-Button-1>", lambda _e: self._open_selected_sheet()
        )

        # -- Tab: Sobre ---------------------------------------------------
        tab_ab = tk.Frame(notebook)
        notebook.add(tab_ab, text="Sobre")
        tk.Label(
            tab_ab,
            text=(
                "Este aplicativo substitui o workbook VBA Economia_16.01.2023.xlsm.\n"
                "Cada botão executa a macro correspondente, grava o resultado em\n"
                "'Saida\\' e copia o texto para a área de transferência."
            ),
            font=("Segoe UI", 11),
            justify="left",
        ).pack(anchor="w", padx=20, pady=20)
        tk.Label(
            tab_ab,
            text=f"Versão: {APP_VERSION}\nAutor: tacatapix / PackFazupix",
            font=("Segoe UI", 10),
        ).pack(anchor="w", padx=20)

        # -- Status bar ---------------------------------------------------
        sb = tk.Frame(self.root, bg="#263238", height=24)
        sb.pack(side="bottom", fill="x")
        tk.Label(
            sb,
            textvariable=self.status_var,
            fg="white",
            bg="#263238",
            anchor="w",
        ).pack(fill="x", padx=10)

    def _make_button_grid(
        self, parent: tk.Frame, items: List[tuple], title: str
    ) -> None:
        tk.Label(
            parent,
            text=title,
            font=("Segoe UI", 13, "bold"),
        ).pack(anchor="w", padx=10, pady=(10, 0))
        grid = tk.Frame(parent)
        grid.pack(fill="both", expand=True, padx=10, pady=10)
        for i, (label, action, _output) in enumerate(items):
            b = tk.Button(
                grid,
                text=label,
                command=action,
                width=36,
                height=2,
                bg="#2e7d32",
                fg="white",
                activebackground="#1b5e20",
                activeforeground="white",
                font=("Segoe UI", 10, "bold"),
            )
            b.grid(row=i // 2, column=i % 2, padx=8, pady=6, sticky="ew")
        for c in range(2):
            grid.columnconfigure(c, weight=1)

    # ------------------------------------------------------------------
    # Loading
    # ------------------------------------------------------------------
    def _load_async(self) -> None:
        def job() -> None:
            try:
                path = bundled_xlsm_path()
                self._update_status(f"Lendo {os.path.basename(path)}...")
                wb = Workbook(path)
                wb.load(
                    progress_cb=lambda i, n, name: self._update_status(
                        f"Carregando {name} ({i}/{n})"
                    )
                )
                self.wb = wb
                self.root.after(0, self._on_loaded)
            except Exception as exc:  # pragma: no cover - GUI feedback
                tb = traceback.format_exc()
                self.root.after(
                    0,
                    lambda: messagebox.showerror(
                        "Falha ao carregar workbook", f"{exc}\n\n{tb}"
                    ),
                )

        threading.Thread(target=job, daemon=True).start()

    def _on_loaded(self) -> None:
        assert self.wb is not None
        for name in self.wb.names():
            self.sheet_list.insert("end", name)
        self._update_status(
            f"Pronto. {len(self.wb.names())} planilhas carregadas. Saída: {_output_dir()}"
        )

    def _update_status(self, msg: str) -> None:
        self.status_var.set(msg)

    # ------------------------------------------------------------------
    # Macro runners
    # ------------------------------------------------------------------
    def _guard(self) -> bool:
        if self.wb is None:
            messagebox.showwarning(APP_TITLE, "A planilha ainda está carregando.")
            return False
        return True

    def _run_generic(
        self,
        name: str,
        fn: Callable[[Workbook], object],
        out_file: Optional[str],
        success_msg: str,
    ) -> None:
        if not self._guard():
            return
        assert self.wb is not None

        def job():
            try:
                self._update_status(f"Executando {name}...")
                result = fn(self.wb)  # type: ignore[arg-type]
                text = result if isinstance(result, str) else str(result)
                if out_file:
                    path = _save_text(out_file, text)
                    self._update_status(f"Gerado {out_file}")
                else:
                    path = None
                _copy_to_clipboard(self.root, text)
                msg = success_msg
                if path:
                    msg += f"\n\nArquivo: {path}"
                msg += "\n(Texto também copiado para a área de transferência.)"
                self.root.after(0, lambda: messagebox.showinfo(APP_TITLE, msg))
            except macros.MacroError as e:
                self.root.after(
                    0, lambda: messagebox.showwarning(APP_TITLE, str(e))
                )
            except Exception as e:  # pragma: no cover - GUI feedback
                tb = traceback.format_exc()
                self.root.after(
                    0,
                    lambda: messagebox.showerror(
                        APP_TITLE, f"Falha em {name}: {e}\n\n{tb}"
                    ),
                )

        threading.Thread(target=job, daemon=True).start()

    # -- Individual macros -------------------------------------------------
    def _run_gerar_types(self) -> None:
        self._run_generic(
            "GERARTYPES",
            macros.gerar_types,
            "types.xml",
            "A aplicação terminou o processo de geração do arquivo Types.",
        )

    def _run_tratamento(self) -> None:
        self._run_generic(
            "TRATAMENTOTYPES",
            macros.tratamento_types,
            "trata_types.txt",
            "Tratamento dos Types concluído.",
        )

    def _run_identif(self) -> None:
        if not self._guard():
            return
        try:
            n = macros.identificacao_mod(self.wb)  # type: ignore[arg-type]
            messagebox.showinfo(
                APP_TITLE,
                f"Identificação MOD concluída: {n} itens marcados.",
            )
        except macros.MacroError as e:
            messagebox.showwarning(APP_TITLE, str(e))

    def _run_traderconfig(self) -> None:
        self._run_generic(
            "GERARTRADERCONFIG",
            macros.gerar_traderconfig,
            "TraderConfig.txt",
            "Arquivo TraderConfig gerado.",
        )

    def _run_traderobjects(self) -> None:
        self._run_generic(
            "GERARTRADEROBJECTS",
            macros.gerar_traderobjects,
            "TraderObjects.txt",
            "Arquivo TraderObjects gerado.",
        )

    def _run_tp_general(self) -> None:
        self._run_generic(
            "TP_GENERAL",
            macros.tp_general,
            "TP_General.txt",
            "Atualização do TP_General concluída.",
        )

    def _run_tp_ids(self) -> None:
        self._run_generic(
            "TP_IDs",
            macros.tp_ids,
            "TP_IDs.json",
            "Atualização do TP_IDs concluída.",
        )

    def _run_tp_price(self) -> None:
        self._run_generic(
            "TP_Price",
            macros.tp_price,
            "TP_Price.json",
            "Atualização do TP_Price concluída.",
        )

    def _run_spawnable(self) -> None:
        self._run_generic(
            "SPAWNABLETYPES",
            macros.spawnable_types,
            "SpawnableTypes.xml",
            "SpawnableTypes gerado com sucesso.",
        )

    def _run_armas_dup(self) -> None:
        if not self._guard():
            return
        try:
            n = macros.armas_duplicadas(self.wb)  # type: ignore[arg-type]
            messagebox.showinfo(
                APP_TITLE, f"Armas duplicadas marcadas: {n}."
            )
        except macros.MacroError as e:
            messagebox.showwarning(APP_TITLE, str(e))

    def _run_sorteio(self) -> None:
        if not self._guard():
            return
        try:
            n = macros.sorteio(self.wb)  # type: ignore[arg-type]
            messagebox.showinfo(APP_TITLE, f"SORTEIO concluído: {n} itens sorteados.")
        except macros.MacroError as e:
            messagebox.showwarning(APP_TITLE, str(e))

    def _run_cat_sorteio(self) -> None:
        if not self._guard():
            return
        try:
            n = macros.categoria_sorteio(self.wb)  # type: ignore[arg-type]
            messagebox.showinfo(APP_TITLE, f"Categorias de sorteio: {n}.")
        except macros.MacroError as e:
            messagebox.showwarning(APP_TITLE, str(e))

    def _run_evento(self, key: str) -> None:
        fn_map: Dict[str, Callable] = {
            "cj187": (macros.evento_cj187, "EventosCJ187.txt"),
            "airdrop": (macros.evento_airdrop, "EventosAirdrop.txt"),
            "treasure": (macros.evento_treasure, "EventosTreasure.txt"),
            "koth": (macros.evento_koth, "EventosKOTH.txt"),
        }
        fn, out = fn_map[key]
        self._run_generic(
            f"EVENTO {key.upper()}",
            fn,
            out,
            f"Evento {key.upper()} preenchido.",
        )

    # ------------------------------------------------------------------
    # Sheet viewer
    # ------------------------------------------------------------------
    def _open_selected_sheet(self) -> None:
        if not self._guard():
            return
        sel = self.sheet_list.curselection()
        if not sel:
            return
        name = self.sheet_list.get(sel[0])
        SheetViewer(
            self.root,
            self.wb.sheet(name),  # type: ignore[union-attr]
            on_save_all=self._save_workbook,
        )

    def _current_sheet_name(self) -> Optional[str]:
        sel = self.sheet_list.curselection()
        if not sel:
            return None
        return self.sheet_list.get(sel[0])

    def _save_workbook(self) -> None:
        if not self._guard():
            return
        assert self.wb is not None
        default = os.path.join(_output_dir(), "Economia_editada.xlsx")
        path = filedialog.asksaveasfilename(
            title="Salvar workbook como...",
            defaultextension=".xlsx",
            initialfile=os.path.basename(default),
            initialdir=os.path.dirname(default),
            filetypes=[("Excel XLSX", "*.xlsx")],
        )
        if not path:
            return

        def job():
            try:
                self._update_status("Salvando workbook...")
                out = self.wb.save_as(path)  # type: ignore[union-attr]
                self._update_status(f"Salvo em {out}")
                self.root.after(
                    0,
                    lambda: messagebox.showinfo(APP_TITLE, f"Workbook salvo em:\n{out}"),
                )
            except Exception as e:
                tb = traceback.format_exc()
                self.root.after(
                    0, lambda: messagebox.showerror(APP_TITLE, f"Erro ao salvar:\n{e}\n\n{tb}")
                )

        threading.Thread(target=job, daemon=True).start()

    def _save_current_sheet(self) -> None:
        if not self._guard():
            return
        name = self._current_sheet_name()
        if not name:
            messagebox.showinfo(APP_TITLE, "Selecione uma planilha na lista.")
            return
        default = os.path.join(_output_dir(), f"{name}.xlsx")
        path = filedialog.asksaveasfilename(
            title=f"Salvar planilha {name}",
            defaultextension=".xlsx",
            initialfile=os.path.basename(default),
            initialdir=os.path.dirname(default),
            filetypes=[("Excel XLSX", "*.xlsx")],
        )
        if not path:
            return
        try:
            out = self.wb.save_sheet_as(name, path)  # type: ignore[union-attr]
            messagebox.showinfo(APP_TITLE, f"Planilha salva em:\n{out}")
        except Exception as e:
            tb = traceback.format_exc()
            messagebox.showerror(APP_TITLE, f"Erro ao salvar:\n{e}\n\n{tb}")

    def _export_csv(self) -> None:
        if not self._guard():
            return
        sel = self.sheet_list.curselection()
        if not sel:
            return
        name = self.sheet_list.get(sel[0])
        path = filedialog.asksaveasfilename(
            title=f"Exportar {name}",
            defaultextension=".csv",
            initialfile=f"{name}.csv",
        )
        if not path:
            return
        sheet = self.wb.sheet(name)  # type: ignore[union-attr]
        import csv

        with open(path, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            for row in sheet.data:
                w.writerow(["" if v is None else v for v in row])
        messagebox.showinfo(APP_TITLE, f"Exportado para {path}")

    # ------------------------------------------------------------------
    def run(self) -> None:  # pragma: no cover - manual entrypoint
        self.root.mainloop()


def main() -> None:  # pragma: no cover - manual entrypoint
    try:
        EconomiaApp().run()
    except Exception:
        tb = traceback.format_exc()
        try:
            messagebox.showerror(APP_TITLE, tb)
        except Exception:
            print(tb, file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":  # pragma: no cover
    main()
