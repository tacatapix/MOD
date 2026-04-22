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
    """Simple read/edit view of a ``Sheet``.

    Uses a ``ttk.Treeview`` for speed because some sheets (notably the
    ``Types`` sheet) are huge.  Editing a cell happens in-place through
    double-click.
    """

    MAX_ROWS = 5000  # safety cap for huge sheets

    def __init__(self, master: tk.Tk, sheet: Sheet) -> None:
        super().__init__(master)
        self.title(f"{APP_TITLE} — {sheet.name}")
        self.geometry("1100x650")
        self.sheet = sheet
        self._build()

    # -- UI ----------------------------------------------------------------
    def _build(self) -> None:
        top = tk.Frame(self)
        top.pack(fill="x", padx=4, pady=4)
        tk.Label(top, text=f"Planilha: {self.sheet.name}").pack(side="left")
        tk.Label(
            top,
            text=f"  Linhas: {self.sheet.max_row}  Colunas: {self.sheet.max_col}",
        ).pack(side="left")

        truncated = self.sheet.max_row > self.MAX_ROWS
        if truncated:
            tk.Label(
                top,
                text=f"(exibindo as primeiras {self.MAX_ROWS} linhas para performance)",
                fg="#c07",
            ).pack(side="left")

        ncols = max(self.sheet.max_col, 1)
        cols = [f"c{i+1}" for i in range(ncols)]

        tree_frame = tk.Frame(self)
        tree_frame.pack(fill="both", expand=True, padx=4, pady=4)

        self.tree = ttk.Treeview(
            tree_frame, columns=cols, show="headings", height=30
        )
        for i, c in enumerate(cols, 1):
            self.tree.heading(c, text=self._column_letter(i))
            self.tree.column(c, width=100, stretch=False)

        vsb = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        hsb = ttk.Scrollbar(tree_frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscroll=vsb.set, xscroll=hsb.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")
        tree_frame.rowconfigure(0, weight=1)
        tree_frame.columnconfigure(0, weight=1)

        self.tree.bind("<Double-1>", self._edit_cell)

        limit = min(self.sheet.max_row, self.MAX_ROWS)
        for i in range(limit):
            row = self.sheet.data[i]
            vals = [(row[j] if j < len(row) else "") for j in range(ncols)]
            vals = ["" if v is None else str(v) for v in vals]
            self.tree.insert("", "end", iid=str(i + 1), values=vals)

    @staticmethod
    def _column_letter(col: int) -> str:
        s = ""
        while col > 0:
            col, rem = divmod(col - 1, 26)
            s = chr(65 + rem) + s
        return s

    def _edit_cell(self, event) -> None:
        row_id = self.tree.identify_row(event.y)
        col_id = self.tree.identify_column(event.x)
        if not row_id or not col_id:
            return
        col_index = int(col_id.replace("#", "")) - 1
        if col_index < 0:
            return
        x, y, w, h = self.tree.bbox(row_id, col_id)
        current = self.tree.set(row_id, self.tree["columns"][col_index])

        entry = tk.Entry(self.tree)
        entry.place(x=x, y=y, width=w, height=h)
        entry.insert(0, current)
        entry.focus()

        def commit(_evt=None):
            new = entry.get()
            self.tree.set(row_id, self.tree["columns"][col_index], new)
            self.sheet.set(int(row_id), col_index + 1, new)
            entry.destroy()

        entry.bind("<Return>", commit)
        entry.bind("<FocusOut>", lambda e: entry.destroy())


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
        SheetViewer(self.root, self.wb.sheet(name))  # type: ignore[arg-type]

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
