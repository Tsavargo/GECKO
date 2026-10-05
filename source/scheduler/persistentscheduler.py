import multiprocessing
from collections.abc import Callable
from contextlib import suppress
from multiprocessing.connection import Connection
from typing import Any

from .datatypes import Task
from .priorityqueue import PriorityQueue
from .scheduler import Scheduler, execute



# HELPER
def workerLoop(connection: Connection) -> None:
    while (task := connection.recv()) is not None:
        execute(task, connection)



# SCHEDULER
class PersistentScheduler(Scheduler):
    """Reuses worker processes between the tasks of a run, the workers are stopped when the run ends."""

    def __init__(self, queue: PriorityQueue[Task], onOutput: Callable[[str, Any], None], log: Callable[..., None]) -> None:
        super().__init__(queue, onOutput, log)
        self.idle: list[tuple[Connection, multiprocessing.Process]] = []

    def spawn(self) -> tuple[Connection, multiprocessing.Process]:
        parentEnd, childEnd = self.context.Pipe()
        process = self.context.Process(target=workerLoop, args=[childEnd], daemon=True)
        process.start()
        childEnd.close()
        return parentEnd, process

    def dispatch(self, task: Task) -> None:
        while self.idle and not self.idle[-1][1].is_alive():
            self.idle.pop()[0].close()
        connection, process = self.idle.pop() if self.idle else self.spawn()
        connection.send(task)
        self.busy[connection] = process

    def release(self, connection: Connection) -> None:
        self.idle.append((connection, self.busy.pop(connection)))

    def shutdown(self) -> None:
        for connection, process in self.idle:
            with suppress(OSError):
                connection.send(None)
            connection.close()
            process.join()
        self.idle.clear()
        super().shutdown()
