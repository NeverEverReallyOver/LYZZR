import random
from src.agent_builder import AgentProfile, HardAttributes, HardPreferences, Persona

# 姓氏库 (Surnames)
SURNAMES = [
    "李", "王", "张", "刘", "陈", "杨", "赵", "黄", "周", "吴",
    "徐", "孙", "胡", "朱", "高", "林", "何", "郭", "马", "罗",
    "梁", "宋", "郑", "谢", "韩", "唐", "冯", "于", "董", "萧",
    "程", "曹", "袁", "邓", "许", "傅", "沈", "曾", "彭", "吕",
    "苏", "卢", "蒋", "蔡", "贾", "丁", "魏", "薛", "叶", "阎",
    "欧阳", "上官", "司马", "诸葛", "夏侯", "皇甫", "慕容" # 复姓
]

# 男性名字库 (Given Names - Male)
MALE_GIVEN_NAMES_1_CHAR = [
    "伟", "强", "磊", "洋", "勇", "军", "杰", "涛", "超", "明",
    "刚", "平", "辉", "鹏", "华", "飞", "鑫", "波", "斌", "浩",
    "凯", "峰", "帅", "亮", "龙", "晨", "俊", "宇", "博", "雷",
    "昊", "铭", "轩", "然", "越", "岩", "哲", "涵", "皓", "睿"
]

MALE_GIVEN_NAMES_2_CHAR = [
    "子墨", "浩宇", "宇轩", "子轩", "浩然", "梓豪", "一诺", "梓睿", "俊熙", "铭轩",
    "建国", "国强", "志强", "志刚", "文博", "天宇", "智勇", "嘉豪", "俊杰", "子豪",
    "伟成", "安邦", "鸿煊", "博文", "致远", "修杰", "黎昕", "海超", "伟泽", "旭尧"
]

# 女性名字库 (Given Names - Female)
FEMALE_GIVEN_NAMES_1_CHAR = [
    "静", "敏", "燕", "艳", "丽", "娟", "莉", "芳", "娜", "琳",
    "洁", "梅", "玲", "丹", "萍", "红", "玉", "兰", "霞", "婷",
    "慧", "莹", "雪", "佳", "倩", "雅", "露", "颖", "菲", "琦",
    "悦", "欣", "怡", "通过", "宁", "童", "彤", "曼", "希", "艺"
]

FEMALE_GIVEN_NAMES_2_CHAR = [
    "子涵", "梓萱", "一诺", "诗涵", "欣怡", "梓涵", "晨曦", "紫涵", "雨桐", "雨婷",
    "梦洁", "雅静", "思颖", "梦璐", "惠茜", "漫妮", "语嫣", "桑榆", "曼玉", "雪芳",
    "优璇", "雨嘉", "明美", "可馨", "惠蝶", "香怡", "靖瑶", "瑾萱", "梦柏", "天瑜"
]

# 英文名库 (English Names)
MALE_ENGLISH_NAMES = [
    "James", "John", "Robert", "Michael", "William", "David", "Richard", "Joseph", "Thomas", "Charles",
    "Christopher", "Daniel", "Matthew", "Anthony", "Donald", "Mark", "Paul", "Steven", "Andrew", "Kenneth",
    "George", "Joshua", "Kevin", "Brian", "Edward", "Ronald", "Timothy", "Jason", "Jeffrey", "Ryan",
    "Jacob", "Gary", "Nicholas", "Eric", "Stephen", "Jonathan", "Larry", "Justin", "Scott", "Brandon"
]

FEMALE_ENGLISH_NAMES = [
    "Mary", "Patricia", "Jennifer", "Linda", "Elizabeth", "Barbara", "Susan", "Jessica", "Sarah", "Karen",
    "Nancy", "Lisa", "Betty", "Margaret", "Sandra", "Ashley", "Kimberly", "Emily", "Donna", "Michelle",
    "Dorothy", "Carol", "Amanda", "Melissa", "Deborah", "Stephanie", "Rebecca", "Laura", "Sharon", "Cynthia",
    "Kathleen", "Amy", "Shirley", "Angela", "Helen", "Anna", "Brenda", "Pamela", "Nicole", "Samantha"
]

class CandidateGenerator:
    """
    随机嘉宾生成器
    """
    
    @staticmethod
    def _generate_chinese_name(gender: str) -> str:
        surname = random.choice(SURNAMES)
        
        if gender == "female":
            # 30% 概率单字名，70% 概率双字名
            if random.random() < 0.3:
                given_name = random.choice(FEMALE_GIVEN_NAMES_1_CHAR)
            else:
                given_name = random.choice(FEMALE_GIVEN_NAMES_2_CHAR)
        else:
            if random.random() < 0.3:
                given_name = random.choice(MALE_GIVEN_NAMES_1_CHAR)
            else:
                given_name = random.choice(MALE_GIVEN_NAMES_2_CHAR)
                
        return surname + given_name

    @staticmethod
    def generate_random_agent(user_id: str, preferences: HardPreferences = None) -> AgentProfile:
        # 1. 确定性别 (严格遵循偏好)
        gender = "female"
        if preferences and preferences.preferred_gender:
            gender = preferences.preferred_gender
        else:
            gender = random.choice(["male", "female"])
            
        # 2. 生成名字 (多样化：中文二字/三字/四字，英文名)
        name_type = random.random()
        
        if name_type < 0.15: 
            # 15% 概率生成英文名
            if gender == "female":
                name = random.choice(FEMALE_ENGLISH_NAMES)
            else:
                name = random.choice(MALE_ENGLISH_NAMES)
        else:
            # 85% 概率生成中文名
            name = CandidateGenerator._generate_chinese_name(gender)
        
        # 3. 确定年龄 (基于偏好微调)
        if preferences:
            # 假设基准年龄 25，根据 max_age_gap 波动
            base_age = 25 
            min_age = max(18, base_age - preferences.max_age_gap)
            max_age = min(60, base_age + preferences.max_age_gap)
            age = random.randint(min_age, max_age)
        else:
            age = random.randint(22, 35)
        
        jobs = ["UI设计师", "后端工程师", "产品经理", "市场专员", "插画师", "会计", "教师", "自媒体博主", "律师", "医生"]
        job = random.choice(jobs)
        
        # 4. 确定地点
        if preferences and preferences.allowed_locations:
            # 80% 概率生成在偏好城市，20% 随机
            if random.random() < 0.8:
                location = random.choice(preferences.allowed_locations)
            else:
                location = random.choice(["杭州", "上海", "北京", "深圳", "成都"])
        else:
            locations = ["杭州", "上海", "北京", "深圳", "成都"]
            location = random.choice(locations)
        
        mbtis = ["INFP", "ENFP", "INFJ", "ENFJ", "INTJ", "ENTJ", "INTP", "ENTP", 
                 "ISFP", "ESFP", "ISTP", "ESTP", "ISFJ", "ESFJ", "ISTJ", "ESTJ"]
        mbti = random.choice(mbtis)
        
        interests_pool = [
            "科幻电影", "马拉松", "手冲咖啡", "剧本杀", "露营", "摄影", "撸猫", 
            "投资理财", "二次元", "烹饪", "摇滚乐", "古典音乐", "网球", "Citywalk"
        ]
        interests = random.sample(interests_pool, k=3)
        
        # 5. 生成图灵校准答案 (赋予价值观)
        calibration_data = CandidateGenerator._generate_calibration_answers()
        
        return AgentProfile(
            user_id=user_id,
            name=name,
            attributes=HardAttributes(
                age=age,
                height=random.randint(155, 185),
                weight=random.randint(45, 80),
                job=job,
                annual_salary=f"{random.randint(10, 80)}w",
                location=location,
                gender=gender # 确保这里的性别与偏好一致
            ),
            preferences=HardPreferences(5, 160, [location]), 
            persona=Persona(mbti, interests, calibration_data)
        )

    @staticmethod
    def _generate_calibration_answers() -> list[dict]:
        """
        随机生成价值观问答数据
        """
        # 定义问题集和可能的回答倾向
        questions_pool = [
            {
                "question": "如果对方迟到了30分钟，你会说什么？",
                "options": [
                    "没事，我也刚到。（随和包容）",
                    "我会很担心，问问是不是出什么事了。（体贴）",
                    "我会有点生气，告诉对方下次要注意。（原则性强）",
                    "直接走人，我最讨厌不守时。（零容忍）"
                ]
            },
            {
                "question": "你最喜欢的周末活动是什么？",
                "options": [
                    "宅在家里打游戏或者看剧。（宅属性）",
                    "去户外爬山或者露营。（户外属性）",
                    "和朋友聚餐、逛街、探店。（社交属性）",
                    "去书店或者咖啡馆看书学习。（文艺属性）"
                ]
            },
            {
                "question": "对方问了一个你不想回答的问题，怎么婉拒？",
                "options": [
                    "哈哈，这个秘密以后再告诉你。（幽默）",
                    "直接说“我不想回答这个问题”。（直率）",
                    "转移话题，聊点别的。（圆滑）",
                    "沉默不语，装作没看见。（回避）"
                ]
            }
        ]
        
        calibration = []
        for q in questions_pool:
            answer = random.choice(q["options"])
            calibration.append({"question": q["question"], "answer": answer})
            
        return calibration

    @staticmethod
    def generate_pool(count: int = 20, preferences: HardPreferences = None) -> list[AgentProfile]:
        return [CandidateGenerator.generate_random_agent(f"guest_{i}", preferences) for i in range(count)]
