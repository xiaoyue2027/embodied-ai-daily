#!/usr/bin/env python3
"""
Markdown -> PDF 导出（使用 WeasyPrint）

特点：
  - 中文字体回退（自动找系统字体）
  - 卡片化样式，模仿品牌报告
  - 页眉显示日报标题，页脚显示页码 + 生成时间
  - 表格、代码块、引用、列表全支持

用法：
  python3.11 export_pdf.py input.md output.pdf
  python3.11 export_pdf.py --input /tmp/daily.md --output /tmp/daily.pdf --title "具身智能日报"
"""

import argparse
import sys
from pathlib import Path
from typing import List, Optional


# ---------------------- 字体探测 ----------------------

def find_chinese_fonts() -> List[str]:
    """查找系统中可用的中文字体"""
    candidates = [
        # 思源系列
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/opentype/noto/NotoSerifCJK-Regular.ttc",
        "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",
        "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
        # macOS
        "/System/Library/Fonts/PingFang.ttc",
        "/System/Library/Fonts/STHeiti Medium.ttc",
        "/Library/Fonts/Songti.ttc",
        # Windows
        "C:/Windows/Fonts/msyh.ttc",
        "C:/Windows/Fonts/simhei.ttf",
        "C:/Windows/Fonts/simsun.ttc",
    ]
    return [p for p in candidates if Path(p).exists()]


def find_emoji_fonts() -> List[str]:
    """查找系统中可用的 emoji 字体"""
    candidates = [
        "/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf",
        "/usr/share/fonts/truetype/noto/NotoEmoji-Regular.ttf",
        "/System/Library/Fonts/Apple Color Emoji.ttc",
        "C:/Windows/Fonts/seguiemj.ttf",
    ]
    return [p for p in candidates if Path(p).exists()]


# ---------------------- 样式模板 ----------------------

def build_css(fonts: List[str]) -> str:
    """构造内联 CSS"""
    if fonts:
        # 用字体 logical name（不带 .ttc 扩展名），保证 WeasyPrint 能正确识别
        font_family = ', '.join(f'"{Path(f).stem.replace("-Regular","")}"' for f in fonts[:3])
    else:
        font_family = '"DejaVu Sans", sans-serif'

    # 拼接 emoji 字体 fallback（让 ★ ⭐ 🏭 等符号能正常显示）
    emoji_fonts = [
        '"Noto Color Emoji"',
        '"Apple Color Emoji"',
        '"Segoe UI Emoji"',
        '"DejaVu Sans"',
    ]
    font_family = f"{font_family}, " + ", ".join(emoji_fonts)

    return f"""
@page {{
    size: A4;
    margin: 2.2cm 2cm 2.5cm 2cm;
    @top-center {{
        content: "具身智能日报 · embodied-ai-daily";
        font-family: {font_family};
        font-size: 9pt;
        color: #888;
    }}
    @bottom-left {{
        content: "由 embodied-ai-daily Skill 自动生成";
        font-family: {font_family};
        font-size: 8pt;
        color: #aaa;
    }}
    @bottom-right {{
        content: "第 " counter(page) " / " counter(pages) " 页";
        font-family: {font_family};
        font-size: 8pt;
        color: #aaa;
    }}
}}

body {{
    font-family: {font_family};
    color: #1a1a1a;
    line-height: 1.6;
    font-size: 10.5pt;
    word-wrap: break-word;
    overflow-wrap: break-word;
}}

p, li, blockquote, h1, h2, h3, h4 {{
    word-wrap: break-word;
    overflow-wrap: break-word;
    max-width: 100%;
}}

ul, ol {{
    padding-left: 22px;
}}

h1 {{
    color: #1a1a1a;
    font-size: 22pt;
    border-bottom: 3px solid #1a73e8;
    padding-bottom: 8px;
    margin-top: 0;
}}

h2 {{
    color: #1a73e8;
    font-size: 16pt;
    border-left: 4px solid #1a73e8;
    padding-left: 10px;
    margin-top: 32px;
    page-break-after: avoid;
}}

h3 {{
    color: #333;
    font-size: 13pt;
    background: #f5f9ff;
    padding: 8px 12px;
    border-radius: 4px;
    margin-top: 22px;
    page-break-after: avoid;
}}

h4 {{
    color: #555;
    font-size: 12pt;
    margin-top: 16px;
}}

p {{
    margin: 8px 0;
    text-align: justify;
}}

ul, ol {{
    margin: 8px 0;
    padding-left: 28px;
}}

li {{
    margin: 4px 0;
}}

blockquote {{
    border-left: 4px solid #1a73e8;
    padding: 10px 16px;
    color: #555;
    background: #f5f9ff;
    margin: 14px 0;
    font-size: 10.5pt;
    border-radius: 0 4px 4px 0;
}}

a {{
    color: #1a73e8;
    text-decoration: none;
    border-bottom: 1px dotted #1a73e8;
}}

code {{
    background: #f6f8fa;
    padding: 2px 6px;
    border-radius: 3px;
    font-size: 0.9em;
    color: #d6336c;
}}

pre {{
    background: #f6f8fa;
    padding: 12px;
    border-radius: 6px;
    overflow-x: auto;
    font-size: 9.5pt;
    border-left: 3px solid #1a73e8;
}}

hr {{
    border: none;
    border-top: 1px dashed #ccc;
    margin: 24px 0;
}}

table {{
    width: 100%;
    border-collapse: collapse;
    margin: 12px 0;
    font-size: 10.5pt;
}}

th, td {{
    border: 1px solid #e0e0e0;
    padding: 8px 12px;
    text-align: left;
}}

th {{
    background: #f5f9ff;
    color: #1a73e8;
    font-weight: 600;
}}

tr:nth-child(even) {{
    background: #fafbfc;
}}

/* 板块分割线 */
h2 {{
    page-break-before: auto;
}}

/* 重要程度星标 */
"""


# ---------------------- 主体 ----------------------

def md_to_pdf(md_path: str, pdf_path: str, title: Optional[str] = None) -> dict:
    """
    把 Markdown 转 PDF
    """
    try:
        from weasyprint import HTML, CSS
        import markdown
    except ImportError as e:
        return {"ok": False, "error": f"缺少依赖: {e}。请运行：sudo pip3 install weasyprint markdown"}

    md_text = Path(md_path).read_text(encoding="utf-8")
    title = title or "具身智能日报"

    # Markdown -> HTML
    html_body = markdown.markdown(
        md_text,
        extensions=["extra", "codehilite", "tables", "toc"],
    )

    fonts = find_chinese_fonts()
    css_text = build_css(fonts)

    html_doc = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>{title}</title>
</head>
<body>
{html_body}
</body>
</html>"""

    try:
        HTML(string=html_doc).write_pdf(pdf_path, stylesheets=[CSS(string=css_text)])
        return {
            "ok": True,
            "pdf": pdf_path,
            "size_kb": round(Path(pdf_path).stat().st_size / 1024, 1),
            "fonts_used": [Path(f).name for f in fonts[:3]],
        }
    except Exception as e:
        return {"ok": False, "error": str(e)}


def main():
    ap = argparse.ArgumentParser(description="Markdown -> PDF 导出")
    ap.add_argument("input", nargs="?", help="输入 Markdown 路径")
    ap.add_argument("output", nargs="?", help="输出 PDF 路径")
    ap.add_argument("--input", dest="input_kw", help="输入（关键字版）")
    ap.add_argument("--output", dest="output_kw", help="输出（关键字版）")
    ap.add_argument("--title", default="具身智能日报", help="PDF 标题")
    args = ap.parse_args()

    md_path = args.input or args.input_kw
    pdf_path = args.output or args.output_kw

    if not md_path or not pdf_path:
        print("用法: python3.11 export_pdf.py input.md output.pdf", file=sys.stderr)
        sys.exit(1)

    result = md_to_pdf(md_path, pdf_path, args.title)
    print(result)
    sys.exit(0 if result.get("ok") else 1)


if __name__ == "__main__":
    main()
