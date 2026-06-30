# 具身智能日报 Skill

每天 9:00 自动抓取具身智能行业信息，生成日报 + PDF，推送到企业微信群。

## 🚀 3 分钟部署（GitHub Actions 版本）

### 1. 推到你的 GitHub 仓库

```bash
# 在你本地
cd /path/to/embodied-ai-daily
git init
git add .
git commit -m "init: 具身智能日报 Skill"
git branch -M main
git remote add origin https://github.com/你的用户名/embodied-ai-daily.git
git push -u origin main
```

### 2. 配置两个 Secret

进入 GitHub 仓库 → **Settings** → **Secrets and variables** → **Actions** → **New repository secret**

| Name | Value | 用途 |
|------|-------|------|
| `TAVILY_API_KEY` | `tvly-你的key` | 抓取当日信息 |
| `WECHAT_WORK_WEBHOOK` | `https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=xxx` | 推送到企业微信群 |

### 3. 启用 Workflow

进入 **Actions** 标签页 → 左侧选 "具身智能日报" → 右键 **Enable workflow**

### 4. 手动测试

Actions 页面 → 选 "具身智能日报" → **Run workflow** → 选日期 → Run

等 2-3 分钟，去企业微信群看是否收到日报。

## ⏰ 自动运行

- **每天北京时间 9:00** 自动触发（无需任何操作）
- 完整流程：抓数据 → 生成日报 → 生成 PDF → 推 markdown + PDF 到企业微信
- 日报和 PDF 保存在 GitHub Artifacts，**90 天可下载**

## 📁 文件结构

```
embodied-ai-daily/
├── .github/workflows/daily.yml    # GitHub Actions 工作流
├── SKILL.md                        # Skill 主文档
├── scripts/
│   ├── fetch_websearch.py         # Tavily 抓数据
│   ├── run_daily.py               # 主调度
│   ├── push.py                    # 推送（飞书/钉钉/邮件/微信/企业微信）
│   ├── export_pdf.py              # Markdown → PDF
│   ├── archive.py                 # 月度归档
│   ├── test_simplify.py           # 单元测试
│   ├── install_cron.sh            # 传统 cron 部署（可选）
│   ├── cron_daily.py              # cron 包装脚本
│   ├── fetch_kol.py               # KOL/公众号 Playwright 抓取
│   └── keywords.py                # 关键词工具
├── references/sources.md
└── assets/daily_template.md
```

## 💡 高级用法

### 手动指定日期

在 GitHub Actions 页面 → Run workflow → 填日期如 `2026-07-01`

### 关闭自动推送

如果想先生成日报不推送，把 Secret `WECHAT_WORK_WEBHOOK` 删掉即可

### 在本地跑

```bash
# 装依赖
pip3 install playwright markdown weasyprint
python3.11 -m playwright install chromium

# 配环境变量
export TAVILY_API_KEY="tvly-xxx"
export WECHAT_WORK_WEBHOOK="https://qyapi.weixin.qq.com/..."

# 跑
python3.11 scripts/run_daily.py --input /tmp/web.json --no-browser --date $(date +%Y-%m-%d) --pdf --push wechat_work --push-pdf
```

## ❓ 常见问题

**Q: Workflow 跑失败？**
A: 进 Actions 页面看报错，90% 是依赖装不上。检查 requirements 是否正确。

**Q: 9:00 没收到？**
A: GitHub Actions 定时任务**不保证准时**（通常 ±5-15 分钟）。需要严格准时用自建服务器 cron。

**Q: Tavily 1000 credits 用完？**
A: 每月 1 日自动重置。或升级 Tavily 付费版。

**Q: 可以加更多推送渠道吗？**
A: 完全可以。改 `run_daily.py` 的 `--push` 参数支持飞书/钉钉/邮件/微信服务号。

## 📊 成本

| 项 | 费用 |
|----|------|
| GitHub Actions | 免费（公开仓库无限制；私有仓库 2000 分钟/月） |
| Tavily API | 免费 1000 credits/月（够用 30+ 天） |
| 存储 | Artifacts 90 天免费，仓库 commit 永久免费 |
| **总计** | **0 元** |

## 📜 License

MIT
