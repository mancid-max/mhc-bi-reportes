from __future__ import annotations

import csv
import os
from pathlib import Path
from flask import Flask, render_template

app = Flask(__name__)

BI_DIR   = Path(os.environ.get("BI_REPORTES_BI_DIR", r"Z:\BI"))
SEED_DIR = Path(__file__).parent / "seed"

COLECCIONES           = ["40", "41", "42", "43"]
TEMPORADAS_HISTORICAS = {"40", "41", "42"}
TEMPORADAS_ACTUALES   = {"43", "44"}


def _read_csv(path: Path) -> list[dict]:
    for enc in ("utf-8-sig", "latin-1", "cp1252"):
        try:
            with open(path, encoding=enc, errors="replace", newline="") as f:
                return list(csv.DictReader(f, delimiter=";"))
        except Exception:
            continue
    return []


def _to_int(v) -> int:
    try:
        return int(str(v or "").strip().replace(".", "").replace(",", ""))
    except Exception:
        return 0


def _ventas_path() -> Path:
    p = BI_DIR / "VENTAS-TOD-2026.CSV"
    return p if p.exists() and p.stat().st_size > 0 else SEED_DIR / "VENTAS-TOD-2026.CSV"


def _pedidos_path() -> Path:
    p = SEED_DIR / "PEDIDOS.Txt"
    return p if p.exists() and p.stat().st_size > 0 else Path()


# ── Reporte 1: Mejores clientes (todas las colecciones) ──────────────────────

def report_mejores_clientes() -> dict:
    path  = _ventas_path()
    empty = {"available": False, "rows": [], "total_ventas": 0, "total_prendas": 0, "total_documentos": 0}
    if not path.exists():
        return {c: empty for c in COLECCIONES}

    rows = _read_csv(path)
    data: dict[str, dict] = {c: {} for c in COLECCIONES}

    for r in rows:
        temp = str(r.get("Temporada") or "").strip()
        if temp not in COLECCIONES:
            continue
        rut    = str(r.get("Rut")     or "").strip()
        nombre = str(r.get("cliente") or "").strip() or rut
        total  = _to_int(r.get("Total"))
        cant   = _to_int(r.get("Cant"))
        num    = str(r.get("Numero")  or "").strip()
        key    = rut or nombre

        if key not in data[temp]:
            data[temp][key] = {"rut": rut, "cliente": nombre,
                               "total": 0, "prendas": 0, "documentos": set()}
        data[temp][key]["total"]    += total
        data[temp][key]["prendas"]  += cant
        data[temp][key]["documentos"].add(num)

    result = {}
    for cole in COLECCIONES:
        filas = sorted(
            [
                {
                    "rut":       v["rut"],
                    "cliente":   v["cliente"],
                    "total":     v["total"],
                    "prendas":   v["prendas"],
                    "documentos": len(v["documentos"]),
                }
                for v in data[cole].values() if v["total"] > 0 and v["prendas"] > 10
            ],
            key=lambda x: -x["total"],
        )
        result[cole] = {
            "available":        bool(filas),
            "rows":             filas,
            "total_ventas":     sum(r["total"]      for r in filas),
            "total_prendas":    sum(r["prendas"]    for r in filas),
            "total_documentos": sum(r["documentos"] for r in filas),
        }
    return result


# ── Reporte 2: Clientes que no compraron ─────────────────────────────────────

def report_no_compraron() -> dict:
    path = _ventas_path()
    if not path.exists():
        return {"available": False, "rows": [], "total": 0}

    rows = _read_csv(path)
    # Clientes que compraron en C42 con más de 10 prendas
    en_c42:  dict[str, dict] = {}
    # Clientes que compraron en C43
    en_c43:  set[str]        = set()

    for r in rows:
        temp = str(r.get("Temporada") or "").strip()
        rut    = str(r.get("Rut")     or "").strip()
        nombre = str(r.get("cliente") or "").strip() or rut
        key    = rut or nombre

        if temp == "42":
            if key not in en_c42:
                en_c42[key] = {"rut": rut, "cliente": nombre, "total": 0, "prendas": 0}
            en_c42[key]["total"]   += _to_int(r.get("Total"))
            en_c42[key]["prendas"] += _to_int(r.get("Cant"))

        if temp == "43":
            en_c43.add(key)

    no_compraron = sorted(
        [
            {
                "rut":             v["rut"],
                "cliente":         v["cliente"],
                "total_historico": v["total"],
                "prendas_c42":     v["prendas"],
            }
            for key, v in en_c42.items()
            if key not in en_c43 and v["prendas"] > 10
        ],
        key=lambda x: -x["total_historico"],
    )
    return {"available": True, "rows": no_compraron, "total": len(no_compraron)}


# ── Reporte 3: Modelo + Pedidos por Bota (todas las colecciones) ──────────────

def report_modelo_bota() -> dict:
    path  = _pedidos_path()
    empty = {"available": False, "botas": [], "modelos": [],
             "total_solicitado": 0, "total_despachado": 0, "total_saldo": 0}
    if not path.exists():
        return {c: empty for c in COLECCIONES}

    rows = _read_csv(path)
    cole_data: dict[str, dict] = {c: {"botas": {}, "modelos": {}} for c in COLECCIONES}

    for r in rows:
        cole = str(r.get("COLECCION") or "").strip()
        if cole not in COLECCIONES:
            continue

        bota       = str(r.get("SubCateg")    or "").strip() or "Sin categoría"
        categ      = str(r.get("Categ")       or "").strip()
        art        = str(r.get("ARTICULO")    or "").strip()
        desc       = str(r.get("DESCRIPCION") or "").strip()
        solicitado = _to_int(r.get("SOLICITADO"))
        despachado = _to_int(r.get("DESPACHADO"))
        saldo      = _to_int(r.get("saldo"))

        botas = cole_data[cole]["botas"]
        if bota not in botas:
            botas[bota] = {"bota": bota, "categ": categ,
                           "solicitado": 0, "despachado": 0, "saldo": 0, "clientes": set()}
        botas[bota]["solicitado"] += solicitado
        botas[bota]["despachado"] += despachado
        botas[bota]["saldo"]      += saldo
        botas[bota]["clientes"].add(str(r.get("RUT") or "").strip())

        modelos = cole_data[cole]["modelos"]
        if art not in modelos:
            modelos[art] = {"articulo": art, "descripcion": desc, "bota": bota,
                            "solicitado": 0, "despachado": 0, "saldo": 0}
        modelos[art]["solicitado"] += solicitado
        modelos[art]["despachado"] += despachado
        modelos[art]["saldo"]      += saldo

    result = {}
    for cole in COLECCIONES:
        botas_raw   = cole_data[cole]["botas"]
        modelos_raw = cole_data[cole]["modelos"]
        botas_list  = sorted(
            [
                {**v, "clientes": len(v["clientes"]),
                 "pct_despachado": round(v["despachado"] / v["solicitado"] * 100) if v["solicitado"] else 0}
                for v in botas_raw.values()
            ],
            key=lambda x: -x["solicitado"],
        )
        modelos_list = sorted(modelos_raw.values(), key=lambda x: -x["solicitado"])
        ts = sum(b["solicitado"] for b in botas_list)
        td = sum(b["despachado"] for b in botas_list)
        result[cole] = {
            "available":        bool(botas_list),
            "botas":            botas_list,
            "modelos":          modelos_list,
            "total_solicitado": ts,
            "total_despachado": td,
            "total_saldo":      sum(b["saldo"] for b in botas_list),
        }
    return result


# ── Vista principal ───────────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template(
        "index.html",
        mejores_clientes=report_mejores_clientes(),
        no_compraron=report_no_compraron(),
        modelo_bota=report_modelo_bota(),
    )
