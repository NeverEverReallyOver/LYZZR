import time
import json
import os
from datetime import datetime
from typing import List, Dict, Callable, Optional
from src.agent_builder import AgentProfile
from src.agentscope_adapter import DatingAgent
from agentscope.message import Msg

import asyncio

class ChatSession:
    def __init__(
        self, 
        agent_a_profile: AgentProfile, 
        agent_b_profile: AgentProfile, 
        model_config_name: str, # 这里其实接收的是 api_key，如果我们在 app.py 里改一下的话
        on_message: Optional[Callable[[str, str], None]] = None
    ):
        # 兼容性处理：如果 model_config_name 是 "kimi_chat" 这种字符串，
        # 说明 app.py 还没改。我们需要 api_key。
        # 这是一个临时的 hack，实际上我们需要在 app.py 里把 api_key 传进来。
        # 但 engine.py 不知道 api_key。
        
        # 既然我们已经决定在 adapter 里直接实例化 model，
        # 那么 DatingAgent 的 __init__ 需要 api_key。
        # 我们修改 app.py 让它传 api_key 给 ChatSession。
        
        self.api_key = model_config_name # 假设这里传的是 key
        
        # 使用 AgentScope 的 Agent
        # 互相传入对方的 profile，实现知己知彼
        self.agent_a = DatingAgent(agent_a_profile, self.api_key, target_profile=agent_b_profile)
        self.agent_b = DatingAgent(agent_b_profile, self.api_key, target_profile=agent_a_profile)
        
        self.history: List[Dict[str, str]] = [] 
        self.on_message = on_message
        self.max_turns = 8

    async def run_turn_async(self, turn: int):
        """
        执行一轮对话 (Agent A -> Agent B) - 异步版本
        """
        # 更新渐进式 Prompt
        self.agent_a.update_system_prompt()
        self.agent_b.update_system_prompt()
        
        # 构造上一轮的消息作为输入
        if not self.history:
            last_msg = Msg(name="System", content="你们现在开始相亲了，请开始聊天。", role="system")
        else:
            last_entry = self.history[-1]
            last_msg = Msg(name=last_entry["name"], content=last_entry["content"], role="assistant")

        # Agent A 发言 (异步调用)
        response_a = await self.agent_a(last_msg)
        self._record_message(self.agent_a.name, response_a.content)
        
        # Agent B 发言 (异步调用)
        response_b = await self.agent_b(response_a)
        self._record_message(self.agent_b.name, response_b.content)

    def run_turn_sync(self, turn: int):
        """
        执行一轮对话 (Agent A -> Agent B) - 同步包装器
        """
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
        loop.run_until_complete(self.run_turn_async(turn))

    # 保留旧方法名以兼容（如果不改 app.py 的话），但建议改 app.py
    def run_turn(self, turn: int):
        return self.run_turn_sync(turn)

    def _record_message(self, name: str, content: str):
        self.history.append({"name": name, "content": content})
        if self.on_message:
            self.on_message(name, content)

    def save_log(self):
        """保存聊天记录到 JSON 文件"""
        if not os.path.exists("logs"):
            os.makedirs("logs")
            
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"logs/chat_as_{self.agent_a.name}_{self.agent_b.name}_{timestamp}.json"
        
        data = {
            "timestamp": timestamp,
            "participants": [self.agent_a.name, self.agent_b.name],
            "history": self.history,
            "framework": "AgentScope"
        }
        
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        return filename
