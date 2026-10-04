"""Shared test helpers.

Local runs on this host keep every temporary folder under the project tree on
the D: drive so nothing is written to the system drive. CI may fall back to the
platform temp dir when the project does not live on D:.
"""
import os
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def scratch_root():
    override = os.environ.get('XHS_TEST_TMP')
    if override:
        Path(override).mkdir(parents=True, exist_ok=True)
        return override
    if ROOT.drive.upper() == 'D:':
        local = ROOT / '.testtmp'
        local.mkdir(exist_ok=True)
        return str(local)
    return tempfile.gettempdir()


def make_temp_dir(prefix='xhs-'):
    return tempfile.mkdtemp(prefix=prefix, dir=scratch_root())
