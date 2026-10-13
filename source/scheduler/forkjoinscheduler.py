from collections.abc import Callable
from typing import Any

from .datatypes import Batch, Function, Task
from .persistentscheduler import PersistentScheduler
from .priorityqueue import PriorityQueue



# SCHEDULER
class ForkJoinScheduler(PersistentScheduler):
    """Runs one batch (the tasks of one key from one step) at a time and waits for all of them before the next step."""

    def __init__(self, functions: dict[str, Function], onExit: Callable[[str, Any], None], log: Callable[..., None]) -> None:
        super().__init__(functions, onExit, log)
        self.batches = PriorityQueue[Batch](self.depth)
        self.pending: dict[str, Batch] = {}

    def enqueue(self, key: str, task: Task, priority: int) -> None:
        if key in self.pending:
            self.pending[key].tasks.append(task)
        else:
            self.pending[key] = Batch(key, [task])

    def flush(self) -> None:
        for batch in self.pending.values():
            self.batches.register(batch, self.functions[batch.key].priority)
        self.pending.clear()

    def run(self) -> None:
        try:
            self.flush()
            while (batch := self.batches.pop()) is not None:
                for task in batch.tasks:
                    self.queue.register(task, 0)
                self.drain()
                self.flush()
        finally:
            self.shutdown()
