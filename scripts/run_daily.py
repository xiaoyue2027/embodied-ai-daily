#!/usr/bin/env python3
"""
具身智能日报 - 主调度脚本

工作流：
  Step 1: WebSearch 抓取主流媒体（36Kr/量子位/智东西/财新/虎嗅 等）
  Step 2: Playwright 抓取 KOL/播客/公众号/即刻（依赖 fetch_kol.py）
  Step 3: 按三板块（行业信息 / 高层访谈 / 品牌营销）整理
  Step 4: 渲染最终 Markdown 日报 + 写文件

输出：
  /workspace/daily_reports/embodied_ai_YYYY-MM-DD.md

用法：
  python3.11 scripts/run_daily.py                       # 当日日报
  python3.11 scripts/run_daily.py --date 2026-06-30    # 指定日期
  python3.11 scripts/run_daily.py --no-browser         # 跳过 Playwright（仅 WebSearch）
  python3.11 scripts/run_daily.py --no-websearch       # 仅 Playwright
  python3.11 scripts/run_daily.py --dry-run            # 不写文件，只打印
"""

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union


# ---------------------- 配置 ----------------------

OUTPUT_DIR = Path(os.environ.get("DAILY_REPORTS_DIR", "/workspace/daily_reports"))
SCRIPT_DIR = Path(__file__).parent

# 主流媒体 WebSearch 关键词组合
WEBSEARCH_QUERIES = [
    ("industry", "具身智能 行业 最新"),
    ("industry", "人形机器人 量产 工厂"),
    ("industry", "具身大模型 VLA 融资"),
    ("interview", "具身智能 CEO 创始人 采访"),
    ("interview", "机器人 创始人 观点 2026"),
    ("marketing", "人形机器人 发布会 联名"),
    ("marketing", "具身智能 品牌 营销"),
]

# 板块识别关键词
INDUSTRY_KEYWORDS = ["融资", "估值", "量产", "工厂", "发布", "技术", "突破", "政策", "专利", "订单", "出货", "营收", "战略", "合作", "投资", "A轮", "B轮", "C轮", "国资委", "工信部", "亿元", "模型", "架构", "应用", "落地", "实景", "实训", "部署"]
INTERVIEW_KEYWORDS = ["专访", "对话", "采访", "创始人", "CEO", "CTO", "首席科学家", "观点", "表示", "认为", "指出", "预测", "判断", "未来", "达沃斯", "MWC", "论坛", "大会", "演讲", "主题", "拆解", "畅谈", "详解"]
MARKETING_KEYWORDS = ["发布会", "联名", "跨界", "KOL", "营销", "广告", "代言", "展", "演示", "开箱", "上手", "评测", "测评", "横评", "视频", "直播", "降价", "调价", "售价", "起售", "现货", "首发", "首销", "限量", "预热", "打榜", "破圈", "出圈", "刷屏", "跑分", "拆解", "对比", "上市", "众筹", "发布", "体验店", "门店", "渠道", "销量", "售罄", "爆款", "现象级"]


# ---------------------- 工具函数 ----------------------

def now_str() -> str:
    """北京时间（UTC+8），避免 GitHub Actions runner（UTC）显示早 8 小时"""
    from datetime import timedelta, timezone
    beijing = datetime.now(timezone(timedelta(hours=8)))
    return beijing.strftime("%Y-%m-%d %H:%M:%S")


def ensure_dir(p: Path) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)


def is_in_sandbox() -> bool:
    """检测当前是否在受限沙盒（无法启动 Chromium）"""
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            b = p.chromium.launch()
            b.close()
            return False
    except Exception:
        return True


def classify_section(text: str) -> str:
    """根据文本内容判断属于哪个板块"""
    if not text:
        return "industry"
    score = {
        "industry": sum(1 for k in INDUSTRY_KEYWORDS if k in text),
        "interview": sum(1 for k in INTERVIEW_KEYWORDS if k in text),
        "marketing": sum(1 for k in MARKETING_KEYWORDS if k in text),
    }
    return max(score, key=score.get) if max(score.values()) > 0 else "industry"


def importance_score(text: str) -> int:
    """根据关键词粗略打分（满分 100，≥30 才入候选）"""
    score = 0
    high_value = [
        ("融资", 20), ("估值", 20), ("量产", 20), ("工厂落地", 20),
        ("创始人", 15), ("CEO", 15), ("专访", 15), ("对话", 15),
        ("政策", 15), ("国资委", 20), ("工信部", 20),
        ("亿元", 15), ("发布", 10), ("突破", 15), ("战略", 10), ("合作", 10),
        ("A轮", 15), ("B轮", 15), ("C轮", 15),
        ("首发", 10), ("独家", 15), ("里程碑", 15),
        ("降价", 12), ("调价", 12), ("营销", 10), ("联名", 12),
        ("VLA", 10), ("VLOA", 12), ("基础模型", 12), ("大模型", 10),
    ]
    for kw, pts in high_value:
        if kw in text:
            score += pts
    return min(score, 100)


# ---------------------- Step 1: WebSearch（占位） ----------------------
# 实际执行由主会话（LLM）调用 WebSearch 工具完成，本脚本仅负责接收/处理结果
# 如果有离线 JSON 输入（--input），直接加载

def load_websearch_results(input_path: Optional[str]) -> List[Dict[str, Any]]:
    """从 JSON 文件加载 WebSearch 结果"""
    if not input_path or not Path(input_path).exists():
        return []
    with open(input_path, "r", encoding="utf-8") as f:
        return json.load(f)


# ---------------------- Step 2: Playwright KOL 抓取 ----------------------

def run_fetch_kol(days: int = 1, show: bool = False) -> Dict[str, Any]:
    """调用 fetch_kol.py 抓取 KOL/播客/公众号/即刻"""
    output = "/tmp/kol_today.json"
    cmd = [
        "python3.11", str(SCRIPT_DIR / "fetch_kol.py"),
        "--days", str(days),
        "--output", output,
    ]
    if show:
        cmd.append("--show")

    print(f"[Step 2] 抓取 KOL/播客/公众号/即刻 ...", file=sys.stderr)
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
        if result.returncode != 0:
            print(f"  ⚠️ fetch_kol 退出码 {result.returncode}", file=sys.stderr)
            print(f"  stderr: {result.stderr[:200]}", file=sys.stderr)
            return {}
        if Path(output).exists():
            with open(output, "r", encoding="utf-8") as f:
                return json.load(f)
    except subprocess.TimeoutExpired:
        print("  ⚠️ fetch_kol 超时（180s）", file=sys.stderr)
    except Exception as e:
        print(f"  ⚠️ fetch_kol 异常: {e}", file=sys.stderr)
    return {}


# ---------------------- Step 3: 三板块分类整理 ----------------------

def organize_sections(items: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    """把原始 items 分到三个板块，按重要性降序"""
    sections = {"industry": [], "interview": [], "marketing": []}
    for it in items:
        text = json.dumps(it, ensure_ascii=False)
        section = it.get("section") or classify_section(text)
        it["section"] = section
        it["importance"] = importance_score(text)
        if it["importance"] >= 30:  # 阈值可调
            sections[section].append(it)
    for k in sections:
        sections[k].sort(key=lambda x: x.get("importance", 0), reverse=True)
    return sections


# ---------------------- Step 4: 渲染 Markdown ----------------------

SECTION_NAMES = {
    "industry": "一、行业信息",
    "interview": "二、高层访谈",
    "marketing": "三、品牌市场营销动作",
}


def render_markdown(
    date_str: str,
    weekday: str,
    sections: Dict[str, List[Dict[str, Any]]],
    kol_data: Optional[Dict[str, Any]] = None,
    max_items_per_section: Optional[int] = None,
) -> str:
    """
    max_items_per_section: 每个板块最多放多少条（None=不限制，int=限制）
    """
    if max_items_per_section is not None:
        sections = {k: v[:max_items_per_section] for k, v in sections.items()}
    total = sum(len(v) for v in sections.values())
    lines = [
        f"# 具身智能日报 · {date_str}（周{weekday}）",
        "",
        f"> 今日要闻共 **{total}** 条 | 行业信息 **{len(sections['industry'])}** 条 | "
        f"高层访谈 **{len(sections['interview'])}** 条 | 品牌营销 **{len(sections['marketing'])}** 条",
        f"> 生成时间：{now_str()} | 工具：`embodied-ai-daily` Skill v1.0",
        "",
        "---",
        "",
    ]

    for key, header in SECTION_NAMES.items():
        items = sections[key]
        lines.append(f"## {header}")
        lines.append("")
        if not items:
            lines.append("_（今日无符合条件的内容）_")
            lines.append("")
            continue
        for i, it in enumerate(items, 1):
            title = it.get("title", "（无标题）")
            url = it.get("url", "")
            # 重要性用 A 字符（避免 PDF 字体问题）
            stars = "A" * max(1, min(5, it.get("importance", 0) // 20 + 1))
            # 多重热度标签：标题关键词 + Tavily score
            tags = []
            full_text = (title + " " + it.get("summary", "")).lower()
            if any(k in full_text for k in ["10万+", "10万阅读", "十万+", "爆款"]):
                tags.append("爆款")
            if any(k in full_text for k in ["5万+", "5万阅读", "5w+", "五万"]):
                tags.append("热文")
            # Tavily score（相关性分数）反映热度
            heat_tag_from_score = it.get("heat_tag", "").strip("[]")
            if heat_tag_from_score and heat_tag_from_score not in tags:
                tags.append(heat_tag_from_score)
            hot_tag = " [" + "][".join(tags) + "]" if tags else ""
            lines.append(f"### {i}. [{title}]({url})（重要性：{stars}{hot_tag}）")
            lines.append("")
            if it.get("source"):
                lines.append(f"- **来源**：{it['source']}")
            if it.get("author") or it.get("show") or it.get("topic"):
                meta = []
                if it.get("author"):
                    meta.append(f"作者：{it['author']}")
                if it.get("show"):
                    meta.append(f"节目：{it['show']}")
                if it.get("topic"):
                    meta.append(f"话题：{it['topic']}")
                lines.append(f"- **归属**：{' / '.join(meta)}")
            if it.get("date"):
                lines.append(f"- **日期**：{it['date']}")
            if it.get("summary"):
                lines.append(f"- **摘要**：{it['summary']}")
            lines.append("")

    # 编辑视角
    lines.append("## 📌 编辑视角")
    lines.append("")
    top_industry = sections["industry"][:3]
    if top_industry:
        lines.append("**今日 TOP 3 行业信号**")
        for i, it in enumerate(top_industry, 1):
            lines.append(f"{i}. {it.get('title', '')}")
        lines.append("")

    # KOL 数据补充
    if kol_data and kol_data.get("total", 0) > 0:
        lines.append("---")
        lines.append("")
        lines.append("## 附：KOL / 播客 / 公众号 / 即刻 当日抓取")
        lines.append("")
        for ch, items in kol_data.get("results", {}).items():
            if not items:
                continue
            ch_name = {"wechat": "微信公众号（搜狗）", "xiaoyuzhou": "小宇宙播客", "jike": "即刻话题圈"}.get(ch, ch)
            lines.append(f"### {ch_name}（{len(items)} 条）")
            lines.append("")
            for it in items[:10]:
                title = it.get("title", "")
                url = it.get("url", "")
                extra = []
                if it.get("author"):
                    extra.append(it["author"])
                if it.get("show"):
                    extra.append(it["show"])
                if it.get("topic"):
                    extra.append(it["topic"])
                extra_str = f" — {', '.join(extra)}" if extra else ""
                lines.append(f"- [{title}]({url}){extra_str}")
            lines.append("")

    lines.append("---")
    lines.append("")
    lines.append(f"*本报由 `embodied-ai-daily` Skill 自动生成 | {now_str()}*")
    return "\n".join(lines)


# ---------------------- 主流程 ----------------------

def main():
    ap = argparse.ArgumentParser(description="具身智能日报 - 主调度")
    from datetime import timedelta, timezone
    beijing_today = datetime.now(timezone(timedelta(hours=8))).strftime("%Y-%m-%d")
    ap.add_argument("--date", default=beijing_today, help="日报日期 (YYYY-MM-DD)")
    ap.add_argument("--input", default="", help="WebSearch 结果 JSON 路径（可选）")
    ap.add_argument("--no-browser", action="store_true", help="跳过 Playwright 抓取")
    ap.add_argument("--no-websearch", action="store_true", help="跳过 WebSearch（仅 Playwright）")
    ap.add_argument("--dry-run", action="store_true", help="不写文件，只打印到 stdout")
    ap.add_argument("--days", type=int, default=1, help="时间窗（天）")
    ap.add_argument("--show-browser", action="store_true", help="显示浏览器（调试）")
    ap.add_argument("--pdf", action="store_true", help="同步生成 PDF 版本")
    ap.add_argument("--push-pdf", action="store_true", help="推送时同时发送 PDF 文件（仅 wechat_work）")
    ap.add_argument("--push", choices=["feishu", "dingtalk", "email", "wechat_mp", "wechat_work"], default="", help="推送渠道")
    ap.add_argument("--webhook", default="", help="飞书/钉钉/企业微信 Webhook URL")
    ap.add_argument("--smtp-host", default="", help="SMTP 主机")
    ap.add_argument("--smtp-port", type=int, default=465, help="SMTP 端口")
    ap.add_argument("--smtp-user", default="", help="SMTP 用户名")
    ap.add_argument("--smtp-password", default="", help="SMTP 密码")
    ap.add_argument("--to", default="", help="收件人（逗号分隔）")
    ap.add_argument("--appid", default="", help="公众号 AppID（wechat_mp 用）")
    ap.add_argument("--appsecret", default="", help="公众号 AppSecret")
    ap.add_argument("--openids", default="", help="接收者 openid（逗号分隔）")
    ap.add_argument("--template-id", default="", help="微信模板消息 ID（可选）")
    args = ap.parse_args()

    # 解析日期
    try:
        dt = datetime.strptime(args.date, "%Y-%m-%d")
        weekday_cn = ["一", "二", "三", "四", "五", "六", "日"][dt.weekday()]
    except ValueError:
        print(f"日期格式错误: {args.date}", file=sys.stderr)
        sys.exit(1)

    print(f"\n========== 具身智能日报 · {args.date} ==========\n", file=sys.stderr)

    # Step 1: WebSearch（占位 - 由主会话注入或从 input 加载）
    websearch_items = []
    if not args.no_websearch:
        if args.input:
            websearch_items = load_websearch_results(args.input)
            print(f"[Step 1] 从 {args.input} 加载 {len(websearch_items)} 条 WebSearch 结果", file=sys.stderr)
        else:
            print(f"[Step 1] ⚠️ 未提供 --input，跳过 WebSearch。建议在 LLM 会话中调用 WebSearch 后注入。", file=sys.stderr)

    # Step 2: Playwright 抓取
    kol_data = {}
    if not args.no_browser:
        if is_in_sandbox():
            print(f"[Step 2] ⚠️ 当前环境无法启动 Chromium（沙盒限制），跳过 Playwright", file=sys.stderr)
        else:
            kol_data = run_fetch_kol(days=args.days, show=args.show_browser)
            print(f"  ✓ 抓取 {kol_data.get('total', 0)} 条", file=sys.stderr)
    else:
        print(f"[Step 2] 已禁用 Playwright", file=sys.stderr)

    # 把 KOL 结果合并到 items
    all_items = list(websearch_items)
    for ch_items in kol_data.get("results", {}).values():
        all_items.extend(ch_items)

    # 去重：三级策略
    #   1. URL 完全相同 → 跳过
    #   2. 核心公司 + 关键数字（如"智平方"+"200亿"）相同 → 视为同一新闻
    #   3. 标题前 15 字相同 → 视为同一新闻
    import re
    seen_urls = set()
    seen_signatures = set()
    seen_title_keys = set()
    deduped_items = []

    # 核心公司/品牌词（含 ETF 等金融产品）
    KEY_ENTITIES = [
        "智平方", "自变量", "跨维智能", "宇树", "智元", "银河通用", "傅利叶",
        "优必选", "星动纪元", "逐际动力", "特斯联", "Figure", "Optimus",
        "易方达", "汇添富", "华夏", "国证", "机器人ETF", "机器人指数", "机器人产业",
        "融资", "估值", "具身", "B轮", "C轮", "A轮",
    ]
    # 关键金额/数字模式
    KEY_NUMBERS = re.compile(r"(\d+)\s*[亿万]")

    for it in all_items:
        url = it.get("url", "")
        title = (it.get("title", "") or "").strip()
        summary = (it.get("summary", "") or "").strip()

        if url and url in seen_urls:
            continue

        # 归一化标题
        norm_title = re.sub(r"[^\w\u4e00-\u9fff]+", "", title)[:15]

        # 提取"公司+数字"签名
        entities_in_title = [e for e in KEY_ENTITIES if e in title or e in summary[:200]]
        numbers_in_title = KEY_NUMBERS.findall(title + " " + summary[:100])
        signature = ""
        if entities_in_title and numbers_in_title:
            # 用最大数字（最可能是核心数字）+ 第一个公司
            biggest_num = max(int(n) for n in numbers_in_title)
            signature = f"{entities_in_title[0]}_{biggest_num}"

        if signature and signature in seen_signatures:
            continue
        if norm_title and norm_title in seen_title_keys:
            continue

        if url:
            seen_urls.add(url)
        if signature:
            seen_signatures.add(signature)
        if norm_title:
            seen_title_keys.add(norm_title)
        deduped_items.append(it)

    dup_count = len(all_items) - len(deduped_items)
    if dup_count > 0:
        print(f"[去重] 移除 {dup_count} 条重复新闻（URL + 公司+数字签名 + 标题）", file=sys.stderr)
    all_items = deduped_items

    # Step 3: 分类
    sections = organize_sections(all_items)
    print(f"\n[Step 3] 分类完成：行业 {len(sections['industry'])}, 访谈 {len(sections['interview'])}, 营销 {len(sections['marketing'])}\n", file=sys.stderr)

    # Step 4: 渲染（完整版，用于 PDF + 文件存档）
    md = render_markdown(args.date, weekday_cn, sections, kol_data if kol_data else None)

    # 给企业微信专门生成精简版（每个板块最多 N 条，避免超 4096 字节）
    md_compact = None
    n_compact = 0
    if args.push == "wechat_work":
        # 简化后单条约 250 字节，4096 字节限制下，3 板块共 12 条较稳
        # 但简化后还有"摘要"等行，所以保守点 5 条/板块
        from push import _simplify_for_wechat
        for n in (5, 4, 3, 2):
            candidate = render_markdown(args.date, weekday_cn, sections, kol_data if kol_data else None, max_items_per_section=n)
            # 立即简化（run_daily 负责简化，push.py 不再二次简化）
            candidate_simplified = _simplify_for_wechat(candidate)
            if len(candidate_simplified.encode("utf-8")) < 3500:  # 留 ~500 字节给标题
                md_compact = candidate_simplified
                n_compact = n
                break
        if md_compact is None:
            candidate = render_markdown(args.date, weekday_cn, sections, kol_data if kol_data else None, max_items_per_section=2)
            md_compact = _simplify_for_wechat(candidate)
            n_compact = 2
        compact_bytes = len(md_compact.encode('utf-8'))
        print(f"  → 企业微信精简版: {compact_bytes} 字节（每板块 ≤ {n_compact} 条）", file=sys.stderr)

    # 输出
    if args.dry_run:
        print(md)
    else:
        out_path = OUTPUT_DIR / f"embodied_ai_{args.date}.md"
        ensure_dir(out_path)
        out_path.write_text(md, encoding="utf-8")
        print(f"✓ 日报已保存: {out_path}", file=sys.stderr)
        print(f"  共 {sum(len(v) for v in sections.values())} 条", file=sys.stderr)

        # 同步写一份 latest 软链（如果支持）
        latest = OUTPUT_DIR / "latest.md"
        try:
            if latest.exists() or latest.is_symlink():
                latest.unlink()
            latest.symlink_to(out_path.name)
        except Exception:
            pass

    # Step 5: PDF 导出（可选）
    pdf_path = None
    if args.pdf:
        try:
            from export_pdf import md_to_pdf
            pdf_path = out_path.with_suffix(".pdf")
            result = md_to_pdf(str(out_path), str(pdf_path), title=f"具身智能日报 · {args.date}")
            if result.get("ok"):
                print(f"✓ PDF 已生成: {pdf_path}（{result.get('size_kb')} KB）", file=sys.stderr)
            else:
                print(f"⚠️ PDF 生成失败: {result.get('error')}", file=sys.stderr)
                pdf_path = None
        except Exception as e:
            print(f"⚠️ PDF 模块异常: {e}", file=sys.stderr)
            pdf_path = None

    # Step 6: 推送（可选）
    if args.push:
        try:
            from push import push_markdown, push_file
            target = _resolve_push_target(args)
            if not target:
                print("⚠️ 推送跳过：未配置 webhook/邮箱", file=sys.stderr)
            else:
                # 推 markdown 摘要（企业微信用精简版，其他渠道用完整版）
                if args.push == "wechat_work" and md_compact:
                    # 精简版 → 告诉 push.py 不要再 simplify
                    from push import push_wechat_work as _push_ww
                    result = _push_ww(target, md_compact, pre_simplified=True)
                    label = f"精简版 (≤{n_compact}/板块)"
                else:
                    result = push_markdown(args.push, target, md)
                    label = "完整版"
                if result.get("ok"):
                    print(f"✓ 已推送到 {args.push} (markdown, {label})", file=sys.stderr)
                else:
                    print(f"⚠️ 推送 markdown 失败: {result.get('error', 'unknown')}", file=sys.stderr)

                # 如果是 wechat_work + PDF 存在 + 用户要推 PDF，再推文件
                if args.push_pdf and pdf_path and args.push == "wechat_work":
                    file_result = push_file("wechat_work", target, str(pdf_path), f"具身智能日报-{args.date}.pdf")
                    if file_result.get("ok"):
                        print(f"✓ 已推送 PDF 到 {args.push}", file=sys.stderr)
                    else:
                        print(f"⚠️ 推送 PDF 失败: {file_result.get('error', file_result)}", file=sys.stderr)
        except Exception as e:
            print(f"⚠️ 推送异常: {e}", file=sys.stderr)


def _resolve_push_target(args) -> Optional[Union[str, Dict]]:
    """根据命令行参数和环境变量解析推送目标"""
    if args.push in ("feishu", "dingtalk", "wechat_work"):
        webhook = args.webhook or os.environ.get(f"{args.push.upper()}_WEBHOOK", "")
        if args.push == "wechat_work":
            webhook = webhook or os.environ.get("WECHAT_WORK_WEBHOOK", "")
        return webhook if webhook else None
    elif args.push == "email":
        cfg = {
            "to_addr": [x.strip() for x in (args.to or os.environ.get("EMAIL_TO", "")).split(",") if x.strip()],
            "smtp_host": args.smtp_host or os.environ.get("SMTP_HOST", ""),
            "smtp_port": int(args.smtp_port or os.environ.get("SMTP_PORT", "465")),
            "user": args.smtp_user or os.environ.get("SMTP_USER", ""),
            "password": args.smtp_password or os.environ.get("SMTP_PASSWORD", ""),
        }
        if not all([cfg["to_addr"], cfg["smtp_host"], cfg["user"], cfg["password"]]):
            return None
        return cfg
    elif args.push == "wechat_mp":
        cfg = {
            "appid": args.appid or os.environ.get("WECHAT_APPID", ""),
            "appsecret": args.appsecret or os.environ.get("WECHAT_APPSECRET", ""),
            "openids": [x.strip() for x in (args.openids or os.environ.get("WECHAT_OPENIDS", "")).split(",") if x.strip()],
        }
        if args.template_id or os.environ.get("WECHAT_TEMPLATE_ID"):
            cfg["template_id"] = args.template_id or os.environ.get("WECHAT_TEMPLATE_ID")
        if not all([cfg["appid"], cfg["appsecret"], cfg["openids"]]):
            return None
        return cfg
    return None


if __name__ == "__main__":
    main()
