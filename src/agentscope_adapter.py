import agentscope
from agentscope.agent import AgentBase
from agentscope.message import Msg
from agentscope.model import OpenAIChatModel
from src.agent_builder import AgentProfile
import logging

class SimpleMemory:
    """
    一个简单的 Memory 实现，适配 AgentScope 的 Msg 格式
    """
    def __init__(self):
        self.history = []
    
    def add(self, msg):
        self.history.append(msg)
        
    def get_memory(self):
        return self.history

class DatingAgent(AgentBase):
    """
    适配 AgentScope 的相亲 Agent
    """
    def __init__(self, profile: AgentProfile, api_key: str, target_profile: AgentProfile = None):
        # 初始化 AgentBase (不带参数)
        super().__init__()
        
        # 手动设置 Agent 属性
        self.name = profile.name
        self.profile = profile
        self.target_profile = target_profile # 记录对方信息
        self.turn_count = 1
        
        # 生成初始 System Prompt (传入对方信息)
        self.sys_prompt = profile.generate_system_prompt(turn_count=1, target_profile=target_profile)
        
        # 净化 API Key：去除空白字符
        if api_key:
            # 强力净化：去除首尾空格，并强制只保留 ASCII 字符
            api_key = api_key.strip()
            try:
                # 尝试编码为 ascii，忽略无法编码的字符（如中文、特殊符号）
                api_key = api_key.encode('ascii', 'ignore').decode('ascii')
            except Exception as e:
                print(f"[Warning] Failed to sanitize API Key: {e}")
                
            # 简单的 ASCII 检查，如果包含非 ASCII 字符则打印警告
            if not api_key.isascii():
                print(f"[Warning] API Key contains non-ASCII characters! This may cause connection errors. Key: {api_key[:5]}...")
        
        # 直接初始化 OpenAIChatModel
        # 使用 Kimi (Moonshot AI) 的配置
        self.model = OpenAIChatModel(
            model_name="moonshot-v1-8k",
            api_key=api_key,
            stream=False, # 禁用流式输出，确保返回完整的 ChatResponse 对象
            client_kwargs={
                "base_url": "https://api.moonshot.cn/v1",
            }
        )
        
        # 初始化 Memory
        self.memory = SimpleMemory()

    async def reply(self, x: dict = None) -> dict:
        """
        AgentScope Agent 的核心回复方法
        """
        # 1. 记录对方的消息到 memory
        if x:
            self.memory.add(x)
            
        # 2. 准备 prompt
        # 手动构造 OpenAI 格式的消息列表
        messages = [{"role": "system", "content": self.sys_prompt}]
        
        # 将历史记录转换为 OpenAI 格式
        for msg in self.memory.get_memory():
            role = msg.role
            content = msg.content
            # 确保 role 是 user/assistant/system 之一
            if role not in ["user", "assistant", "system"]:
                role = "user" # 默认 fallback
            messages.append({"role": role, "content": content})
            
        # 3. 调用模型
        # OpenAIChatModel.__call__ 是异步的，直接 await
        response = await self.model(messages=messages)
        
        # 4. 解析响应
        # response 是 ChatResponse 对象
        # content 是一个 list，包含 TextBlock 等 (但可能是 dict 形式)
        text_content = ""
        for block in response.content:
            # 兼容对象属性访问和字典访问
            block_type = block.type if hasattr(block, "type") else block.get("type")
            
            if block_type == "text":
                text = block.text if hasattr(block, "text") else block.get("text")
                text_content += text
            elif block_type == "thinking":
                # 可以选择是否包含思考过程
                pass
                
        # 5. 记录自己的回复
        msg = Msg(self.name, text_content, role="assistant")
        self.memory.add(msg)
        
        return msg

    def update_system_prompt(self):
        """
        根据轮次更新 system prompt
        """
        self.turn_count += 1
        # 更新时同样传入 target_profile
        new_prompt = self.profile.generate_system_prompt(
            turn_count=self.turn_count, 
            target_profile=self.target_profile
        )
        self.sys_prompt = new_prompt

_agentscope_inited = False

def init_agentscope(api_key: str):
    """
    初始化 AgentScope 全局配置 (Idempotent)
    """
    global _agentscope_inited
    
    if _agentscope_inited:
        return "kimi_chat"

    # AgentScope init 在这个版本不需要 model_configs
    agentscope.init(
        project="LoveAndAgents",
        # save_api_invoke=True, # 这个版本不支持 save_api_invoke
        logging_level="INFO" 
    )
    _agentscope_inited = True

    return "kimi_chat"
