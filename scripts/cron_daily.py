#!/usr/bin/env python3
"""
cron 触发的日报生成脚本
- 加载 ~/.bashrc 中的环境变量
- 沙盒检测（无 Playwright 也能跑）
- 默认跑 WebSearch 7 次 + 生成日报 + 推送到 WECHAT_WORK_WEBHOOK
"""
import datetime
import json
import os
import subprocess
import sys
from pathlib import Path

# ---------- 加载环境变量 ----------
# cron 不会自动加载 ~/.bashrc，手动读
BASHRC = Path.home() / ".bashrc"
if BASHRC.exists():
    for line in BASHRC.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = line.strip()
        if line.startswith("export ") and "=" in line:
            kv = line[7:].split("=", 1)
            if len(kv) == 2 and kv[0] and kv[0] not in os.environ:
                val = kv[1].strip().strip('"').strip("'")
                os.environ[kv[0]] = val

SKILL_DIR = Path(os.environ.get("SKILL_DIR", Path(__file__).parent.parent))
TODAY = datetime.date.today().strftime("%Y-%m-%d")
LOG_FILE = SKILL_DIR / "logs" / f"daily_{TODAY}.log"

def log(msg: str):
    ts = datetime.datetime.now().strftime("%H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line, flush=True)
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with LOG_FILE.open("a", encoding="utf-8") as f:
        f.write(line + "\n")

log(f"========== 具身智能日报 · {TODAY} 开始 ==========")

# ---------- 抓取 WebSearch ----------
# 注：cron 中无法直接调用 LLM 工具（WebSearch），所以这里支持两种模式：
#   1. 如果 /tmp/websearch_today.json 存在，使用它（推荐：上游 LLM 准备好）
#   2. 否则生成一份"无内容"占位日报（不推送，避免空消息骚扰）

WS_JSON = Path("/tmp/websearch_today.json")
if not WS_JSON.exists():
    log("⚠️ /tmp/websearch_today.json 不存在，跳过推送（请由 LLM 准备 WebSearch 结果）")
    sys.exit(0)

try:
    items = json.loads(WS_JSON.read_text(encoding="utf-8"))
    log(f"加载 {len(items)} 条 WebSearch 结果")
except Exception as e:
    log(f"⚠️ 解析 WebSearch JSON 失败: {e}")
    sys.exit(1)

# ---------- 自检：跑 simplify 单元测试 ----------
log("自检：运行 simplify 单元测试...")
test_cmd = [
    "python3.11",
    str(SKILL_DIR / "scripts" / "test_simplify.py"),
]
r = subprocess.run(test_cmd, capture_output=True, text=True, timeout=60)
if r.returncode != 0:
    log(f"⚠️ 单元测试失败，跳过推送避免发出坏格式日报：")
    log(r.stdout[-500:])
    log(r.stderr[-500:])
    sys.exit(2)
log(f"✓ 单元测试通过：{r.stdout.strip().split(chr(10))[-1]}")

# ---------- 跑日报 ----------
WEBHOOK = os.environ.get("WECHAT_WORK_WEBHOOK", "")
PUSH_FLAG = "--push wechat_work" if WEBHOOK else ""

cmd = [
    "python3.11",
    str(SKILL_DIR / "scripts" / "run_daily.py"),
    "--input", str(WS_JSON),
    "--no-browser",  # cron 环境通常没 Chromium
    "--date", TODAY,
    "--pdf",
]
if PUSH_FLAG:
    cmd.extend(PUSH_FLAG.split())

if WEBHOOK:
    cmd.extend(["--webhook", WEBHOOK])

log(f"执行: {' '.join(cmd)}")
result = subprocess.run(cmd, capture_output=True, text=True)
log(result.stdout.strip().replace("\n", " | "))
if result.returncode != 0:
    log(f"⚠️ run_daily 退出码 {result.returncode}: {result.stderr[:300]}")
    sys.exit(result.returncode)

# ---------- 归档 ----------
log("归档...")
archive_cmd = [
    "python3.11",
    str(SKILL_DIR / "scripts" / "archive.py"),
    "--month", TODAY[:7],
]
r = subprocess.run(archive_cmd, capture_output=True, text=True)
log(r.stdout.strip().replace("\n", " | "))

log("========== 今日完成 ==========")
