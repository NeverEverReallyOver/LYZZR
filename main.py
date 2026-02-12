from src.agent_builder import AgentProfile, HardAttributes, HardPreferences, Persona
from src.engine import ChatSession
from src.agentscope_adapter import init_agentscope
from src.evaluator import MatchEvaluator
from src.llm_service import KimiLLMService
import os
import src.boot as boot

# 1. Bootstrap Environment
boot.bootstrap_environment()

# 注意：在实际项目中，API Key 应该放在环境变量或配置文件中，不要直接写在代码里。
KIMI_API_KEY = "sk-LCb9vdRXXKgEFQBChCzJpCyW9dowTs69O1KWnuCBuJSvGdZp"

def create_agent_alex():
    return AgentProfile(
        user_id="u1",
        name="Alex",
        attributes=HardAttributes(26, 178, 70, "后端工程师", "50w", "杭州", gender="male"),
        preferences=HardPreferences(3, 160, ["杭州"], preferred_gender="female"),
        persona=Persona("INTP", ["科幻", "Rust编程", "塞尔达传说"], ["逻辑", "真诚", "极客"])
    )

def create_agent_sarah():
    return AgentProfile(
        user_id="u2",
        name="Sarah",
        attributes=HardAttributes(24, 165, 50, "UI设计师", "30w", "杭州", gender="female"),
        preferences=HardPreferences(5, 175, ["杭州", "上海"], preferred_gender="male"),
        persona=Persona("ENFP", ["当代艺术展", "手冲咖啡", "宫崎骏电影"], ["自由", "浪漫", "好奇心"])
    )

def main():
    print("正在初始化 AgentScope...")
    
    # 1. 初始化 AgentScope
    # 如果 Windows 下遇到 DLL 问题，请参考 app.py 中的 patch 代码
    model_config_name = init_agentscope(KIMI_API_KEY)
    
    print("正在初始化 Agent...")
    alex = create_agent_alex()
    sarah = create_agent_sarah()

    # 2. 启动聊天引擎
    print("开始对话...")
    # on_message 回调用于打印消息
    def print_msg(name, content):
        print(f"\n[{name}]: {content}")

    session = ChatSession(alex, sarah, model_config_name, on_message=print_msg)
    
    # 运行 3 轮
    for i in range(3):
        print(f"--- Round {i+1} ---")
        session.run_turn(i+1)
    
    filename = session.save_log()
    print(f"\n对话结束，日志已保存: {filename}")
    
    # 3. 聊天结束后，进行评估
    # 注意：Evaluator 目前还是使用 KimiLLMService 独立调用，未完全迁移到 AgentScope Pipeline
    print("\n🔍 --- 正在进行 AI 情感分析与打分 ---")
    llm = KimiLLMService(api_key=KIMI_API_KEY)
    evaluator = MatchEvaluator(llm)
    report = evaluator.evaluate(alex.name, sarah.name, session.history)
    
    print(f"\n📊 === 匹配报告: {report['score']}分 ===")
    print(f"📝 简报: {report['summary']}")
    print(f"💡 建议: {report['recommendation']}")
    # print(f"🧐 详细分析: {report['analysis']}")

if __name__ == "__main__":
    main()
