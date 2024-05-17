class MemoryItem:
    def __init__(
        self,
        data,
        status,
    ):
        self.data = data
        self.status = status

    def __str__(self) -> str:
        return f"{self.data}, {self.status}"