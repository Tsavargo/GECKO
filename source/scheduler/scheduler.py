import multiprocessing
from abc import ABC, abstractmethod
from collections.abc import Callable
from multiprocessing.connection import Connection, wait
import os
import time
import traceback
from typing import Any
import logging

from .datatypes import ErrorMessage, Message, OutputMessage, Task, TimeMessage
from .priorityqueue import PriorityQueue
from .proxy import Proxy



# HELPER
def workerLimit() -> int:
    limit = os.process_cpu_count() or 1
    memory = os.environ.get("AWS_LAMBDA_FUNCTION_MEMORY_SIZE")
    if memory:
        limit = min(limit, int(memory) // 1769)
    return max(1, limit)


def execute(task: Task, connection: Connection) -> None:
    start = time.perf_counter()
    try:
        task.handler(task.data, Proxy(connection))
    except (Exception, SystemExit):
        connection.send(ErrorMessage(traceback.format_exc()))
    connection.send(TimeMessage(start, time.perf_counter()))



# SCHEDULER
class Scheduler(ABC):
    def __init__(self, queue: PriorityQueue[Task], onOutput: Callable[[str, Any], None], log: Callable[..., None]) -> None:
        self.queue = queue
        self.onOutput = onOutput
        self.log = log
        self.limit = workerLimit()
        self.context = multiprocessing.get_context("fork")
        self.busy: dict[Connection, multiprocessing.Process] = {}

    @abstractmethod
    def dispatch(self, task: Task) -> None:
        """Start the task on a worker and register its connection in self.busy."""

    @abstractmethod
    def release(self, connection: Connection) -> None:
        """Called when the worker behind the connection has finished its task."""

    def handle(self, message: Message) -> None:
        match message:
            case OutputMessage(key, output):
                self.onOutput(key, output)
            case TimeMessage(start, end):
                self.log(logging.INFO, "TASK_FINISHED", durationMs=round((end - start) * 1000, 3))
            case ErrorMessage(error):
                self.log(logging.ERROR, "TASK_FAILED", error=error)
            case _:
                self.log(logging.WARNING, "UNKNOWN_MESSAGE", message=repr(message))

    def retire(self, connection: Connection) -> multiprocessing.Process:
        process = self.busy.pop(connection)
        connection.close()
        process.join()
        return process

    def reap(self, connection: Connection) -> None:
        self.log(logging.WARNING, "WORKER_DIED", exitCode=self.retire(connection).exitcode)

    def shutdown(self) -> None:
        for connection, process in self.busy.items():
            process.kill()
            connection.close()
            process.join()
        self.busy.clear()

    def run(self) -> None:
        try:
            while True:
                while len(self.busy) < self.limit and (task := self.queue.pop()) is not None:
                    self.dispatch(task)
                if not self.busy:
                    return
                for connection in wait(list[Connection](self.busy)):
                    try:
                        message = connection.recv()
                    except EOFError:
                        self.reap(connection)
                        continue
                    self.handle(message)
                    if isinstance(message, TimeMessage):
                        self.release(connection)
        finally:
            self.shutdown()
