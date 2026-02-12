# 💘 恋与代理人 (Love and Agents) - 公网真实版

这是一个基于 Multi-Agent（多智能体）技术的社交模拟实验平台。

## ✨ 核心功能

*   **真实交互**：基于 Supabase 云端数据库，支持真实用户注册与数据持久化。
*   **AI 替身**：每个用户拥有一个由 LLM 驱动的 AI 替身，学习你的价值观和说话风格。
*   **图灵校准**：通过一系列价值观问答，让 AI 更精准地模仿你的思维方式。
*   **智能匹配**：AI 替身在广场上自动与其他用户的替身进行海选和初聊。
*   **深度对话**：匹配成功后，进入双方 AI 的深度聊天室，并由裁判 AI 生成匹配报告。

## 🛠️ 技术栈

*   **Frontend**: Streamlit
*   **Backend**: Python, AgentScope
*   **Database**: Supabase (PostgreSQL)
*   **LLM**: Kimi (Moonshot AI)

## 🚀 如何运行

1.  安装依赖：
    ```bash
    pip install -r requirements.txt
    ```

2.  配置密钥：
    在 `.streamlit/secrets.toml` 中配置 Supabase 连接信息。

3.  启动应用：
    ```bash
    streamlit run app.py
    ```
