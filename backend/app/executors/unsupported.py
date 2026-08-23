from .base import TargetNotImplementedError


class UnsupportedExecutor:
    def __init__(self, target_type: str):
        self.target_type = target_type

    def execute(self, sql: str, limit: int = 200):
        raise TargetNotImplementedError(f"{self.target_type} is reserved but not connected in this POC.")
