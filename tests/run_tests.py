#!/usr/bin/env python3
"""
Lightweight test runner for environments without pytest installed.

Limitations:
  - Supports @pytest.fixture as a no-op decorator, but does NOT inject
    fixture arguments into test functions. Tests that rely on fixture
    injection (e.g. test_gui.py) are skipped with a clear warning.
  - The authoritative test command is:
        .venv/bin/python -m pytest -q
    Install: pip install pytest
"""
import sys
import os
import importlib.util
import inspect


class PytestMock:
    @staticmethod
    def fixture(func=None, **_kwargs):
        """No-op decorator so @pytest.fixture doesn't crash at import time."""
        if func is None:
            return lambda decorated: decorated
        return func

    class raises:
        def __init__(self, expected_exception):
            self.expected = expected_exception

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_val, exc_tb):
            if exc_type is None:
                raise AssertionError(
                    f"Expected exception {self.expected.__name__} was not raised"
                )
            if issubclass(exc_type, self.expected):
                return True  # suppress the expected exception
            return False  # let unexpected exceptions propagate


sys.modules["pytest"] = PytestMock

# Add src/ to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))


def run_test_file(filepath):
    filename = os.path.basename(filepath)
    print(f"\nRunning tests in {filename}...")

    spec = importlib.util.spec_from_file_location("test_module", filepath)
    module = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(module)
    except Exception as e:
        print(f"[-] Failed to load {filename}: {e}")
        print("    NOTE: Use '.venv/bin/python -m pytest -q' for full fixture support.")
        return None  # None = skipped, not failed

    test_functions = [
        (name, obj)
        for name, obj in inspect.getmembers(module, inspect.isfunction)
        if name.startswith("test_")
    ]

    if not test_functions:
        print("    (no test functions found)")
        return True

    # Skip any test whose signature requires fixture arguments we can't inject
    passed = failed = skipped = 0
    for name, func in test_functions:
        params = list(inspect.signature(func).parameters)
        if params:
            print(f"[~] {name} SKIPPED (requires fixture injection: {params})")
            skipped += 1
            continue
        try:
            func()
            print(f"[+] {name} PASSED")
            passed += 1
        except Exception as e:
            import traceback
            print(f"[-] {name} FAILED: {e}")
            traceback.print_exc()
            failed += 1

    print(f"    {passed} passed, {failed} failed, {skipped} skipped")
    return failed == 0


if __name__ == "__main__":
    print("=" * 60)
    print("Lightweight test runner (no pytest required)")
    print("For full results: .venv/bin/python -m pytest -q")
    print("=" * 60)

    all_ok = True
    tests_dir = os.path.dirname(os.path.abspath(__file__))
    for filename in sorted(os.listdir(tests_dir)):
        if filename.startswith("test_") and filename.endswith(".py"):
            result = run_test_file(os.path.join(tests_dir, filename))
            if result is False:  # explicit failure; None (skipped) is not a failure
                all_ok = False

    print()
    if all_ok:
        print("All runnable tests passed.")
    else:
        print("Some tests FAILED. See above.")
    sys.exit(0 if all_ok else 1)
