---
name: embodied-ai-daily
description: 每日具身智能（Embodied AI）行业要情报送。当用户需要在每天早上 9 点整点获取一份关于具身智能行业的日报，或请求"具身智能日报"/"具身智能早报"/"具身 AI 行业每日信息"时触发此 Skill。该 Skill 会从中文互联网、小红书、微信公众号、各大新闻媒体渠道（36Kr、虎嗅、量子位、机器之心、智东西、IT之家、雷峰网、钛媒体等）抓取整理信息，并按重要性分三个板块呈现：① 行业信息 ② 高层访谈 ③ 品牌市场营销动作。
---

# 具身智能每日行业日报

## 概述

每天早上 9 点，自动整理并推送关于**具身智能（Embodied AI / 具身 AI / 人形机器人 / 机器人基础模型）**的行业重要信息，涵盖产业动态、高层访谈、品牌市场动作三大板块。

适用对象：关注具身智能行业的投资人、产品经理、市场人员、研究者、企业战略团队。

## 触发场景

- 用户说"给我一份今天的具身智能日报"
- 用户说"具身智能早报"/"具身 AI 行业晨报"
- 定时任务：每天 09:00 自动触发
- 用户手动输入 `/embodied-ai-daily`

## 工作流程

执行以下步骤生成日报：

### 1. 信息抓取

并行从以下渠道搜索过去 24 小时的具身智能相关内容：

| 渠道类型 | 具体来源 |
|---------|---------|
| 主流媒体 | 36Kr、虎嗅、量子位（QbitAI）、机器之心（Synced）、智东西、IT之家、雷峰网、**晚点 LatePost**、钛媒体、DoNews、第一财经 |
| 重点作者 | 微信公众号「**张小珺**」等高产深度作者（具身智能/硬科技） |
| 播客节目 | **三表龙门阵**、**八分半**、**T 中文播客** 等科技商业播客（AI/机器人/硬科技对话） |
| 社区 | **即刻 App** 具身智能 / 人形机器人话题圈 |
| 搜索引擎 | Google 中文、`site:weixin.qq.com`、`site:mp.weixin.qq.com` 微信公众号检索 |
| 小红书 | 小红书 App 内具身智能/机器人/人形机器人话题 |
| 行业垂类 | 中国机器人网、机器人在线、OFweek 机器人、人形机器人联盟 |
| 学术与机构 | 中国信通院、CAICT 人工智能所、IEEE Spectrum 中文版、arXiv 中文综述 |
| 海外补充 | Reuters Tech、Bloomberg Tech、The Information、TechCrunch（用于跨境信息） |

关键词矩阵（组合使用）：
- 具身智能、具身 AI、Embodied AI
- 人形机器人、Humanoid Robot
- 机器人基础模型、Robotics Foundation Model
- VLA 模型（Vision-Language-Action）
- 端到端自动驾驶、具身大模型
- 公司关键词：宇树（Unitree）、智元（AgiBot）、银河通用（Galbot）、傅利叶（FFT）、星动纪元、逐际动力、优必选、特斯拉 Optimus、Figure AI、1X、Boston Dynamics、Physical Intelligence、Skild AI

### 2. 重要性排序

按以下规则对每条信息打分（满分 100）：

- **政策与监管**（25 分）：国家或地方层面针对具身智能/机器人的产业政策、补贴、标准、白皮书
- **融资金额**（20 分）：单笔 ≥ 1 亿元加 20 分，每增加 1 亿加 5 分，封顶 30 分
- **头部公司动作**（20 分）：宇树/智元/银河通用/优必选/特斯拉/Figure/1X 等头部公司新品、量产、战略合作
- **技术突破**（15 分）：VLA 模型、端到端控制、Sim2Real 突破、世界模型
- **高层发声**（10 分）：CEO/CTO/首席科学家公开发言、采访、署名文章
- **市场动作**（10 分）：营销活动、发布会、KOL 投放、跨界联名

保留评分 ≥ 50 分的内容，按分数降序排列。

### 3. 内容分类

每条信息归入以下三个板块之一：

#### 板块 1：行业信息（Industry News）
- 行业政策、投融资、产业链上下游、市场规模数据
- 头部公司产品发布、量产进度、技术路线
- 学术突破与论文
- 行业大会与展会（ICRA、IROS、WAIC、机器人展）

#### 板块 2：高层访谈（Executive Interviews）
- 创始人/CEO/CTO 在公开场合（采访、播客、论坛）的核心观点
- 高管署名文章、行业研判、未来预测
- 战略级公开发言（如"未来 3 年量产 X 万台"类承诺）

#### 板块 3：品牌市场营销动作（Brand & Marketing）
- 新品发布会、媒体沟通会
- KOL 合作、跨界联名、IP 营销
- 展会参展、概念视频、社交媒体爆款
- 招聘品牌动作、PR 活动

### 4. 输出格式

使用以下 Markdown 模板（中文，默认时区 GMT+8）：

```markdown
# 具身智能日报 · YYYY-MM-DD（周X）

> 今日要闻共 N 条 | 行业信息 A 条 | 高层访谈 B 条 | 品牌营销 C 条
> 数据采集时间：HH:MM | 覆盖渠道：12 个

---

## 一、行业信息

### 1. [标题]（重要性：⭐⭐⭐⭐⭐）
- **来源**：36Kr / 量子位 / 微信公众号"XX" / 小红书 @XX
- **时间**：HH:MM
- **摘要**：150 字以内核心事实
- **关键数据**：（如融资金额、量产数量、参数等）
- **链接**：URL

### 2. ...

---

## 二、高层访谈

### 1. [访谈主题]（重要性：⭐⭐⭐⭐）
- **受访人**：姓名 · 职务 · 公司
- **来源**：财新 / 虎嗅 / 微信公众号"XX" / 视频号
- **核心观点**：
  1. 观点 1
  2. 观点 2
  3. 观点 3
- **金句**："原话引用"
- **链接**：URL

---

## 三、品牌市场营销动作

### 1. [品牌动作]（重要性：⭐⭐⭐）
- **品牌**：公司名
- **动作类型**：发布会 / 联名 / 视频 / 展会
- **内容描述**：做了什么、面向谁
- **传播效果**：播放量、互动量（如可获取）
- **链接**：URL

---

## 📌 编辑视角（可选）
- 今日 TOP 3 行业信号
- 与昨日/上周的对比观察
- 值得持续跟踪的 3 件事
```

### 5. 定时与推送

支持两种触发方式：

**方式 A：手动触发**
- 用户在对话中直接说"运行具身智能日报"
- 模型立即执行抓取 → 整理 → 输出

**方式 B：定时任务**
- 通过 `automation-task-manager` Skill 配置 cron 任务
- 表达式：`0 9 * * *`（每天 09:00）
- 命令：调用本 Skill 并输出到指定渠道（飞书/钉钉/邮件/Markdown 文件）

## 资源说明

本 Skill 主要通过 WebSearch、WebFetch 调用实时检索能力；KOL/播客/公众号/即刻通过专用 Playwright 脚本抓取。如下扩展：

- `references/`：可放置特定公司/赛道的深度背景资料（如 `sources.md`）
- `assets/`：可放置日报 HTML 模板、邮件模板（如 `daily_template.md`）
- `scripts/`：可放置去重脚本、关键词扩展脚本、渠道抓取脚本
  - `keywords.py`：中英文关键词扩展
  - `fetch_kol.py`：基于 Playwright 的 KOL/播客/公众号/即刻当日抓取脚本
  - **`run_daily.py`**：主调度脚本（一键跑完整日报，自动检测沙盒环境）
  - **`push.py`**：推送模块（飞书 / 钉钉 / 邮件 SMTP / 微信服务号 / 企业微信）
  - **`export_pdf.py`**：Markdown → PDF 导出（基于 WeasyPrint）
  - **`archive.py`**：历史归档 + 月度趋势报告生成
  - **`fetch_websearch.py`**：基于 Tavily API 的 WebSearch 抓取（cron 前置）
  - **`install_cron.sh`**：Linux/macOS 定时任务部署脚本
  - **`cron_daily.py`**：由 install_cron.sh 生成的 cron 包装脚本（自动加载 bashrc）
  - **`test_simplify.py`**：简化器单元测试（确保企业微信推送内容长期稳定）

### `fetch_kol.py` 使用说明

**前置依赖**

```bash
sudo pip3 install playwright beautifulsoup4
python3.11 -m playwright install chromium
```

**常用命令**

```bash
# 抓取所有渠道（微信 + 小宇宙 + 即刻），时间窗 1 天，输出 JSON
python3.11 scripts/fetch_kol.py --days 1 --output /tmp/kol_today.json

# 只抓微信公众号，自定义关键词
python3.11 scripts/fetch_kol.py --source wechat --keyword "具身智能,VLA,人形机器人" --days 2

# 只抓小宇宙播客
python3.11 scripts/fetch_kol.py --source xiaoyuzhou

# 同时输出 Markdown 片段（可直接贴入日报）
python3.11 scripts/fetch_kol.py --markdown /tmp/kol_today.md

# 调试：显示浏览器窗口
python3.11 scripts/fetch_kol.py --show --source jike
```

**配置项**

脚本顶部的三个字典可以替换为你订阅的播客/话题/KOL：

- `XIAOYUZHOU_SHOWS`：小宇宙播客 ID（从 https://www.xiaoyuzhoufm.com 复制节目页 URL）
- `JIKES_TOPICS`：即刻话题圈（注意即刻 Web 站需要登录才能看完整内容）
- `DEFAULT_KOL_KEYWORDS`：搜狗微信检索的默认关键词列表

**典型工作流（与日报集成）**

1. 执行 `fetch_kol.py --markdown /tmp/kol.md` 得到 KOL/播客/即刻/公众号的当日片段
2. 同时通过 WebSearch 抓取 36Kr / 量子位 / 智东西等主流媒体
3. 把 `/tmp/kol.md` 作为"板块 4：用户/市场声音"插入日报，或合并到原三板块的对应小节

### `run_daily.py` 使用说明

一键跑完整日报，**自动检测沙盒环境**——若当前 sandbox 无法启动 Chromium，会优雅降级为"仅 WebSearch"模式。

**前置依赖**

```bash
sudo pip3 install playwright beautifulsoup4
python3.11 -m playwright install chromium   # 仅当需要 Playwright 时
```

**常用命令**

```bash
# 完整流程：WebSearch + Playwright + 渲染日报 → 输出到 /workspace/daily_reports/
python3.11 scripts/run_daily.py

# 指定日期
python3.11 scripts/run_daily.py --date 2026-06-30

# 只跑 WebSearch 流程（跳过 Playwright）
python3.11 scripts/run_daily.py --no-browser

# 配合 WebSearch 注入：先用 LLM 调 WebSearch，把结果存为 JSON，再交给 run_daily 渲染
python3.11 scripts/run_daily.py --input /tmp/websearch_results.json

# 调试：直接打印 Markdown 到 stdout，不写文件
python3.11 scripts/run_daily.py --dry-run

# 显示浏览器（仅 Playwright 模式）
python3.11 scripts/run_daily.py --show-browser
```

**输出位置**

- `/workspace/daily_reports/embodied_ai_YYYY-MM-DD.md` —— 指定日期的日报
- `/workspace/daily_reports/latest.md` —— 软链指向最新一份（便于自动化消费）

**典型自动化工作流（与 LLM 配合）**

1. LLM 在早晨 9:00 调用 `WebSearch` 7 次（参考 `WEBSEARCH_QUERIES` 配置）
2. 把结果合并为 JSON，写到 `/tmp/websearch_today.json`
3. 触发 `python3.11 scripts/run_daily.py --input /tmp/websearch_today.json`
4. 完成后读 `/workspace/daily_reports/latest.md` 推送到飞书/钉钉/邮件

### 一体化命令（日报 + PDF + 推送 + 归档）

```bash
# 完整流程：日报 → PDF → 推送到飞书
python3.11 scripts/run_daily.py --input /tmp/websearch_today.json \
    --pdf --push feishu --webhook $FEISHU_WEBHOOK

# 完整流程：日报 → PDF → 推送到钉钉
python3.11 scripts/run_daily.py --input /tmp/websearch_today.json \
    --pdf --push dingtalk --webhook $DINGTALK_WEBHOOK

# 完整流程：日报 → PDF → 推送到邮件
python3.11 scripts/run_daily.py --input /tmp/websearch_today.json \
    --pdf --push email \
    --smtp-host smtp.qq.com --smtp-port 465 \
    --smtp-user your@qq.com --smtp-password $QQ_AUTH_CODE \
    --to team-lead@x.com,pm@x.com

# 完整流程：日报 → PDF → 推送到企业微信群机器人（含 PDF 文件）
python3.11 scripts/run_daily.py --input /tmp/websearch_today.json \
    --pdf --push wechat_work --push-pdf

# 完整流程：日报 → PDF → 推送到微信服务号（认证服务号）
python3.11 scripts/run_daily.py --input /tmp/websearch_today.json \
    --pdf --push wechat_mp \
    --appid $WECHAT_APPID --appsecret $WECHAT_SECRET \
    --openids "oXyz123,oXyz456" --template-id $TPL_ID
```

> 💡 `push` / `webhook` / `smtp-*` 参数都支持从同名环境变量自动读取：
> `FEISHU_WEBHOOK` / `DINGTALK_WEBHOOK` / `WECHAT_WORK_WEBHOOK` / `SMTP_HOST` / `SMTP_PORT` / `SMTP_USER` / `SMTP_PASSWORD` / `EMAIL_TO` / `WECHAT_APPID` / `WECHAT_SECRET` / `WECHAT_OPENIDS` / `WECHAT_TEMPLATE_ID`

### 推送渠道（push.py）

| 渠道 | 实现 | 协议 | 适用场景 |
|------|------|------|---------|
| 飞书 | interactive 卡片（标题 + 富文本 + 分割线 + 备注） | 自定义机器人 Webhook | 飞书用户 |
| 钉钉 | markdown 类型消息（@指定人） | 自定义机器人 Webhook | 钉钉用户 |
| 邮件 | multipart（纯文本 + HTML）| SMTP/SSL 465 / STARTTLS 587 | 通用邮箱 |
| **微信服务号** | 模板消息（默认带"日报"模板）；缺模板时兜底用客服消息 | OAuth2.0 access_token + 模板 API | 公众号关注用户 |
| **企业微信** | markdown 类型消息 + **文件消息（PDF/Word 等）** | 群机器人 Webhook + upload_media API | 企业内部群 |

**企业微信文件推送特点**
- 用 `upload_media` 上传文件 → 拿 `media_id`（3 天有效）
- 再发 `msgtype: file` 消息引用 `media_id`
- 单文件 ≤ 20MB
- 一条命令推 markdown + PDF：`--push wechat_work --push-pdf`

**企业微信 markdown 长度自适应**
- 完整版（PDF / 邮件用）：所有条目
- 精简版（企业微信用）：**自动按 4096 字节限制倒推每板块最大条目数**（5 → 4 → 3 → 2）
- run_daily.py 内部完成 render + simplify + 字节估算，推送时不再二次简化（避免内容丢失）

**特点**
- 自动从 Markdown 提取标题 + 摘要作为卡片头
- 长度超限自动截断（避免被飞书/钉钉拒收）
- 失败自动重试 1 次
- access_token 自动缓存（2 小时），避免重复获取

**微信服务号前置条件**
1. 拥有**已认证**的微信服务号
2. 在公众平台添加模板（建议字段：title / summary / content / date）
3. 接收者需在 48 小时内与公众号互动过（首次推送必须用模板消息；后续可改用客服消息）

**企业微信前置条件**
1. 在企业微信群里添加"群机器人"
2. 复制机器人 Webhook URL
3. 群成员都会收到推送（无 48h 限制）

### PDF 导出（export_pdf.py）

使用 WeasyPrint 把 Markdown 转成 A4 品牌报告：

- 自动探测中文字体（思源黑体/NotoSansCJK/微软雅黑/苹方/宋体）
- 板块用蓝色主题（#1a73e8），与飞书卡片一致
- 页眉显示日报名，页脚显示页码 + 生成时间
- 表格、代码块、引用、列表全支持
- 内置 `markdown` 扩展：extra / codehilite / tables / toc

### 历史归档（archive.py）

每天日报会被自动归档到 `monthly/YYYY-MM/`，每周/月可生成趋势报告。

```bash
# 归档当月所有日报
python3.11 scripts/archive.py

# 归档指定范围
python3.11 scripts/archive.py --from 2026-06-01 --to 2026-06-30

# 生成月度趋势报告（不重新归档）
python3.11 scripts/archive.py --report-only --month 2026-06

# 列出已归档的所有月份
python3.11 scripts/archive.py --list-months
```

**月度报告包含**：
- 整体概览（板块占比）
- 热点关键词 TOP 15
- 信息源 TOP 10
- 资本动向（融资频次）
- 本月 TOP 10 事件
- 完整事件流（按日期倒序）

输出位置：`/workspace/daily_reports/monthly/YYYY-MM/monthly_report_YYYY-MM.md`

### 定时任务部署（install_cron.sh）

把日报任务挂到系统 cron，**完全无人值守**。

**安装**

```bash
bash scripts/install_cron.sh
```

**会自动完成**：
1. 生成 `scripts/cron_daily.py` 包装脚本（自动从 `~/.bashrc` 加载环境变量）
2. 创建 `logs/` 目录
3. 写入 2 条 crontab：
   - `08:55` - `fetch_websearch.py`（抓数据到 `/tmp/websearch_today.json`）
   - `09:00` - `cron_daily.py`（生成日报 + 推送到企业微信 + 归档）

**前置条件**

`~/.bashrc` 中配置以下环境变量：

```bash
# 推送渠道
export WECHAT_WORK_WEBHOOK="https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=xxx"

# WebSearch 抓取（注册 https://tavily.com 免费 1000 credits/月）
export TAVILY_API_KEY="tvly-xxx"

# Skill 路径
export SKILL_DIR="/opt/embodied-ai-daily"
```

**卸载**

```bash
bash scripts/install_cron.sh --remove
```

**验证**

```bash
# 1. 查看 cron 任务（应该看到 2 条）
crontab -l | grep embodied

# 2. 手动测试抓取
TAVILY_API_KEY=xxx python3.11 scripts/fetch_websearch.py --output /tmp/test.json

# 3. 手动测试推送
python3.11 scripts/cron_daily.py

# 4. 查看日志
tail -f logs/cron.log
tail -f logs/fetch_websearch.log
```

**完整自动化时间线**

```
08:55  cron 触发 fetch_websearch.py
       ↓ Tavily API 抓 7-15 个查询（行业/访谈/营销三个板块）
       ↓ 输出 /tmp/websearch_today.json（约 20-40 条原始数据）
09:00  cron 触发 cron_daily.py
       ↓ 加载 ~/.bashrc 拿环境变量
       ↓ 调 run_daily.py 生成日报 + PDF
       ↓ 推送到企业微信群
       ↓ 归档到 monthly/2026-07/
09:05  你醒来，日报已经在群里
```

### WebSearch 抓取（fetch_websearch.py）

使用 **Tavily Search API**（为 AI 优化的搜索引擎）：

**为什么选 Tavily**
- 免费 1000 credits/月，够日报用
- 支持中文、时间过滤、域名白名单
- 不像 Google/Bing 那样有反爬
- 返回结构化结果（title/url/content）

**关键词矩阵**

| 板块 | 关键词 |
|------|--------|
| 行业信息 | 具身智能 行业 / 人形机器人 量产 / 具身大模型 融资 / 政策 国务院 / Embodied AI news |
| 高层访谈 | 具身智能 CEO 采访 / 创始人 对话 / 公开演讲 |
| 品牌营销 | 发布会 联名 / 跨界 营销 / 视频 爆款 |

**用法**

```bash
export TAVILY_API_KEY="tvly-xxx"

# 抓全部板块（默认 7+4+4 = 15 个查询）
python3.11 scripts/fetch_websearch.py --output /tmp/websearch_today.json

# 只抓行业板块
python3.11 scripts/fetch_websearch.py --section industry

# 调整时间窗（默认 day）
python3.11 scripts/fetch_websearch.py --time-range week

# 调整每个查询的结果数（默认 6，最大 20）
python3.11 scripts/fetch_websearch.py --max-results 10
```

**优先级域名白名单**：36Kr、量子位、机器之心、智东西、雷峰网、虎嗅、钛媒体、IT之家、财新、第一财经、知乎、B 站等 25+ 中文主流/垂类媒体。

## 使用示例

**示例 1：手动触发**
> 用户：今天具身智能有什么大事？
> AI：执行本 Skill 抓取 → 按三板块输出日报

**示例 2：定时触发**
> 用户：帮我每天早上 9 点推送具身智能日报到我的飞书
> AI：调用 `automation-task-manager` 创建 cron 任务 → 配置 webhook → 完成

**示例 3：聚焦某个细分**
> 用户：今天只要人形机器人量产相关的
> AI：在抓取阶段加入过滤器"量产、交付、产线、工厂" → 输出聚焦版日报

## 注意事项

1. **时效性**：只取过去 24 小时信息，过期信息降权或丢弃
2. **去重**：同一事件多源报道时，保留最权威源（如 36Kr、官方公众号）
3. **客观性**：高层访谈板块需引用原话，避免过度解读
4. **链接完整性**：每条信息必须附原始 URL
5. **不实信息**：若搜索结果置信度低，标注"⚠️ 待核实"
