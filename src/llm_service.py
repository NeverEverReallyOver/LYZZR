import os
import random
from abc import ABC, abstractmethod
from openai import OpenAI

class LLMService(ABC):
    @abstractmethod
    def generate_response(self, system_prompt: str, chat_history: list) -> str:
        pass

class MockLLMService(LLMService):
    """
    用于演示的伪 LLM 服务。
    不需要 API Key，只会返回预设的对话模板。
    """
    def generate_response(self, system_prompt: str, chat_history: list) -> str:
        # 简单的关键词匹配来模拟对话流
        last_msg = chat_history[-1]['content'] if chat_history else ""
        
        if not chat_history:
            return "你好呀！很高兴认识你。"
        
        if "你好" in last_msg:
            return "哈喽！你也在这里相亲吗？我看你的资料很有趣。"
        elif "兴趣" in last_msg or "爱好" in last_msg:
            return "我也挺喜欢的！最近有看什么好书或者电影吗？"
        elif "电影" in last_msg:
            return "科幻片是我的最爱，特别是《星际穿越》。你呢？"
        elif "Rust" in last_msg or "编程" in last_msg:
            return "哇，技术大佬！我也在学 Python，感觉编程很有意思但也有点难。"
        elif "再见" in last_msg:
            return "好的，下次聊！祝你生活愉快。"
        else:
            options = [
                "这个观点很有趣，能展开说说吗？",
                "哈哈，确实是这样。那你平时周末喜欢做什么？",
                "我对这个话题也很感兴趣！",
                "感觉我们可以聊得很来。"
            ]
            return random.choice(options)

class KimiLLMService(LLMService):
    """
    使用 Moonshot (Kimi) API 的真实 LLM 服务
    """
    def __init__(self, api_key: str, model: str = "moonshot-v1-8k"):
        self.client = OpenAI(
            api_key=api_key,
            base_url="https://api.moonshot.cn/v1",
        )
        self.model = model

    def generate_response(self, system_prompt: str, chat_history: list) -> str:
        # 构造消息列表: system prompt + history
        messages = [{"role": "system", "content": system_prompt}] + chat_history
        
        try:
            completion = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.7, # 让对话稍微活泼一点
            )
            return completion.choices[0].message.content
        except Exception as e:
            return f"[系统错误] API 调用失败: {str(e)}"
