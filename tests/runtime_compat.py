from __future__ import annotations

import os
from typing import Any


def enable_windows_fd_cleanup() -> None:
    """Delay deletion of genlayer-test's fd-0 message file on Windows.

    Version 0.29.2 follows the POSIX unlink-while-open pattern. Windows keeps
    the file locked until the VM restores stdin, so this test-only adapter
    queues the exact unlink until deactivation.
    """

    if os.name != "nt":
        return

    from gltest.direct import loader
    from gltest.direct.vm import VMContext

    if getattr(loader, "_truecost_fd_cleanup_enabled", False):
        return

    original_inject = loader._inject_message_to_fd0
    original_cleanup = VMContext._cleanup_after_deactivate

    def inject_and_queue(vm: Any) -> None:
        queue = getattr(vm, "_truecost_pending_unlinks", None)
        if queue is None:
            queue = []
            vm._truecost_pending_unlinks = queue
        real_unlink = os.unlink

        def queue_unlink(path: str) -> None:
            queue.append(path)

        os.unlink = queue_unlink
        try:
            original_inject(vm)
        finally:
            os.unlink = real_unlink

    def cleanup_and_unlink(self: Any) -> None:
        queue = list(getattr(self, "_truecost_pending_unlinks", []))
        try:
            original_cleanup(self)
        finally:
            for path in queue:
                try:
                    os.unlink(path)
                except FileNotFoundError:
                    pass
            self._truecost_pending_unlinks = []

    loader._inject_message_to_fd0 = inject_and_queue
    VMContext._cleanup_after_deactivate = cleanup_and_unlink
    loader._truecost_fd_cleanup_enabled = True
