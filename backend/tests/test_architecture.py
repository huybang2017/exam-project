"""Bảo vệ ranh giới các tầng: phụ thuộc chỉ được hướng vào trong (presentation -> application -> domain)."""
import ast
from pathlib import Path

APP = Path(__file__).resolve().parents[1] / "app"

# tầng -> các gốc import bị cấm
FORBIDDEN = {
    "domain": ("app.application", "app.infrastructure", "app.presentation", "fastapi", "sqlalchemy", "pydantic", "jwt"),
    "application": ("app.infrastructure", "app.presentation", "fastapi", "sqlalchemy", "pydantic", "jwt"),
    "infrastructure": ("app.presentation", "fastapi"),
}


def imports_of(path: Path) -> set[str]:
    found: set[str] = set()
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Import):
            found.update(a.name for a in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            found.add(node.module)
    return found


def violations(layer: str) -> list[str]:
    bad = []
    for path in (APP / layer).rglob("*.py"):
        for module in imports_of(path):
            if any(module == f or module.startswith(f + ".") for f in FORBIDDEN[layer]):
                bad.append(f"{path.relative_to(APP)} import {module}")
    return bad


def test_domain_is_pure_python():
    assert violations("domain") == []


def test_application_depends_only_on_domain():
    assert violations("application") == []


def test_infrastructure_does_not_know_presentation():
    assert violations("infrastructure") == []


def test_legacy_flat_modules_are_gone():
    legacy = ["routers", "services", "deps.py", "schemas.py", "models.py", "security.py", "cache.py", "database.py", "config.py"]
    assert [name for name in legacy if (APP / name).exists()] == []
