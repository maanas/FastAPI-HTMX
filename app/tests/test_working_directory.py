"""The app starts and serves pages and static files from any working directory."""

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

# Runs in a child process: the interpreter's cwd is a scratch directory, not the repo.
SCRIPT = """
import os
from fastapi.testclient import TestClient
from app.app import app

assert os.getcwd() != {root!r}
with TestClient(app) as client:
    login = client.get("/login")
    css = client.get("/static/css/app.css")
print(login.status_code, css.status_code)
"""


def test_app_serves_pages_and_static_files_from_another_directory(tmp_path):
    result = subprocess.run(
        [sys.executable, "-c", SCRIPT.format(root=str(ROOT))],
        cwd=tmp_path,
        env={**os.environ, "PYTHONPATH": str(ROOT), "PYTHONDONTWRITEBYTECODE": "1"},
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr[-800:]
    assert result.stdout.split()[-2:] == ["200", "200"]
