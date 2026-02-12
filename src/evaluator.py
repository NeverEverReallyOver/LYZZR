from typing import List, Dict
import json
from agentscope.model import OpenAIChatModel

class MatchEvaluator:
    """
    严苛的对话质量评估器
    """
    def __init__(self, api_key: str):
        # 使用独立的 Evaluation Model (通常可以使用更强大的模型，这里复用 Kimi)
        self.model = OpenAIChatModel(
            model_name="moonshot-v1-8k",
            api_key=api_key,
            stream=False,
            client_kwargs={
                "base_url": "https://api.moonshot.cn/v1",
            }
        )

    def evaluate(self, chat_history: List[Dict[str, str]], agent_a_profile, agent_b_profile) -> Dict:
        """
        对聊天记录进行多维度评分 (引入图灵校准作为基准)
        """
        # 1. 整理对话记录
        dialogue_text = ""
        for msg in chat_history:
            dialogue_text += f"{msg['name']}: {msg['content']}\n"

        # 2. 提取用户 (Agent A) 的校准基准
        calibration_benchmark = ""
        if agent_a_profile.persona.turing_calibration_data:
            calibration_benchmark = "【甲方（用户）的价值观基准】\n"
            for item in agent_a_profile.persona.turing_calibration_data:
                calibration_benchmark += f"- 问题: {item['question']}\n  - 甲方期望的理想回答/甲方自己的回答: {item['answer']}\n"
        else:
            calibration_benchmark = "（甲方未提供价值观校准数据，请根据常理判断）"

        # 3. 构造 Evaluation Prompt
        prompt = f"""
你是一位极其严苛、目光毒辣的**情感与沟通专家**。
请根据以下两人的聊天记录，评估他们是否真的合适。

【嘉宾资料】
甲方 (用户): {agent_a_profile.name} ({agent_a_profile.attributes.age}岁, {agent_a_profile.attributes.job}, {agent_a_profile.persona.mbti})
乙方 (候选人): {agent_b_profile.name} ({agent_b_profile.attributes.age}岁, {agent_b_profile.attributes.job}, {agent_b_profile.persona.mbti})

{calibration_benchmark}

【聊天记录】
{dialogue_text}

【评估维度与标准】
请从以下三个维度进行打分（0-100分），并给出理由：

1. **互动质量 (Interaction Quality)**: 
   - 双方是否都有主动发起话题？
   - 回复长度是否平衡？
   - 是否存在一方热情、一方敷衍（如只回“嗯嗯”、“哈哈”）的情况？

2. **价值观契合 (Values Alignment) - 核心维度！**:
   - **重点检查**：乙方在回答甲方的“价值观探测问题”时，是否符合甲方的【价值观基准】？
   - 如果甲方的基准是“讨厌迟到”，而乙方表现出“随意”，此项分数必须低于 50 分。
   - 如果乙方不仅回答了，而且观点与甲方高度一致，加分。

3. **心动信号 (Chemistry)**:
   - 有没有明显的调情、夸奖、共鸣？
   - 语气是否轻松愉快？

【最终结论】
综合以上分数，给出一个总分（Total Score）。
- 如果价值观（维度2）严重冲突，总分不得超过 60 分（一票否决）。
- 只有在价值观匹配且聊得来的情况下，才能给高分。

请以 JSON 格式输出，格式如下：
{{
    "interaction_score": 0,
    "interaction_comment": "...",
    "values_score": 0,
    "values_comment": "...",
    "chemistry_score": 0,
    "chemistry_comment": "...",
    "total_score": 0,
    "final_verdict": "...",
    "suggestion": "..."
}}
"""
        import asyncio
        try:
            # 调用模型
            # 简单的同步包装
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
            response = loop.run_until_complete(self.model(messages=[{"role": "user", "content": prompt}]))
            
            # 解析 JSON
            content = response.content[0].text if hasattr(response.content[0], 'text') else response.content[0].get('text')
            
            # 清理可能的 markdown 标记
            content = content.replace("```json", "").replace("```", "").strip()
            
            return json.loads(content)
            
        except Exception as e:
            print(f"[Evaluator Error] {e}")
            return {
                "interaction_score": 50,
                "interaction_comment": "评估失败",
                "values_score": 50,
                "values_comment": "评估失败",
                "chemistry_score": 50,
                "chemistry_comment": "评估失败",
                "total_score": 50,
                "final_verdict": "评估出错",
                "suggestion": f"系统错误: {e}"
            }
