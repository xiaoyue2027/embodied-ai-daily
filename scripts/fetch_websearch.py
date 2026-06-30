#!/usr/bin/env python3
"""
具身智能日报 - WebSearch 自动抓取
使用 Tavily Search API（https://tavily.com）

为什么选 Tavily：
  - 为 AI 优化的搜索引擎，返回结构化结果
  - 支持中文、时间过滤、域名白名单
  - 免费 1000 credits/月，够日报用
  - 不像 Google/Bing 那样有反爬

用法：
  export TAVILY_API_KEY="tvly-xxx"
  python3.11 fetch_websearch.py --output /tmp/websearch_today.json

  # 指定抓哪几类
  python3.11 fetch_websearch.py --output /tmp/x.json --max-results 8

  # 指定时间窗（默认最近 24 小时）
  python3.11 fetch_websearch.py --time-range day
"""

import argparse
import json
import os
import sys
import urllib.request
import urllib.error
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional


# Tavily Search API endpoint
TAVILY_API_URL = "https://api.tavily.com/search"

# 抓取关键词矩阵（按板块分组）
INDUSTRY_QUERIES = [
    "具身智能 行业 最新",
    "人形机器人 量产 工厂",
    "具身大模型 VLA 融资",
    "人形机器人 估值 独角兽",
    "具身智能 政策 国务院",
    "机器人基础模型 发布",
    "Embodied AI humanoid robot news",
]

INTERVIEW_QUERIES = [
    "具身智能 CEO 创始人 采访",
    "具身智能 创始人 对话 观点",
    "具身智能 创始人 预测 未来",
    "机器人 创始人 公开演讲",
]

MARKETING_QUERIES = [
    # 通用品牌/营销动作
    "具身智能 品牌 发布会",
    "人形机器人 品牌 营销 活动",
    "机器人 展会 表演",
    "机器人 晚会 直播 综艺",
    "机器人 短视频 爆款 小红书",
    "机器人 抖音 KOL 达人",
    "机器人 品牌合作 联名",
    "机器人 体验 概念 线下快闪",
    # 头部公司具体动作
    "宇树 视频 出圈 营销",
    "优必选 发布会 现场 表演",
    "智元 品牌活动 营销",
    "银河通用 视频 体验",
    "傅利叶 线下 活动",
]

# 优先来源（中文媒体 + 头部垂类）
PRIORITY_DOMAINS = [
    # 主流科技/财经
    "36kr.com", "qbitai.com", "jiqizhixin.com", "zhidxcom.com",
    "leiphone.com", "huxiu.com", "tmtpost.com", "ithome.com",
    "caixin.com", "yicai.com",
    # 垂类机器人
    "airoboticinfo.com", "robot-china.com",
    # 视频/社区
    "bilibili.com", "zhihu.com", "163.com", "qq.com",
    "sina.com.cn", "sohu.com", "ifeng.com", "thepaper.cn",
    "stcn.com", "21jingji.com",
    # 社交
    "xiaohongshu.com", "mp.weixin.qq.com",
    # 短视频 / 视频平台
    "douyin.com", "bilibili.com", "kuaishou.com",
    "youtube.com", "v.qq.com", "ixigua.com",
]

EXCLUDE_DOMAINS = [
    "pornhub.com", "xvideos.com", "reddit.com",  # 噪音
]


def tavily_search(
    api_key: str,
    query: str,
    max_results: int = 6,
    time_range: str = "day",
    topic: str = "news",
    include_domains: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """调用 Tavily Search API"""
    payload = {
        "api_key": api_key,
        "query": query,
        "max_results": max_results,
        "search_depth": "basic",
        "topic": topic,
        "time_range": time_range,
        "include_answer": False,
        "include_raw_content": False,
    }
    if include_domains:
        payload["include_domains"] = include_domains

    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        TAVILY_API_URL,
        data=data,
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def normalize_result(item: Dict[str, Any], section: str) -> Dict[str, Any]:
    """把 Tavily 结果转成日报所需的格式"""
    return {
        "title": item.get("title", "").strip(),
        "url": item.get("url", ""),
        "source": _extract_domain(item.get("url", "")),
        "summary": (item.get("content", "") or "").strip()[:300],
        "date": datetime.now().strftime("%Y-%m-%d"),
        "section_hint": section,
    }


def _extract_domain(url: str) -> str:
    """从 URL 提取友好域名"""
    try:
        from urllib.parse import urlparse
        d = urlparse(url).netloc
        return d.replace("www.", "")
    except Exception:
        return ""


def run(args) -> List[Dict[str, Any]]:
    api_key = args.api_key or os.environ.get("TAVILY_API_KEY", "")
    if not api_key:
        print("错误：未设置 TAVILY_API_KEY", file=sys.stderr)
        print("  注册：https://tavily.com （免费 1000 credits/月）", file=sys.stderr)
        print("  设置：export TAVILY_API_KEY='tvly-xxx'", file=sys.stderr)
        sys.exit(1)

    # 选关键词矩阵
    sections = {
        "industry": INDUSTRY_QUERIES,
        "interview": INTERVIEW_QUERIES,
        "marketing": MARKETING_QUERIES,
    }
    if args.section:
        sections = {args.section: sections[args.section]}

    all_items: List[Dict[str, Any]] = []
    seen_urls = set()
    credits_used = 0

    for section, queries in sections.items():
        print(f"\n[板块] {section}（{len(queries)} 个查询）", file=sys.stderr)
        for q in queries:
            try:
                print(f"  → {q}", file=sys.stderr)
                resp = tavily_search(
                    api_key=api_key,
                    query=q,
                    max_results=args.max_results,
                    time_range=args.time_range,
                    topic="news",
                    include_domains=PRIORITY_DOMAINS,
                )
                results = resp.get("results", [])
                credits_used += resp.get("usage", {}).get("credits", 1)

                for r in results:
                    url = r.get("url", "")
                    if not url or url in seen_urls:
                        continue
                    seen_urls.add(url)
                    item = normalize_result(r, section)
                    if item["title"]:
                        all_items.append(item)
                print(f"    ✓ {len(results)} 条", file=sys.stderr)
            except urllib.error.HTTPError as e:
                body = e.read().decode("utf-8", errors="ignore")
                print(f"    ✗ HTTP {e.code}: {body[:200]}", file=sys.stderr)
            except Exception as e:
                print(f"    ✗ {type(e).__name__}: {e}", file=sys.stderr)

    print(f"\n共 {len(all_items)} 条 / 消耗 {credits_used} credits", file=sys.stderr)
    return all_items


def main():
    ap = argparse.ArgumentParser(description="具身智能日报 - WebSearch 抓取（Tavily）")
    ap.add_argument("--api-key", default="", help="Tavily API Key（默认读 TAVILY_API_KEY 环境变量）")
    ap.add_argument("--output", default="/tmp/websearch_today.json", help="输出 JSON 路径")
    ap.add_argument("--max-results", type=int, default=6, help="每个查询返回的最大结果数（1-20）")
    ap.add_argument("--time-range", default="day", choices=["day", "week", "month", "year", "d", "w", "m", "y"], help="时间窗")
    ap.add_argument("--section", default="", choices=["", "industry", "interview", "marketing"], help="只抓一个板块")
    args = ap.parse_args()

    items = run(args)

    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False, indent=2)
    print(f"\n✓ 已保存: {args.output}（{len(items)} 条）", file=sys.stderr)


if __name__ == "__main__":
    main()
