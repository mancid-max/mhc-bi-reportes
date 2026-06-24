from __future__ import annotations
import shutil, sys, os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS_DIR = ROOT / "docs"
SEED_DIR = ROOT / "seed"
BI_DIR = Path(os.environ.get("BI_REPORTES_BI_DIR", r"Z:\BI"))

def _sync_bi_to_seed() -> None:
    if not BI_DIR.exists():
        print("Z:\\BI no disponible, usando seed existente.")
        return
    for bi_name, seed_name in [("VENTAS-TOD-2026.CSV", "VENTAS-TOD-2026.CSV")]:
        src = BI_DIR / bi_name
        dst = SEED_DIR / seed_name
        if src.exists() and src.stat().st_size > 0:
            shutil.copy2(src, dst)
            print(f"  Sync: {bi_name} -> seed/{seed_name}")

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

os.environ["BI_REPORTES_BI_DIR"] = str(BI_DIR)

import app as app_module

def main() -> None:
    print("Sincronizando desde Z:\\BI...")
    _sync_bi_to_seed()
    with app_module.app.test_request_context("/"):
        html = app_module.index()
        if hasattr(html, "get_data"):
            html = html.get_data(as_text=True)
        else:
            html = str(html)

    html = html.replace('href="styles.css"', 'href="styles.css"')
    html = html.replace('href="/static/styles.css"', 'href="styles.css"')

    DOCS_DIR.mkdir(exist_ok=True)
    shutil.copy2(ROOT / "static" / "styles.css", DOCS_DIR / "styles.css")
    (DOCS_DIR / "index.html").write_text(html, encoding="utf-8")
    (DOCS_DIR / "404.html").write_text(html, encoding="utf-8")
    (DOCS_DIR / ".nojekyll").write_text("", encoding="utf-8")
    print(f"Sitio generado en {DOCS_DIR}")

if __name__ == "__main__":
    main()
