import json
from typing import Any

import boto3


class ClientSQS:
    def __init__(self) -> None:
        self.sqsClient = boto3.client("sqs")

    def publishMessage(self, queueUrl: str, message: Any, key: str) -> None:
        self.sqsClient.send_message(
            QueueUrl=queueUrl,
            MessageBody=json.dumps(message),
            MessageAttributes={"key": {"DataType": "String", "StringValue": key}},
        )


client: ClientSQS | None = None


def sqsClient() -> ClientSQS:
    global client
    if client is None:
        client = ClientSQS()
    return client


def publishMessage(queueUrl: str, message: Any, key: str) -> None:
    sqsClient().publishMessage(queueUrl, message, key)
