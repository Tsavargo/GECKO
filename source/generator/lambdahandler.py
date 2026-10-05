import importlib
import json
import logging
import os
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from awsutil import sqs
from scheduler import PriorityQueue, Proxy, Task, OneShotScheduler

logging.basicConfig(level=logging.INFO)

COMPOSITE_DIR: Path = Path(__file__).resolve().parent
OUTPUT_QUEUE_URL: str = os.environ.get("OUTPUT_QUEUE_URL", "")

logger = logging.getLogger("composite")
logger.setLevel(logging.INFO)


def log(level: int, event: str, **fields: Any) -> None:
    logger.log(level, json.dumps({"time": datetime.now(timezone.utc).isoformat(), "event": event, **fields}, default=str))


@dataclass
class Function:
    name: str
    handler: Callable[[Any, Proxy], None]
    priority: int


def loadHandler(name: str) -> Callable[[Any, Proxy], None]:
    return importlib.import_module(f"{name}.process").process


def loadFunctions(configPath: Path) -> dict[str, Function]:
    config = json.loads(configPath.read_text(encoding="utf-8"))
    if not config.get("functions"):
        raise ValueError("config.json: 'functions' must be a non-empty list")

    functions: dict[str, Function] = {}
    for entry in config["functions"]:
        if entry["input"] in functions:
            raise ValueError(f"config.json: input {entry['input']!r} is consumed by more than one function")
        functions[entry["input"]] = Function(entry["name"], loadHandler(entry["name"]), entry["priority"])
    return functions


def onOutput(key: str, output: Any) -> None:
    function = functions.get(key)
    if function is not None:
        queue.register(Task(output, function.handler), function.priority)
    elif OUTPUT_QUEUE_URL:
        sqs.publishMessage(OUTPUT_QUEUE_URL, output, key)
    else:
        log(logging.INFO, "PIPELINE_FINISHED", key=key, output=output)


functions = loadFunctions(COMPOSITE_DIR.joinpath("config.json"))
queue = PriorityQueue[Task](max(function.priority for function in functions.values()) + 1)
scheduler = OneShotScheduler(queue, onOutput, log)

if OUTPUT_QUEUE_URL:
    sqs.sqsClient()


def lambda_handler(event: dict[str, Any], context: Any) -> None:
    record = event["Records"][0]
    onOutput(record["messageAttributes"]["key"]["stringValue"], json.loads(record["body"]))
    scheduler.run()
