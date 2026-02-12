import os
import sys
import src.boot as boot

# 1. Bootstrap Environment (Must be first)
boot.bootstrap_environment()

import streamlit as st
import time
import random
import traceback
from src.agent_builder import AgentProfile, HardAttributes, HardPreferences, Persona
from src.agentscope_adapter import init_agentscope
from src.engine import ChatSession
from src.generator import CandidateGenerator
from src.storage import CloudStorage

# 页面配置
st.set_page_config(
    page_title="恋与代理人 - 公网真实版",
    page_icon="💘",
    layout="wide"
)

# 构造 AgentProfile 对象
def build_agent_profile(data, user_id, preferences):
    return AgentProfile(
        user_id=user_id,
        name=data["name"],
        attributes=HardAttributes(
            age=data["age"], 
            height=175, 
            weight=65, 
            job=data["job"], 
            annual_salary="保密", 
            location="杭州",
            gender=data["gender"]
        ),
        preferences=preferences,
        persona=Persona(
            mbti=data["mbti"], 
            interests=data["interests"], 
            values_keywords=[],
            turing_calibration_data=data.get("calibration_data", [])
        )
    )

def main():
    try:
        # 初始化存储
        storage = CloudStorage()
        
        with st.sidebar:
            st.header("⚙️ 全局设置")
            default_key = "sk-dBCw59NIdtyRyKEIjcUdddV0ktfagO5JhHmXLlP4oZwGSLzd"
            api_key = st.text_input("Kimi API Key", value=default_key, type="password")
            
            if not api_key:
                st.error("请输入 Kimi API Key 才能开始！")
                st.stop()
            
            # 初始化 AgentScope
            if 'agentscope_inited' not in st.session_state:
                try:
                    model_config_name = init_agentscope(api_key)
                    st.session_state.agentscope_inited = True
                    st.session_state.model_config_name = model_config_name
                    st.success("AgentScope 已连接！")
                except Exception as e:
                    st.error(f"AgentScope 初始化失败: {e}")

        # -----------------------------------------------------------------------------
        # 0. 登录/注册模块 (Login/Register)
        # -----------------------------------------------------------------------------
        if 'current_user' not in st.session_state:
            st.session_state.current_user = None

        if not st.session_state.current_user:
            render_login_page(storage)
            return # 登录前不渲染后续内容

        # -----------------------------------------------------------------------------
        # 已登录状态
        # -----------------------------------------------------------------------------
        current_user = st.session_state.current_user
        st.sidebar.divider()
        st.sidebar.success(f"当前登录: {current_user.name} ({current_user.user_id})")
        if st.sidebar.button("登出"):
            st.session_state.current_user = None
            st.session_state.candidate_pool = None
            st.rerun()

        # 初始化 Session State
        if 'messages' not in st.session_state:
            st.session_state.messages = []
        if 'chat_active' not in st.session_state:
            st.session_state.chat_active = False
        if 'report' not in st.session_state:
            st.session_state.report = None
        if 'candidate_pool' not in st.session_state:
            st.session_state.candidate_pool = None
        if 'selected_candidate' not in st.session_state:
            st.session_state.selected_candidate = None

        # 加载真实用户池
        if st.session_state.candidate_pool is None:
            with st.spinner("正在从云端加载真实嘉宾..."):
                real_candidates = storage.get_candidate_pool(current_user.user_id)
                
                # 如果真实用户不够，用虚拟用户填充 (可选)
                if len(real_candidates) < 5:
                    st.toast(f"云端用户仅 {len(real_candidates)} 位，正在补充虚拟嘉宾...", icon="🤖")
                    virtual_needed = 20 - len(real_candidates)
                    virtual_candidates = CandidateGenerator.generate_pool(virtual_needed, current_user.preferences)
                    real_candidates.extend(virtual_candidates)
                
                st.session_state.candidate_pool = real_candidates

        st.title("💘 恋与代理人 (Love and Agents) - 公网版")
        st.caption("所有嘉宾均为真实注册用户（或混合虚拟数据）")

        # -----------------------------------------------------------------------------
        # 1. 嘉宾广场
        # -----------------------------------------------------------------------------
        st.header("1. 嘉宾广场 (Candidate Pool)")
        
        candidates = st.session_state.candidate_pool
        cols = st.columns(5)
        for i, candidate in enumerate(candidates):
            with cols[i % 5]:
                with st.container(border=True):
                    gender_icon = "👩" if candidate.attributes.gender == "female" else "👨"
                    is_real = "✅ 真实" if not candidate.user_id.startswith("guest_") else "🤖 虚拟"
                    
                    st.markdown(f"**{candidate.name}**")
                    st.caption(f"{is_real} | {candidate.attributes.age}岁")
                    st.caption(f"📍{candidate.attributes.location} | {candidate.attributes.job}")
                    st.text(candidate.persona.mbti)
                    st.markdown(f"*{', '.join(candidate.persona.interests[:2])}*")

        st.divider()

        # -----------------------------------------------------------------------------
        # 2. 筛选过程
        # -----------------------------------------------------------------------------
        col_action, col_status = st.columns([1, 3])
        with col_action:
            start_screening = st.button("🔍 开始智能筛选", type="primary", disabled=st.session_state.chat_active)

        if start_screening:
            # 使用当前登录用户作为 Agent A
            agent_a = current_user
            
            with st.status("正在运行筛选算法...", expanded=True) as status:
                st.write("正在分析兴趣契合度...")
                progress_bar = st.progress(0)
                scores = []
                
                for i, cand in enumerate(candidates):
                    # 简单打分逻辑
                    score = random.randint(50, 95)
                    common_interests = set(agent_a.persona.interests) & set(cand.persona.interests)
                    if common_interests:
                        score += 10
                        st.write(f"发现共同兴趣 [{', '.join(common_interests)}] -> {cand.name} 加分!")
                    
                    scores.append((cand, score))
                    progress_bar.progress((i + 1) / len(candidates))
                    time.sleep(0.05)
                
                scores.sort(key=lambda x: x[1], reverse=True)
                top_candidate = scores[0][0]
                st.session_state.selected_candidate = top_candidate
                status.update(label="筛选完成！", state="complete", expanded=False)
            
            st.success(f"🎉 匹配成功！决定与 **{top_candidate.name}** 进行深入交流。")
            st.session_state.chat_active = True
            st.session_state.messages = []
            st.rerun()

        # -----------------------------------------------------------------------------
        # 3. 聊天室
        # -----------------------------------------------------------------------------
        if st.session_state.chat_active and st.session_state.selected_candidate:
            agent_a = current_user
            agent_b = st.session_state.selected_candidate
            
            st.header(f"2. 深度聊天室: {agent_a.name} ❤️ {agent_b.name}")
            
            # 渲染历史消息
            for msg in st.session_state.messages:
                is_agent_a = msg["name"] == agent_a.name
                role = "user" if is_agent_a else "assistant"
                avatar = "👨" if (agent_a.attributes.gender if is_agent_a else agent_b.attributes.gender) == "male" else "👩"
                st.chat_message(role, avatar=avatar).write(f"**{msg['name']}**: {msg['content']}")

            # 如果没有消息，开始自动对话
            if not st.session_state.messages:
                session = ChatSession(agent_a, agent_b, model_config_name=api_key, on_message=None)
                
                max_turns = 8
                for turn in range(1, max_turns + 1):
                    with st.spinner(f"正在进行第 {turn}/{max_turns} 轮对话..."):
                        session.run_turn_sync(turn)
                        last_two = session.history[-2:]
                        
                        for msg in last_two:
                            st.session_state.messages.append(msg)
                            is_agent_a = msg["name"] == agent_a.name
                            role = "user" if is_agent_a else "assistant"
                            avatar = "👨" if (agent_a.attributes.gender if is_agent_a else agent_b.attributes.gender) == "male" else "👩"
                            st.chat_message(role, avatar=avatar).write(f"**{msg['name']}**: {msg['content']}")
                        time.sleep(1)
                
                session.save_log()
                
                # 评估
                with st.spinner("正在生成最终裁判报告..."):
                    from src.evaluator import MatchEvaluator
                    evaluator = MatchEvaluator(api_key)
                    report = evaluator.evaluate(session.history, agent_a, agent_b)
                    st.session_state.report = report
                st.rerun()

        # -----------------------------------------------------------------------------
        # 4. 评估报告
        # -----------------------------------------------------------------------------
        if st.session_state.report:
            st.header("3. 最终裁判报告")
            report = st.session_state.report
            st.json(report) # 简单展示，完整版参考原 app.py
            
            if st.button("🔄 再来一次"):
                st.session_state.chat_active = False
                st.session_state.messages = []
                st.session_state.report = None
                st.session_state.selected_candidate = None
                st.rerun()

    except Exception as e:
        st.error("程序运行错误")
        st.code(traceback.format_exc())

def render_login_page(storage):
    st.title("👋 欢迎来到恋与代理人 (公网版)")
    
    tab1, tab2 = st.tabs(["🚀 注册/更新资料", "🔑 直接登录"])
    
    with tab1:
        st.subheader("创建你的 AI 替身")
        username = st.text_input("设置用户名 (唯一ID)", key="reg_username")
        
        # 复用之前的表单逻辑
        agent_data = render_agent_form("Reg", "Alex", 26, "后端工程师", "INTP", "科幻, 编程", "👨", show_calibration=True)
        
        # 偏好设置
        st.markdown("#### 择偶偏好")
        pref_gender = st.selectbox("偏好性别", ["female", "male"], format_func=lambda x: "女生" if x=="female" else "男生")
        pref_loc = st.multiselect("偏好城市", ["杭州", "上海", "北京", "深圳", "成都"], default=["杭州"])
        
        if st.button("提交注册"):
            if not username:
                st.error("请输入用户名")
                return
            
            # 校验校准数据
            if len(agent_data.get("calibration_data", [])) < 3:
                st.error("请完成所有图灵校准问题！")
                return

            preferences = HardPreferences(5, 160, pref_loc, pref_gender)
            profile = build_agent_profile(agent_data, username, preferences)
            
            if storage.register_user(username, profile):
                st.success("注册成功！")
                st.session_state.current_user = profile
                st.rerun()
            else:
                st.error("注册失败，请检查数据库连接或联系管理员。")
    
    with tab2:
        st.subheader("回来寻找真爱？")
        login_user = st.text_input("请输入用户名", key="login_username")
        if st.button("登录"):
            user = storage.get_user_by_username(login_user)
            if user:
                st.success(f"欢迎回来，{user.name}！")
                st.session_state.current_user = user
                st.rerun()
            else:
                st.error("用户不存在，请先注册。")

def render_agent_form(prefix, default_name, default_age, default_job, default_mbti, default_interests, default_gender="👨", show_calibration=False):
    # 复用原 app.py 的表单代码，略微简化
    gender_options = {"male": "男 👨", "female": "女 👩"}
    
    with st.container(border=True):
        name = st.text_input("昵称", value=default_name, key=f"{prefix}_name")
        col_g, col_a = st.columns(2)
        with col_g:
            gender = st.selectbox("性别", ["male", "female"], index=0 if default_gender=="👨" else 1, key=f"{prefix}_gender")
        with col_a:
            age = st.number_input("年龄", value=default_age, min_value=18, max_value=60, key=f"{prefix}_age")
            
        mbti = st.selectbox("MBTI", ["INFP", "ENFP", "INFJ", "ENFJ", "INTJ", "ENTJ", "INTP", "ENTP", "ISFP", "ESFP", "ISTP", "ESTP", "ISFJ", "ESFJ", "ISTJ", "ESTJ"], index=6, key=f"{prefix}_mbti")
        job = st.text_input("职业", value=default_job, key=f"{prefix}_job")
        interests_str = st.text_area("兴趣爱好 (用逗号分隔)", value=default_interests, key=f"{prefix}_interests")
        
        calibration_data = []
        if show_calibration:
            st.markdown("---")
            st.caption("🧠 **图灵校准 (必填)**")
            q1 = "如果对方迟到了30分钟，你会说什么？"
            a1 = st.text_input(q1, key=f"{prefix}_cal_q1")
            if a1: calibration_data.append({"question": q1, "answer": a1})
            
            q2 = "你最喜欢的周末活动是什么？"
            a2 = st.text_input(q2, key=f"{prefix}_cal_q2")
            if a2: calibration_data.append({"question": q2, "answer": a2})
            
            q3 = "对方问了一个你不想回答的问题，怎么婉拒？"
            a3 = st.text_input(q3, key=f"{prefix}_cal_q3")
            if a3: calibration_data.append({"question": q3, "answer": a3})

        return {
            "name": name, "age": age, "gender": gender, "job": job,
            "mbti": mbti, "interests": [i.strip() for i in interests_str.split(",")],
            "calibration_data": calibration_data
        }

if __name__ == "__main__":
    main()
