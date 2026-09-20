# -*- coding: utf-8 -*-
"""Compile/syntax smoke tests so Kodi does not hit import-* SyntaxError at runtime."""
from __future__ import absolute_import

import ast
import compileall
import os
import py_compile
import unittest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
SHIPPED_PY = []
for dirpath, dirnames, filenames in os.walk(ROOT):
    dirnames[:] = [d for d in dirnames if d not in (
        '.git', '__pycache__', 'artifacts', 'workshop', 'tests',
    )]
    for name in filenames:
        if name.endswith('.py'):
            SHIPPED_PY.append(os.path.join(dirpath, name))


def _nested_star_imports(path):
    with open(path, 'r') as fh:
        tree = ast.parse(fh.read(), filename=path)
    bad = []

    class Visitor(ast.NodeVisitor):
        def visit_FunctionDef(self, node):
            self._scan(node)
            self.generic_visit(node)

        def visit_AsyncFunctionDef(self, node):
            self._scan(node)
            self.generic_visit(node)

        def visit_ClassDef(self, node):
            self._scan(node)
            self.generic_visit(node)

        def _scan(self, node):
            for child in ast.walk(node):
                if isinstance(child, ast.ImportFrom) and any(
                    alias.name == '*' for alias in child.names
                ):
                    bad.append((path, child.lineno, child.module))

    Visitor().visit(tree)
    return bad


class CompileSmokeTests(unittest.TestCase):
    def test_shipped_python_compiles(self):
        py_compile.compile(os.path.join(ROOT, 'default.py'), doraise=True)
        py_compile.compile(os.path.join(ROOT, 'service.py'), doraise=True)
        py_compile.compile(os.path.join(ROOT, 'resources', 'lib', 'precache.py'), doraise=True)
        ok = compileall.compile_dir(os.path.join(ROOT, 'resources'), quiet=1, force=True)
        self.assertTrue(ok)

    def test_no_star_import_inside_functions_or_classes(self):
        failures = []
        for path in SHIPPED_PY:
            failures.extend(_nested_star_imports(path))
        self.assertEqual(
            failures, [],
            'import * is only legal at module level; found: {0}'.format(failures),
        )


if __name__ == '__main__':
    unittest.main()
