"""类型与枚举（与 maibot_sdk.types 对齐）。"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, List


class HookMode(str, Enum):
    """Hook 触发模式。"""

    BLOCKING = "blocking"
    OBSERVE = "observe"


class HookOrder(int, Enum):
    """Hook 执行优先级。"""

    EARLY = -100
    NORMAL = 0
    LATE = 100


class ErrorPolicy(str, Enum):
    """Hook 处理器抛异常时的策略。"""

    RAISE = "raise"
    SKIP = "skip"


class ToolParamType(str, Enum):
    """LLM Tool 参数类型。"""

    STRING = "string"
    INTEGER = "integer"
    NUMBER = "number"
    BOOLEAN = "boolean"
    ARRAY = "array"
    OBJECT = "object"


@dataclass
class ToolParameterInfo:
    """LLM Tool 参数描述。"""

    name: str
    param_type: Any
    description: str = ""
    required: bool = False
    default: Any = None
    enum: List[Any] = field(default_factory=list)


__all__ = [
    "HookMode",
    "HookOrder",
    "ErrorPolicy",
    "ToolParamType",
    "ToolParameterInfo",
]
