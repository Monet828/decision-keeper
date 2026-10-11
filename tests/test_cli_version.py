"""CLI の --version が pyproject.toml の version を表示することの検査。"""

from __future__ import annotations

import re

import pytest
from conftest import ROOT

from decision_keeper.__main__ import main


def _pyproject_version() -> str:
    text = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    m = re.search(r'^version\s*=\s*"([^"]+)"', text, re.MULTILINE)
    assert m
    return m.group(1)


def test_version_prints_pyproject_version_and_exits_zero(capsys):
    with pytest.raises(SystemExit) as exc:
        main(["--version"])
    assert exc.value.code == 0
    assert _pyproject_version() in capsys.readouterr().out
