"""F1 regression: live spider modules must resolve Scrapling names and session wiring.

These tests pass even when scrapling is not installed, because base.py falls back
to typing-Any stand-ins. They fail if any spider module references Request/Response/
a session class it never imported (the F1 bug), or if its async parse signatures
cannot be resolved.
"""
import asyncio
import inspect

import scrapers.sources.amazon as amazon
import scrapers.sources.deodap as deodap
import scrapers.sources.flipkart as flipkart
import scrapers.sources.meesho as meesho
from scrapers.sources import base


def _collect(agen):
    async def _run():
        return [item async for item in agen]

    return asyncio.run(_run())


class _FakeManager:
    def __init__(self):
        self.calls = []

    def add(self, name, session, **kwargs):
        self.calls.append((name, session, kwargs))


class _FakeSession:
    def __init__(self, **kwargs):
        self.kwargs = kwargs


class _FakeRequest:
    def __init__(self, url, callback=None, meta=None):
        self.url = url
        self.callback = callback
        self.meta = meta or {}


def test_modules_reexport_scrapling_names():
    assert amazon.Request is base.Request
    assert amazon.Response is base.Response
    assert amazon.AsyncStealthySession is base.AsyncStealthySession

    assert meesho.Request is base.Request
    assert meesho.Response is base.Response
    assert meesho.AsyncDynamicSession is base.AsyncDynamicSession

    assert flipkart.Request is base.Request
    assert flipkart.Response is base.Response
    assert flipkart.AsyncStealthySession is base.AsyncStealthySession

    assert deodap.Request is base.Request
    assert deodap.Response is base.Response
    assert deodap.FetcherSession is base.FetcherSession


CALLBACKS = {
    amazon.AmazonMoversSpider: ["parse", "parse_list", "parse_product"],
    meesho.MeeshoSpider: ["parse", "parse_trending", "parse_product"],
    flipkart.FlipkartSpider: ["parse", "parse_bestsellers", "parse_product"],
    deodap.DeodapSpider: ["parse", "parse_category", "parse_product"],
}


def test_parse_callback_signatures_resolve():
    for cls, names in CALLBACKS.items():
        for name in names:
            sig = inspect.signature(getattr(cls, name))
            assert "response" in sig.parameters


def test_amazon_configure_sessions_registers_stealth(monkeypatch):
    monkeypatch.setattr(amazon, "AsyncStealthySession", _FakeSession)
    spider = object.__new__(amazon.AmazonMoversSpider)
    spider.adaptive_domain = "amazon.in"
    spider.concurrent_requests_per_domain = 5
    manager = _FakeManager()

    spider.configure_sessions(manager)

    name, session, kwargs = manager.calls[0]
    assert name == "stealth"
    assert session.kwargs["headless"] is True
    assert session.kwargs["network_idle"] is True
    assert kwargs["default"] is True


def test_amazon_start_requests_yields_list_urls(monkeypatch):
    monkeypatch.setattr(amazon, "Request", _FakeRequest)
    spider = object.__new__(amazon.AmazonMoversSpider)

    requests = _collect(spider.start_requests())

    assert len(requests) == len(amazon.BESTSELLERS_URLS)
    assert all(r.callback.__name__ == "parse_list" for r in requests)
    assert all(r.url.startswith("https://www.amazon.in/") for r in requests)


def test_meesho_configure_sessions_registers_dynamic(monkeypatch):
    monkeypatch.setattr(meesho, "AsyncDynamicSession", _FakeSession)
    spider = object.__new__(meesho.MeeshoSpider)
    spider.adaptive_domain = "meesho.com"
    spider.concurrent_requests_per_domain = 4
    manager = _FakeManager()

    spider.configure_sessions(manager)

    name, session, kwargs = manager.calls[0]
    assert name == "dynamic"
    assert session.kwargs["network_idle"] is True
    assert kwargs["default"] is True


def test_meesho_start_requests_yields_trending_url(monkeypatch):
    monkeypatch.setattr(meesho, "Request", _FakeRequest)
    spider = object.__new__(meesho.MeeshoSpider)

    requests = _collect(spider.start_requests())

    assert len(requests) == 1
    assert requests[0].callback.__name__ == "parse_trending"
    assert "meesho.com" in requests[0].url


def test_flipkart_configure_sessions_registers_stealth_cloudflare(monkeypatch):
    monkeypatch.setattr(flipkart, "AsyncStealthySession", _FakeSession)
    spider = object.__new__(flipkart.FlipkartSpider)
    spider.adaptive_domain = "flipkart.com"
    spider.concurrent_requests_per_domain = 4
    manager = _FakeManager()

    spider.configure_sessions(manager)

    name, session, kwargs = manager.calls[0]
    assert name == "stealth"
    assert session.kwargs["solve_cloudflare"] is True
    assert kwargs["default"] is True


def test_flipkart_start_requests_yields_bestsellers_url(monkeypatch):
    monkeypatch.setattr(flipkart, "Request", _FakeRequest)
    spider = object.__new__(flipkart.FlipkartSpider)

    requests = _collect(spider.start_requests())

    assert len(requests) == 1
    assert requests[0].callback.__name__ == "parse_bestsellers"
    assert "flipkart.com" in requests[0].url


def test_deodap_configure_sessions_registers_fetcher(monkeypatch):
    monkeypatch.setattr(deodap, "FetcherSession", _FakeSession)
    spider = object.__new__(deodap.DeodapSpider)
    spider.adaptive_domain = "deodap.in"
    manager = _FakeManager()

    spider.configure_sessions(manager)

    name, session, kwargs = manager.calls[0]
    assert name == "http"
    assert session.kwargs["impersonate"] == "chrome"
    assert kwargs["default"] is True


def test_deodap_start_requests_yields_category_pages(monkeypatch):
    monkeypatch.setattr(deodap, "Request", _FakeRequest)
    monkeypatch.setattr(deodap, "MAX_COLLECTION_PAGES", 1)
    spider = object.__new__(deodap.DeodapSpider)
    spider.categories = ["kitchen-tools"]

    requests = _collect(spider.start_requests())

    assert len(requests) == 1
    assert requests[0].callback.__name__ == "parse_category"
    assert "/collections/kitchen-tools" in requests[0].url
