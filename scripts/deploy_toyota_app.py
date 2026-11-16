#!/usr/bin/env python3
"""Build and deploy toyota-call-center.

`.build/` is gitignored, so `databricks sync .build ...` skips the frontend.
This copies the bundle to a staging directory outside the repo, then syncs.
Never deploys carenet-nba.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / ".build"
STAGING = Path("/tmp/toyota-cc-deploy")
WORKSPACE_SRC = "/Workspace/Users/brijendra.raghuwanshi@databricks.com/apps/toyota-call-center"
APP_NAME = "toyota-call-center"


def run(command: list[str]) -> None:
    subprocess.run(command, cwd=ROOT, check=True)


def main() -> int:
    run([sys.executable, str(ROOT / "scripts" / "build_databricks_app.py")])
    if STAGING.exists():
        shutil.rmtree(STAGING)
    shutil.copytree(BUILD, STAGING)
    run(["databricks", "sync", "--full", "--watch=false", str(STAGING), WORKSPACE_SRC])
    run(["databricks", "apps", "deploy", APP_NAME, "--source-code-path", WORKSPACE_SRC])
    print(f"Deployed {APP_NAME} from {STAGING}")
    return 0


if __name__ == "__main__":
    os.chdir(ROOT)
    raise SystemExit(main())
