#!/usr/bin/env python3
"""
KOL / 播客 / 即刻 / 公众号 渠道当日抓取脚本

依赖：
  pip3 install playwright beautifulsoup4
  python3.11 -m playwright install chromium

功能：
  1. 抓取小宇宙播客（八分半、T 中文播客、三表龙门阵）的最近一期/动态
  2. 抓取即刻 App 具身智能话题圈（通过 Web 站）
  3. 抓取搜狗微信上「具身智能 / 张小珺 / 周鑫雨 / 史海涛 / 周小燕」的当日文章
  4. 输出统一格式的 JSON / Markdown 片段

用法：
  python3.11 fetch_kol.py --days 1 --output /tmp/kol_today.json
  python3.11 fetch_kol.py --source xiaoyuzhou --days 3
  python3.11 fetch_kol.py --source wechat --keyword 具身智能
"""

import argparse
import json
import re
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional


# ---------------------- 工具函数 ----------------------

def now_str() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def safe_filename(s: str) -> str:
    return re.sub(r"[^\w\-_.]", "_", s)[:80]


def normalize_date(s: str) -> Optional[str]:
    """把各种日期字符串归一为 YYYY-MM-DD"""
    if not s:
        return None
    s = s.strip()
    # 已经是标准日期
    m = re.match(r"(\d{4})[-./](\d{1,2})[-./](\d{1,2})", s)
    if m:
        return f"{m.group(1)}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"
    # 相对日期：今天 / 昨天 / X小时前
    today = datetime.now().date()
    if "今天" in s:
        return str(today)
    if "昨天" in s:
        return str(today - timedelta(days=1))
    if "前天" in s:
        return str(today - timedelta(days=2))
    m = re.search(r"(\d+)\s*小时前", s)
    if m:
        return str(today)
    m = re.search(r"(\d+)\s*天前", s)
    if m:
        return str(today - timedelta(days=int(m.group(1))))
    return None


def within_days(date_str: Optional[str], days: int) -> bool:
    if not date_str:
        return True  # 没日期时保留，交给人工判断
    try:
        d = datetime.strptime(date_str, "%Y-%m-%d").date()
        return (datetime.now().date() - d).days <= days
    except Exception:
        return True


# ---------------------- 抓取器：微信公众号（搜狗微信）----------------------

def fetch_wechat_sogou(keyword: str, days: int = 1, headless: bool = True) -> List[Dict[str, Any]]:
    """
    通过搜狗微信（weixin.sogou.com）搜索公众号文章。
    注意：搜狗微信有反爬，建议低频使用，单次最多抓 1-2 页。
    """
    from playwright.sync_api import sync_playwright

    results: List[Dict[str, Any]] = []
    url = f"https://weixin.sogou.com/weixin?type=2&query={keyword}&ie=utf8"

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        context = browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
        )
        page = context.new_page()
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=30000)
            page.wait_for_timeout(2000)

            items = page.query_selector_all("li[class*='vr-list']") or page.query_selector_all("ul.news-list2 li")
            for it in items[:20]:
                try:
                    title_el = it.query_selector("a[uigs='article_title']") or it.query_selector("h3 a") or it.query_selector("a")
                    title = title_el.inner_text().strip() if title_el else ""
                    href = title_el.get_attribute("href") if title_el else ""

                    summary_el = it.query_selector("p[class*='txt-info']") or it.query_selector("p.txt-info")
                    summary = summary_el.inner_text().strip() if summary_el else ""

                    author_el = it.query_selector("a[uigs='account_article_name']") or it.query_selector(".account")
                    author = author_el.inner_text().strip() if author_el else ""

                    time_el = it.query_selector("span.time") or it.query_selector(".s2")
                    time_txt = time_el.inner_text().strip() if time_el else ""
                    date = normalize_date(time_txt)

                    if not within_days(date, days):
                        continue
                    if not title:
                        continue

                    results.append({
                        "source": "wechat-sogou",
                        "title": title,
                        "summary": summary[:200],
                        "author": author,
                        "date": date,
                        "url": href,
                        "keyword": keyword,
                    })
                except Exception as e:
                    print(f"[wechat] item parse error: {e}", file=sys.stderr)
                    continue
        except Exception as e:
            print(f"[wechat] fetch error: {e}", file=sys.stderr)
        finally:
            browser.close()

    return results


# ---------------------- 抓取器：小宇宙播客 ----------------------

XIAOYUZHOU_SHOWS = {
    "八分半": "https://www.xiaoyuzhoufm.com/podcast/5e4c1c1e8b7c5d0008f5f0c4",
    "T 中文播客": "https://www.xiaoyuzhoufm.com/podcast/5e8d2f8e8b7c5d0008f5f0c8",
    "三表龙门阵": "https://www.xiaoyuzhoufm.com/podcast/5e8d2f8e8b7c5d0008f5f0c9",
}


def fetch_xiaoyuzhou(show_name: str, days: int = 7, headless: bool = True) -> List[Dict[str, Any]]:
    """
    抓取小宇宙某个播客的最近 N 期节目标题。
    实际 URL 需要从 https://www.xiaoyuzhoufm.com 站内搜索后填入 XIAOYUZHOU_SHOWS。
    """
    from playwright.sync_api import sync_playwright

    url = XIAOYUZHOU_SHOWS.get(show_name)
    if not url:
        print(f"[xiaoyuzhou] 未知播客: {show_name}，请先在 XIAOYUZHOU_SHOWS 中配置 URL", file=sys.stderr)
        return []

    results: List[Dict[str, Any]] = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        page = browser.new_page()
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=30000)
            page.wait_for_timeout(2500)
            items = page.query_selector_all("a[href*='/episode/']")
            for it in items[:10]:
                try:
                    href = it.get_attribute("href") or ""
                    title_el = it.query_selector("h3, .episode-title, [class*='title']")
                    title = (title_el.inner_text().strip() if title_el else it.inner_text().strip())[:200]
                    if not title:
                        continue
                    full_url = f"https://www.xiaoyuzhoufm.com{href}" if href.startswith("/") else href
                    results.append({
                        "source": "xiaoyuzhou",
                        "show": show_name,
                        "title": title,
                        "date": None,  # 播客列表页通常不直接显示日期
                        "url": full_url,
                    })
                except Exception as e:
                    print(f"[xiaoyuzhou] item error: {e}", file=sys.stderr)
                    continue
        except Exception as e:
            print(f"[xiaoyuzhou] fetch error: {e}", file=sys.stderr)
        finally:
            browser.close()

    return results


# ---------------------- 抓取器：即刻 App ----------------------

JIKES_TOPICS = {
    "具身智能": "https://web.okjike.com/topic/具身智能",
    "人形机器人": "https://web.okjike.com/topic/人形机器人",
    "机器人": "https://web.okjike.com/topic/机器人",
}


def fetch_jike(topic: str, days: int = 1, headless: bool = True) -> List[Dict[str, Any]]:
    """
    抓取即刻某个话题圈的最近动态。
    注意：即刻 Web 站 https://web.okjike.com 需要登录才能看完整内容。
    未登录时仅返回公开热门。
    """
    from playwright.sync_api import sync_playwright

    url = JIKES_TOPICS.get(topic) or f"https://web.okjike.com/topic/{topic}"
    results: List[Dict[str, Any]] = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        page = browser.new_page()
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=30000)
            page.wait_for_timeout(2500)
            # 即刻帖子卡片
            items = page.query_selector_all("a[href*='/post/']") or page.query_selector_all("article")
            for it in items[:20]:
                try:
                    href = it.get_attribute("href") or ""
                    title = it.inner_text().strip()[:200]
                    if not title or len(title) < 5:
                        continue
                    full_url = f"https://web.okjike.com{href}" if href.startswith("/") else href
                    results.append({
                        "source": "jike",
                        "topic": topic,
                        "title": title,
                        "date": None,
                        "url": full_url,
                    })
                except Exception:
                    continue
        except Exception as e:
            print(f"[jike] fetch error: {e}", file=sys.stderr)
        finally:
            browser.close()

    return results


# ---------------------- 主流程 ----------------------

DEFAULT_KOL_KEYWORDS = [
    "具身智能",
    "人形机器人",
    "张小珺",
    "周鑫雨",
    "史海涛 具身",
    "周小燕 具身",
]


def run(args) -> Dict[str, Any]:
    output: Dict[str, Any] = {
        "fetched_at": now_str(),
        "days": args.days,
        "results": {
            "wechat": [],
            "xiaoyuzhou": [],
            "jike": [],
        },
    }

    sources = args.source.split(",") if args.source else ["wechat", "xiaoyuzhou", "jike"]

    if "wechat" in sources:
        keywords = args.keyword.split(",") if args.keyword else DEFAULT_KOL_KEYWORDS
        for kw in keywords:
            print(f"[+] 抓取微信：{kw}", file=sys.stderr)
            try:
                items = fetch_wechat_sogou(kw, days=args.days, headless=not args.show)
                output["results"]["wechat"].extend(items)
            except Exception as e:
                print(f"[wechat] {kw} 抓取失败: {e}", file=sys.stderr)
            time.sleep(2)  # 频率控制

    if "xiaoyuzhou" in sources:
        for show in XIAOYUZHOU_SHOWS.keys():
            print(f"[+] 抓取播客：{show}", file=sys.stderr)
            try:
                items = fetch_xiaoyuzhou(show, days=args.days, headless=not args.show)
                output["results"]["xiaoyuzhou"].extend(items)
            except Exception as e:
                print(f"[xiaoyuzhou] {show} 抓取失败: {e}", file=sys.stderr)
            time.sleep(1)

    if "jike" in sources:
        for topic in JIKES_TOPICS.keys():
            print(f"[+] 抓取即刻：{topic}", file=sys.stderr)
            try:
                items = fetch_jike(topic, days=args.days, headless=not args.show)
                output["results"]["jike"].extend(items)
            except Exception as e:
                print(f"[jike] {topic} 抓取失败: {e}", file=sys.stderr)
            time.sleep(1)

    # 统计
    total = sum(len(v) for v in output["results"].values())
    output["total"] = total
    print(f"\n✓ 共抓取 {total} 条", file=sys.stderr)

    return output


def to_markdown(data: Dict[str, Any]) -> str:
    """把抓取结果格式化为 Markdown 片段，方便 Skill 直接贴入日报"""
    lines = [f"## KOL / 播客 / 即刻 / 公众号 当日抓取（{data['fetched_at']}）\n"]
    for ch, items in data["results"].items():
        if not items:
            continue
        ch_name = {"wechat": "微信公众号（搜狗）", "xiaoyuzhou": "小宇宙播客", "jike": "即刻话题圈"}[ch]
        lines.append(f"### {ch_name}（{len(items)} 条）\n")
        for i, it in enumerate(items, 1):
            title = it.get("title", "")
            url = it.get("url", "")
            extra = ""
            if it.get("author"):
                extra += f"  \n  作者：{it['author']}"
            if it.get("show"):
                extra += f"  \n  节目：{it['show']}"
            if it.get("topic"):
                extra += f"  \n  话题：{it['topic']}"
            if it.get("date"):
                extra += f"  \n  日期：{it['date']}"
            if it.get("summary"):
                extra += f"  \n  摘要：{it['summary']}"
            lines.append(f"{i}. [{title}]({url}){extra}")
        lines.append("")
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser(description="具身智能日报 - KOL/播客/公众号/即刻 抓取")
    ap.add_argument("--source", default="wechat,xiaoyuzhou,jike", help="渠道：wechat,xiaoyuzhou,jike（逗号分隔）")
    ap.add_argument("--keyword", default="", help="微信关键词（逗号分隔），默认用内置 KOL 列表")
    ap.add_argument("--days", type=int, default=1, help="时间窗（天）")
    ap.add_argument("--output", default="", help="输出 JSON 路径")
    ap.add_argument("--markdown", default="", help="输出 Markdown 路径")
    ap.add_argument("--show", action="store_true", help="显示浏览器（调试用）")
    args = ap.parse_args()

    data = run(args)

    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"✓ JSON 已保存: {args.output}", file=sys.stderr)

    if args.markdown:
        Path(args.markdown).parent.mkdir(parents=True, exist_ok=True)
        with open(args.markdown, "w", encoding="utf-8") as f:
            f.write(to_markdown(data))
        print(f"✓ Markdown 已保存: {args.markdown}", file=sys.stderr)

    if not args.output and not args.markdown:
        print(json.dumps(data, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
