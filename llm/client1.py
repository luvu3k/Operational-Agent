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
import os
import sys
from openai import OpenAI
from dotenv import load_dotenv
from typing import List, Optional, Dict

load_dotenv("D:/aiAgent/Operational Agent/.env")
print(__file__)

class LLM:
    def __init__(self, model: str | None = None, 
                 api_key: str | None = None,
                 base_url: str | None = None,
                 timeout: int | None = None) -> None:
        self.model = model or os.getenv("OPENAI_MODEL")
        api_key = api_key or os.getenv("CLOSEAI_API_KEY")
        base_url = base_url or os.getenv("CLOSEAI_BASE_URL")
        timeout = timeout or int(os.getenv("LLM_TIMEOUT", 60))

        if not all([self.model, api_key, base_url]):
            raise ValueError("模型ID、API密钥和服务地址必须被提供或在.env文件中定义。")
    
        self.client = OpenAI(api_key=api_key, base_url=base_url, timeout=timeout)

    def chat(self, messages: List[Dict[str, str]], temperature: float = 0) -> str:
        """
        调用大语言模型进行思考，并返回其响应。
        """

        print(f"🧠 正在调用 {self.model} 模型...")
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
                stream=True,
            )
            # 处理流式响应
            print("✅ 大语言模型响应成功:")
            collected_content = []
            for chunk in response:
                content = chunk.choices[0].delta.content or ""
                print(content, end="", flush=True)
                collected_content.append(content)
            return "".join(collected_content)

        except Exception as e:
            print(f"❌ 调用LLM API时发生错误: {e}")
            return None
        
if __name__ == "__main__":
    llm = LLM(model="deepseek-v3.2")
    print("测试LLM客户端...")
    messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "简单介绍你自己？"},
    ]
    response = llm.chat(messages)
        