#!/usr/bin/env python3
"""
具身智能日报 - 关键词扩展脚本
用于在抓取阶段自动生成中英文双语关键词矩阵
"""

KEYWORDS = {
    "core_concepts": {
        "zh": ["具身智能", "具身AI", "具身大模型", "机器人基础模型", "Embodied AI"],
        "en": ["embodied AI", "embodied intelligence", "robotics foundation model", "RFM"]
    },
    "humanoid": {
        "zh": ["人形机器人", "双足机器人", "通用人形机器人", "全尺寸人形"],
        "en": ["humanoid robot", "bipedal robot", "full-size humanoid"]
    },
    "tech_models": {
        "zh": ["VLA模型", "VLM", "世界模型", "端到端控制", "Sim2Real", "模仿学习", "强化学习"],
        "en": ["VLA", "vision-language-action", "world model", "end-to-end control", "imitation learning"]
    },
    "industry": {
        "zh": ["机器人量产", "工厂落地", "产线部署", "商业化", "规模化交付"],
        "en": ["mass production", "factory deployment", "commercialization"]
    },
    "companies_china": [
        "宇树", "Unitree", "智元", "AgiBot", "银河通用", "Galbot",
        "傅利叶", "FFT", "星动纪元", "逐际动力", "优必选", "UBTECH",
        "小鹏", "Iron", "Xiaopeng Iron", "小米", "CyberOne",
        "荣耀", "追觅", "稚晖君", "智元机器人", "国家地方共建人形机器人创新中心"
    ],
    "companies_global": [
        "Tesla Optimus", "Figure AI", "1X Technologies", "Boston Dynamics",
        "Physical Intelligence", "Skild AI", "Apptronik", "Agility Robotics",
        "Sanctuary AI", "Neura Robotics"
    ],
    "events": ["ICRA", "IROS", "RSS", "CoRL", "WAIC", "世界人工智能大会", "中国机器人展"],
    "policies": ["工信部", "具身智能", "白皮书", "产业政策", "机器人产业", "标准制定"],
    "marketing_keywords": ["发布会", "概念视频", "联名", "KOL投放", "跨界", "IP合作"]
}


def expand_zh_keywords() -> list:
    """生成中文搜索关键词"""
    keywords = []
    keywords.extend(KEYWORDS["core_concepts"]["zh"])
    keywords.extend(KEYWORDS["humanoid"]["zh"])
    keywords.extend(KEYWORDS["tech_models"]["zh"])
    keywords.extend(KEYWORDS["industry"]["zh"])
    keywords.extend(KEYWORDS["companies_china"])
    keywords.extend(KEYWORDS["events"])
    keywords.extend(KEYWORDS["policies"])
    return list(set(keywords))


def expand_en_keywords() -> list:
    """生成英文搜索关键词"""
    keywords = []
    keywords.extend(KEYWORDS["core_concepts"]["en"])
    keywords.extend(KEYWORDS["humanoid"]["en"])
    keywords.extend(KEYWORDS["tech_models"]["en"])
    keywords.extend(KEYWORDS["industry"]["en"])
    keywords.extend(KEYWORDS["companies_global"])
    keywords.extend(KEYWORDS["events"])
    return list(set(keywords))


def build_search_queries(time_window_hours: int = 24) -> list:
    """构造带时间窗口的搜索查询（用于 WebSearch）"""
    base_zh = expand_zh_keywords()
    queries = []
    for kw in base_zh:
        queries.append(f"{kw} 过去{time_window_hours}小时")
        queries.append(f"{kw} 最新")
        queries.append(f"{kw} 今日")
    return queries


if __name__ == "__main__":
    print("=== 中文关键词 ===")
    for kw in expand_zh_keywords():
        print(f"  - {kw}")
    print(f"\n共 {len(expand_zh_keywords())} 个中文关键词")

    print("\n=== 英文关键词 ===")
    for kw in expand_en_keywords():
        print(f"  - {kw}")
    print(f"\n共 {len(expand_en_keywords())} 个英文关键词")

    print("\n=== 示例搜索查询（前10条）===")
    for q in build_search_queries()[:10]:
        print(f"  - {q}")
