from dataclasses import dataclass, field
from typing import List, Dict, Optional
import json

@dataclass
class HardAttributes:
    """用户基础硬性属性"""
    age: int
    height: int          # 单位: cm
    weight: int          # 单位: kg
    job: str
    annual_salary: str   # 例如: "30w-50w"
    location: str        # 例如: "上海"
    gender: str = "female" # male, female

@dataclass
class HardPreferences:
    """硬性择偶标准"""
    max_age_gap: int     # 最大接受年龄差
    min_height: int      # 最低身高要求
    allowed_locations: List[str] # 接受的地域列表
    preferred_gender: str = "female" # 偏好性别

@dataclass
class Persona:
    """性格与软属性"""
    mbti: str            # 例如: "INFP", "ENTJ"
    interests: List[str] # 核心兴趣，建议 3-5 个
    values_keywords: List[str] = field(default_factory=list) # 价值观关键词

    # 图灵校准数据：存储用户对特定情境的真实回答
    # 格式: [{"question": "对方迟到半小时...", "answer": "我会先去旁边的书店逛逛..."}]
    turing_calibration_data: List[Dict[str, str]] = field(default_factory=list)

class AgentProfile:
    """
    用户专属 Agent 档案
    """
    def __init__(
        self, 
        user_id: str, 
        name: str, 
        attributes: HardAttributes,
        preferences: HardPreferences,
        persona: Persona
    ):
        self.user_id = user_id
        self.name = name
        self.attributes = attributes
        self.preferences = preferences
        self.persona = persona
        self.is_active = False

    def calibrate(self, question: str, user_answer: str):
        """
        图灵校准：通过用户的回答来训练 Agent
        """
        entry = {"question": question, "answer": user_answer}
        self.persona.turing_calibration_data.append(entry)

    def to_json(self) -> str:
        """导出为 JSON 格式，用于传递给 LLM"""
        return json.dumps(self, default=lambda o: o.__dict__, ensure_ascii=False, indent=2)

    def generate_system_prompt(self, turn_count: int = 1, target_profile: Optional['AgentProfile'] = None) -> str:
        """
        生成用于 LLM 的 System Prompt (增强版 - 注入灵魂 + 渐进式深度 + 动态态度)
        
        Args:
            turn_count (int): 当前对话轮数，用于控制话题深度
            target_profile (AgentProfile): 对方的资料，用于评估匹配度
        """
        # 1. 基础人设与风格
        mbti_style = {
            "I": "你比较内向，说话不用太长，喜欢倾听，偶尔会有点社恐。",
            "E": "你非常外向，热情主动，喜欢用感叹号，是话题的开启者。",
            "N": "你喜欢聊抽象的话题（未来、梦想、理论），不太关注琐碎的日常。",
            "S": "你很务实，喜欢聊具体的吃喝玩乐、工作生活，不喜欢空谈。",
            "T": "你逻辑性很强，说话直接，注重事实，不喜欢太情绪化的表达。",
            "F": "你很感性，注重对方的情绪，说话温柔体贴，富有同理心。",
            "J": "你做事有计划，喜欢确定性，不喜欢对方太随性。",
            "P": "你很随性，喜欢灵活变通，讨厌被条条框框束缚。"
        }
        
        style_guide = ""
        for char in self.persona.mbti:
            if char in mbti_style:
                style_guide += f"- {mbti_style[char]}\n"

        # 2. 匹配度评估与动态态度 (如果已知对方信息)
        attitude_instruction = ""
        attitude_level = "NEUTRAL"
        
        if target_profile:
            match_score = self._evaluate_match(target_profile)
            attitude_level = "HIGH" if match_score >= 6 else "LOW"
            
            target_info = f"""
# Match Profile (对方资料)
- 名字: {target_profile.name}
- 性别: {"男" if target_profile.attributes.gender == "male" else "女"}
- 年龄: {target_profile.attributes.age}岁
- 职业: {target_profile.attributes.job}
- MBTI: {target_profile.persona.mbti}
- 兴趣: {", ".join(target_profile.persona.interests)}
"""
            
            attitude_desc = self._get_attitude_guide(attitude_level)
            attitude_instruction = f"""
{target_info}

# Internal Assessment (内心评估 - 重要！)
你刚才在心里快速评估了一下对方，匹配分数大约是 {match_score}/10。
你的态度策略是：{'🌟 热情积极 (High Interest)' if attitude_level == 'HIGH' else '❄️ 礼貌冷淡 (Low Interest)'}

具体表现指南 (请严格遵守):
{attitude_desc}
"""
        else:
            attitude_instruction = """
# Attitude
目前你还不了解对方，请保持礼貌和好奇，尝试通过对话了解对方的信息。
"""

        # 3. 渐进式对话深度控制
        phase_instruction = ""
        
        # 尝试从自己的校准数据中提取一个话题作为“必考题”
        trap_question = "你对未来有什么规划？" # 默认兜底
        if self.persona.turing_calibration_data:
            import random
            # 随机选一个校准问题
            calib_item = random.choice(self.persona.turing_calibration_data)
            trap_question = calib_item['question']
        
        if turn_count <= 2:
            phase_instruction = "【阶段1：破冰】\n- 刚开始认识，简单寒暄。\n- 如果态度是High，可以主动找话题；如果Low，就礼貌回复即可。"
        elif turn_count <= 5:
            phase_instruction = f"【阶段2：价值观探测 (Value Probing)】\n- 这是一个关键阶段！你需要通过提问来了解对方的价值观。\n- **强制任务**: 请自然地向对方抛出以下问题（这是你非常看重的一点）：\n  “{trap_question}”\n- 仔细观察对方的回答是否符合你的期待。"
        else:
            phase_instruction = "【阶段3：收尾 (Closing)】\n- 如果已经约定了下次聊/见面的时间，请直接简短告别（如“好的，那就这么定了，拜拜！”），**绝对不要**再发表长篇大论的感言。\n- 严禁复读对方的“一起成长”、“成为好朋友”等客套话。\n- 目标是干净利落地结束对话。"

        prompt = f"""
# Role
你不是AI，你是 **{self.name}**。
你正在一个相亲 App 上与人聊天。

# My Profile
- 性别: {"男" if self.attributes.gender == "male" else "女"}
- 年龄: {self.attributes.age}岁
- 职业: {self.attributes.job}
- 所在地: {self.attributes.location}
- MBTI: {self.persona.mbti}
- 兴趣: {", ".join(self.persona.interests)}

# Personality & Style
{style_guide}
- **语言风格**: 请完全口语化，像在微信上聊天一样。
- **回复长度**: 控制在 1-3 句话以内。
- **禁止**: 绝对不要说“作为 AI”、“我是一个程序”之类的话。

{attitude_instruction}

# Critical Communication Rule (最高优先级！)
- **Answer FIRST**: 如果对方问了你一个问题，你必须**先回答**这个问题。绝对不要忽略对方的问题而直接开启新话题。
- **NO REPETITION**: 严禁重复对方发过来的客套话（如“希望能成为好朋友”、“一起成长”）。如果对方已经说了告别语，你只需要回一个简单的“拜拜”或“回见”。
- **Stop the Loop**: 如果发现对话已经陷入互相吹捧的循环（例如都在说“哈哈太好了”），请主动通过提出一个**具体的、完全不同**的新问题（如“对了，你最近在看什么书？”）来打破循环，或者直接结束对话。
- **Follow-up**: 回答完之后，再决定是否反问或开启新话题。
- 避免自说自话。

# Current Phase
{phase_instruction}

# Context
你正在和一个刚认识的陌生人聊天。只输出你回复的内容，不要输出心理活动。
"""
        # 如果有校准数据，加入参考
        if self.persona.turing_calibration_data:
            prompt += "\n# Tone Reference (你的过往语录)\n"
            for item in self.persona.turing_calibration_data:
                prompt += f"- 问: {item['question']}\n  答: {item['answer']}\n"
        
        return prompt

    def _evaluate_match(self, target: 'AgentProfile') -> int:
        """
        简单的硬规则匹配打分 (0-10)
        """
        score = 5 # 初始分
        
        # 1. 硬性条件 - 年龄
        try:
            my_age = int(self.attributes.age)
            target_age = int(target.attributes.age)
            age_diff = abs(my_age - target_age)
            
            # 检查是否在接受范围内 (如果有 preferences)
            if hasattr(self, 'preferences') and hasattr(self.preferences, 'max_age_gap'):
                if age_diff <= self.preferences.max_age_gap:
                    score += 1
                else:
                    score -= 2 # 超出接受范围，扣分
            elif age_diff <= 5: # 默认逻辑
                score += 1
        except:
            pass
            
        # 2. 硬性条件 - 身高 (简单逻辑)
        # 假设 self.preferences.min_height 存在
        if hasattr(self, 'preferences') and hasattr(self.preferences, 'min_height'):
             try:
                 if int(target.attributes.height) >= int(self.preferences.min_height):
                     score += 1
                 else:
                     score -= 2
             except:
                 pass

        # 3. 兴趣重叠
        my_interests = set(self.persona.interests)
        target_interests = set(target.persona.interests)
        # 简单的文本模糊匹配
        common = 0
        for mi in my_interests:
            for ti in target_interests:
                if mi in ti or ti in mi:
                    common += 1
        
        if common > 0:
            score += 3
            
        # 4. MBTI 匹配 (简单版：E和I互补，N和S相似)
        if self.persona.mbti and target.persona.mbti:
            # E/I 互补加分
            if self.persona.mbti[0] != target.persona.mbti[0]: 
                score += 1
            # N/S 相似加分
            if self.persona.mbti[1] == target.persona.mbti[1]: 
                score += 1
            
        return min(max(score, 0), 10)

    def _get_attitude_guide(self, level):
        if level == "HIGH":
            return """
            - 表现出明显的兴趣！
            - **Answer + Ask**: 先详细回答对方的问题，然后顺势反问一个相关细节。
            - 语气上扬，多用 emoji (😊, ✨, 🎉, 🤣)。
            - 尝试夸奖对方，或者寻找共鸣（“天哪我也是！”）。
            """
        else:
            return """
            - 保持礼貌但疏离。
            - **Answer Only**: 简短回答对方的问题，不要反问。
            - 使用“嗯嗯”、“挺好的”、“哈哈”来结束话题。
            - 给人一种“我在忙”或者“话题终结者”的感觉。
            - 不要使用太多 emoji。
            """
