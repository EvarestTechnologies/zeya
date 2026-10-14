"""Every node source must be accepted by the OCS Python-node validator."""

import ast

import pytest

from ocs.tests.conftest import NODES
from ocs.tests.sandbox import make_executor

NODE_FILES = sorted(p for p in NODES.glob("*.py") if p.name != "__init__.py")


def test_expected_nodes_exist():
    assert {p.stem for p in NODE_FILES} >= {"danger_gate", "emergency_response", "registration"}


@pytest.mark.parametrize("path", NODE_FILES, ids=lambda p: p.stem)
def test_source_passes_ocs_validation(path):
    make_executor(path.read_text())


@pytest.mark.parametrize("path", NODE_FILES, ids=lambda p: p.stem)
def test_source_has_only_main_at_top_level(path):
    # OCS exec()s node code with separate locals, so module-level names are invisible
    # inside main. Everything must live inside main.
    body = ast.parse(path.read_text()).body
    statements = [n for n in body if not (isinstance(n, ast.Expr) and isinstance(n.value, ast.Constant))]
    assert len(statements) == 1
    assert isinstance(statements[0], ast.FunctionDef) and statements[0].name == "main"


@pytest.mark.parametrize("path", NODE_FILES, ids=lambda p: p.stem)
def test_nodes_avoid_tuple_unpacking_assignment(path):
    # OCS before 930956ce0 (2026) has no _unpack_sequence_, so "a, b = ..." fails at run time
    # inside a node. Avoiding it keeps the nodes working on old and new instances.
    for node in ast.walk(ast.parse(path.read_text())):
        if isinstance(node, ast.Assign):
            assert not any(isinstance(t, ast.Tuple | ast.List) for t in node.targets), (
                f"{path.name}:{node.lineno} uses tuple-unpacking assignment"
            )
