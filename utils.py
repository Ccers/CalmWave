# utils.py
from dataclasses import dataclass

@dataclass
class Data:
    code: str
    msg: str
    result: object = None


