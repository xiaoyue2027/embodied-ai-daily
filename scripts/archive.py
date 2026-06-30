#!/usr/bin/env python3
"""
具身智能日报 - 历史归档与月度趋势报告

功能：
  1. 把日报按月归档到 monthly/YYYY-MM/
  2. 解析日报内容，提取统计指标
  3. 生成月度趋势报告（融资、热度、TOP 事件、环比变化）

用法：
  # 归档并生成当月报告
  python3.11 archive.py

  # 归档指定日期范围
  python3.11 archive.py --from 2026-06-01 --to 2026-06-30

  # 只生成月度报告（不重新归档）
  python3.11 archive.py --report-only --month 2026-06

  # 查看已归档的所有月份
  python3.11 archive.py --list-months
"""

import argparse
import json
import re
import shutil
import sys
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


DAILY_DIR = Path("/workspace/daily_reports")
ARCHIVE_DIR = Path("/workspace/daily_reports/monthly")


# ---------------------- 归档 ----------------------

def archive_daily(daily_path: Path, month_dir: Path) -> Path:
    """把日报复制到按月归档目录"""
    month_dir.mkdir(parents=True, exist_ok=True)
    target = month_dir / daily_path.name
    if not target.exists():
        shutil.copy2(daily_path, target)
    return target


def list_dailies(start: Optional[str] = None, end: Optional[str] = None) -> List[Path]:
    """列出日报文件，可选时间范围"""
    if not DAILY_DIR.exists():
        return []
    files = sorted(DAILY_DIR.glob("embodied_ai_*.md"))
    if not start and not end:
        return files
    out = []
    for f in files:
        m = re.search(r"embodied_ai_(\d{4}-\d{2}-\d{2})\.md", f.name)
        if not m:
            continue
        d = m.group(1)
        if start and d < start:
            continue
        if end and d > end:
            continue
        out.append(f)
    return out


# ---------------------- 解析 ----------------------

SECTION_PATTERNS = {
    "industry": re.compile(r"^##\s+一、行业信息", re.M),
    "interview": re.compile(r"^##\s+二、高层访谈", re.M),
    "marketing": re.compile(r"^##\s+三、品牌市场营销动作", re.M),
}

ITEM_HEADER = re.compile(r"^###\s+\d+\.\s+\[(?P<title>[^\]]+)\]\((?P<url>[^)]+)\)", re.M)
SUMMARY_LINE = re.compile(r"^- \*\*摘要\*\*：(.+)$", re.M)
SOURCE_LINE = re.compile(r"^- \*\*来源\*\*：(.+)$", re.M)
DATE_LINE = re.compile(r"^- \*\*日期\*\*：(.+)$", re.M)


def parse_daily(md_path: Path) -> Dict[str, Any]:
    """解析单份日报"""
    text = md_path.read_text(encoding="utf-8")
    date_match = re.search(r"embodied_ai_(\d{4}-\d{2}-\d{2})\.md", md_path.name)
    date = date_match.group(1) if date_match else "unknown"

    # 总览
    summary_match = re.search(r">\s*今日要闻共\s*\*\*(\d+)\*\*\s*条\s*\|\s*行业信息\s*\*\*(\d+)\*\*\s*条\s*\|\s*高层访谈\s*\*\*(\d+)\*\*\s*条\s*\|\s*品牌营销\s*\*\*(\d+)\*\*\s*条", text)
    counts = {
        "total": int(summary_match.group(1)) if summary_match else 0,
        "industry": int(summary_match.group(2)) if summary_match else 0,
        "interview": int(summary_match.group(3)) if summary_match else 0,
        "marketing": int(summary_match.group(4)) if summary_match else 0,
    }

    # 提取每个板块的条目
    items = []
    for section_key, section_pat in SECTION_PATTERNS.items():
        m = section_pat.search(text)
        if not m:
            continue
        start = m.end()
        # 找下一个 ## 开头（即下一板块）或文件结尾
        next_section = re.search(r"^##\s+", text[start:], re.M)
        end = start + next_section.start() if next_section else len(text)
        section_text = text[start:end]
        for h in ITEM_HEADER.finditer(section_text):
            title = h.group("title")
            url = h.group("url")
            after = section_text[h.end():]
            # 找摘要
            sm = SUMMARY_LINE.search(after[:500])
            summary = sm.group(1).strip() if sm else ""
            # 找来源
            src_m = SOURCE_LINE.search(after[:500])
            source = src_m.group(1).strip() if src_m else ""
            # 找日期
            dt_m = DATE_LINE.search(after[:500])
            item_date = dt_m.group(1).strip() if dt_m else date
            items.append({
                "section": section_key,
                "title": title,
                "url": url,
                "summary": summary,
                "source": source,
                "date": item_date,
            })

    return {"date": date, "counts": counts, "items": items}


# ---------------------- 月度统计 ----------------------

def build_month_report(month: str, daily_data: List[Dict[str, Any]]) -> str:
    """生成月度趋势报告"""
    total_days = len(daily_data)
    if total_days == 0:
        return f"# {month} 月度报告\n\n_本月暂无日报数据_\n"

    # 汇总
    total_items = sum(d["counts"]["total"] for d in daily_data)
    section_totals = {
        "industry": sum(d["counts"]["industry"] for d in daily_data),
        "interview": sum(d["counts"]["interview"] for d in daily_data),
        "marketing": sum(d["counts"]["marketing"] for d in daily_data),
    }

    # 热度统计：来源 / 关键词
    source_counter = Counter()
    keyword_counter = Counter()
    funding_keywords = ["融资", "估值", "亿元", "A轮", "B轮", "C轮", "战略", "投资", "收购"]
    funding_total = 0
    all_items = []

    for d in daily_data:
        for it in d["items"]:
            source_counter[it.get("source", "未知")] += 1
            all_items.append({**it, "date": d["date"]})
            # 关键词统计
            for k in ["融资", "估值", "量产", "工厂", "VLA", "VLOA", "基础模型", "发布", "战略", "投资", "合作", "国资委", "工信部", "首发", "降价", "联名", "出海"]:
                if k in (it.get("title", "") + it.get("summary", "")):
                    keyword_counter[k] += 1
            # 融资事件
            for k in funding_keywords:
                if k in (it.get("title", "") + it.get("summary", "")):
                    funding_total += 1
                    break

    # TOP 10 事件（按时间排，简化版：取最新 10 条）
    top_items = sorted(all_items, key=lambda x: x["date"], reverse=True)[:10]

    # 来源 TOP 10
    top_sources = source_counter.most_common(10)
    top_keywords = keyword_counter.most_common(15)

    # 日均产出
    avg_per_day = round(total_items / total_days, 1)

    # 渲染
    lines = [
        f"# 具身智能 · {month} 月度趋势报告",
        "",
        f"> 统计周期：{month}-01 ~ {last_day_of_month(month)}",
        f"> 覆盖日报：{total_days} 天 | 累计要闻：{total_items} 条",
        f"> 日均产出：{avg_per_day} 条",
        "",
        "---",
        "",
        "## 一、整体概览",
        "",
        "| 板块 | 条数 | 占比 |",
        "|------|------|------|",
    ]
    total = total_items or 1
    for sec, label in [("industry", "行业信息"), ("interview", "高层访谈"), ("marketing", "品牌营销")]:
        n = section_totals[sec]
        pct = round(n / total * 100, 1)
        lines.append(f"| {label} | {n} | {pct}% |")
    lines.append(f"| **合计** | **{total_items}** | **100%** |")
    lines.append("")

    # 热度
    lines.append("## 二、热点关键词 TOP 15")
    lines.append("")
    lines.append("| 排名 | 关键词 | 提及次数 |")
    lines.append("|------|--------|---------|")
    for i, (kw, cnt) in enumerate(top_keywords, 1):
        lines.append(f"| {i} | {kw} | {cnt} |")
    lines.append("")

    # 来源
    lines.append("## 三、信息源 TOP 10")
    lines.append("")
    lines.append("| 排名 | 来源 | 报道数 |")
    lines.append("|------|------|--------|")
    for i, (src, cnt) in enumerate(top_sources, 1):
        lines.append(f"| {i} | {src} | {cnt} |")
    lines.append("")

    # 融资
    lines.append("## 四、资本动向")
    lines.append("")
    lines.append(f"- 本月涉及融资/估值相关事件：**{funding_total}** 条")
    lines.append(f"- 平均每 {round(total_days / max(funding_total, 1), 1)} 天有 1 起融资动态")
    lines.append("")

    # TOP 10 事件
    lines.append("## 五、本月 TOP 10 事件")
    lines.append("")
    for i, it in enumerate(top_items, 1):
        sec_label = {"industry": "行业", "interview": "访谈", "marketing": "营销"}.get(it["section"], "其他")
        title = it["title"]
        url = it["url"]
        date = it["date"]
        lines.append(f"{i}. [{title}]({url}) — {date} · {sec_label}")
    lines.append("")

    # 完整事件流（按日期倒序）
    lines.append("## 六、完整事件流")
    lines.append("")
    by_date = defaultdict(list)
    for it in all_items:
        by_date[it["date"]].append(it)
    for d in sorted(by_date.keys(), reverse=True):
        lines.append(f"### {d}（{len(by_date[d])} 条）")
        lines.append("")
        for it in by_date[d][:20]:  # 每天最多列 20 条
            sec_label = {"industry": "🏭", "interview": "🎤", "marketing": "📣"}.get(it["section"], "•")
            lines.append(f"- {sec_label} [{it['title']}]({it['url']})")
        lines.append("")

    lines.append("---")
    lines.append("")
    lines.append(f"*本报告由 `embodied-ai-daily` Skill 自动生成 | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*")

    return "\n".join(lines)


def last_day_of_month(month: str) -> str:
    """返回 YYYY-MM 月份最后一天（YYYY-MM-DD）"""
    import calendar
    y, m = month.split("-")
    last = calendar.monthrange(int(y), int(m))[1]
    return f"{int(m):02d}-{last:02d}"


# ---------------------- 主流程 ----------------------

def main():
    ap = argparse.ArgumentParser(description="具身智能日报 - 归档与月度报告")
    ap.add_argument("--from", dest="from_date", default="", help="起始日期 YYYY-MM-DD")
    ap.add_argument("--to", dest="to_date", default="", help="结束日期 YYYY-MM-DD")
    ap.add_argument("--month", default=datetime.now().strftime("%Y-%m"), help="生成哪个月的报告")
    ap.add_argument("--report-only", action="store_true", help="只生成报告，不重新归档")
    ap.add_argument("--list-months", action="store_true", help="列出已归档的所有月份")
    args = ap.parse_args()

    if args.list_months:
        if not ARCHIVE_DIR.exists():
            print("暂无归档")
            return
        for d in sorted(ARCHIVE_DIR.iterdir()):
            if d.is_dir():
                n = len(list(d.glob("*.md")))
                print(f"  {d.name} ({n} 份日报)")
        return

    # Step 1: 归档
    if not args.report_only:
        dailies = list_dailies(args.from_date or None, args.to_date or None)
        print(f"[归档] 共 {len(dailies)} 份日报", file=sys.stderr)
        for d in dailies:
            month = d.name[len("embodied_ai_"):][:7]  # 2026-06-30.md -> 2026-06
            target = archive_daily(d, ARCHIVE_DIR / month)
            print(f"  → {target}", file=sys.stderr)

    # Step 2: 生成月度报告
    target_month_dir = ARCHIVE_DIR / args.month
    if not target_month_dir.exists():
        print(f"错误：未找到 {args.month} 的归档目录 {target_month_dir}", file=sys.stderr)
        sys.exit(1)

    month_files = sorted(target_month_dir.glob("embodied_ai_*.md"))
    print(f"\n[报告] 解析 {len(month_files)} 份日报", file=sys.stderr)
    parsed = [parse_daily(f) for f in month_files]

    report = build_month_report(args.month, parsed)
    report_path = target_month_dir / f"monthly_report_{args.month}.md"
    report_path.write_text(report, encoding="utf-8")
    print(f"\n✓ 月度报告已生成: {report_path}", file=sys.stderr)
    print(f"  统计 {len(parsed)} 天 / {sum(d['counts']['total'] for d in parsed)} 条", file=sys.stderr)


if __name__ == "__main__":
    main()
