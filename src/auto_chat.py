import agentscope
from agentscope.agent import AgentBase, UserAgent
from agentscope.message import Msg
# 彻底放弃 agentscope 的模型封装，直接用 openai 原生库，稳如老狗
from openai import OpenAI
from src.agent_builder import AgentProfile
from src.agentscope_adapter import SimpleMemory

# 手动定义 DialogAgent，适配 agentscope 1.0.15+
class DialogAgent(AgentBase):
    def __init__(self, name: str, sys_prompt: str, api_key: str):
        super().__init__() # AgentBase 初始化不接受参数
        self.name = name
        self.sys_prompt = sys_prompt
        self.memory = SimpleMemory()  # 初始化 memory
        
        # 使用原生 OpenAI 客户端（同步模式）
        try:
            self.client = OpenAI(
                api_key=api_key,
                base_url="https://api.moonshot.cn/v1", # 既然是 Kimi，直接指定 base_url
            )
        except Exception as e:
            print(f"Warning: Failed to instantiate OpenAI Client: {e}")
            self.client = None

    def __call__(self, *args, **kwargs) -> Msg:
        # 强制覆盖父类 AgentBase 的 async __call__
        # 使其变为同步调用，直接返回 Msg 对象而非 Coroutine
        return self._reply_sync(*args, **kwargs)

    def _reply_sync(self, x: dict = None) -> Msg:
        # 记录输入消息到内存
        if x:
            self.memory.add(x)

        # 构建提示词
        msgs = []
        # System Prompt
        msgs.append({"role": "system", "content": self.sys_prompt})
        
        # History
        for m in self.memory.get_memory():
            if isinstance(m, Msg):
                role = m.role if hasattr(m, 'role') else "user"
                content = m.content if hasattr(m, 'content') else str(m)
                # 处理 content 为列表的情况 (multimodal)
                if isinstance(content, list):
                    text_content = ""
                    for block in content:
                        if isinstance(block, dict) and block.get("type") == "text":
                            text_content += block.get("text", "")
                        elif isinstance(block, str):
                            text_content += block
                    content = text_content
                
                msgs.append({"role": role, "content": content})
        
        # 调用模型 (同步调用，绝对不会返回 coroutine)
        if self.client:
            try:
                completion = self.client.chat.completions.create(
                    model="moonshot-v1-8k",
                    messages=msgs,
                    temperature=0.7,
                )
                
                content_str = completion.choices[0].message.content
                
                # 构造返回的 Msg
                res_msg = Msg(name=self.name, content=content_str, role="assistant")
                self.memory.add(res_msg)
                return res_msg
                
            except Exception as e:
                return Msg(name=self.name, content=f"[Model Error: {e}]", role="assistant")
        else:
            return Msg(name=self.name, content="[Error: No model loaded]", role="assistant")

    def reply(self, x: dict = None) -> Msg:
        return self._reply_sync(x)

class AutoChatController:
    """
    自动聊天控制器：管理两个Agent之间的多轮对话
    """
    def __init__(self, agent_a_profile: AgentProfile, agent_b_profile: AgentProfile, model_config_name: str):
        self.profile_a = agent_a_profile
        self.profile_b = agent_b_profile
        self.api_key = model_config_name # 这里其实传进来的是 api_key
        self.history = []
        
        # 初始化 Agents
        self.agent_a = self._create_agent(self.profile_a)
        self.agent_b = self._create_agent(self.profile_b)

    def _create_agent(self, profile: AgentProfile):
        # 构建 System Prompt
        sys_prompt = f"""你现在扮演 {profile.name}。
        你的设定如下：
        - 性别: {profile.attributes.gender}
        - 年龄: {profile.attributes.age}
        - 职业: {profile.attributes.job}
        - MBTI: {profile.persona.mbti}
        - 兴趣: {', '.join(profile.persona.interests)}
        
        在对话中，请完全沉浸在这个角色中，用符合你人设的语气说话。
        如果对方是你感兴趣的类型，可以表现得热情一点；否则保持礼貌但有距离感。
        
        重要规则：
        1. 每次回答不要太长，像微信聊天一样自然。
        2. 不要重复对方的话。
        3. 如果对方问了你不知道的问题，可以用你的性格来应对。
        """
        
        # 使用自定义的 DialogAgent
        return DialogAgent(
            name=profile.name,
            sys_prompt=sys_prompt,
            api_key=self.api_key
        )

    def run_conversation(self, max_turns: int = 5):
        """
        运行自动对话
        """
        # 开场白 (由 A 发起)
        msg = Msg(name="System", content="你们在广场上相遇了，开始聊天吧。", role="system")
        self.agent_a.speak(msg) # 这里的 speak 只是为了让 agent 知道 context，实际不开场
        
        # 第一句话由 A 说
        msg_a = self.agent_a(Msg(name="System", content="请向对方打个招呼。", role="system"))
        self.history.append(msg_a)
        
        current_msg = msg_a
        
        for _ in range(max_turns):
            # B 回复 A
            msg_b = self.agent_b(current_msg)
            self.history.append(msg_b)
            
            # A 回复 B
            msg_a = self.agent_a(msg_b)
            self.history.append(msg_a)
            
            current_msg = msg_a
            
            # 简单模拟思考时间，避免请求过快
            time.sleep(1)
            
        return self.history
