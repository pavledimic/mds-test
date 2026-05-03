from concurrent.futures import Future, ThreadPoolExecutor
from typing import Any, Callable


class WorkerPool:
    def __init__(self, max_workers: int = 10) -> None:
        self._executor = ThreadPoolExecutor(max_workers=max_workers)

    def submit(self, fn: Callable[..., Any], *args: Any, **kwargs: Any) -> Future:
        return self._executor.submit(fn, *args, **kwargs)

    def shutdown(self, wait: bool = True) -> None:
        self._executor.shutdown(wait=wait)

    def __enter__(self) -> "WorkerPool":
        return self

    def __exit__(self, *_: Any) -> None:
        self.shutdown()
