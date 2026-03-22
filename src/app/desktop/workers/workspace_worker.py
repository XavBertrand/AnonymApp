from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from typing import Any, Callable


class WorkspaceWorker:
    def __init__(self) -> None:
        self._executor = ThreadPoolExecutor(max_workers=1)

    def submit(self, fn: Callable[..., Any], /, *args: Any, **kwargs: Any):
        return self._executor.submit(fn, *args, **kwargs)
