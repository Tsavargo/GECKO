from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .proxy import Proxy


@dataclass
class OutputMessage:
    key: str
    output: Any

@dataclass
class ErrorMessage:
    error: str

@dataclass
class TimeMessage:
    start: float
    end: float

type Message = OutputMessage | ErrorMessage | TimeMessage

@dataclass
class Task[Type]:
    data: Type
    handler: Callable[[Type, Proxy], None]