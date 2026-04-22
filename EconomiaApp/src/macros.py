"""Python port of every VBA macro shipped with the Economia workbook.

Each public function accepts a :class:`workbook.Workbook` that has already
been loaded, mutates the relevant sheets in-memory (exactly like the VBA
did on a live Excel instance) and returns the TEXT that the original
VBA copied to the clipboard.

The caller (``gui.py``) is responsible for:

* writing the returned text to disk / clipboard, and
* showing the trailing ``MsgBox`` message to the user.

All behaviour was reproduced from ``xl/vbaProject.bin`` of the source
workbook.  Comments cite the original Portuguese comments so the mapping
is easy to audit against the VBA source.
"""

from __future__ import annotations

import random
import re
from dataclasses import dataclass
from typing import Callable, List, Optional, Tuple

from workbook import Sheet, Workbook, _cell_to_str


ProgressCallback = Optional[Callable[[int, int, str], None]]


# ---------------------------------------------------------------------------
# Utility helpers
# ---------------------------------------------------------------------------
def _s(v) -> str:
    return _cell_to_str(v)


def _find_header(ws: Sheet, header: str, *, row1_only: bool = True) -> int:
    """Locate a header label on row 1 like the VBA Do Until loops.

    Raises ``MacroError`` if the label cannot be found so the caller can
    surface the same message the VBA macros used.
    """
    if row1_only:
        col = ws.find_header(header, row=1)
        if col is None:
            raise MacroError(f"Coluna '{header}' não encontrada em {ws.name}")
        return col
    found = ws.find(header, exact=True)
    if not found:
        raise MacroError(f"Valor '{header}' não encontrado em {ws.name}")
    return found[1]


class MacroError(RuntimeError):
    """Raised when a macro cannot find an expected label/column/row."""


# ---------------------------------------------------------------------------
# GERARTYPES  ->  types.xml
# ---------------------------------------------------------------------------
def gerar_types(wb: Workbook, progress: ProgressCallback = None) -> str:
    """Port of ``TYPES.GERARTYPES``.

    Reads ``ListagemTrader`` + ``PersistênciaOFFTP`` combined with
    ``SetCategorias`` to produce the XML body of ``types.xml``.
    """
    types = wb.sheet("Types")
    sc = wb.sheet("SetCategorias")
    trader = wb.sheet("ListagemTrader")
    persist = wb.sheet("PersistênciaOFFTP")

    types.clear()
    types.set(1, 1, '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>')
    types.set(2, 1, "<types>")

    # -- locate SetCategorias columns ----------------------------------
    sc_headers = [
        "CATEGORIA",
        "CATEGORIAS",
        "<nominal>",
        "<lifetime>",
        "<restock>",
        "<min>",
        "<quantmin>",
        "<quantmax>",
        "<cost>",
        "<flags count_in_cargo=",
        '<category name="',
        '<tag="',
        '<usage name="',
        '<value name="',
    ]
    sc_cols = {h: _find_header(sc, h) for h in sc_headers}
    ul_sc = sc.last_row_from_bottom(1)

    # Build a quick index of (CATEGORIA, CATEGORIAS) -> row on SetCategorias
    sc_index = {}
    for r in range(2, ul_sc + 1):
        k = (_s(sc.cell(r, sc_cols["CATEGORIA"])),
             _s(sc.cell(r, sc_cols["CATEGORIAS"])))
        if k[0] or k[1]:
            sc_index[k] = r

    # -- helpers -------------------------------------------------------
    def _fetch_type_fields(row: int) -> dict:
        out = {
            "nominal": _s(sc.cell(row, sc_cols["<nominal>"])),
            "lifetime": _s(sc.cell(row, sc_cols["<lifetime>"])),
            "restock": _s(sc.cell(row, sc_cols["<restock>"])),
            "min": _s(sc.cell(row, sc_cols["<min>"])),
            "quantmin": _s(sc.cell(row, sc_cols["<quantmin>"])),
            "quantmax": _s(sc.cell(row, sc_cols["<quantmax>"])),
            "cost": _s(sc.cell(row, sc_cols["<cost>"])),
            "flags": _s(sc.cell(row, sc_cols["<flags count_in_cargo="])),
            "category": _s(sc.cell(row, sc_cols['<category name="'])),
            "tag": _s(sc.cell(row, sc_cols['<tag="'])),
            "usages": [
                _s(sc.cell(row, sc_cols['<usage name="'] + i)) for i in range(5)
            ],
            "values": [
                _s(sc.cell(row, sc_cols['<value name="'] + i)) for i in range(4)
            ],
        }
        return out

    lin1 = 2  # will be incremented for each emitted line

    def _emit(produto: str, fields: dict) -> None:
        nonlocal lin1
        lin1 += 1
        types.set(lin1, 2, f'<type name="{produto}">')
        specs = [
            ("nominal", "<nominal>{0}</nominal>"),
            ("lifetime", "<lifetime>{0}</lifetime>"),
            ("restock", "<restock>{0}</restock>"),
            ("min", "<min>{0}</min>"),
            ("quantmin", "<quantmin>{0}</quantmin>"),
            ("quantmax", "<quantmax>{0}</quantmax>"),
            ("cost", "<cost>{0}</cost>"),
        ]
        for key, tmpl in specs:
            if fields[key]:
                lin1 += 1
                types.set(lin1, 3, tmpl.format(fields[key]))
        if fields["flags"]:
            lin1 += 1
            types.set(lin1, 3, f'<flags {fields["flags"]}/>')
        if fields["category"]:
            lin1 += 1
            types.set(lin1, 3, f'<category name="{fields["category"]}"/>')
        if fields["tag"]:
            lin1 += 1
            types.set(lin1, 3, f'<tag name="{fields["tag"]}"/>')
        for u in fields["usages"]:
            if u:
                lin1 += 1
                types.set(lin1, 3, f'<usage name="{u}"/>')
        for v in fields["values"]:
            if v:
                lin1 += 1
                types.set(lin1, 3, f'<value name="{v}"/>')
        lin1 += 1
        types.set(lin1, 2, "</type>")

    # -- walk ListagemTrader -------------------------------------------
    warnings: List[str] = []

    def _walk(src: Sheet, label: str) -> None:
        col_uso = _find_header(src, "USO")
        col_categorias = _find_header(src, "CATEGORIAS")
        col_categoria = _find_header(src, "CATEGORIA")
        col_produto = _find_header(src, "PRODUTO")
        ulinha = src.last_row_from_bottom(col_categoria or 1)

        categoria = ""
        total = ulinha
        for r in range(2, ulinha + 1):
            if progress and r % 500 == 0:
                progress(r, total, f"{label} L{r}")

            cat_val = _s(src.cell(r, col_categoria))
            prod_val = _s(src.cell(r, col_produto))
            uso_val = _s(src.cell(r, col_uso))

            if cat_val and not prod_val:
                categoria = cat_val
                continue

            if not cat_val and prod_val and uso_val == "SIM":
                categorias = _s(src.cell(r, col_categorias))
                key = (categoria, categorias)
                sc_row = sc_index.get(key)
                if sc_row is None:
                    # Warn but continue -- replicates the tolerant behaviour
                    # used by server admins when SetCategorias is incomplete.
                    warnings.append(
                        f"{label} L{r}: ({categoria} / {categorias}) "
                        f"produto {prod_val} sem entrada em SetCategorias"
                    )
                    continue
                _emit(prod_val, _fetch_type_fields(sc_row))

    _walk(trader, "ListagemTrader")
    _walk(persist, "PersistênciaOFFTP")

    # Attach any skipped rows as a trailing comment block so the user knows
    # which products were not emitted.
    if warnings:
        types.set(types.last_row_from_bottom(2) + 2, 1, "<!-- avisos:")
        base = types.max_row
        for i, w in enumerate(warnings, 1):
            types.set(base + i, 1, f"  - {w}")
        types.set(base + len(warnings) + 1, 1, "-->")

    # closing tag -- VBA writes it in column A of the row right below the
    # last non-empty row of column B.
    last_b = types.last_row_from_bottom(2)
    types.set(last_b + 1, 1, "</types>")

    return types.to_tsv()


# ---------------------------------------------------------------------------
# TRATAMENTOTYPES
# ---------------------------------------------------------------------------
def tratamento_types(wb: Workbook) -> str:
    """Port of ``TRATAMENTOTYPES.TRATAMENTOTYPES``.

    Cleans up the ``TRATA TYPES`` sheet (strip the ``<type name="...">``
    framing and spaces) and returns the resulting comma-separated list.
    """
    ws = wb.sheet("TRATA TYPES")
    rows = ws.data
    # Replace the ``<type name="X">`` wrapper and trim spaces.
    cleaned: List[str] = []
    for row in rows:
        for v in row:
            s = _s(v)
            if not s:
                continue
            s = s.replace('<type name="', "").replace('">', ",").replace(" ", "")
            if s:
                cleaned.append(s)
    return ",".join(cleaned)


# ---------------------------------------------------------------------------
# IDENTIFICAÇÃOMOD
# ---------------------------------------------------------------------------
_MOD_MAP: List[Tuple[str, str]] = [
    ("MSP", "Much Stuff Pack"),
    ("MSFC", "MSF-C"),
    ("MVS_", "Multicam Vest System"),
    ("BBP_", "Base Building Plus"),
    ("CPB", "C.P.B. Weapons"),
    ("Mass", "M.a.s.s. Many Item Overhaul"),
    ("HDSN", "Breaching Charge"),
    ("CJ_", "C.J.-187"),
    ("Hecatombe", "Heca.tombe.Pack"),
    ("TTC", "Mortys"),
    ("SNAFU", "S.N.A.F.U."),
    ("AD_", "Advanced Weapon Scopes"),
    ("GCGN", "S.N.A.F.U."),
    ("Rev_", "R.E.V. Weapons"),
    ("A2", "Remastered Arma 2 Weapon"),
    ("KOD_", "K.O.D. Weapons"),
    ("SN_", "S.N.A.F.U."),
    ("ult_", "Ultimate Weapon"),
    ("DP_", "Drugs Plus"),
    ("CP_", "Cannabis Plus"),
    ("MCK", "Much Car Key"),
    ("JebsGuns", "R.E.V. Weapons"),
    ("Spruce", "shd_Ghillie"),
]


def identificacao_mod(wb: Workbook) -> int:
    """Port of ``IDENTIFICAÇÃOMOD.IDENTIFICAÇÃOMOD``.

    The VBA walks column K on ``ListaritensMOD`` and, whenever it finds
    an item whose name *contains* one of the known prefixes, fills the
    ``MOD`` column (K+4) with the pretty name.
    """
    ws = wb.sheet("CLASS BASE" if "ListaritensMOD" not in wb else "ListaritensMOD")
    changed = 0
    for r in range(1, ws.max_row + 1):
        name = _s(ws.cell(r, 11))
        if not name:
            continue
        for prefix, pretty in _MOD_MAP:
            if prefix.lower() in name.lower() and not _s(ws.cell(r, 15)):
                ws.set(r, 15, pretty)
                changed += 1
                break
    return changed


# ---------------------------------------------------------------------------
# GERARTRADERCONFIG
# ---------------------------------------------------------------------------
def gerar_traderconfig(wb: Workbook) -> str:
    """Port of ``TRADERCONFIG.GERARTRADERCONFIG``.

    Copies ``ListagemTrader!H2:M`` to ``TraderConfig`` and appends the
    ``//<OpenFile> FileName.txt`` / ``<FileEnd>`` markers.
    """
    src = wb.sheet("ListagemTrader")
    dst = wb.sheet("TraderConfig")
    dst.clear()
    u = src.last_row_from_bottom(1)

    for r in range(2, u + 1):
        for c in range(8, 14):  # H..M
            v = src.cell(r, c)
            if v not in ("", None):
                dst.set(r - 1, c - 7, v)

    last = dst.last_row_from_bottom(3)
    if last < dst.last_row_from_bottom(1):
        last = dst.last_row_from_bottom(1)
    dst.set(last + 2, 1, "//<OpenFile> FileName.txt")
    dst.set(last + 3, 1, "<FileEnd>")

    return dst.to_tsv()


# ---------------------------------------------------------------------------
# GERARTRADEROBJECTS
# ---------------------------------------------------------------------------
def gerar_traderobjects(wb: Workbook) -> str:
    """Port of ``TRADEROBJECTS.GERARTRADEROBJECTS``.

    Copies ``PosiçãoTrader!B:D`` into ``TraderObjects`` and appends the
    file-terminator markers.
    """
    src = wb.sheet("PosiçãoTrader")
    dst = wb.sheet("TraderObjects")
    dst.clear()

    u = src.last_row_from_bottom(2)
    for r in range(1, u + 1):
        for c in range(2, 5):  # B..D
            v = src.cell(r, c)
            if v not in ("", None):
                dst.set(r, c - 1, v)

    last = dst.last_row_from_bottom(1)
    dst.set(last + 2, 1, "//<OpenFile> FileName.txt")
    dst.set(last + 3, 1, "<FileEnd>")
    return dst.to_tsv()


# ---------------------------------------------------------------------------
# SORTEIO  (lottery for event items)
# ---------------------------------------------------------------------------
def sorteio(wb: Workbook) -> int:
    """Port of ``SORTEIO.SORTEIO``.

    Walks ``DefiniçãoSorteio`` categories, for each one picks a random
    line in ``ListagemTrader`` whose PARTICIPA DO SORTEIO = "SIM" and
    writes the drawn number + product name next to the category.
    """
    plan1 = wb.sheet("DefiniçãoSorteio")
    plan2 = wb.sheet("ListagemTrader")

    col_part = _find_header(plan2, "PARTICIPA DO SORTEIO")
    col_num = _find_header(plan2, "NÚMERO DO SORTEIO")
    col_cat = _find_header(plan2, "CATEGORIA")
    col_prod = _find_header(plan2, "PRODUTO")

    # Build a per-category list of eligible rows.
    eligible: dict = {}
    current_cat = ""
    for r in range(2, plan2.max_row + 1):
        cv = _s(plan2.cell(r, col_cat))
        pv = _s(plan2.cell(r, col_prod))
        part = _s(plan2.cell(r, col_part))
        if cv and not pv:
            current_cat = cv
            continue
        if not cv and pv and part == "SIM":
            eligible.setdefault(current_cat, []).append(
                (int(float(_s(plan2.cell(r, col_num)) or 0)), pv)
            )

    rng = random.Random()
    draws = 0
    # DefiniçãoSorteio: column B holds categories, separators are *** and ///
    col_cat_def = 2
    r = 2
    while r <= plan1.max_row:
        val = _s(plan1.cell(r, col_cat_def))
        if val == "// FIM DO SORTEIO":
            break
        if val in ("***", ""):
            r += 1
            continue
        if val == "///":
            col_cat_def += 5
            r = 2
            continue
        lst = eligible.get(val)
        if not lst:
            r += 1
            continue
        lo = min(x[0] for x in lst)
        hi = max(x[0] for x in lst)
        pool = {x[0]: x[1] for x in lst}
        for _ in range(100):
            pick = rng.randint(lo, hi)
            if pick in pool:
                plan1.set(r, col_cat_def + 1, pick)
                plan1.set(r, col_cat_def + 2, pool[pick])
                draws += 1
                break
        r += 1
    return draws


# ---------------------------------------------------------------------------
# CATEGORIASORTEIO
# ---------------------------------------------------------------------------
def categoria_sorteio(wb: Workbook) -> int:
    """Port of ``CATEGORIASORTEIO.CATEGORIASORTEIO``.

    Enumerates every ``CATEGORIA`` on ``ListagemTrader`` that has at
    least one product with PARTICIPA DO SORTEIO = "SIM" and writes
    (index, categoria) into ``CategoriaSorteio``.
    """
    plan1 = wb.sheet("CategoriaSorteio")
    plan2 = wb.sheet("ListagemTrader")
    col_part = _find_header(plan2, "PARTICIPA DO SORTEIO")
    col_cat = _find_header(plan2, "CATEGORIA")

    # Determine which categories have at least one product with "SIM".
    keep: List[str] = []
    current_cat = ""
    has_sim = False
    for r in range(2, plan2.max_row + 1):
        cv = _s(plan2.cell(r, col_cat))
        part = _s(plan2.cell(r, col_part))
        if cv:
            # Category header row
            if has_sim and current_cat:
                keep.append(current_cat)
            current_cat = cv
            has_sim = False
        elif part == "SIM":
            has_sim = True
    if has_sim and current_cat:
        keep.append(current_cat)

    # Reset destination (leave row 1 as headers)
    for r in range(2, plan1.max_row + 1):
        plan1.set(r, 1, None)
        plan1.set(r, 2, None)
    for i, cat in enumerate(keep, 1):
        plan1.set(i + 1, 1, i)
        plan1.set(i + 1, 2, cat)
    return len(keep)


# ---------------------------------------------------------------------------
# EVENTO*  (CJ187, Airdrop, Treasure, KOTH)
# ---------------------------------------------------------------------------
def _evento_generic(
    wb: Workbook,
    event_key: str,
    event_sheet_name: str,
    indicator: str,
) -> str:
    plan1 = wb.sheet("DefiniçãoSorteio")
    plan2 = wb.sheet(event_sheet_name)

    # Locate header cell that matches event_key anywhere on row 1.
    hit = None
    for c in range(1, plan1.max_col + 1):
        if _s(plan1.cell(1, c)) == event_key:
            hit = (1, c)
            break
    if not hit:
        raise MacroError(f"Evento {event_key} não encontrado em DefiniçãoSorteio")
    _, col1 = hit
    col1 += 3  # same offset VBA uses (ActiveCell.Column + 3)

    # Gather drawn items (PRODUTO column next to resultado).
    items: List[List[str]] = [[]]  # list-of-groups
    r = 2
    while r <= plan1.max_row:
        v = _s(plan1.cell(r, col1))
        if v == "":
            r += 1
            continue
        if v == "///":
            break
        if v == "***":
            items.append([])
        else:
            items[-1].append(v)
        r += 1

    # Find the ``"loot": [`` / ``"Items": [`` anchors in plan2.
    anchors: List[Tuple[int, int]] = []
    for r in range(1, plan2.max_row + 1):
        for c in range(1, plan2.max_col + 1):
            if _s(plan2.cell(r, c)) == indicator:
                anchors.append((r, c))

    if not anchors:
        raise MacroError(f"Indicador {indicator} não encontrado em {event_sheet_name}")

    # Write each group into the corresponding anchor.
    for group, (ar, ac) in zip(items, anchors):
        for i, it in enumerate(group):
            plan2.set(ar + 1 + i, ac + 1, f'"{it}')

    return plan2.to_tsv()


def evento_cj187(wb: Workbook) -> str:
    return _evento_generic(wb, "EVENTOCJ187", "EventosCJ187", '"loot": [')


def evento_airdrop(wb: Workbook) -> str:
    return _evento_generic(wb, "EVENTOAIRDROP", "EventosAirdrop", '"Items": [')


def evento_treasure(wb: Workbook) -> str:
    return _evento_generic(wb, "EVENTOTREASURE", "EventosTreasure", '"loot": [')


def evento_koth(wb: Workbook) -> str:
    # EVENTOKOTH macro exists in the workbook with the same shape; the
    # indicator observed in the sheet data is ``"loot": [``.
    return _evento_generic(wb, "EVENTOKOTH", "EventosKOTH", '"loot": [')


# ---------------------------------------------------------------------------
# ARMASDUPLICADAS
# ---------------------------------------------------------------------------
def armas_duplicadas(wb: Workbook) -> int:
    """Port of ``ARMASDUPLICADAS.ARMASDUPLICADAS``.

    Walks rows 3863..4318 of ``ListaritensMOD`` column K looking for
    duplicates and records the first occurrence row number in column J.
    """
    ws = wb.sheet("CLASS BASE" if "ListaritensMOD" not in wb else "ListaritensMOD")
    marked = 0
    for lin in range(3863, 4319):
        arma = _s(ws.cell(lin, 11))
        if not arma:
            continue
        for linha in range(lin + 1, 4319):
            if _s(ws.cell(linha, 11)) == arma:
                ws.set(linha, 10, lin)
                marked += 1
    return marked


# ---------------------------------------------------------------------------
# TP_GENERAL
# ---------------------------------------------------------------------------
def tp_general(wb: Workbook) -> str:
    """Port of ``TP_GENERAL.TP_GENERAL``.

    Writes the list of TRADER_PLUS names into every ``"Role": "..."``
    placeholder of the ``TP_General`` sheet.
    """
    plan1 = wb.sheet("ListagemTrader")
    plan2 = wb.sheet("TP_General")

    col = _find_header(plan1, "TRADER_PLUS")
    traders: List[str] = []
    for r in range(2, plan1.max_row + 1):
        v = _s(plan1.cell(r, col))
        if v == "FIMTP":
            break
        if v:
            traders.append(v)

    # Find every "Role" cell from row 83 onwards and fill with the next trader.
    it = iter(traders)
    for r in range(83, plan2.max_row + 1):
        for c in range(1, plan2.max_col + 1):
            if _s(plan2.cell(r, c)).strip() == "Role":
                try:
                    name = next(it)
                except StopIteration:
                    return plan2.to_tsv()
                plan2.set(r, c, f'"Role": "{name}",')
    return plan2.to_tsv()


# ---------------------------------------------------------------------------
# TP_IDs
# ---------------------------------------------------------------------------
def tp_ids(wb: Workbook) -> str:
    """Port of ``TP_IDs.TP_IDs`` -> generates TraderPlus ``IDs.json``."""
    plan1 = wb.sheet("ListagemTrader")
    plan2 = wb.sheet("TP_ID's")
    plan2.clear()

    col = _find_header(plan1, "TRADER_PLUS")

    out: List[str] = ["{", '  "Version": "2.3",', '  "IDs": [']
    trader_blocks: List[Tuple[str, str, List[str]]] = []

    r = 2
    current_trader: Optional[Tuple[str, str]] = None
    categorias: List[str] = []
    while r <= plan1.max_row:
        v = _s(plan1.cell(r, col))
        if v == "FIMTP":
            if current_trader is not None:
                trader_blocks.append((current_trader[0], current_trader[1], categorias))
            break
        if v:  # trader header
            if current_trader is not None:
                trader_blocks.append((current_trader[0], current_trader[1], categorias))
            trader_num = _s(plan1.cell(r, col - 1))
            current_trader = (trader_num, v)
            categorias = []
        else:
            cat = _s(plan1.cell(r, col + 1))
            if cat:
                categorias.append(cat)
        r += 1

    for i, (num, name, cats) in enumerate(trader_blocks):
        out.append("  {")
        out.append(f'    "Id": {num},')
        out.append('    "Categories": [')
        for j, c in enumerate(cats):
            sep = "" if j == len(cats) - 1 else ","
            out.append(f'      "{c}"{sep}')
        out.append("    ],")
        out.append('    "LicencesRequired": [],')
        out.append('    "CurrenciesAccepted": []')
        out.append("  }" + ("," if i != len(trader_blocks) - 1 else ""))
    out.append("  ]")
    out.append("}")

    for i, line in enumerate(out, 1):
        plan2.set(i, 1, line)
    return "\n".join(out)


# ---------------------------------------------------------------------------
# TP_Price
# ---------------------------------------------------------------------------
def tp_price(wb: Workbook) -> str:
    """Port of ``TP_Price.TP_Price`` -> generates TraderPlus ``Price.json``."""
    plan1 = wb.sheet("ListagemTrader")
    plan2 = wb.sheet("TP_Price")
    plan2.clear()

    col_cat = _find_header(plan1, "TP_CATEGORIA")

    out: List[str] = [
        "{",
        '  "EnableAutoCalculation": 0,',
        '  "EnableAutoDestockAtRestart": 0,',
        '  "EnableDefaultTraderStock": 0,',
        '  "TraderCategories": [',
    ]

    # Gather categories with their products.
    categorias: List[Tuple[str, List[Tuple[str, str, str, str, str, str, str]]]] = []
    current_cat: Optional[str] = None
    products: List[Tuple[str, str, str, str, str, str, str]] = []
    for r in range(2, plan1.max_row + 1):
        v = _s(plan1.cell(r, col_cat))
        if v == "FIMTP_CAT":
            if current_cat is not None:
                categorias.append((current_cat, products))
            break
        if v:  # category header
            if current_cat is not None:
                categorias.append((current_cat, products))
            current_cat = v
            products = []
        else:
            prod = _s(plan1.cell(r, col_cat + 1))
            if not prod:
                continue
            coef = _s(plan1.cell(r, col_cat + 2))
            est = _s(plan1.cell(r, col_cat + 3))
            qt = _s(plan1.cell(r, col_cat + 4))
            cp = _s(plan1.cell(r, col_cat + 5))
            vd = _s(plan1.cell(r, col_cat + 6))
            destoq = _s(plan1.cell(r, col_cat + 7))
            products.append((prod, coef, est, qt, cp, vd, destoq))

    for i, (cat, prods) in enumerate(categorias):
        out.append("    {")
        out.append(f'      "CategoryName": "{cat}",')
        out.append('      "Products": [')
        for j, (prod, coef, est, qt, cp, vd, destoq) in enumerate(prods):
            sep = "" if j == len(prods) - 1 else ","
            parts = [prod + coef, est, qt, cp, vd]
            if destoq:
                parts.append(destoq)
            payload = ",".join(parts)
            out.append(f'        "{payload}"{sep}')
        out.append("      ]")
        out.append("    }" + ("," if i != len(categorias) - 1 else ""))
    out.append("  ]")
    out.append("}")

    for i, line in enumerate(out, 1):
        plan2.set(i, 1, line)
    return "\n".join(out)


# ---------------------------------------------------------------------------
# SPAWNABLETYPES
# ---------------------------------------------------------------------------
def spawnable_types(wb: Workbook) -> str:
    """Port of ``SPAWNABLETYPES.SPAWNABLETYPES``.

    Generates the Spawnable Types XML from ``Combinações`` + ``SetCombinações``.
    """
    plan1 = wb.sheet("Spawnable")
    plan2 = wb.sheet("SetCombinações")
    plan3 = wb.sheet("Combinações")
    plan1.clear()

    col_categorias = _find_header(plan2, "CATEGORIAS")
    col_integral = _find_header(plan2, "INTEGRAL")
    col_parcial = _find_header(plan2, "PARCIAL")

    set_map = {}
    for r in range(2, plan2.max_row + 1):
        k = _s(plan2.cell(r, col_categorias))
        if not k:
            continue
        set_map[k] = (
            _s(plan2.cell(r, col_integral)),
            _s(plan2.cell(r, col_parcial)),
        )

    c_uso = _find_header(plan3, "USO")
    c_cats = _find_header(plan3, "CATEGORIAS")
    c_armas = _find_header(plan3, "ARMAS")
    c_equip = _find_header(plan3, "EQUIPAMENTOS")

    out: List[str] = []
    arma: Optional[str] = None
    current_category: Optional[str] = None
    category_open = False
    for r in range(2, plan3.max_row + 1):
        uso = _s(plan3.cell(r, c_uso))
        cats = _s(plan3.cell(r, c_cats))
        arma_val = _s(plan3.cell(r, c_armas))
        equip = _s(plan3.cell(r, c_equip))

        if arma_val and not equip:
            # close previous arma if any
            if category_open:
                out.append("        </attachments>")
                category_open = False
            if arma is not None:
                out.append("    </type>")
            arma = arma_val
            out.append(f'    <type name="{arma}">')
            current_category = None
            continue

        if not arma_val and equip and uso == "SIM":
            # new category ?
            if cats != current_category:
                if category_open:
                    out.append("        </attachments>")
                current_category = cats
                integral, parcial = set_map.get(cats, ("", ""))
                out.append(f'        <attachments chance="{integral}">')
                category_open = True
            else:
                integral, parcial = set_map.get(cats, ("", ""))
            out.append(
                f'            <item name="{equip}" chance="{parcial}" />'
            )

    if category_open:
        out.append("        </attachments>")
    if arma is not None:
        out.append("    </type>")

    for i, line in enumerate(out, 1):
        plan1.set(i, 1, line)
    return "\n".join(out)
