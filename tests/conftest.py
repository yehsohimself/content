"""Content test setup: the code is copied into a temporary folder and the server is loaded from content_sunucu.py; your own content/ data is never touched."""
import importlib.util
import json
import os
import shutil
import sys
from pathlib import Path

import pytest

GERCEK_KOK = Path(__file__).resolve().parent.parent


@pytest.fixture(scope="session")
def kok(tmp_path_factory):
    k = tmp_path_factory.mktemp("content")
    for py in GERCEK_KOK.glob("*.py"):
        shutil.copy(py, k / py.name)
    shutil.copytree(GERCEK_KOK / "static", k / "static")
    (k / "content").mkdir()
    (k / "kayitlar").mkdir()
    (k / "ayarlar.json").write_text(json.dumps({"claude": False}), encoding="utf-8")
    os.environ["CONTENT_KOK"] = str(k / "content")
    sys.path.insert(0, str(k))
    for m in [m for m in list(sys.modules) if m in ("gizli", "claude_yaz", "ortak", "content") or m.startswith("content_")]:
        del sys.modules[m]
    import claude_yaz                                      # no Claude program during tests
    claude_yaz.program = lambda: None
    claude_yaz.durum = lambda zorla=False: {"program": False, "giris": False, "kullanim": False}
    return k


@pytest.fixture(scope="session")
def site(kok):
    spec = importlib.util.spec_from_file_location("content_sunucu", kok / "content_sunucu.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules["content_sunucu"] = mod
    spec.loader.exec_module(mod)
    mod.app.config["TESTING"] = True
    return mod


@pytest.fixture
def istemci(site):
    return site.app.test_client()
