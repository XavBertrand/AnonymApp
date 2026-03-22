from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from typing import Any, Callable


class WorkspaceWorker:
    def __init__(self, dispatcher: Callable[[Callable[[], None]], None] | None = None) -> None:
        self._executor = ThreadPoolExecutor(max_workers=1)
        self._dispatcher = dispatcher or (lambda callback: callback())

    def submit(
        self,
        fn: Callable[..., Any],
        /,
        *args: Any,
        on_success: Callable[[Any], None] | None = None,
        on_error: Callable[[Exception], None] | None = None,
        **kwargs: Any,
    ):
        future = self._executor.submit(fn, *args, **kwargs)

        def _notify() -> None:
            try:
                result = future.result()
            except Exception as exc:
                if on_error is not None:
                    on_error(exc)
            else:
                if on_success is not None:
                    on_success(result)

        future.add_done_callback(lambda _future: self._dispatcher(_notify))
        return future
