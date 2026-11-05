"""Every model module must be imported at API startup, or create_all never creates its table
in a fresh database (the Form 4 table was missing in production for exactly this reason)."""
import os, re

ROOT = os.path.join(os.path.dirname(__file__), "..")


def _model_modules():
    d = os.path.join(ROOT, "app", "models")
    return sorted(f[:-3] for f in os.listdir(d) if f.endswith(".py") and f != "__init__.py")


def _startup_import_block():
    src = open(os.path.join(ROOT, "app", "api", "main.py")).read()
    m = re.search(r"from app\.models import \((.*?)\)|from app\.models import ([^\n(]+)", src, re.S)
    assert m, "startup import of app.models not found"
    return m.group(1) or m.group(2)


def test_every_model_module_is_imported_at_startup():
    block = _startup_import_block()
    imported = set(re.findall(r"[A-Za-z_]+", block))
    missing = [m for m in _model_modules() if m not in imported]
    assert not missing, f"models not imported in main.py startup: {missing}"
