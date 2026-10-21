#!/usr/bin/env python3
from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / ".build"
PACKAGE_SRC = ROOT / "src" / "callcenter_usecase"
PACKAGE_DST = BUILD / "callcenter_usecase"
UI_ROOT = PACKAGE_SRC / "ui"
PUBLIC_DIR = UI_ROOT / "public"


def copytree(src: Path, dst: Path) -> None:
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(
        src,
        dst,
        ignore=shutil.ignore_patterns(
            "__pycache__",
            "*.pyc",
            "ui",
        ),
    )


def build_frontend(dist: Path) -> None:
    dist.mkdir(parents=True, exist_ok=True)
    entrypoint = ROOT / "node_modules" / ".apx" / "entrypoint.ts"
    if entrypoint.exists():
        env = os.environ.copy()
        env["APX_APP_NAME"] = "callcenter_usecase"
        command = [
            "apx",
            "bun",
            "run",
            str(entrypoint),
            "build",
            str(UI_ROOT),
            str(dist),
            str(PUBLIC_DIR),
        ]
        try:
            subprocess.run(command, cwd=ROOT, env=env, check=True)
            if (dist / "index.html").exists():
                print(f"Built React frontend into {dist}")
                return
        except (OSError, subprocess.CalledProcessError) as error:
            print(f"React build failed, falling back to ui-preview.html: {error}")
    shutil.copyfile(ROOT / "ui-preview.html", dist / "index.html")
    print("Packaged ui-preview.html as the frontend fallback")


def write_runtime_files() -> None:
    shutil.copyfile(ROOT / "app.yml", BUILD / "app.yml")
    shutil.copyfile(ROOT / "app.yml", BUILD / "app.yaml")
    shutil.copyfile(ROOT / "README.md", BUILD / "README.md")
    shutil.copyfile(ROOT / "BUILD_NOTES.md", BUILD / "BUILD_NOTES.md")
    (BUILD / "app.py").write_text(
        "\n".join(
            [
                "import os",
                "import uvicorn",
                "",
                "if __name__ == '__main__':",
                "    port = int(os.environ.get('DATABRICKS_APP_PORT', '8000'))",
                "    uvicorn.run(",
                "        'callcenter_usecase.backend.app:app',",
                "        host='0.0.0.0',",
                "        port=port,",
                "        workers=1,",
                "    )",
                "",
            ]
        ),
        encoding="utf-8",
    )
    requirements = "\n".join(
        [
            "fastapi>=0.119.0",
            "python-multipart>=0.0.20",
            "pydantic-settings>=2.11.0",
            "python-dotenv>=1.0.0",
            "uvicorn>=0.37.0",
            "databricks-sdk>=0.89.0",
            "sqlmodel>=0.0.27",
            "psycopg[binary,pool]>=3.2.11",
            "",
        ]
    )
    (BUILD / "requirements.txt").write_text(requirements, encoding="utf-8")


def main() -> int:
    if BUILD.exists():
        shutil.rmtree(BUILD)
    BUILD.mkdir(parents=True)

    copytree(PACKAGE_SRC, PACKAGE_DST)
    if (ROOT / "data").exists():
        shutil.copytree(ROOT / "data", BUILD / "data", dirs_exist_ok=True)

    build_frontend(PACKAGE_DST / "__dist__")
    write_runtime_files()
    print(f"Built Databricks App source bundle at {BUILD}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
