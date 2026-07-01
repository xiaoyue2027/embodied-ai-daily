#!/usr/bin/env python3
"""
生成企业微信 PDF 下载链接推送的 payload
被 .github/workflows/daily-run.yml 调用
"""
import json
import sys


def main():
    pdf_url = sys.argv[1] if len(sys.argv) > 1 else "https://example.com/daily.pdf"
    date_str = sys.argv[2] if len(sys.argv) > 2 else "2026-07-01"

    content = (
        f"## 📄 完整 PDF 下载\n\n"
        f"**具身智能日报 {date_str}** 已生成\n\n"
        f"📎 **点击下载**：[具身智能日报-{date_str}.pdf]({pdf_url})\n\n"
        f"> PDF 包含全部条目的完整版（企业微信 markdown 显示有字节限制）"
    )

    payload = {
        "msgtype": "markdown",
        "markdown": {"content": content},
    }
    print(json.dumps(payload, ensure_ascii=False))


if __name__ == "__main__":
    main()
