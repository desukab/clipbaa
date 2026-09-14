def test_package_importable():
    import scrapers
    assert scrapers.__name__ == "scrapers"


def test_cli_placeholder_runs():
    from scrapers.cli import main
    assert main([]) == 0