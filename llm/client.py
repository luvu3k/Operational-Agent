"""
作用：
- 提供项目统一且尽量简洁的 LLM 客户端构建方式。
- 仅支持两种配置来源：显式传参，或从 `.env` 中读取 `LLM_MODEL_ID`、`LLM_API_KEY`、`LLM_BASE_URL`、`LLM_TIMEOUT`。
- 保持与 `core.react_agent`、`core.agent`、`core.tool_calling` 当前调用方式兼容，并保留结构化响应。

调用关系：
- 被 `core.react_agent` 调用，用于执行 ReAct 规划与总结阶段的大模型请求。
- 可被 `tools` 层、未来的 `memory` 层直接复用，通过 `chat`、`chat_stream`、`simple_chat` 与模型交互。
- 底层统一调用官方 `openai` Python SDK，只要目标服务兼容 OpenAI 接口即可接入。
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any, Dict, Iterator, List, Optional, Sequence, Union

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - 兼容未安装 python-dotenv 的环境
    def load_dotenv(*_args: Any, **_kwargs: Any) -> bool:
        return False

try:
    from openai import OpenAI
except ImportError:  # pragma: no cover - 兼容未安装 openai SDK 的环境
    OpenAI = None  # type: ignore[assignment]


MessageContent = Union[str, List[Dict[str, Any]]]
Message = Dict[str, Any]


@dataclass
class LLMUsage:
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


@dataclass
class LLMResponse:
    provider: str
    model: str
    content: str
    finish_reason: Optional[str] = None
    reasoning_content: Optional[str] = None
    tool_calls: List[Dict[str, Any]] = field(default_factory=list)
    usage: Optional[LLMUsage] = None
    raw_response: Any = None


@dataclass
class LLMConfig:
    model: str
    api_key: str
    base_url: str
    timeout: int = 60
    max_retries: int = 2
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None
    provider: str = "openai_compatible"
    detection_source: str = "unknown"


def load_env_if_needed() -> None:
    """加载项目根目录 `.env`，但不覆盖已有系统环境变量。"""
    from pathlib import Path

    env_path = Path(__file__).parent.parent / ".env"
    load_dotenv(str(env_path), override=False)


def _first_non_empty(candidates: Sequence[Optional[str]]) -> Optional[str]:
    for candidate in candidates:
        if candidate is not None and str(candidate).strip():
            return str(candidate).strip()
    return None


def _resolve_timeout(explicit_timeout: Optional[float]) -> int:
    if explicit_timeout is not None:
        return int(explicit_timeout)
    return int(float(os.getenv("LLM_TIMEOUT", 60)))


def resolve_model(explicit_model: Optional[str] = None) -> str:
    """优先使用显式传入的模型名，否则从 `LLM_MODEL_ID` 环境变量读取。"""
    model = _first_non_empty([explicit_model, os.getenv("LLM_MODEL_ID")])
    if model:
        return model
    raise ValueError("模型ID必须被提供，或在 `.env` 中定义 `LLM_MODEL_ID`。")


def resolve_api_key(explicit_api_key: Optional[str] = None) -> str:
    """优先使用显式传入的 API Key，否则从 `LLM_API_KEY` 环境变量读取。"""
    api_key = _first_non_empty([explicit_api_key, os.getenv("LLM_API_KEY")])
    if api_key:
        return api_key
    raise ValueError("API Key必须被提供，或在 `.env` 中定义 `LLM_API_KEY`。")


def resolve_base_url(explicit_base_url: Optional[str] = None) -> str:
    """优先使用显式传入的 base_url，否则从 `LLM_BASE_URL` 环境变量读取。"""
    base_url = _first_non_empty([explicit_base_url, os.getenv("LLM_BASE_URL")])
    if base_url:
        return base_url
    raise ValueError("服务地址必须被提供，或在 `.env` 中定义 `LLM_BASE_URL`。")


def build_openai_client(config: LLMConfig) -> OpenAI:
    """使用最终配置创建底层 OpenAI SDK 客户端。"""
    if OpenAI is None:
        raise ImportError("当前环境未安装 `openai` SDK，无法创建 LLM 客户端。")
    return OpenAI(
        api_key=config.api_key,
        base_url=config.base_url,
        timeout=config.timeout,
        max_retries=config.max_retries,
    )


def normalize_messages(messages: Sequence[Message]) -> List[Message]:
    """标准化消息列表，并保留 tool calling 需要的附加字段。"""
    normalized: List[Message] = []
    for message in messages:
        if "role" not in message:
            raise ValueError(f"消息缺少 role 字段: {message}")
        normalized.append(dict(message))
    return normalized


def _extract_message_text(content: MessageContent) -> str:
    if isinstance(content, str):
        return content
    text_parts: List[str] = []
    for item in content:
        if item.get("type") == "text":
            text_parts.append(str(item.get("text", "")))
    return "".join(text_parts)


def normalize_chat_response(raw_response: Any, config: LLMConfig, request_model: str) -> LLMResponse:
    """将底层 Chat Completions 响应归一化为项目内部统一格式。"""
    choice = raw_response.choices[0] if getattr(raw_response, "choices", None) else None
    message = getattr(choice, "message", None)
    usage_raw = getattr(raw_response, "usage", None)

    content = ""
    reasoning_content = None
    tool_calls: List[Dict[str, Any]] = []
    finish_reason = getattr(choice, "finish_reason", None)

    if message is not None:
        content = _extract_message_text(getattr(message, "content", "") or "")
        reasoning_content = getattr(message, "reasoning_content", None)
        raw_tool_calls = getattr(message, "tool_calls", None) or []
        for tool_call in raw_tool_calls:
            tool_calls.append(
                {
                    "id": getattr(tool_call, "id", None),
                    "type": getattr(tool_call, "type", None),
                    "function": {
                        "name": getattr(getattr(tool_call, "function", None), "name", None),
                        "arguments": getattr(getattr(tool_call, "function", None), "arguments", None),
                    },
                }
            )

    usage = None
    if usage_raw is not None:
        usage = LLMUsage(
            prompt_tokens=getattr(usage_raw, "prompt_tokens", 0) or 0,
            completion_tokens=getattr(usage_raw, "completion_tokens", 0) or 0,
            total_tokens=getattr(usage_raw, "total_tokens", 0) or 0,
        )

    return LLMResponse(
        provider=config.provider,
        model=request_model,
        content=content,
        finish_reason=finish_reason,
        reasoning_content=reasoning_content,
        tool_calls=tool_calls,
        usage=usage,
        raw_response=raw_response,
    )


class LLM:
    """
    项目统一 LLM 客户端。

    初始化优先级：
    - 若显式传入 `model`、`api_key`、`base_url`，优先使用显式参数。
    - 否则分别从 `.env` 中读取 `LLM_MODEL_ID`、`LLM_API_KEY`、`LLM_BASE_URL`。
    - 超时时间从显式 `timeout` 读取；若未提供，则读取 `LLM_TIMEOUT`，默认 60 秒。
    """

    def __init__(
        self,
        model: Optional[str] = None,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout: Optional[float] = None,
        max_retries: int = 2,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> None:
        load_env_if_needed()

        explicit_used = any(value is not None and str(value).strip() for value in [model, api_key, base_url])
        self.config = LLMConfig(
            model=resolve_model(model),
            api_key=resolve_api_key(api_key),
            base_url=resolve_base_url(base_url),
            timeout=_resolve_timeout(timeout),
            max_retries=max_retries,
            temperature=temperature,
            max_tokens=max_tokens,
            detection_source="explicit" if explicit_used else "env",
        )
        self.client = build_openai_client(self.config)

    def chat(
        self,
        messages: Sequence[Message],
        *,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
        tool_choice: Optional[Union[str, Dict[str, Any]]] = None,
        response_format: Optional[Dict[str, Any]] = None,
        extra_body: Optional[Dict[str, Any]] = None,
        stop: Optional[Union[str, List[str]]] = None,
    ) -> LLMResponse:
        """发起一次标准聊天请求，返回统一结构化响应。"""
        request_model = resolve_model(model) if model is not None else self.config.model
        payload: Dict[str, Any] = {
            "model": request_model,
            "messages": normalize_messages(messages),
        }
        final_temperature = temperature if temperature is not None else self.config.temperature
        final_max_tokens = max_tokens if max_tokens is not None else self.config.max_tokens
        if final_temperature is not None:
            payload["temperature"] = final_temperature
        if final_max_tokens is not None:
            payload["max_tokens"] = final_max_tokens
        if tools:
            payload["tools"] = tools
        if tool_choice is not None:
            payload["tool_choice"] = tool_choice
        if response_format is not None:
            payload["response_format"] = response_format
        if extra_body:
            payload["extra_body"] = extra_body
        if stop is not None:
            payload["stop"] = stop

        raw_response = self.client.chat.completions.create(**payload)
        return normalize_chat_response(raw_response, self.config, request_model)

    def chat_stream(
        self,
        messages: Sequence[Message],
        *,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
        tool_choice: Optional[Union[str, Dict[str, Any]]] = None,
    ) -> Iterator[str]:
        """发起流式请求并逐段返回文本内容。"""
        request_model = resolve_model(model) if model is not None else self.config.model
        payload: Dict[str, Any] = {
            "model": request_model,
            "messages": normalize_messages(messages),
            "stream": True,
        }
        final_temperature = temperature if temperature is not None else self.config.temperature
        final_max_tokens = max_tokens if max_tokens is not None else self.config.max_tokens
        if final_temperature is not None:
            payload["temperature"] = final_temperature
        if final_max_tokens is not None:
            payload["max_tokens"] = final_max_tokens
        if tools:
            payload["tools"] = tools
        if tool_choice is not None:
            payload["tool_choice"] = tool_choice

        stream = self.client.chat.completions.create(**payload)
        for chunk in stream:
            if not getattr(chunk, "choices", None):
                continue
            delta = getattr(chunk.choices[0], "delta", None)
            if delta is None:
                continue
            piece = getattr(delta, "content", None)
            if piece:
                yield piece

    def simple_chat(
        self,
        user_text: str,
        *,
        model: Optional[str] = None,
        system_prompt: Optional[str] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
        tool_choice: Optional[Union[str, Dict[str, Any]]] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> LLMResponse:
        """以最少参数发起一次对话。"""
        messages: List[Message] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": user_text})
        return self.chat(
            messages,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            tools=tools,
            tool_choice=tool_choice,
        )

    @property
    def provider(self) -> str:
        return self.config.provider

    @property
    def model(self) -> str:
        return self.config.model


UnifiedLLMClient = LLM


if __name__ == "__main__":
    print("=== client.py 本地测试 ===")
    load_env_if_needed()

    try:
        llm = LLM()
        print("客户端创建成功：")
        print(f"- provider: {llm.provider}")
        print(f"- model: {llm.model}")
        print(f"- base_url: {llm.config.base_url}")
        print(f"- detection_source: {llm.config.detection_source}")
    except Exception as exc:
        print(f"客户端创建失败: {exc}")
        raise SystemExit(0)

    try:
        response = llm.simple_chat(
            "请用一句中文介绍你自己。",
            system_prompt="你是一个用于测试 LLM 接口的助手。",
            temperature=0,
            max_tokens=64,
        )
        print("真实调用成功：")
        print(response)
    except Exception as exc:
        print(f"真实 API 调用失败: {exc}")
