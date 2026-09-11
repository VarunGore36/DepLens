from deplens.analysis import link_imports, parse_imports_text, parse_usage_text
from deplens.dependencies import parse_requirements_text
from deplens.graph import DependencyGraph
from deplens.prediction import build_impact, impact_json, impact_markdown


def _setup():
    graph = DependencyGraph.from_specs(
        parse_requirements_text("requests==2.28.0\n").specs, root="demo"
    )
    imports = parse_imports_text("import requests\nfrom requests import get\n")
    links = link_imports(imports.records, ["requests"])
    usages = parse_usage_text(
        "import requests\nfrom requests import get\nrequests.get('https://x.test')\n"
    ).usages
    return graph, links, usages


def test_build_impact_traces_files_and_apis():
    graph, links, usages = _setup()
    report = build_impact("requests", "==2.28.0", "==2.31.0", graph, links, usages)
    assert report.package == "requests"
    assert report.direct is True and report.depth == 1
    assert report.affected_files == ["<source>"]
    assert "requests.get" in report.affected_apis
    assert report.risk > 0 and report.band in ("low", "medium", "high")
    assert {p.rule for p in report.predictions} >= {"major-version", "code-usage"}


def test_build_impact_unknown_package_is_empty():
    graph, links, usages = _setup()
    report = build_impact("numpy", None, "==1.26.0", graph, links, usages)
    assert report.affected_files == [] and report.affected_apis == []
    assert report.direct is False and report.depth is None


def test_impact_markdown_and_json():
    graph, links, usages = _setup()
    report = build_impact("requests", "==2.28.0", "==2.31.0", graph, links, usages)
    text = impact_markdown(report)
    assert "# Impact: requests" in text
    assert "## Affected files" in text and "## Affected APIs" in text
    assert "over-approximations" in text
    payload = impact_json(report)
    assert payload["package"] == "requests"
    assert payload["band"] == report.band
