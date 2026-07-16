"""maibot_sdk 测试桩（stub）。

仅用于在未安装真实 MaiBot Plugin SDK 的环境下跑单元/集成测试。
提供与 SDK 2.x 表面兼容的最小化装饰器与基类，使 plugin.py、injector.py、
interceptor.py、kb/api.py 能被导入并实例化。

⚠️ 这不是真实 SDK：
- 不实现 RPC、Hook 调度、组件注册、配置文件读写等运行时行为；
- 装饰器只把组件元数据挂在方法上，供测试用 getattr 反射检查；
- 在真实 MaiBot 环境中请 pip 安装 maibot_plugin_sdk，conftest 会优先用真实 SDK。
"""

from __future__ import annotations

import logging
from typing import Any, Callable, Optional

from pydantic import BaseModel, Field

from .components import (
    _COMPONENT_INFO_ATTR,
    APIComponentInfo,
    CommandComponentInfo,
    HookHandlerComponentInfo,
    ToolComponentInfo,
)
from .context import PluginContext, PluginPaths
from .types import (
    ErrorPolicy,
    HookMode,
    HookOrder,
    ToolParameterInfo,
    ToolParamType,
)


# --------------------------------------------------------------------
# 配置基类
# --------------------------------------------------------------------


class PluginConfigBase(BaseModel):
    """插件配置基类（对齐 pydantic BaseModel，允许任意类型字段）。"""

    model_config = {  # type: ignore[assignment]
        "arbitrary_types_allowed": True,
        "extra": "allow",
    }


# --------------------------------------------------------------------
# 装饰器
# --------------------------------------------------------------------


def HookHandler(
    hook: str,
    *,
    name: str = "",
    description: str = "",
    mode: Any = None,
    order: Any = None,
    error_policy: Any = None,
) -> Callable[[Callable], Callable]:
    """标记一个方法为 Hook 处理器。桩：只挂元数据，不注册。"""

    info = HookHandlerComponentInfo(
        name=name or hook,
        hook=hook,
        description=description,
        mode=mode,
        order=order,
        error_policy=error_policy,
    )

    def decorator(func: Callable) -> Callable:
        setattr(func, _COMPONENT_INFO_ATTR, info)
        return func

    return decorator


def API(
    name: str,
    *,
    description: str = "",
    version: str = "1",
    public: bool = True,
) -> Callable[[Callable], Callable]:
    info = APIComponentInfo(
        name=name, description=description, version=version, public=public
    )

    def decorator(func: Callable) -> Callable:
        setattr(func, _COMPONENT_INFO_ATTR, info)
        return func

    return decorator


def Tool(
    name: str,
    *,
    description: str = "",
    brief_description: str = "",
    parameters: Optional[list] = None,
) -> Callable[[Callable], Callable]:
    info = ToolComponentInfo(
        name=name,
        description=description,
        brief_description=brief_description,
        parameters=parameters or [],
    )

    def decorator(func: Callable) -> Callable:
        setattr(func, _COMPONENT_INFO_ATTR, info)
        return func

    return decorator


def Command(
    name: str,
    *,
    description: str = "",
    pattern: str = "",
) -> Callable[[Callable], Callable]:
    info = CommandComponentInfo(name=name, description=description, pattern=pattern)

    def decorator(func: Callable) -> Callable:
        setattr(func, _COMPONENT_INFO_ATTR, info)
        return func

    return decorator


# --------------------------------------------------------------------
# 插件基类
# --------------------------------------------------------------------


class _NullPaths:
    def __init__(self) -> None:
        self.data_dir: Any = None
        self.runtime_dir: Any = None


class _NullCtx:
    """实例化时的占位 context，测试用 _set_context 覆盖。"""

    def __init__(self) -> None:
        self.logger = logging.getLogger("maibot_sdk.stub")
        self.paths = _NullPaths()


class MaiBotPlugin:
    """插件基类（测试桩）。"""

    config_model: Any = None

    def __init__(self) -> None:
        self.ctx: Any = _NullCtx()
        self._plugin_config_instance: Any = None
        self._plugin_config_data: dict = {}

    # ---- 上下文注入 ----
    def _set_context(self, ctx: Any) -> None:
        self.ctx = ctx

    def _get_logger(self) -> logging.Logger:
        return logging.getLogger(self.__class__.__name__)

    # ---- 配置 ----
    @property
    def config(self) -> Any:
        if self._plugin_config_instance is not None:
            return self._plugin_config_instance
        if self.config_model is not None:
            try:
                self._plugin_config_instance = self.config_model(
                    **self._plugin_config_data
                )
            except Exception:
                return self._plugin_config_data
            return self._plugin_config_instance
        return self._plugin_config_data

    # ---- 生命周期（默认空实现，子类覆盖）----
    async def on_load(self) -> None:
        return None

    async def on_unload(self) -> None:
        return None

    async def on_config_update(
        self, scope: str, config_data: dict, version: str
    ) -> None:
        return None


__all__ = [
    # 装饰器
    "API",
    "Command",
    "Tool",
    "HookHandler",
    # 基类
    "MaiBotPlugin",
    "PluginConfigBase",
    "Field",
    # 组件元信息
    "_COMPONENT_INFO_ATTR",
    "HookHandlerComponentInfo",
    "APIComponentInfo",
    "ToolComponentInfo",
    "CommandComponentInfo",
    # 类型
    "HookMode",
    "HookOrder",
    "ErrorPolicy",
    "ToolParamType",
    "ToolParameterInfo",
    # 上下文
    "PluginContext",
    "PluginPaths",
]
