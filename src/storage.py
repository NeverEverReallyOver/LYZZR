import streamlit as st
from sqlalchemy import text
from src.agent_builder import AgentProfile, HardAttributes, HardPreferences, Persona
import json
import hashlib

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

    def _hash_password(self, password: str) -> str:
        """简单的 SHA256 哈希"""
        return hashlib.sha256(password.encode()).hexdigest()

    def register_user(self, username: str, password: str, profile: AgentProfile) -> bool:
        """
        注册或更新用户信息 (包含密码)
        """
        if not self.is_connected:
            st.error("注册失败：数据库未连接，请检查配置或网络。")
            return False

        # 密码加密 (SHA256)
        hashed_password = self._hash_password(password)

        # 准备数据
        data = {
            "username": username,
            "password_hash": hashed_password,
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
            INSERT INTO users (username, password_hash, name, gender, age, job, mbti, interests, location, calibration_data, preferences)
            VALUES (:username, :password_hash, :name, :gender, :age, :job, :mbti, :interests, :location, :calibration_data, :preferences)
            ON CONFLICT (username) 
            DO UPDATE SET
                password_hash = EXCLUDED.password_hash,
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

    def verify_user(self, username: str, password: str) -> bool:
        """
        验证用户登录
        """
        if not self.is_connected:
            return False
            
        try:
            df = self.conn.query("SELECT password_hash FROM users WHERE username = :username", params={"username": username}, ttl=0)
            if df.empty:
                return False
            
            stored_hash = df.iloc[0]["password_hash"]
            if not stored_hash: # 旧用户可能没有密码
                return False
                
            # 兼容处理：如果是 $2b$ 开头的，说明是 bcrypt (旧数据)，否则是 SHA256 (新数据)
            if stored_hash.startswith("$2b$"):
                 # 如果遇到旧的 bcrypt 密码，因为没有 bcrypt 库了，直接报错或提示重置
                 # 这是一个权宜之计，为了让新用户能用
                 print("Found legacy bcrypt password, cannot verify without bcrypt lib.")
                 return False
            else:
                 return stored_hash == self._hash_password(password)
        except Exception as e:
            print(f"Login error: {e}")
            return False

    def save_match_record(self, user_a: str, user_b: str, chat_log: list, score: int, report: str):
        """
        保存匹配记录
        """
        if not self.is_connected: return
        
        try:
            sql = text("""
                INSERT INTO match_records (user_a, user_b, chat_log, match_score, report)
                VALUES (:user_a, :user_b, :chat_log, :score, :report)
            """)
            
            with self.conn.session as s:
                s.execute(sql, {
                    "user_a": user_a,
                    "user_b": user_b,
                    "chat_log": json.dumps(chat_log, ensure_ascii=False),
                    "score": score,
                    "report": report
                })
                s.commit()
        except Exception as e:
            st.error(f"保存匹配记录失败: {e}")

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

    def get_match_history(self, username: str, current_user_name: str = None) -> list[dict]:
        """
        [Deprecated] 旧接口，为了兼容性保留，内部调用 get_top_matches
        """
        return self.get_top_matches(username, limit=100, current_user_name=current_user_name)

    def get_top_matches(self, username: str, limit: int = 3, current_user_name: str = None) -> list[dict]:
        """
        获取排行榜 (按分数降序)
        """
        if not self.is_connected: return []
        
        try:
            # 关联查询对方的名字 (使用 LEFT JOIN 以包含虚拟用户)
            # 如果是虚拟用户 (u.name 为 NULL)，暂时用 ID 代替，后续 UI 层可以优化显示
            sql = """
                SELECT r.*, COALESCE(u.name, 'AI Guest') as partner_name 
                FROM match_records r
                LEFT JOIN users u ON (u.username = r.user_b AND r.user_a = :u) OR (u.username = r.user_a AND r.user_b = :u)
                WHERE r.user_a = :u OR r.user_b = :u
                ORDER BY r.match_score DESC
                LIMIT :limit
            """
            df = self.conn.query(sql, params={"u": username, "limit": limit}, ttl=0)
            records = df.to_dict(orient="records")
            
            # 后处理：如果是 AI Guest，尝试从 chat_log 中解析名字
            self._enrich_virtual_user_names(records, current_user_name)
            
            return records
        except Exception as e:
            st.error(f"获取排行榜失败: {e}")
            return []

    def get_recent_matches(self, username: str, limit: int = 5, current_user_name: str = None) -> list[dict]:
        """
        获取最近对话记录 (按时间倒序)
        """
        if not self.is_connected: return []
        
        try:
            sql = """
                SELECT r.*, COALESCE(u.name, 'AI Guest') as partner_name 
                FROM match_records r
                LEFT JOIN users u ON (u.username = r.user_b AND r.user_a = :u) OR (u.username = r.user_a AND r.user_b = :u)
                WHERE r.user_a = :u OR r.user_b = :u
                ORDER BY r.created_at DESC
                LIMIT :limit
            """
            df = self.conn.query(sql, params={"u": username, "limit": limit}, ttl=0)
            records = df.to_dict(orient="records")
            
            self._enrich_virtual_user_names(records, current_user_name)
            
            return records
        except Exception as e:
            st.error(f"获取最近记录失败: {e}")
            return []

    def _enrich_virtual_user_names(self, records: list[dict], current_user_name: str = None):
        """
        辅助函数：尝试从 chat_log 中解析虚拟用户的名字
        """
        for r in records:
            if r['partner_name'] == 'AI Guest':
                try:
                    chat_log = r.get('chat_log')
                    if isinstance(chat_log, str):
                        chat_log = json.loads(chat_log)
                    
                    names = set()
                    for msg in chat_log:
                        if msg.get('name') and msg.get('name') != 'System':
                            names.add(msg.get('name'))
                    
                    # 排除当前用户的名字
                    if current_user_name and current_user_name in names:
                        names.remove(current_user_name)
                    
                    if names:
                        # 简单策略：取列表里出现的第一个名字，加上 (AI)
                        r['partner_name'] = list(names)[0] + " (AI)"
                except:
                    pass

    def get_chatted_users(self, username: str) -> dict:
        """
        获取已聊过的用户ID及其最高分数
        返回: { 'target_username': max_score }
        """
        if not self.is_connected: return {}
        try:
            sql = """
                SELECT user_a, user_b, match_score FROM match_records 
                WHERE user_a = :u OR user_b = :u
            """
            df = self.conn.query(sql, params={"u": username}, ttl=0)
            
            result = {}
            for _, row in df.iterrows():
                partner = row['user_b'] if row['user_a'] == username else row['user_a']
                score = row['match_score']
                if partner not in result or score > result[partner]:
                    result[partner] = score
            return result
        except Exception as e:
            return {}

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
