import streamlit as st
from sqlalchemy import text
from src.agent_builder import AgentProfile, HardAttributes, HardPreferences, Persona
import json

class CloudStorage:
    """
    Supabase 数据库直连封装 (SQLAlchemy)
    """
    def __init__(self):
        try:
            # 使用 Streamlit 原生连接 (基于 SQLAlchemy)
            self.conn = st.connection("supabase", type="sql")
            self.is_connected = True
        except Exception as e:
            st.error(f"[系统错误] 数据库连接失败: {e}")
            self.is_connected = False

    def register_user(self, username: str, profile: AgentProfile) -> bool:
        """
        注册或更新用户信息
        """
        if not self.is_connected:
            st.error("注册失败：数据库未连接，请检查配置或网络。")
            return False

        # 准备数据
        data = {
            "username": username,
            "name": profile.name,
            "gender": profile.attributes.gender,
            "age": profile.attributes.age,
            "job": profile.attributes.job,
            "mbti": profile.persona.mbti,
            "interests": profile.persona.interests, # Array
            "location": profile.attributes.location,
            "calibration_data": json.dumps(profile.persona.turing_calibration_data, ensure_ascii=False), # JSON
            "preferences": json.dumps(profile.preferences.__dict__, ensure_ascii=False) # JSON
        }

        sql = text("""
            INSERT INTO users (username, name, gender, age, job, mbti, interests, location, calibration_data, preferences)
            VALUES (:username, :name, :gender, :age, :job, :mbti, :interests, :location, :calibration_data, :preferences)
            ON CONFLICT (username) 
            DO UPDATE SET
                name = EXCLUDED.name,
                gender = EXCLUDED.gender,
                age = EXCLUDED.age,
                job = EXCLUDED.job,
                mbti = EXCLUDED.mbti,
                interests = EXCLUDED.interests,
                location = EXCLUDED.location,
                calibration_data = EXCLUDED.calibration_data,
                preferences = EXCLUDED.preferences;
        """)

        try:
            with self.conn.session as s:
                s.execute(sql, data)
                s.commit()
            return True
        except Exception as e:
            st.error(f"注册失败: {e}")
            return False

    def get_user_by_username(self, username: str) -> AgentProfile:
        """
        根据用户名获取用户档案
        """
        if not self.is_connected:
            return None
            
        try:
            # query() 返回的是 DataFrame
            df = self.conn.query("SELECT * FROM users WHERE username = :username", params={"username": username}, ttl=0)
            
            if not df.empty:
                # 取第一行，转为字典
                record = df.iloc[0].to_dict()
                return self._record_to_profile(record)
            return None
        except Exception as e:
            print(f"Fetch user error: {e}")
            return None

    def get_candidate_pool(self, current_username: str, limit: int = 20) -> list[AgentProfile]:
        """
        获取广场嘉宾（排除自己）
        """
        if not self.is_connected:
            return []
            
        try:
            sql = "SELECT * FROM users WHERE username != :username ORDER BY created_at DESC LIMIT :limit"
            df = self.conn.query(sql, params={"username": current_username, "limit": limit}, ttl=0)
            
            profiles = []
            # 遍历 DataFrame 的每一行
            for _, record in df.iterrows():
                profiles.append(self._record_to_profile(record.to_dict()))
            return profiles
        except Exception as e:
            st.error(f"获取嘉宾失败: {e}")
            return []

    def _record_to_profile(self, record: dict) -> AgentProfile:
        """
        将数据库记录转换为 AgentProfile 对象
        """
        # 处理 JSON 字段 (pandas 读取后可能是 string 也可能是 dict/list，取决于驱动)
        # psycopg2 通常会自动解析 JSON，但在 DataFrame 中可能是 dict
        # 也有可能是 string，做个防御性编程
        
        pref_data = record.get("preferences", {})
        if isinstance(pref_data, str):
            try:
                pref_data = json.loads(pref_data)
            except:
                pref_data = {}
                
        calib_data = record.get("calibration_data", [])
        if isinstance(calib_data, str):
            try:
                calib_data = json.loads(calib_data)
            except:
                calib_data = []

        # 处理 Array 字段 (interests)
        # pandas 读取 Postgres array 通常是 list，如果是 string 也要处理
        interests = record.get("interests", [])
        if isinstance(interests, str):
            # 简单处理 {a,b,c} 格式？或者 JSON list？
            # 假设驱动处理好了，如果不行则为空
            pass 

        preferences = HardPreferences(
            max_age_gap=pref_data.get("max_age_gap", 5),
            min_height=pref_data.get("min_height", 160),
            allowed_locations=pref_data.get("allowed_locations", ["杭州"]),
            preferred_gender=pref_data.get("preferred_gender", "female")
        )

        return AgentProfile(
            user_id=record.get("username"),
            name=record.get("name"),
            attributes=HardAttributes(
                age=record.get("age"),
                height=175, 
                weight=60, 
                job=record.get("job"),
                annual_salary="保密",
                location=record.get("location"),
                gender=record.get("gender")
            ),
            preferences=preferences,
            persona=Persona(
                mbti=record.get("mbti"),
                interests=interests if isinstance(interests, list) else [],
                turing_calibration_data=calib_data
            )
        )
