"""
Role：
- 封装项目中使用的官方 OpenAI 客户端。
- 实现模型respond方法，提供统一的接口供上层调用。
- 提供单一的模型访问构建点。

Called：
- `Operational-Agent.agent`

Call：
- `config.settings`
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Iterator, List, Optional, Sequence, Union

from dotenv import load_dotenv
from openai import OpenAI


MessageContent = Union[str, List[Dict[str, Any]]]
Message = Dict[str, Any]


class ProviderType(str, Enum):
    OPENAI = "openai"
    DEEPSEEK = "deepseek"
    QWEN = "qwen"
    OPENAI_COMPATIBLE = "openai_compatible"


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
    provider: ProviderType
    model: str
    api_key: str
    base_url: Optional[str] = None
    timeout: float = 120.0
    max_retries: int = 2
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None

    @property
    def is_openai_compatible(self) -> bool:
        return self.provider in {
            ProviderType.OPENAI,
            ProviderType.DEEPSEEK,
            ProviderType.QWEN,
            ProviderType.OPENAI_COMPATIBLE,
        }


def load_env_if_needed() -> None:
    load_dotenv(override=False)


def detect_provider(
    explicit_provider: Optional[str] = None,
    explicit_base_url: Optional[str] = None,
) -> ProviderType:
    """
    自动识别 provider。
    优先级：
    1. 显式传入 provider
    2. 环境变量 LLM_PROVIDER
    3. 根据 base_url 推断
    4. 根据存在的 API Key 推断
    5. 默认 openai
    """
    provider_raw = (explicit_provider or os.getenv("LLM_PROVIDER", "")).strip().lower()
    if provider_raw:
        if provider_raw in {"openai"}:
            return ProviderType.OPENAI
        if provider_raw in {"deepseek"}:
            return ProviderType.DEEPSEEK
        if provider_raw in {"qwen", "dashscope"}:
            return ProviderType.QWEN
        return ProviderType.OPENAI_COMPATIBLE

    base_url = (explicit_base_url or os.getenv("LLM_BASE_URL", "")).strip().lower()
    if "api.deepseek.com" in base_url:
        return ProviderType.DEEPSEEK
    if "dashscope.aliyuncs.com" in base_url or "dashscope-intl.aliyuncs.com" in base_url:
        return ProviderType.QWEN
    if "api.openai.com" in base_url:
        return ProviderType.OPENAI
    if base_url:
        return ProviderType.OPENAI_COMPATIBLE

    if os.getenv("DEEPSEEK_API_KEY"):
        return ProviderType.DEEPSEEK
    if os.getenv("DASHSCOPE_API_KEY"):
        return ProviderType.QWEN
    if os.getenv("OPENAI_API_KEY"):
        return ProviderType.OPENAI

    return ProviderType.OPENAI


def resolve_api_key(
    provider: ProviderType,
    explicit_api_key: Optional[str] = None,
) -> str:
    if explicit_api_key:
        return explicit_api_key

    generic = os.getenv("LLM_API_KEY")
    if generic:
        return generic

    if provider == ProviderType.OPENAI:
        key = os.getenv("OPENAI_API_KEY")
    elif provider == ProviderType.DEEPSEEK:
        key = os.getenv("DEEPSEEK_API_KEY")
    elif provider == ProviderType.QWEN:
        key = os.getenv("DASHSCOPE_API_KEY")
    else:
        key = os.getenv("OPENAI_API_KEY") or os.getenv("DEEPSEEK_API_KEY") or os.getenv("DASHSCOPE_API_KEY")

    if not key:
        raise ValueError(f"Cannot resolve API key for provider={provider.value}")

    return key


def resolve_base_url(
    provider: ProviderType,
    explicit_base_url: Optional[str] = None,
) -> Optional[str]:
    if explicit_base_url:
        return explicit_base_url

    env_base_url = os.getenv("LLM_BASE_URL")
    if env_base_url:
        return env_base_url

    if provider == ProviderType.OPENAI:
        return None
    if provider == ProviderType.DEEPSEEK:
        return "https://api.deepseek.com"
    if provider == ProviderType.QWEN:
        return "https://dashscope.aliyuncs.com/compatible-mode/v1"

    return None


def normalize_messages(messages: Sequence[Message]) -> List[Message]:
    normalized: List[Message] = []
    for msg in messages:
        role = msg.get("role")
        content = msg.get("content", "")
        if not role:
            raise ValueError(f"Invalid message without role: {msg}")
        normalized.append({"role": role, "content": content})
    return normalized


def build_openai_client(config: LLMConfig) -> OpenAI:
    kwargs: Dict[str, Any] = {
        "api_key": config.api_key,
        "timeout": config.timeout,
        "max_retries": config.max_retries,
    }
    if config.base_url:
        kwargs["base_url"] = config.base_url
    return OpenAI(**kwargs)


def normalize_chat_response(raw_response: Any, config: LLMConfig) -> LLMResponse:
    choice = raw_response.choices[0] if getattr(raw_response, "choices", None) else None
    message = getattr(choice, "message", None)
    usage_raw = getattr(raw_response, "usage", None)

    content = ""
    reasoning_content = None
    tool_calls: List[Dict[str, Any]] = []
    finish_reason = getattr(choice, "finish_reason", None)

    if message is not None:
        content = getattr(message, "content", "") or ""

        raw_tool_calls = getattr(message, "tool_calls", None) or []
        for tc in raw_tool_calls:
            tool_calls.append(
                {
                    "id": getattr(tc, "id", None),
                    "type": getattr(tc, "type", None),
                    "function": {
                        "name": getattr(getattr(tc, "function", None), "name", None),
                        "arguments": getattr(getattr(tc, "function", None), "arguments", None),
                    },
                }
            )

        # DeepSeek reasoning model may expose reasoning_content
        reasoning_content = getattr(message, "reasoning_content", None)

    usage = None
    if usage_raw is not None:
        usage = LLMUsage(
            prompt_tokens=getattr(usage_raw, "prompt_tokens", 0) or 0,
            completion_tokens=getattr(usage_raw, "completion_tokens", 0) or 0,
            total_tokens=getattr(usage_raw, "total_tokens", 0) or 0,
        )

    return LLMResponse(
        provider=config.provider.value,
        model=config.model,
        content=content,
        finish_reason=finish_reason,
        reasoning_content=reasoning_content,
        tool_calls=tool_calls,
        usage=usage,
        raw_response=raw_response,
    )


class UnifiedLLMClient:
    """
    项目统一 LLM 调用入口。

    设计目标：
    - 屏蔽 OpenAI / DeepSeek / Qwen 差异
    - 提供统一 chat / stream 接口
    - 统一返回结构，方便 core 层调用
    """

    def __init__(self, config: LLMConfig) -> None:
        self.config = config
        self._sdk_client = build_openai_client(config)

    @classmethod
    def from_env(
        cls,
        model: Optional[str] = None,
        provider: Optional[str] = None,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout: float = 120.0,
        max_retries: int = 2,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> "UnifiedLLMClient":
        load_env_if_needed()

        detected_provider = detect_provider(
            explicit_provider=provider,
            explicit_base_url=base_url,
        )

        resolved_model = model or os.getenv("LLM_MODEL")
        if not resolved_model:
            raise ValueError("LLM model is required. Set `model` or `LLM_MODEL`.")

        config = LLMConfig(
            provider=detected_provider,
            model=resolved_model,
            api_key=resolve_api_key(detected_provider, explicit_api_key=api_key),
            base_url=resolve_base_url(detected_provider, explicit_base_url=base_url),
            timeout=timeout,
            max_retries=max_retries,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return cls(config)

    def chat(
        self,
        messages: Sequence[Message],
        *,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
        tool_choice: Optional[Union[str, Dict[str, Any]]] = None,
        response_format: Optional[Dict[str, Any]] = None,
        extra_body: Optional[Dict[str, Any]] = None,
        stop: Optional[Union[str, List[str]]] = None,
    ) -> LLMResponse:
        normalized_messages = normalize_messages(messages)

        payload: Dict[str, Any] = {
            "model": self.config.model,
            "messages": normalized_messages,
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

        raw_response = self._sdk_client.chat.completions.create(**payload)
        return normalize_chat_response(raw_response, self.config)

    def chat_stream(
        self,
        messages: Sequence[Message],
        *,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
        tool_choice: Optional[Union[str, Dict[str, Any]]] = None,
        response_format: Optional[Dict[str, Any]] = None,
        extra_body: Optional[Dict[str, Any]] = None,
        stop: Optional[Union[str, List[str]]] = None,
    ) -> Iterator[str]:
        normalized_messages = normalize_messages(messages)

        payload: Dict[str, Any] = {
            "model": self.config.model,
            "messages": normalized_messages,
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
        if response_format is not None:
            payload["response_format"] = response_format
        if extra_body:
            payload["extra_body"] = extra_body
        if stop is not None:
            payload["stop"] = stop

        stream = self._sdk_client.chat.completions.create(**payload)

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
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> LLMResponse:
        messages: List[Message] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": user_text})
        return self.chat(
            messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )

    @property
    def provider(self) -> str:
        return self.config.provider.value

    @property
    def model(self) -> str:
        return self.config.model
