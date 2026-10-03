import multiprocessing
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


def runner(task: Task, connection: Connection) -> None:
    start = time.perf_counter()
    try:
        task.handler(task.data, Proxy(connection))
    except Exception:
        connection.send(ErrorMessage(traceback.format_exc()))
    connection.send(TimeMessage(start, time.perf_counter()))



# SCHEDULER
class Scheduler:
    def __init__(self, queue: PriorityQueue[Task], onOutput: Callable[[str, Any], None], log: Callable[..., None]) -> None:
        self.queue = queue
        self.onOutput = onOutput
        self.log = log
        self.limit = workerLimit()
        self.context = multiprocessing.get_context("fork")
        self.workers: dict[Connection, multiprocessing.Process] = {}

    def spawn(self, task: Task) -> None:
        reader, writer = self.context.Pipe(duplex=False)
        process = self.context.Process(target=runner, args=(task, writer))
        process.start()
        writer.close()
        self.workers[reader] = process

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

    def reap(self, reader: Connection) -> None:
        process = self.workers.pop(reader)
        reader.close()
        process.join()
        if process.exitcode:
            self.log(logging.WARNING, "WORKER_DIED", exitCode=process.exitcode)

    def run(self) -> None:
        while True:
            while len(self.workers) < self.limit and (task := self.queue.pop()) is not None:
                self.spawn(task)
            if not self.workers:
                return
            for reader in wait(list[Connection](self.workers)):
                try:
                    self.handle(reader.recv())
                except EOFError:
                    self.reap(reader)