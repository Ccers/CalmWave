# utils.py
from dataclasses import dataclass

@dataclass
class Data:
    code: str
    msg: str
    result: object = None
    def to_dict(self):
        return {
            "code": self.code,
            "msg": self.msg,
            "result": self.result
        }


