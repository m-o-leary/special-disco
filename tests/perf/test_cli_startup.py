from __future__ import annotations

import os
import subprocess
import sys
import time

import pytest


@pytest.mark.skipif(
    os.getenv("PERF") != "1",
    reason="Set PERF=1 to run performance measurements",
)
def test_cli_startup_time() -> None:
    start = time.perf_counter()
    result = subprocess.run(
        [sys.executable, "-m", "doc_parsing.cli", "--help"],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    duration = time.perf_counter() - start

    assert result.returncode == 0
    print(f"CLI startup time: {duration:.3f}s")
