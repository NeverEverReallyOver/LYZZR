import os
import sys
import src.boot as boot
import json # 补充导入
import agentscope # 补充导入 agentscope

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
    page_title="恋与代理人 - Love and Agents",
    page_icon="💘",
    layout="wide",
    initial_sidebar_state="expanded"
)

# [DEBUG] 强制版本号显示，用于验证部署是否更新
st.caption("🚀 Version 2.1 (Public Build - No Bcrypt) | Last Updated: 2026-02-26")

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

        # -----------------------------------------------------------------------------
        # Sidebar Leaderboard & History
        # -----------------------------------------------------------------------------
        with st.sidebar:
            st.divider()
            
            # 1. Top 3 Leaderboard
            st.subheader("🏆 真爱榜 (Top 3)")
            top_matches = storage.get_top_matches(current_user.user_id, limit=3, current_user_name=current_user.name)
            
            if not top_matches:
                st.caption("暂无数据")
            else:
                for idx, record in enumerate(top_matches):
                    # 只有前三名
                    medal = ["🥇", "🥈", "🥉"][idx] if idx < 3 else "🏅"
                    with st.expander(f"{medal} {record['match_score']}分 - {record.get('partner_name', '未知')}"):
                        st.caption(f"📅 {record['created_at']}")
                        st.markdown(f"**简评**: {record.get('report', '暂无')}")
                        if st.button("📄 记录", key=f"top_{record['id']}"):
                            chat_log = record['chat_log']
                            if isinstance(chat_log, str):
                                try:
                                    chat_log = json.loads(chat_log)
                                except:
                                    pass
                            st.json(chat_log)

            st.divider()

            # 2. Recent History (Last 5)
            st.subheader("🕒 最近对话")
            recent_matches = storage.get_recent_matches(current_user.user_id, limit=5, current_user_name=current_user.name)
            
            if not recent_matches:
                st.caption("暂无对话")
            else:
                for record in recent_matches:
                    with st.expander(f"💬 {record.get('partner_name', '未知')} ({record['match_score']}分)"):
                        st.caption(f"⏱️ {record['created_at']}")
                        if st.button("📄 回顾", key=f"recent_{record['id']}"):
                            chat_log = record['chat_log']
                            if isinstance(chat_log, str):
                                try:
                                    chat_log = json.loads(chat_log)
                                except:
                                    pass
                            st.json(chat_log)

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
                
                # 保证池子里至少有 20 个嘉宾，不够就用虚拟人凑
                min_pool_size = 20
                if len(real_candidates) < min_pool_size:
                    virtual_needed = min_pool_size - len(real_candidates)
                    st.toast(f"云端用户 {len(real_candidates)} 位，正在召唤 {virtual_needed} 位 AI 嘉宾...", icon="🤖")
                    
                    # 生成虚拟用户
                    virtual_candidates = []
                    for i in range(virtual_needed):
                        # 生成唯一的虚拟ID
                        v_id = f"guest_{int(time.time())}_{i}"
                        v_agent = CandidateGenerator.generate_random_agent(v_id, current_user.preferences)
                        virtual_candidates.append(v_agent)
                        
                    real_candidates.extend(virtual_candidates)
                
                st.session_state.candidate_pool = real_candidates

        st.title("💘 恋与代理人 (Love and Agents) - 公网版")
        st.caption("所有嘉宾均为真实注册用户（或混合虚拟数据）")

        # -----------------------------------------------------------------------------
        # 布局逻辑重构：分栏显示
        # -----------------------------------------------------------------------------
        
        # 获取已聊列表
        chatted_map = storage.get_chatted_users(current_user.user_id)
        
        # 定义渲染嘉宾列表的函数 (支持 grid 和 list 两种模式)
        def render_candidate_selector(mode="grid"):
            # 搜索栏 (在 list 模式下也显示)
            search_key = "search_grid" if mode == "grid" else "search_list"
            search_query = st.text_input("🔍 搜索嘉宾", "", key=search_key)
            
            # 筛选
            filtered_candidates = st.session_state.candidate_pool
            if search_query:
                filtered_candidates = [c for c in filtered_candidates if search_query.lower() in c.name.lower() or search_query.lower() in c.user_id.lower()]
            
            # 批量操作按钮区域
            col_b1, col_b2 = st.columns([1, 1])
            with col_b1:
                # 注意：key 需要唯一
                btn_key = "btn_batch_grid" if mode == "grid" else "btn_batch_list"
                if st.button("🚀 批量匹配", key=btn_key, type="primary"):
                    # 触发批量逻辑
                    selected = []
                    for cand in st.session_state.candidate_pool:
                        if st.session_state.get(f"select_{cand.user_id}", False):
                            selected.append(cand)
                    if not selected:
                        st.error("请先选择嘉宾！")
                    else:
                        st.session_state.batch_processing = True
                        st.session_state.batch_targets = selected
                        st.rerun()
            
            with col_b2:
                btn_key_s = "btn_screen_grid" if mode == "grid" else "btn_screen_list"
                if st.button("🔍 智能推荐", key=btn_key_s, disabled=st.session_state.chat_active):
                    # 触发智能推荐逻辑 (这里简单复用，实际应封装)
                    # 由于逻辑较长，这里仅设置标记，主循环处理
                    st.session_state.trigger_smart_screen = True
                    st.rerun()

            st.divider()
            
            if mode == "grid":
                # 网格模式 (大卡片)
                st.subheader("1. 嘉宾广场 (Candidate Pool)")
                cols = st.columns(4)
                for i, candidate in enumerate(filtered_candidates):
                    with cols[i % 4]:
                        with st.container(border=True):
                            gender_icon = "👩" if candidate.attributes.gender == "female" else "👨"
                            is_real = "✅" if not candidate.user_id.startswith("guest_") else "🤖"
                            st.markdown(f"**{candidate.name}** {gender_icon}")
                            st.caption(f"{is_real} | {candidate.attributes.age}岁 | {candidate.attributes.job}")
                            
                            if candidate.user_id in chatted_map:
                                st.info(f"{chatted_map[candidate.user_id]}分")
                            else:
                                st.checkbox("选", key=f"select_{candidate.user_id}")
            else:
                # 列表模式 (侧边栏紧凑模式)
                st.subheader("👥 嘉宾列表")
                # 使用 scrollable container
                with st.container(height=600):
                    for candidate in filtered_candidates:
                        cols = st.columns([1, 3])
                        with cols[0]:
                             st.checkbox("选", key=f"select_{candidate.user_id}", label_visibility="collapsed")
                        with cols[1]:
                            gender_icon = "👩" if candidate.attributes.gender == "female" else "👨"
                            is_real = "✅" if not candidate.user_id.startswith("guest_") else "🤖"
                            
                            # 紧凑显示
                            status = ""
                            if candidate.user_id in chatted_map:
                                status = f" | ✅ {chatted_map[candidate.user_id]}分"
                            
                            st.markdown(f"**{candidate.name}** {gender_icon} {status}")
                            st.caption(f"{is_real} {candidate.attributes.job}")
                            st.divider()

        # 判断活跃状态
        is_active_mode = st.session_state.get('batch_processing', False) or \
                         st.session_state.get('chat_active', False) or \
                         st.session_state.get('report') is not None or \
                         st.session_state.get('show_rank', False)

        # -----------------------------------------------------------------------------
        # 主布局渲染
        # -----------------------------------------------------------------------------
        
        # 定义内容渲染函数 (Chat/Report/Batch)
        def render_active_content():
            # 1. 批量处理进度
            if st.session_state.get('batch_processing', False):
                st.header("2. 自动匹配进行中...")
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                from src.auto_chat import AutoChatController
                from src.evaluator import MatchEvaluator
                
                targets = st.session_state.batch_targets
                
                for idx, target in enumerate(targets):
                    status_text.markdown(f"### 🤖 正在与 **{target.name}** ({idx+1}/{len(targets)}) 深入交流中...")
                    detail_bar = st.progress(0)
                    
                    controller = AutoChatController(current_user, target, model_config_name=api_key)
                    
                    chat_history = []
                    # 1. 开场
                    msg = controller.agent_a(controller.agent_b(controller.agent_a(agentscope.message.Msg(name="System", content="你们相遇了", role="system")))) 
                    controller = AutoChatController(current_user, target, model_config_name=api_key)
                    
                    with st.expander(f"💬 {target.name} 的实时聊天记录", expanded=True):
                        msg_a = controller.agent_a(agentscope.message.Msg(name="System", content="请向对方打个招呼。", role="system"))
                        chat_history.append(msg_a)
                        current_msg = msg_a
                        st.chat_message("user", avatar="👨" if current_user.attributes.gender=="male" else "👩").write(f"**{current_user.name}**: {msg_a.content}")
                        
                        max_turns = 5
                        for turn in range(max_turns):
                            msg_b = controller.agent_b(current_msg)
                            chat_history.append(msg_b)
                            st.chat_message("assistant", avatar="👨" if target.attributes.gender=="male" else "👩").write(f"**{target.name}**: {msg_b.content}")
                            detail_bar.progress((turn * 2 + 1) / (max_turns * 2))
                            
                            msg_a = controller.agent_a(msg_b)
                            chat_history.append(msg_a)
                            st.chat_message("user", avatar="👨" if current_user.attributes.gender=="male" else "👩").write(f"**{current_user.name}**: {msg_a.content}")
                            detail_bar.progress((turn * 2 + 2) / (max_turns * 2))
                            current_msg = msg_a
                            time.sleep(0.5)
                    
                    formatted_history = [{"name": m.name, "content": m.content} for m in chat_history]
                    evaluator = MatchEvaluator(api_key)
                    report = evaluator.evaluate(formatted_history, current_user, target)
                    
                    score = report.get("total_score", 0)
                    summary = report.get("final_verdict", "")
                    storage.save_match_record(current_user.user_id, target.user_id, formatted_history, score, summary)
                    progress_bar.progress((idx + 1) / len(targets))
                
                st.session_state.batch_processing = False
                st.success("🎉 所有匹配任务已完成！请查看排行榜。")
                st.session_state.show_rank = True
                st.rerun()

            # 2. 聊天室
            if st.session_state.chat_active and st.session_state.selected_candidate:
                agent_a = current_user
                agent_b = st.session_state.selected_candidate
                st.header(f"2. 深度聊天室: {agent_a.name} ❤️ {agent_b.name}")
                
                for msg in st.session_state.messages:
                    is_agent_a = msg["name"] == agent_a.name
                    role = "user" if is_agent_a else "assistant"
                    avatar = "👨" if (agent_a.attributes.gender if is_agent_a else agent_b.attributes.gender) == "male" else "👩"
                    st.chat_message(role, avatar=avatar).write(f"**{msg['name']}**: {msg['content']}")

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
                    with st.spinner("正在生成最终裁判报告..."):
                        from src.evaluator import MatchEvaluator
                        evaluator = MatchEvaluator(api_key)
                        report = evaluator.evaluate(session.history, agent_a, agent_b)
                        st.session_state.report = report
                        score = report.get("total_score", 0)
                        summary = report.get("final_verdict", "")
                        formatted_history = session.history 
                        storage.save_match_record(current_user.user_id, agent_b.user_id, formatted_history, score, summary)
                    st.rerun()

            # 3. 排行榜
            if st.session_state.get('show_rank', False):
                st.header("🏆 真爱排行榜")
                history = storage.get_match_history(current_user.user_id, current_user_name=current_user.name)
                if not history:
                    st.info("暂无匹配记录")
                else:
                    for record in history:
                        with st.expander(f"🏅 {record['match_score']}分 - {record.get('partner_name', '未知用户')}"):
                            st.write(f"**裁判点评**: {record['report']}")
                            if st.button("查看详细聊天记录", key=f"history_{record['id']}"):
                                chat_log = record['chat_log']
                                if isinstance(chat_log, str):
                                    try: chat_log = json.loads(chat_log)
                                    except: pass
                                st.json(chat_log)

            # 4. 评估报告
            if st.session_state.report:
                st.header("3. 最终裁判报告")
                report = st.session_state.report
                st.json(report)
                if st.button("🔄 再来一次"):
                    st.session_state.chat_active = False
                    st.session_state.messages = []
                    st.session_state.report = None
                    st.session_state.selected_candidate = None
                    st.rerun()

        # 处理智能筛选逻辑 (如果被触发)
        if st.session_state.get('trigger_smart_screen', False):
            st.session_state.trigger_smart_screen = False # Reset
            # 使用当前登录用户作为 Agent A
            agent_a = current_user
            candidates = st.session_state.candidate_pool
            with st.status("正在运行筛选算法...", expanded=True) as status:
                st.write("正在分析兴趣契合度...")
                progress_bar = st.progress(0)
                scores = []
                for i, cand in enumerate(candidates):
                    score = random.randint(50, 95)
                    common_interests = set(agent_a.persona.interests) & set(cand.persona.interests)
                    if common_interests:
                        score += 10
                        st.write(f"发现共同兴趣 [{', '.join(common_interests)}] -> {cand.name} 加分!")
                    scores.append((cand, score))
                    progress_bar.progress((i + 1) / len(candidates))
                    time.sleep(0.05)
                if scores:
                    scores.sort(key=lambda x: x[1], reverse=True)
                    top_candidate = scores[0][0]
                    st.session_state.selected_candidate = top_candidate
                    status.update(label="筛选完成！", state="complete", expanded=False)
                    st.success(f"🎉 匹配成功！决定与 **{top_candidate.name}** 进行深入交流。")
                    st.session_state.chat_active = True
                    st.session_state.messages = []
                    st.rerun()
                else:
                    st.error("当前列表没有嘉宾可选")

        # ---------------------------------------------------------
        # 核心布局逻辑：分栏 vs 全屏
        # ---------------------------------------------------------
        if is_active_mode:
            # 活跃模式：左右分栏 (1:2)
            col_left, col_right = st.columns([1, 2])
            with col_left:
                # 左侧显示紧凑的嘉宾列表
                render_candidate_selector(mode="list")
            with col_right:
                # 右侧显示活跃内容
                render_active_content()
        else:
            # 非活跃模式：全屏显示网格
            render_candidate_selector(mode="grid")
            


    except Exception as e:
        st.error("程序运行错误")
        st.code(traceback.format_exc())

def render_login_page(storage):
    st.title("👋 欢迎来到恋与代理人 (公网版)")
    
    tab1, tab2 = st.tabs(["🚀 注册/更新资料", "🔑 直接登录"])
    
    with tab1:
        st.subheader("创建你的 AI 替身")
        username = st.text_input("设置用户名 (唯一ID)", key="reg_username")
        password = st.text_input("设置密码", type="password", key="reg_password")
        
        # 复用之前的表单逻辑
        agent_data = render_agent_form("Reg", "Alex", 26, "后端工程师", "INTP", "科幻, 编程", "👨", show_calibration=True)
        
        # 偏好设置
        st.markdown("#### 择偶偏好")
        pref_gender = st.selectbox("偏好性别", ["female", "male"], format_func=lambda x: "女生" if x=="female" else "男生")
        pref_loc = st.multiselect("偏好城市", ["杭州", "上海", "北京", "深圳", "成都"], default=["杭州"])
        
        if st.button("提交注册"):
            if not username or not password:
                st.error("请输入用户名和密码")
                return
            
            # 校验校准数据
            if len(agent_data.get("calibration_data", [])) < 3:
                st.error("请完成所有图灵校准问题！")
                return

            preferences = HardPreferences(5, 160, pref_loc, pref_gender)
            profile = build_agent_profile(agent_data, username, preferences)
            
            if storage.register_user(username, password, profile):
                st.success("注册成功！")
                st.session_state.current_user = profile
                st.rerun()
            else:
                st.error("注册失败，请检查数据库连接或联系管理员。")
    
    with tab2:
        st.subheader("回来寻找真爱？")
        login_user = st.text_input("请输入用户名", key="login_username")
        login_pwd = st.text_input("请输入密码", type="password", key="login_password")
        if st.button("登录"):
            if storage.verify_user(login_user, login_pwd):
                user = storage.get_user_by_username(login_user)
                if user:
                    st.success(f"欢迎回来，{user.name}！")
                    st.session_state.current_user = user
                    st.rerun()
                else:
                    st.error("读取用户数据失败")
            else:
                st.error("用户名或密码错误")

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
