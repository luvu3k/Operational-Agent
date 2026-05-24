"""
作用：
- 提供项目统一的 LLM 调用入口，兼容 OpenAI、DeepSeek、Qwen 以及其他 OpenAI 兼容服务。
- 根据环境变量、模型名、服务地址和 API Key 自动识别 provider，尽量减少用户配置负担。

调用关系：
- 被 `core.react_agent` 调用，用于发起 ReAct 规划阶段的模型请求。
- 可被未来的 `core.confirmation`、`tools.code_repair_tool`、`memory.summarizer` 复用。
- 底层调用官方 `openai` Python SDK，但对上层暴露统一的 provider 无关接口。
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from enum import Enum
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


class ProviderType(str, Enum):
    OPENAI = "openai"
    DEEPSEEK = "deepseek"
    QWEN = "qwen"
    OPENAI_COMPATIBLE = "openai_compatible"


@dataclass(frozen=True)
class ProviderProfile:
    provider: ProviderType
    default_model: str
    default_base_url: Optional[str]
    api_key_envs: List[str]
    model_envs: List[str]
    base_url_envs: List[str]
    model_prefixes: List[str]
    base_url_keywords: List[str]


PROVIDER_PROFILES: Dict[ProviderType, ProviderProfile] = {
    ProviderType.OPENAI: ProviderProfile(
        provider=ProviderType.OPENAI,
        default_model="gpt-4.1-mini",
        default_base_url=None,
        api_key_envs=["OPENAI_API_KEY"],
        model_envs=["OPENAI_MODEL"],
        base_url_envs=["OPENAI_BASE_URL"],
        model_prefixes=["gpt-", "o1", "o3", "o4"],
        base_url_keywords=["api.openai.com"],
    ),
    ProviderType.DEEPSEEK: ProviderProfile(
        provider=ProviderType.DEEPSEEK,
        default_model="deepseek-chat",
        default_base_url="https://api.deepseek.com",
        api_key_envs=["DEEPSEEK_API_KEY"],
        model_envs=["DEEPSEEK_MODEL"],
        base_url_envs=["DEEPSEEK_BASE_URL"],
        model_prefixes=["deepseek-"],
        base_url_keywords=["api.deepseek.com"],
    ),
    ProviderType.QWEN: ProviderProfile(
        provider=ProviderType.QWEN,
        default_model="qwen-plus",
        default_base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
        api_key_envs=["DASHSCOPE_API_KEY", "QWEN_API_KEY"],
        model_envs=["QWEN_MODEL", "DASHSCOPE_MODEL"],
        base_url_envs=["QWEN_BASE_URL", "DASHSCOPE_BASE_URL"],
        model_prefixes=["qwen-"],
        base_url_keywords=["dashscope.aliyuncs.com", "dashscope-intl.aliyuncs.com"],
    ),
    ProviderType.OPENAI_COMPATIBLE: ProviderProfile(
        provider=ProviderType.OPENAI_COMPATIBLE,
        default_model="gpt-4.1-mini",
        default_base_url=None,
        api_key_envs=["CLOSEAI_API_KEY", "OPENAI_COMPATIBLE_API_KEY"],
        model_envs=["CLOSEAI_MODEL", "OPENAI_COMPATIBLE_MODEL"],
        base_url_envs=["CLOSEAI_BASE_URL", "OPENAI_COMPATIBLE_BASE_URL"],
        model_prefixes=[],
        base_url_keywords=[],
    ),
}


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
    detection_source: str = "unknown"


def load_env_if_needed() -> None:
    """加载当前项目目录下的环境变量，但不覆盖已有系统变量。"""
    load_dotenv(override=False)


def _first_non_empty(candidates: Sequence[Optional[str]]) -> Optional[str]:
    for candidate in candidates:
        if candidate is not None and str(candidate).strip():
            return str(candidate).strip()
    return None


def _normalize_provider_name(value: str) -> ProviderType:
    name = value.strip().lower()
    if name in {"openai"}:
        return ProviderType.OPENAI
    if name in {"deepseek"}:
        return ProviderType.DEEPSEEK
    if name in {"qwen", "dashscope"}:
        return ProviderType.QWEN
    return ProviderType.OPENAI_COMPATIBLE


def _infer_provider_from_base_url(base_url: Optional[str]) -> Optional[ProviderType]:
    if not base_url:
        return None
    text = base_url.strip().lower()
    for provider, profile in PROVIDER_PROFILES.items():
        if any(keyword in text for keyword in profile.base_url_keywords):
            return provider
    return ProviderType.OPENAI_COMPATIBLE


def _infer_provider_from_model(model: Optional[str]) -> Optional[ProviderType]:
    if not model:
        return None
    text = model.strip().lower()
    for provider, profile in PROVIDER_PROFILES.items():
        if any(text.startswith(prefix) for prefix in profile.model_prefixes):
            return provider
    return None


def _infer_provider_from_keys() -> Optional[ProviderType]:
    for provider, profile in PROVIDER_PROFILES.items():
        if any(os.getenv(env_name) for env_name in profile.api_key_envs):
            return provider
    if os.getenv("LLM_API_KEY"):
        return ProviderType.OPENAI_COMPATIBLE
    return None


def detect_provider(
    explicit_provider: Optional[str] = None,
    explicit_base_url: Optional[str] = None,
    explicit_model: Optional[str] = None,
) -> tuple[ProviderType, str]:
    """
    自动识别 provider。

    优先级：
    1. 显式 provider / `LLM_PROVIDER`
    2. base_url / 各 provider 专属 base_url
    3. model / 各 provider 专属 model
    4. API Key
    5. 默认回退为 OpenAI
    """
    provider_value = _first_non_empty([explicit_provider, os.getenv("LLM_PROVIDER")])
    if provider_value:
        return _normalize_provider_name(provider_value), "provider"

    base_url = _first_non_empty(
        [
            explicit_base_url,
            os.getenv("LLM_BASE_URL"),
            os.getenv("CLOSEAI_BASE_URL"),
            os.getenv("OPENAI_COMPATIBLE_BASE_URL"),
            os.getenv("OPENAI_BASE_URL"),
            os.getenv("DEEPSEEK_BASE_URL"),
            os.getenv("QWEN_BASE_URL"),
            os.getenv("DASHSCOPE_BASE_URL"),
        ]
    )
    provider_from_base_url = _infer_provider_from_base_url(base_url)
    if provider_from_base_url is not None:
        return provider_from_base_url, "base_url"

    model = _first_non_empty(
        [
            explicit_model,
            os.getenv("LLM_MODEL"),
            os.getenv("CLOSEAI_MODEL"),
            os.getenv("OPENAI_COMPATIBLE_MODEL"),
            os.getenv("OPENAI_MODEL"),
            os.getenv("DEEPSEEK_MODEL"),
            os.getenv("QWEN_MODEL"),
            os.getenv("DASHSCOPE_MODEL"),
        ]
    )
    provider_from_model = _infer_provider_from_model(model)
    if provider_from_model is not None:
        return provider_from_model, "model"

    provider_from_keys = _infer_provider_from_keys()
    if provider_from_keys is not None:
        return provider_from_keys, "api_key"

    return ProviderType.OPENAI, "default"


def resolve_api_key(provider: ProviderType, explicit_api_key: Optional[str] = None) -> str:
    """根据 provider 和环境变量解析最终 API Key。"""
    if explicit_api_key:
        return explicit_api_key.strip()

    generic_key = _first_non_empty([os.getenv("LLM_API_KEY")])
    if generic_key:
        return generic_key

    profile = PROVIDER_PROFILES[provider]
    for env_name in profile.api_key_envs:
        value = os.getenv(env_name)
        if value:
            return value.strip()

    raise ValueError(f"未能为 provider={provider.value} 解析出 API Key。")


def resolve_base_url(provider: ProviderType, explicit_base_url: Optional[str] = None) -> Optional[str]:
    """根据 provider 解析最终 base_url。"""
    base_url = _first_non_empty([explicit_base_url, os.getenv("LLM_BASE_URL")])
    if base_url:
        return base_url

    profile = PROVIDER_PROFILES[provider]
    for env_name in profile.base_url_envs:
        value = os.getenv(env_name)
        if value:
            return value.strip()

    return profile.default_base_url


def resolve_model(provider: ProviderType, explicit_model: Optional[str] = None) -> str:
    """根据 provider 解析最终模型名，并在缺省时提供合理默认值。"""
    model = _first_non_empty([explicit_model, os.getenv("LLM_MODEL")])
    if model:
        return model

    profile = PROVIDER_PROFILES[provider]
    for env_name in profile.model_envs:
        value = os.getenv(env_name)
        if value:
            return value.strip()

    return profile.default_model


def build_openai_client(config: LLMConfig) -> OpenAI:
    """创建底层官方 OpenAI SDK 客户端。"""
    if OpenAI is None:
        raise ImportError("当前环境未安装 openai SDK，无法创建 LLM 客户端。")
    kwargs: Dict[str, Any] = {
        "api_key": config.api_key,
        "timeout": config.timeout,
        "max_retries": config.max_retries,
    }
    if config.base_url:
        kwargs["base_url"] = config.base_url
    return OpenAI(**kwargs)


def normalize_messages(messages: Sequence[Message]) -> List[Message]:
    """标准化消息结构，同时保留 tool 调用所需额外字段。"""
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


def normalize_chat_response(raw_response: Any, config: LLMConfig) -> LLMResponse:
    """将不同 provider 返回的 Chat Completions 响应统一归一化。"""
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
        provider=config.provider.value,
        model=config.model,
        content=content,
        finish_reason=finish_reason,
        reasoning_content=reasoning_content,
        tool_calls=tool_calls,
        usage=usage,
        raw_response=raw_response,
    )


class LLM:
    """
    统一 LLM 调用器。

    设计目标：
    - 保留你当前项目中 `LLM` 的调用方式；
    - 自动识别 provider，尽量减少用户配置；
    - 统一支持普通聊天和 tool calling。
    """

    def __init__(self, config: LLMConfig) -> None:
        self.config = config
        self.client = build_openai_client(config)

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
    ) -> "LLM":
        """从环境变量和显式参数构造统一客户端。"""
        load_env_if_needed()
        detected_provider, detection_source = detect_provider(
            explicit_provider=provider,
            explicit_base_url=base_url,
            explicit_model=model,
        )
        config = LLMConfig(
            provider=detected_provider,
            model=resolve_model(detected_provider, explicit_model=model),
            api_key=resolve_api_key(detected_provider, explicit_api_key=api_key),
            base_url=resolve_base_url(detected_provider, explicit_base_url=base_url),
            timeout=timeout,
            max_retries=max_retries,
            temperature=temperature,
            max_tokens=max_tokens,
            detection_source=detection_source,
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
        """发起一次标准聊天请求，支持 tool calling。"""
        payload: Dict[str, Any] = {
            "model": self.config.model,
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
        return normalize_chat_response(raw_response, self.config)

    def chat_stream(
        self,
        messages: Sequence[Message],
        *,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
        tool_choice: Optional[Union[str, Dict[str, Any]]] = None,
    ) -> Iterator[str]:
        """发起流式请求并逐段返回文本。"""
        payload: Dict[str, Any] = {
            "model": self.config.model,
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
        system_prompt: Optional[str] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
        tool_choice: Optional[Union[str, Dict[str, Any]]] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> LLMResponse:
        """以最小调用方式执行一次对话。"""
        messages: List[Message] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": user_text})
        return self.chat(
            messages,
            temperature=temperature,
            max_tokens=max_tokens,
            tools=tools,
            tool_choice=tool_choice,
        )

    @property
    def provider(self) -> str:
        return self.config.provider.value

    @property
    def model(self) -> str:
        return self.config.model


UnifiedLLMClient = LLM


if __name__ == "__main__":
    print("=== client.py 本地测试 ===")
    load_env_if_needed()

    detected_provider, detection_source = detect_provider()
    resolved_model = resolve_model(detected_provider)
    resolved_base_url = resolve_base_url(detected_provider)

    print("自动识别结果：")
    print(f"- provider: {detected_provider.value}")
    print(f"- detection_source: {detection_source}")
    print(f"- model: {resolved_model}")
    print(f"- base_url: {resolved_base_url}")

    api_key_available = False
    try:
        _ = resolve_api_key(detected_provider)
        api_key_available = True
    except Exception as exc:
        print(f"- api_key: 未解析到可用密钥 ({exc})")

    run_live_test = os.getenv("RUN_LLM_LIVE_TEST", "0") == "1"
    if not run_live_test:
        print("未设置 `RUN_LLM_LIVE_TEST=1`，跳过真实 API 调用测试。")
    elif OpenAI is None:
        print("当前环境未安装 openai SDK，跳过真实 API 调用测试。")
    elif not api_key_available:
        print("当前环境未配置可用 API Key，跳过真实 API 调用测试。")
    else:
        try:
            llm = LLM.from_env()
            response = llm.simple_chat(
                "请用一句中文介绍你自己。",
                system_prompt="你是一个用于测试 LLM 接口的助手。",
                temperature=0,
                max_tokens=64,
            )
            print("真实调用成功：")
            print(f"- provider: {response.provider}")
            print(f"- model: {response.model}")
            print(f"- content: {response.content}")
        except Exception as exc:
            print(f"真实 API 调用失败: {exc}")
