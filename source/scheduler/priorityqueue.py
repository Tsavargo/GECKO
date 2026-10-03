from collections import deque


class PriorityQueue[Type]:
    def __init__(self, depth: int = 2):
        if depth <= 0:
            raise ValueError(f"Invalid number of priority levels: {depth}. Must be a positive integer.")
        self.depth = depth
        self.priorityQueues: list[deque[Type]] = [deque() for stage in range(depth)]

    def register(self, item: Type, itemPriority: int) -> None:
        if not 0 <= itemPriority < self.depth:
            raise ValueError(f"Invalid priority: {itemPriority}. Must be in [0,{self.depth}).")
        self.priorityQueues[itemPriority].append(item)

    def pop(self) -> Type | None:
        for queue in self.priorityQueues:
            if queue: return queue.popleft()
        return None