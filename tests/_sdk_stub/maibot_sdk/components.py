"""组件元信息（与 maibot_sdk.components 对齐）。

测试桩只保留装饰器打在方法上的元数据结构，不实现组件注册/调度。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


# 装饰器把组件信息写到的属性名
_COMPONENT_INFO_ATTR = "_maibot_component_info"


@dataclass
class HookHandlerComponentInfo:
    name: str
    hook: str
    description: str = ""
    mode: Any = None
    order: Any = None
    error_policy: Any = None


@dataclass
class APIComponentInfo:
    name: str
    description: str = ""
    version: str = "1"
    public: bool = True


@dataclass
class ToolComponentInfo:
    name: str
    description: str = ""
    brief_description: str = ""
    parameters: list = field(default_factory=list)


@dataclass
class CommandComponentInfo:
    name: str
    description: str = ""
    pattern: str = ""


__all__ = [
    "_COMPONENT_INFO_ATTR",
    "HookHandlerComponentInfo",
    "APIComponentInfo",
    "ToolComponentInfo",
    "CommandComponentInfo",
]
