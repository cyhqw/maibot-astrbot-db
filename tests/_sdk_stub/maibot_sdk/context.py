"""插件上下文（与 maibot_sdk.context 对齐）。

测试桩提供最小化的 PluginContext：仅满足 plugin.py 在 on_load 中访问
ctx.paths.data_dir / ctx.logger 的需要。RPC、send、api、llm 等能力为空实现。
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class PluginPaths:
    """插件可写目录。"""

    data_dir: Path
    runtime_dir: Path


class _NullSend:
    """占位 send 能力。"""

    async def text(self, msg: str, stream_id: str = "", **_: Any) -> None:
        return None


class _NullApi:
    """占位 api 能力：测试桩不跨插件调用。"""

    async def call(self, api_name: str, *, version: str = "", **kwargs: Any) -> Any:
        raise RuntimeError(
            f"stub ctx.api.call({api_name!r}) 不可用（测试桩无 RPC）"
        )


class _NullLlm:
    """占位 llm 能力。"""

    async def embed(self, *args: Any, **kwargs: Any) -> Any:
        raise RuntimeError("stub ctx.llm.embed 不可用（测试桩无 LLM）")


class PluginContext:
    """插件运行上下文（测试桩）。"""

    def __init__(
        self,
        plugin_id: str = "",
        rpc_call: Any = None,
        paths: Any = None,
        **_: Any,
    ) -> None:
        self.plugin_id = plugin_id
        self.rpc_call = rpc_call
        self.paths = paths
        self.logger = logging.getLogger(f"maibot_sdk.stub.{plugin_id or 'plugin'}")
        self.send = _NullSend()
        self.api = _NullApi()
        self.llm = _NullLlm()


__all__ = ["PluginContext", "PluginPaths"]
