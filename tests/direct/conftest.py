from __future__ import annotations

import sys
from pathlib import Path

import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from tests.runtime_compat import enable_windows_fd_cleanup


enable_windows_fd_cleanup()


@pytest.fixture
def compiler(direct_vm, direct_deploy, direct_alice):
    direct_vm.warp("2026-08-12T10:00:00Z")
    direct_vm.sender = direct_alice
    return direct_deploy(str(PROJECT_ROOT / "contracts" / "true_cost_compiler.py"))


@pytest.fixture(autouse=True)
def clear_nondeterministic_state(direct_vm):
    direct_vm.clear_mocks()
    direct_vm.clear_validators()
    yield
    direct_vm.clear_mocks()
    direct_vm.clear_validators()
