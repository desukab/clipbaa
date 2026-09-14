import os
import re
from pathlib import Path

import pytest

from scrapers.cli import _resolve_scrape_asins, main
from scrapers.errors import ConfigError
from scrapers.io import load_json
from scrapers.sources.amazon import load_seed_asins


def test_list_sources_ok(capsys):
    assert main(["list-sources"]) == 0
    out = capsys.readouterr().out
    assert "amazon" in out and "deodap" in out


def test_validate_config_ok():
    assert main(["validate-config"]) == 0


def test_validate_config_bad_env():
    os.environ["LOG_LEVEL"] = "shouty"
    try:
        assert main(["validate-config"]) == 2
    finally:
        del os.environ["LOG_LEVEL"]


def test_run_mock_e2e(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    out = str(tmp_path / "data")
    code = main(["--output-dir", out, "run", "--mock",
                 "--sources", "amazon,meesho,flipkart,deodap"])
    assert code == 0
    assert load_json(os.path.join(out, "amazon_movers_raw.json"))
    assert load_json(os.path.join(out, "deodap_catalog_raw.json"))
    assert os.path.exists(os.path.join(out, "matched_products.json"))
    assert os.path.exists(os.path.join(out, "winners.md"))
    runs = list((Path(out) / "runs").iterdir())
    assert len(runs) == 1
    manifest = load_json(runs[0] / "manifest.json")
    assert manifest["mode"] == "mock"
    assert manifest["settings"].get("webhook_secret") in (None, "***")


def test_run_unknown_source_exit2(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    assert main(["--output-dir", str(tmp_path / "d"), "run", "--mock", "--sources", "nope"]) == 2


def test_run_live_without_scrapling_exit4(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    assert main(["--output-dir", str(tmp_path / "d"), "run", "--live", "--sources", "amazon"]) == 4


def test_load_seed_asins_reads_real_seed_file():
    asins = load_seed_asins()
    assert asins
    assert all(re.fullmatch(r"B0[A-Z0-9]{8}", a) for a in asins)


def test_resolve_scrape_asins_explicit_wins(monkeypatch):
    from scrapers import cli

    monkeypatch.setattr(cli, "load_seed_asins", lambda: ["B0AAAAAAA1"])
    assert _resolve_scrape_asins(["B0CCCCDDD2"]) == ["B0CCCCDDD2"]


def test_resolve_scrape_asins_falls_back_to_seed(monkeypatch):
    from scrapers import cli

    fake = ["B0AAAAAAA1", "B0BBBBBBB2"]
    monkeypatch.setattr(cli, "load_seed_asins", lambda: fake)
    assert _resolve_scrape_asins(None) == fake
    assert _resolve_scrape_asins([]) == fake


def test_resolve_scrape_asins_nothing_raises(monkeypatch):
    from scrapers import cli

    monkeypatch.setattr(cli, "load_seed_asins", lambda: [])
    with pytest.raises(ConfigError):
        _resolve_scrape_asins(None)
    with pytest.raises(ConfigError):
        _resolve_scrape_asins([])
