from __future__ import annotations

import csv
import io
import os
from collections import defaultdict
from pathlib import Path
from flask import Flask, render_template

app = Flask(__name__)

BI_DIR = Path(os.environ.get("BI_REPORTES_BI_DIR", r"Z:\BI"))
SEED_DIR = Path(__file__).parent / "seed"

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


# ── Reporte 1: Mejores clientes ──────────────────────────────────────────────

def report_mejores_clientes() -> dict:
    path = _ventas_path()
    if not path.exists():
        return {"available": False, "rows": [], "temporadas": []}

    rows = _read_csv(path)
    clientes: dict[str, dict] = {}
    temporadas_vistas: set[str] = set()

    for r in rows:
        temp = str(r.get("Temporada") or "").strip()
        if not temp.isdigit():
            continue
        rut = str(r.get("Rut") or "").strip()
        nombre = str(r.get("cliente") or "").strip() or rut
        total = _to_int(r.get("Total"))
        cant = _to_int(r.get("Cant"))
        num = str(r.get("Numero") or "").strip()

        key = rut or nombre
        if key not in clientes:
            clientes[key] = {
                "rut": rut, "cliente": nombre,
                "total": 0, "prendas": 0,
                "documentos": set(),
                "temporadas": set(),
            }
        clientes[key]["total"] += total
        clientes[key]["prendas"] += cant
        clientes[key]["documentos"].add(num)
        clientes[key]["temporadas"].add(temp)
        temporadas_vistas.add(temp)

    result = sorted(
        [
            {
                "rut": v["rut"],
                "cliente": v["cliente"],
                "total": v["total"],
                "prendas": v["prendas"],
                "documentos": len(v["documentos"]),
                "temporadas": ", ".join(sorted(v["temporadas"])),
            }
            for v in clientes.values() if v["total"] > 0
        ],
        key=lambda x: -x["total"],
    )
    temps_sorted = sorted(t for t in temporadas_vistas if t.isdigit() and 40 <= int(t) <= 50)
    return {"available": True, "rows": result, "temporadas": temps_sorted}


# ── Reporte 2: Clientes que no compraron ─────────────────────────────────────

def report_no_compraron() -> dict:
    path = _ventas_path()
    if not path.exists():
        return {"available": False, "rows": []}

    rows = _read_csv(path)
    historicos: dict[str, dict] = {}
    actuales: set[str] = set()

    for r in rows:
        temp = str(r.get("Temporada") or "").strip()
        if not temp.isdigit():
            continue
        rut = str(r.get("Rut") or "").strip()
        nombre = str(r.get("cliente") or "").strip() or rut
        key = rut or nombre

        if temp in TEMPORADAS_HISTORICAS:
            if key not in historicos:
                historicos[key] = {
                    "rut": rut, "cliente": nombre,
                    "ultima_temp": temp,
                    "temporadas": set(),
                    "total": 0,
                }
            historicos[key]["temporadas"].add(temp)
            historicos[key]["total"] += _to_int(r.get("Total"))
            if int(temp) > int(historicos[key]["ultima_temp"]):
                historicos[key]["ultima_temp"] = temp

        if temp in TEMPORADAS_ACTUALES:
            actuales.add(key)

    no_compraron = sorted(
        [
            {
                "rut": v["rut"],
                "cliente": v["cliente"],
                "ultima_temp": f"T{v['ultima_temp']}",
                "temporadas_activas": ", ".join(f"T{t}" for t in sorted(v["temporadas"])),
                "total_historico": v["total"],
            }
            for key, v in historicos.items() if key not in actuales
        ],
        key=lambda x: x["cliente"],
    )
    return {"available": True, "rows": no_compraron, "total": len(no_compraron)}


# ── Reporte 3: Modelo + Pedidos por Bota ─────────────────────────────────────

def report_modelo_bota() -> dict:
    path = _pedidos_path()
    if not path.exists():
        return {"available": False, "botas": [], "modelos": []}

    rows = _read_csv(path)

    # Por bota (SubCateg)
    botas: dict[str, dict] = {}
    # Por modelo (ARTICULO + DESCRIPCION)
    modelos: dict[str, dict] = {}

    for r in rows:
        bota = str(r.get("SubCateg") or "").strip() or "Sin categoría"
        categ = str(r.get("Categ") or "").strip()
        art = str(r.get("ARTICULO") or "").strip()
        desc = str(r.get("DESCRIPCION") or "").strip()
        solicitado = _to_int(r.get("SOLICITADO"))
        despachado = _to_int(r.get("DESPACHADO"))
        saldo = _to_int(r.get("saldo"))

        # Bota
        if bota not in botas:
            botas[bota] = {"bota": bota, "categ": categ, "solicitado": 0, "despachado": 0, "saldo": 0, "clientes": set()}
        botas[bota]["solicitado"] += solicitado
        botas[bota]["despachado"] += despachado
        botas[bota]["saldo"] += saldo
        botas[bota]["clientes"].add(str(r.get("RUT") or "").strip())

        # Modelo
        modelo_key = art
        modelo_label = f"{art} — {desc}" if desc else art
        if modelo_key not in modelos:
            modelos[modelo_key] = {
                "articulo": art,
                "descripcion": desc,
                "label": modelo_label,
                "bota": bota,
                "solicitado": 0, "despachado": 0, "saldo": 0,
            }
        modelos[modelo_key]["solicitado"] += solicitado
        modelos[modelo_key]["despachado"] += despachado
        modelos[modelo_key]["saldo"] += saldo

    botas_list = sorted(
        [
            {**v, "clientes": len(v["clientes"]),
             "pct_despachado": round(v["despachado"] / v["solicitado"] * 100) if v["solicitado"] else 0}
            for v in botas.values()
        ],
        key=lambda x: -x["solicitado"],
    )
    modelos_list = sorted(modelos.values(), key=lambda x: -x["solicitado"])

    return {
        "available": True,
        "botas": botas_list,
        "modelos": modelos_list,
        "total_solicitado": sum(b["solicitado"] for b in botas_list),
        "total_despachado": sum(b["despachado"] for b in botas_list),
        "total_saldo": sum(b["saldo"] for b in botas_list),
    }


# ── Vista principal ───────────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template(
        "index.html",
        mejores_clientes=report_mejores_clientes(),
        no_compraron=report_no_compraron(),
        modelo_bota=report_modelo_bota(),
    )
