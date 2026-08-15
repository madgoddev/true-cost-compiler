from __future__ import annotations

import os
import sys
import tempfile


def prepare_glsim_runtime() -> None:
    """Apply the two narrow Windows fixes needed by genlayer-test 0.29.2."""

    if sys.platform != "win32":
        return

    from gltest.direct import loader
    from gltest.direct.vm import VMContext

    if not getattr(loader, "_truecost_glsim_fd", False):
        original_cleanup = VMContext._cleanup_after_deactivate
        original_refresh = VMContext._refresh_gl_message

        def inject_message(vm) -> None:
            try:
                from genlayer.py import calldata
                from genlayer.py.types import Address
            except ImportError:
                return
            message = vm.get_message_raw()
            for field in ("contract_address", "sender_address", "origin_address"):
                if isinstance(message[field], bytes):
                    message[field] = Address(message[field])
            stream = tempfile.TemporaryFile(mode="w+b")
            stream.write(calldata.encode(message))
            stream.flush()
            stream.seek(0)
            vm._original_stdin_fd = os.dup(0)
            os.dup2(stream.fileno(), 0)
            vm._truecost_stdin_stream = stream

        def cleanup(vm) -> None:
            stream = getattr(vm, "_truecost_stdin_stream", None)
            try:
                original_cleanup(vm)
            finally:
                if stream is not None:
                    stream.close()
                    vm._truecost_stdin_stream = None

        def refresh(vm) -> None:
            original_refresh(vm)
            gl_module = sys.modules.get("genlayer.gl")
            message = getattr(gl_module, "message_raw", None)
            if isinstance(message, dict):
                message["datetime"] = vm._datetime

        loader._inject_message_to_fd0 = inject_message
        VMContext._cleanup_after_deactivate = cleanup
        VMContext._refresh_gl_message = refresh
        loader._truecost_glsim_fd = True

    import glsim.engine as engine

    if not getattr(engine, "_truecost_unwrap_contract", False):
        original_deploy = engine.deploy_contract

        def deploy_unwrapped(*args, **kwargs):
            contract = original_deploy(*args, **kwargs)
            return getattr(contract, "_instance", contract)

        engine.deploy_contract = deploy_unwrapped
        engine._truecost_unwrap_contract = True
