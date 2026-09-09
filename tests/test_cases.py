from deplens.analysis import (
    collect_imports,
    collect_usage,
    link_imports,
    parse_imports_text,
    parse_usage_text,
)
from deplens.dependencies import parse_requirements_text
from deplens.graph import DependencyGraph
from deplens.prediction import build_case


def test_build_case_with_graph_links_and_usage():
    graph = DependencyGraph.from_specs(
        parse_requirements_text("requests==2.28.0\nurllib3==1.26.0\n").specs
    )
    graph.add_edge("requests", "urllib3")
    imports = parse_imports_text("import requests\nimport os\n")
    links = link_imports(imports.records, ["requests", "urllib3"])
    usages = parse_usage_text("import requests\nrequests.get('https://example.com')\n").usages
    case = build_case("requests", "==2.28.0", "==2.31.0", graph, links, usages)
    assert case.package == "requests"
    assert (case.old_version, case.new_version) == ("2.28.0", "2.31.0")
    assert case.direct is True and case.depth == 1
    assert case.affected_imports == 1
    assert case.affected_apis == 1


def test_build_case_unknown_package():
    graph = DependencyGraph.from_specs(parse_requirements_text("requests==2.28.0\n").specs)
    case = build_case("numpy", None, "==1.26.0", graph)
    assert case.direct is False and case.depth is None
    assert case.affected_imports == 0 and case.affected_apis == 0
    assert (case.old_version, case.new_version) == (None, "1.26.0")


def test_build_case_collect_end_to_end(tmp_path):
    (tmp_path / "requirements.txt").write_text("requests==2.28.0\n")
    (tmp_path / "app.py").write_text("import requests\nrequests.get('https://x.test')\n")
    graph = DependencyGraph.from_specs(
        parse_requirements_text((tmp_path / "requirements.txt").read_text()).specs
    )
    collected_imports = collect_imports(tmp_path)
    collected_usage = collect_usage(tmp_path)
    links = link_imports(collected_imports.records, graph.direct_dependencies())
    case = build_case(
        "requests", "==2.28.0", "==2.31.0", graph, links, collected_usage.usages
    )
    assert case.affected_imports == 1 and case.affected_apis == 1
