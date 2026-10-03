from multiprocessing.connection import Connection
from typing import Any

from .datatypes import OutputMessage


class Proxy:
    def __init__(self, connection: Connection) -> None:
        self.connection = connection

    def register(self, key: str, output: Any) -> None:
        self.connection.send(OutputMessage(key, output))