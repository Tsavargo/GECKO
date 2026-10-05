from collections.abc import Callable
from multiprocessing.connection import Connection
from typing import Any

from .datatypes import Task
from .priorityqueue import PriorityQueue
from .scheduler import Scheduler, execute



# SCHEDULER
class OneShotScheduler(Scheduler):
    """Forks a fresh process for every task, the process exits when the task is done."""

    def __init__(self, queue: PriorityQueue[Task], onOutput: Callable[[str, Any], None], log: Callable[..., None]) -> None:
        super().__init__(queue, onOutput, log)
        self.finished: set[Connection] = set()

    def dispatch(self, task: Task) -> None:
        reader, writer = self.context.Pipe(duplex=False)
        process = self.context.Process(target=execute, args=(task, writer))
        process.start()
        writer.close()
        self.busy[reader] = process

    def release(self, connection: Connection) -> None:
        self.finished.add(connection)

    def reap(self, connection: Connection) -> None:
        if connection in self.finished:
            self.finished.remove(connection)
            self.retire(connection)
        else:
            super().reap(connection)

    def shutdown(self) -> None:
        self.finished.clear()
        super().shutdown()
