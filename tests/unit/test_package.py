"""Smoke test: the package installs and exposes its version."""

import madhya_kanoon_saathi


def test_version_is_set() -> None:
    assert madhya_kanoon_saathi.__version__ == "0.1.0"
