#!/usr/bin/env bash
# 具身智能日报 - cron 部署脚本
# 安装：bash scripts/install_cron.sh
# 卸载：bash scripts/install_cron.sh --remove
# 查看：crontab -l | grep embodied

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL_DIR="$(dirname "$SCRIPT_DIR")"

CRON_LINE_WS="55 8 * * * /usr/bin/python3.11 ${SKILL_DIR}/scripts/fetch_websearch.py --output /tmp/websearch_today.json >> ${SKILL_DIR}/logs/fetch_websearch.log 2>&1"
CRON_LINE="0 9 * * * /usr/bin/python3.11 ${SKILL_DIR}/scripts/cron_daily.py >> ${SKILL_DIR}/logs/cron.log 2>&1"
CRON_TAG="# embodied-ai-daily"

# ---------- 卸载 ----------
if [[ "$1" == "--remove" || "$1" == "-r" ]]; then
    echo "🗑  卸载 embodied-ai-daily cron 任务..."
    crontab -l 2>/dev/null | grep -v "$CRON_TAG" | grep -v "cron_daily.py" | grep -v "fetch_websearch.py" | crontab - 2>/dev/null || true
    echo "✓ 已卸载"
    exit 0
fi

# ---------- 安装 ----------
echo "🚀 部署 embodied-ai-daily cron 任务"
echo "   Skill 目录: $SKILL_DIR"
echo "   抓取时间: 每天 08:55（fetch_websearch.py）"
echo "   推送时间: 每天 09:00（cron_daily.py）"
echo ""

# 1. 创建 logs 目录
mkdir -p "$SKILL_DIR/logs"

# 2. 检查环境变量（webhook）
if [[ -z "$WECHAT_WORK_WEBHOOK" && -f "$HOME/.bashrc" ]]; then
    echo "⚠️  当前 shell 未设置 WECHAT_WORK_WEBHOOK，cron 任务会从 ~/.bashrc 读取"
fi
if [[ -z "$TAVILY_API_KEY" && -f "$HOME/.bashrc" ]]; then
    echo "⚠️  当前 shell 未设置 TAVILY_API_KEY，cron 任务会从 ~/.bashrc 读取"
    echo "   注册地址: https://tavily.com （免费 1000 credits/月）"
fi

# 3. 生成 cron 任务包装脚本（确保环境变量被加载）
cat > "$SKILL_DIR/scripts/cron_daily.py" << 'PYEOF'
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
PYEOF

chmod +x "$SKILL_DIR/scripts/cron_daily.py"
echo "✓ 包装脚本已生成: $SKILL_DIR/scripts/cron_daily.py"

# 4. 写入 crontab
echo ""
echo "📋 准备写入 crontab（2 条）:"
echo "   08:55  $CRON_LINE_WS"
echo "   09:00  $CRON_LINE"
echo ""

CURRENT_CRON=$(crontab -l 2>/dev/null || true)
if echo "$CURRENT_CRON" | grep -q "cron_daily.py\|fetch_websearch.py"; then
    echo "⚠️  已存在 embodied-ai-daily cron 任务，跳过安装"
    echo "   如需重新安装，请先运行: bash install_cron.sh --remove"
else
    # 保留旧任务，追加新任务
    (
        echo "$CURRENT_CRON"
        echo ""
        echo "$CRON_LINE_WS $CRON_TAG"
        echo "$CRON_LINE $CRON_TAG"
    ) | crontab -
    echo "✓ cron 任务已安装（2 条）"
    echo ""
    echo "当前 crontab 中 embodied-ai-daily 部分:"
    crontab -l | grep -A0 "embodied-ai-daily" | grep -v "^$" || crontab -l | tail -5
fi

echo ""
echo "✅ 部署完成！"
echo ""
echo "验证方法："
echo "  1. 查看 cron 任务：crontab -l | grep embodied"
echo "  2. 手动测试：    python3.11 $SKILL_DIR/scripts/cron_daily.py"
echo "  3. 查看日志：    tail -f $SKILL_DIR/logs/cron.log"
echo ""
echo "卸载：bash $0 --remove"
