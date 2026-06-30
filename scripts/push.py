#!/usr/bin/env python3
"""
日报推送模块 - 支持飞书 / 钉钉 / 邮件 / 微信服务号 / 企业微信

用法（被 run_daily.py 调用）：
  from push import push_markdown
  push_markdown(md_text, channel="feishu", target=WEBHOOK_URL)
  push_markdown(md_text, channel="dingtalk", target=WEBHOOK_URL)
  push_markdown(md_text, channel="email", target=("to@x.com", smtp_cfg))
  push_markdown(md_text, channel="wechat_mp", target={appid, appsecret, openids, ...})
  push_markdown(md_text, channel="wechat_work", target=WEBHOOK_URL)

也支持命令行：
  python3.11 push.py --channel feishu --webhook $FS --file /path/to/daily.md
"""

import argparse
import json
import os
import re
import smtplib
import sys
import urllib.request
import urllib.error
import urllib.parse
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from typing import Any, Dict, Optional, Tuple, Union


# ---------------------- 通用工具 ----------------------

def truncate_for_card(text: str, max_len: int = 4000, by_bytes: bool = False) -> str:
    """
    飞书/钉钉卡片有长度限制。
    by_bytes=False（默认）按字符截断（用于飞书/钉钉，限制按字符）
    by_bytes=True 按 UTF-8 字节截断（用于企业微信，限制 4096 字节，中文 1 字 = 3 字节）
    """
    if by_bytes:
        encoded = text.encode("utf-8")
        if len(encoded) <= max_len:
            return text
        # 按字节截断，但要避免切断多字节字符
        truncated = encoded[: max_len - 50]
        return truncated.decode("utf-8", errors="ignore") + "\n\n...(内容过长，已截断)"
    else:
        if len(text) <= max_len:
            return text
        return text[: max_len - 50] + "\n\n...(内容过长，已截断)"


def extract_title(md: str) -> str:
    """从 Markdown 提取第一行 # 标题"""
    for line in md.split("\n"):
        if line.startswith("# "):
            return line[2:].strip()
    return "日报"


def extract_summary(md: str) -> str:
    """提取摘要（> 开头那行）"""
    for line in md.split("\n"):
        if line.strip().startswith(">"):
            return line.strip().lstrip("> ").strip()
    return ""


# ---------------------- 飞书 ----------------------

def push_feishu(webhook: str, markdown: str, title: Optional[str] = None) -> Dict[str, Any]:
    """
    飞书机器人 Webhook - 富文本消息
    https://open.feishu.cn/document/client-docs/bot-v3/add-custom-bot
    """
    title = title or extract_title(markdown)
    summary = extract_summary(markdown)
    body = truncate_for_card(markdown, 3500)

    # 飞书 interactive 卡片
    payload = {
        "msg_type": "interactive",
        "card": {
            "header": {
                "title": {"tag": "plain_text", "content": title[:60]},
                "template": "blue",
            },
            "elements": [
                {
                    "tag": "div",
                    "text": {"tag": "lark_md", "content": body},
                },
                {"tag": "hr"},
                {
                    "tag": "note",
                    "elements": [
                        {"tag": "plain_text", "content": "📰 由 embodied-ai-daily Skill 自动生成"}
                    ],
                },
            ],
        },
    }
    return _post_json(webhook, payload)


def push_feishu_text(webhook: str, markdown: str) -> Dict[str, Any]:
    """飞书纯文本消息（更轻量，无卡片）"""
    payload = {
        "msg_type": "text",
        "content": {"text": truncate_for_card(markdown, 4000)},
    }
    return _post_json(webhook, payload)


# ---------------------- 钉钉 ----------------------

def push_dingtalk(webhook: str, markdown: str, title: Optional[str] = None, at_mobiles: Optional[list] = None) -> Dict[str, Any]:
    """
    钉钉自定义机器人 - Markdown 消息
    https://open.dingtalk.com/document/orgapp/custom-robot-access
    """
    title = title or extract_title(markdown)
    payload = {
        "msgtype": "markdown",
        "markdown": {
            "title": title[:60],
            "text": truncate_for_card(markdown, 3500),
        },
        "at": {"atMobiles": at_mobiles or [], "isAtAll": False},
    }
    return _post_json(webhook, payload)


# ---------------------- 邮件 ----------------------

def push_email(
    md_text: str,
    to_addr: Union[str, list],
    smtp_host: str,
    smtp_port: int,
    user: str,
    password: str,
    from_addr: Optional[str] = None,
    subject_prefix: str = "【具身智能日报】",
) -> Dict[str, Any]:
    """
    通过 SMTP 发送日报邮件（支持 QQ/163/Gmail/企业邮箱）
    """
    from_addr = from_addr or user
    if isinstance(to_addr, str):
        to_addr = [to_addr]

    title = extract_title(md_text)
    subject = f"{subject_prefix} {title}"
    html = _md_to_simple_html(md_text)

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = from_addr
    msg["To"] = ", ".join(to_addr)
    msg.attach(MIMEText(md_text, "plain", "utf-8"))
    msg.attach(MIMEText(html, "html", "utf-8"))

    try:
        if smtp_port == 465:
            server = smtplib.SMTP_SSL(smtp_host, smtp_port, timeout=30)
        else:
            server = smtplib.SMTP(smtp_host, smtp_port, timeout=30)
            server.starttls()
        server.login(user, password)
        server.sendmail(from_addr, to_addr, msg.as_string())
        server.quit()
        return {"ok": True, "channel": "email", "to": to_addr}
    except Exception as e:
        return {"ok": False, "channel": "email", "error": str(e)}


def _md_to_simple_html(md: str) -> str:
    """极简 Markdown -> HTML（邮件友好）"""
    lines = md.split("\n")
    html = ['<html><body style="font-family:-apple-system,Segoe UI,Helvetica,Arial,sans-serif;line-height:1.6;color:#333;max-width:800px;margin:20px auto;padding:0 20px;">']
    in_code = False
    for line in lines:
        if line.startswith("# "):
            html.append(f'<h1 style="color:#1a1a1a;border-bottom:2px solid #1a73e8;padding-bottom:8px;">{esc(line[2:])}</h1>')
        elif line.startswith("## "):
            html.append(f'<h2 style="color:#1a73e8;margin-top:32px;">{esc(line[3:])}</h2>')
        elif line.startswith("### "):
            html.append(f'<h3 style="color:#333;margin-top:20px;">{esc(line[4:])}</h3>')
        elif line.startswith("> "):
            html.append(f'<blockquote style="border-left:4px solid #1a73e8;padding:8px 16px;color:#666;background:#f5f9ff;margin:12px 0;">{esc(line[2:])}</blockquote>')
        elif line.startswith("- "):
            html.append(f'<li style="margin:4px 0;">{esc(line[2:])}</li>')
        elif re.match(r"^\d+\.\s", line):
            text = re.sub(r"^\d+\.\s", "", line)
            html.append(f'<li style="margin:4px 0;">{esc(text)}</li>')
        elif line.strip() == "---":
            html.append('<hr style="border:none;border-top:1px solid #eee;margin:24px 0;">')
        elif line.strip().startswith("```"):
            if not in_code:
                html.append('<pre style="background:#f6f8fa;padding:12px;border-radius:6px;overflow-x:auto;">')
                in_code = True
            else:
                html.append("</pre>")
                in_code = False
        elif in_code:
            html.append(esc(line))
        elif line.strip():
            # 处理内联链接 [text](url)
            line2 = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2" style="color:#1a73e8;">\1</a>', line)
            line2 = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", line2)
            html.append(f'<p style="margin:8px 0;">{line2}</p>')
    html.append("</body></html>")
    return "\n".join(html)


def esc(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


# ---------------------- 微信服务号 ----------------------
# 微信对个人订阅号/服务号消息推送有严格限制，企业级通常采用以下三种方案：
#   1. 微信服务号模板消息（需认证服务号 + access_token）
#   2. 企业微信群机器人（与飞书/钉钉类似，webhook 推送）
#   3. 公众号客服消息（48 小时内互动过的用户）
# 这里同时实现 1+2，模板消息可发给任意关注用户，企业微信最稳定

# 微信 API 缓存（access_token 2 小时过期）
_TOKEN_CACHE: Dict[str, Any] = {}


def _get_wechat_access_token(appid: str, appsecret: str) -> Optional[str]:
    """获取/缓存微信 access_token"""
    import time
    cache_key = f"{appid}::{appsecret}"
    now = time.time()
    cached = _TOKEN_CACHE.get(cache_key)
    if cached and cached["expire_at"] > now + 60:
        return cached["token"]

    url = "https://api.weixin.qq.com/cgi-bin/token"
    params = {"grant_type": "client_credential", "appid": appid, "secret": appsecret}
    full_url = f"{url}?{urllib.parse.urlencode(params)}"
    try:
        with urllib.request.urlopen(full_url, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        if "access_token" in data:
            _TOKEN_CACHE[cache_key] = {
                "token": data["access_token"],
                "expire_at": now + data.get("expires_in", 7200),
            }
            return data["access_token"]
        return None
    except Exception:
        return None


def _md_to_wechat_text(md: str, max_len: int = 1800) -> str:
    """把 Markdown 转为微信文本（保留链接 / 标题 / 列表，去掉格式）"""
    lines = []
    for line in md.split("\n"):
        s = line.rstrip()
        if not s:
            lines.append("")
            continue
        if s.startswith("# "):
            lines.append(f"📰 {s[2:].strip()}")
            continue
        if s.startswith("## "):
            lines.append(f"\n【{s[3:].strip()}】")
            continue
        if s.startswith("### "):
            lines.append(f"\n▪ {s[4:].strip()}")
            continue
        if s.startswith("> "):
            lines.append(f"  {s[2:].strip()}")
            continue
        # 保留内联链接 [text](url) → text: url
        s2 = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", lambda m: f"{m.group(1)}: {m.group(2)}", s)
        # 加粗 **text** → text
        s2 = re.sub(r"\*\*([^*]+)\*\*", r"\1", s2)
        # 去掉 [TOC] 等
        s2 = s2.replace("---", "——————")
        lines.append(s2)

    text = "\n".join(lines)
    if len(text) > max_len:
        text = text[: max_len - 30] + "\n\n…(内容过长，查看完整版请打开链接)"
    return text


def push_wechat_mp(
    appid: str,
    appsecret: str,
    openids: Union[str, list],
    md_text: str,
    template_id: Optional[str] = None,
    url: Optional[str] = None,
) -> Dict[str, Any]:
    """
    微信服务号模板消息推送（需认证服务号 + 已添加模板）
    https://developers.weixin.qq.com/doc/offiaccount/Message_Management/Template_Message_Interface.html

    参数：
      appid, appsecret: 公众号凭证
      openids: 接收者 openid（单个或列表）
      template_id: 模板 ID（可选，默认使用"通用日报"模板；未设置时会先用客服消息兜底）
      url: 点击消息跳转的 URL（默认跳到日报 PDF / 链接）
    """
    if isinstance(openids, str):
        openids = [openids]

    token = _get_wechat_access_token(appid, appsecret)
    if not token:
        return {"ok": False, "error": "获取 access_token 失败，请检查 appid/appsecret"}

    title = extract_title(md_text)
    summary = extract_summary(md_text)
    content = _md_to_wechat_text(md_text)

    # 优先用模板消息
    if template_id:
        results = []
        api_url = "https://api.weixin.qq.com/cgi-bin/message/template/send"
        for oid in openids:
            payload = {
                "touser": oid,
                "template_id": template_id,
                "url": url or "https://example.com/daily",
                "data": {
                    "title": {"value": title[:60], "color": "#1a73e8"},
                    "summary": {"value": summary[:100] or "今日要闻已就绪", "color": "#666666"},
                    "content": {"value": content[:1500], "color": "#333333"},
                    "date": {"value": datetime.now().strftime("%Y-%m-%d %H:%M"), "color": "#999999"},
                },
            }
            r = _post_json(f"{api_url}?access_token={token}", payload)
            results.append({"openid": oid, "result": r})
        ok_count = sum(1 for x in results if x["result"].get("ok"))
        return {
            "ok": ok_count > 0,
            "channel": "wechat-mp",
            "sent": ok_count,
            "total": len(openids),
            "details": results,
        }

    # 兜底：使用客服消息（用户需在 48 小时内与公众号互动过）
    api_url = "https://api.weixin.qq.com/cgi-bin/message/custom/send"
    results = []
    for oid in openids:
        payload = {
            "touser": oid,
            "msgtype": "text",
            "text": {"content": f"{title}\n\n{content[:1800]}"},
        }
        r = _post_json(f"{api_url}?access_token={token}", payload)
        results.append({"openid": oid, "result": r})
    ok_count = sum(1 for x in results if x["result"].get("ok"))
    return {
        "ok": ok_count > 0,
        "channel": "wechat-mp-custom",
        "sent": ok_count,
        "total": len(openids),
        "details": results,
        "note": "未配置 template_id，使用客服消息兜底（需 48h 内互动）",
    }


def _simplify_for_wechat(md: str) -> str:
    """
    把 markdown 简化成适合企业微信的紧凑格式，减少字节占用。
    - 板块标题用 emoji 替代
    - 条目用 • 替代 ###
    - 链接单独行展示
    - 去掉编辑视角（含 TOP 3、报尾等冗余内容）
    - 去掉引用块的 ** 加粗
    """
    lines = []
    in_editor_view = False
    for line in md.split("\n"):
        s = line.rstrip()

        # 进入编辑视角后所有内容都跳过（直到文件结束）
        if s.startswith("## 📌 编辑视角"):
            in_editor_view = True
            continue
        if in_editor_view:
            continue

        if not s:
            lines.append("")
            continue
        if s.startswith("# "):
            lines.append(s[2:].strip())
            continue
        if s.startswith("## 一、行业信息"):
            lines.append("【一】🏭 行业信息")
            continue
        if s.startswith("## 二、高层访谈"):
            lines.append("【二】🎤 高层访谈")
            continue
        if s.startswith("## 三、品牌市场营销动作"):
            lines.append("【三】📣 品牌营销")
            continue
        if s.startswith("### "):
            # 条目标题：[title](url)（重要性：⭐⭐⭐）
            import re
            m = re.match(r"^###\s+\d+\.\s+\[([^\]]+)\]\(([^)]+)\)（重要性：([⭐]+)）", s)
            if m:
                title, url, stars = m.group(1), m.group(2), m.group(3)
                lines.append(f"• {title} {stars}")
                lines.append(f"  {url}")
            else:
                lines.append(f"• {s[4:]}")
            continue
        if s.startswith("- **来源**："):
            lines.append("  📰 " + s[len("- **来源**：") :])
            continue
        if s.startswith("- **日期**："):
            # 简短日期显示
            continue
        if s.startswith("- **摘要**："):
            text = s[len("- **摘要**：") :]
            lines.append(f"  {text}")
            continue
        if s.startswith("> "):
            # 总览行
            text = s[2:].strip()
            import re
            text = re.sub(r"\*\*", "", text)
            lines.append(f"📊 {text}")
            continue
        if s.startswith("---") or s.startswith("*本报") or s.startswith("*本报告"):
            continue
        # 其他行：去掉 ** 加粗
        import re
        s2 = re.sub(r"\*\*([^*]+)\*\*", r"\1", s)
        lines.append(s2)
    return "\n".join(lines)


def _truncate_to_section(text: str, max_bytes: int) -> str:
    """
    智能截断：在不超过 max_bytes 的前提下，优先保留尽量多的板块。
    策略：找到能让总字节数 <= max_bytes 的最大板块数。
    """
    encoded = text.encode("utf-8")
    if len(encoded) <= max_bytes:
        return text

    # 找到板块标题位置
    sections = []
    for marker in ["## 一、行业信息", "## 二、高层访谈", "## 三、品牌市场营销动作"]:
        idx = text.find(marker)
        if idx >= 0:
            sections.append((idx, marker))
    sections.sort()

    if not sections:
        # 没有板块标题，直接字节截断
        truncated = encoded[:max_bytes - 50].decode("utf-8", errors="ignore")
        return truncated + "\n\n...(内容过长，已截断)"

    # 添加一个虚拟的"末尾"边界
    boundaries = [s[0] for s in sections] + [len(text)]

    # 找出能放下的最大板块数
    best_end = boundaries[0]  # 至少保留第一个板块
    for end in boundaries[1:]:
        candidate = text[:end]
        if len(candidate.encode("utf-8")) <= max_bytes:
            best_end = end

    if best_end == len(text):
        # 全部都能放下，但内容本身超长，需要截最后一段
        truncated = encoded[:max_bytes - 50].decode("utf-8", errors="ignore")
        return truncated + "\n\n...(内容过长，已截断)"

    # 找到 best_end 对应的板块（用第一个包含在 best_end 内的板块索引）
    kept_sections = sum(1 for s in sections if s[0] < best_end)
    truncated_text = text[:best_end].rstrip()
    if kept_sections < len(sections):
        truncated_text += f"\n\n...（仅显示前 {kept_sections} 个板块，共 {len(sections)} 个）"
    return truncated_text


def push_wechat_work(
    webhook: str,
    markdown: str,
    mentioned_list: Optional[list] = None,
    pre_simplified: bool = False,
) -> Dict[str, Any]:
    """
    企业微信群机器人推送（最稳定，无 48h 限制）
    https://developer.work.weixin.qq.com/document/path/91770

    参数：
      webhook: 群机器人 Webhook URL
      markdown: 日报内容（完整或简化版）
      mentioned_list: @指定成员的 userid（可选）
      pre_simplified: True 表示 markdown 已经是简化版（run_daily.py 传过来的紧凑版），
                      不要再跑 simplify 了

    注意：企业微信 markdown 消息内容最大 4096 字节（UTF-8）
    """
    if pre_simplified:
        # 已是简化版，只做截断
        title = extract_title(markdown)
        content = _truncate_to_section(markdown, 4000)
        full_text = f"{title}\n\n{content}"
        if len(full_text.encode("utf-8")) > 4096:
            content = _truncate_to_section(markdown, 3500)
            full_text = f"{title}\n\n{content}"
    else:
        # 完整 markdown：先简化再截断
        title = extract_title(markdown)
        MAX_CONTENT_BYTES = 4000
        content = _truncate_to_section(_simplify_for_wechat(markdown), MAX_CONTENT_BYTES)
        full_text = f"{title}\n\n{content}"
        if len(full_text.encode("utf-8")) > 4096:
            content = _truncate_to_section(_simplify_for_wechat(markdown), 3500)
            full_text = f"{title}\n\n{content}"

    payload = {
        "msgtype": "markdown",
        "markdown": {
            "content": full_text,
        },
    }
    if mentioned_list:
        payload["markdown"]["mentioned_list"] = mentioned_list
    return _post_json(webhook, payload)


# ---------------------- 通用 POST ----------------------

def _post_json(url: str, payload: Dict[str, Any], timeout: int = 15) -> Dict[str, Any]:
    """通用 JSON POST，带错误重试一次"""
    data = json.dumps(payload).encode("utf-8")
    headers = {"Content-Type": "application/json; charset=utf-8"}

    for attempt in range(2):
        try:
            req = urllib.request.Request(url, data=data, headers=headers, method="POST")
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                body = resp.read().decode("utf-8")
                try:
                    return {"ok": True, "status": resp.status, "body": json.loads(body)}
                except Exception:
                    return {"ok": True, "status": resp.status, "body": body}
        except urllib.error.HTTPError as e:
            return {"ok": False, "status": e.code, "error": e.read().decode("utf-8", errors="ignore")}
        except Exception as e:
            if attempt == 0:
                import time
                time.sleep(2)
                continue
            return {"ok": False, "error": str(e)}


# ---------------------- 企业微信文件推送 ----------------------

def _extract_webhook_key(webhook: str) -> str:
    """从 webhook URL 提取 key 参数"""
    from urllib.parse import urlparse, parse_qs
    parsed = urlparse(webhook)
    qs = parse_qs(parsed.query)
    return qs.get("key", [""])[0]


def _post_multipart(url: str, file_path: Path, filename: str, content_type: str) -> Dict[str, Any]:
    """multipart/form-data 上传文件"""
    import uuid
    boundary = f"----WebKitFormBoundary{uuid.uuid4().hex[:16]}"
    file_data = Path(file_path).read_bytes()
    file_length = len(file_data)

    body = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="media"; filename="{filename}"; filelength={file_length}\r\n'
        f"Content-Type: {content_type}\r\n\r\n"
    ).encode("utf-8") + file_data + f"\r\n--{boundary}--\r\n".encode("utf-8")

    req = urllib.request.Request(
        url,
        data=body,
        headers={
            "Content-Type": f"multipart/form-data; boundary={boundary}",
            "Content-Length": str(len(body)),
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return {"ok": True, "status": resp.status, "body": json.loads(resp.read().decode("utf-8"))}
    except urllib.error.HTTPError as e:
        return {"ok": False, "status": e.code, "error": e.read().decode("utf-8", errors="ignore")}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def push_wechat_work_file(webhook: str, file_path: str, filename: Optional[str] = None) -> Dict[str, Any]:
    """
    上传文件到企业微信并发送到群（仅企业微信群机器人支持）
    https://developer.work.weixin.qq.com/document/path/91770

    流程：
      1. POST /cgi-bin/webhook/upload_media?key=KEY&type=file 上传文件
      2. POST /cgi-bin/webhook/send?key=KEY 发 msgtype=file 消息

    限制：
      - 文件大小 ≤ 20MB
      - media_id 仅 3 天内有效
      - 每个 webhook 每分钟最多 20 条消息

    参数：
      webhook: 群机器人 Webhook URL
      file_path: 本地文件路径
      filename: 自定义文件名（可选，默认用原文件名）
    """
    fp = Path(file_path)
    if not fp.exists():
        return {"ok": False, "error": f"文件不存在: {file_path}"}

    file_size = fp.stat().st_size
    if file_size < 5:
        return {"ok": False, "error": "文件小于 5 字节，企业微信要求至少 5 字节"}
    if file_size > 20 * 1024 * 1024:
        return {"ok": False, "error": f"文件 {file_size} 字节超过 20MB 限制"}

    key = _extract_webhook_key(webhook)
    if not key:
        return {"ok": False, "error": "无效的 webhook URL（缺少 key 参数）"}

    name = filename or fp.name

    # 1. 上传素材
    upload_url = f"https://qyapi.weixin.qq.com/cgi-bin/webhook/upload_media?key={key}&type=file"
    print(f"[upload] {name}（{file_size} 字节）", file=sys.stderr)
    upload_result = _post_multipart(upload_url, fp, name, "application/octet-stream")

    if not upload_result.get("ok"):
        return {"ok": False, "step": "upload", "result": upload_result}

    body = upload_result.get("body", {})
    media_id = body.get("media_id", "")
    errcode = body.get("errcode", -1)
    if errcode != 0 or not media_id:
        return {"ok": False, "step": "upload", "errcode": errcode, "errmsg": body.get("errmsg", "no media_id")}

    print(f"[upload] ✓ media_id: {media_id}", file=sys.stderr)

    # 2. 发文件消息
    send_payload = {
        "msgtype": "file",
        "file": {"media_id": media_id},
    }
    send_url = f"https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key={key}"
    print(f"[send] 发文件消息", file=sys.stderr)
    send_result = _post_json(send_url, send_payload)

    if send_result.get("ok"):
        send_body = send_result.get("body", {})
        if send_body.get("errcode") == 0:
            return {
                "ok": True,
                "channel": "wechat_work_file",
                "filename": name,
                "file_size": file_size,
                "media_id": media_id,
                "note": "media_id 3 天内有效",
            }
        return {"ok": False, "step": "send", "errcode": send_body.get("errcode"), "errmsg": send_body.get("errmsg")}
    return {"ok": False, "step": "send", "result": send_result}


# ---------------------- 顶层入口 ----------------------

def push_markdown(channel: str, target: Union[str, Tuple, Dict], md_text: str) -> Dict[str, Any]:
    """
    统一推送入口
    channel: feishu | dingtalk | email | wechat_mp | wechat_work
    target:
      - feishu/dingtalk/wechat_work: webhook URL 字符串
      - email: dict with {to, smtp_host, smtp_port, user, password, from_addr?}
      - wechat_mp: dict with {appid, appsecret, openids, template_id?, url?}
    """
    if channel == "feishu":
        return push_feishu(target, md_text)
    elif channel == "dingtalk":
        return push_dingtalk(target, md_text)
    elif channel == "email":
        if isinstance(target, str):
            return {"ok": False, "error": "email channel 需要 dict 配置"}
        return push_email(md_text, **target)
    elif channel == "wechat_mp":
        if isinstance(target, str):
            return {"ok": False, "error": "wechat_mp channel 需要 dict 配置（appid/appsecret/openids）"}
        return push_wechat_mp(**target, md_text=md_text)
    elif channel == "wechat_work":
        return push_wechat_work(target, md_text)
    else:
        return {"ok": False, "error": f"未知渠道: {channel}"}


def push_file(channel: str, target: str, file_path: str, filename: Optional[str] = None) -> Dict[str, Any]:
    """
    统一文件推送入口
    channel: wechat_work（暂时只支持企业微信）
    target: webhook URL
    file_path: 本地文件路径
    """
    if channel == "wechat_work":
        return push_wechat_work_file(target, file_path, filename)
    return {"ok": False, "error": f"渠道 {channel} 不支持文件推送"}


# ---------------------- CLI ----------------------

def main():
    ap = argparse.ArgumentParser(description="具身智能日报 - 推送")
    ap.add_argument("--channel", required=True,
                    choices=["feishu", "dingtalk", "email", "wechat_mp", "wechat_work"],
                    help="推送渠道")
    ap.add_argument("--webhook", default="", help="飞书/钉钉/企业微信 Webhook URL")
    ap.add_argument("--file", required=True, help="Markdown 日报文件路径")
    # email
    ap.add_argument("--smtp-host", default="", help="SMTP 主机（email 用）")
    ap.add_argument("--smtp-port", type=int, default=465, help="SMTP 端口")
    ap.add_argument("--user", default="", help="SMTP 用户名")
    ap.add_argument("--password", default="", help="SMTP 密码/授权码")
    ap.add_argument("--to", default="", help="收件人（逗号分隔）")
    # wechat_mp
    ap.add_argument("--appid", default="", help="公众号 AppID（wechat_mp 用）")
    ap.add_argument("--appsecret", default="", help="公众号 AppSecret")
    ap.add_argument("--openids", default="", help="接收者 openid（逗号分隔）")
    ap.add_argument("--template-id", default="", help="模板消息 ID（可选）")
    ap.add_argument("--mode", choices=["markdown", "file"], default="markdown", help="推送模式：markdown 文本 / file 文件")
    ap.add_argument("--filename", default="", help="文件模式下的显示名（可选）")
    args = ap.parse_args()

    if args.mode == "file":
        # 文件模式
        if args.channel != "wechat_work":
            print("错误：仅企业微信（wechat_work）支持文件推送", file=sys.stderr)
            sys.exit(1)
        if not args.webhook:
            print("错误：需要 --webhook", file=sys.stderr)
            sys.exit(1)
        result = push_file(args.channel, args.webhook, args.file, args.filename or None)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        sys.exit(0 if result.get("ok") else 1)

    # markdown 模式
    md = Path(args.file).read_text(encoding="utf-8")

    if args.channel in ("feishu", "dingtalk", "wechat_work"):
        if not args.webhook:
            print(f"错误：{args.channel} 需要 --webhook", file=sys.stderr)
            sys.exit(1)
        result = push_markdown(args.channel, args.webhook, md)
    elif args.channel == "email":
        if not all([args.smtp_host, args.user, args.password, args.to]):
            print("错误：email 模式需要 --smtp-host/--user/--password/--to", file=sys.stderr)
            sys.exit(1)
        target = {
            "to_addr": [x.strip() for x in args.to.split(",")],
            "smtp_host": args.smtp_host,
            "smtp_port": args.smtp_port,
            "user": args.user,
            "password": args.password,
        }
        result = push_markdown("email", target, md)
    else:  # wechat_mp
        if not all([args.appid, args.appsecret, args.openids]):
            print("错误：wechat_mp 模式需要 --appid/--appsecret/--openids", file=sys.stderr)
            sys.exit(1)
        target = {
            "appid": args.appid,
            "appsecret": args.appsecret,
            "openids": [x.strip() for x in args.openids.split(",")],
        }
        if args.template_id:
            target["template_id"] = args.template_id
        result = push_markdown("wechat_mp", target, md)

    print(json.dumps(result, ensure_ascii=False, indent=2))
    sys.exit(0 if result.get("ok") else 1)


if __name__ == "__main__":
    main()
