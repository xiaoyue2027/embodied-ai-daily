#!/usr/bin/env python3
"""
简化器单元测试 - 确保 _simplify_for_wechat 长期稳定
"""
import sys
import importlib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import push
importlib.reload(push)
from push import _simplify_for_wechat


def test_strips_editor_view():
    """编辑视角及之后所有内容必须被去掉"""
    md = """# 具身智能日报

> 总览行

## 一、行业信息

• 条目 1

## 二、高层访谈

• 访谈 1

## 三、品牌营销

• 营销 1

## 📌 编辑视角

**TOP 3**
1. xxx
2. yyy
3. zzz

---

*本报由 Skill 自动生成*
"""
    result = _simplify_for_wechat(md)
    assert "编辑视角" not in result, "❌ 编辑视角标题未被去掉"
    assert "TOP 3" not in result, "❌ TOP 3 未被去掉"
    assert "1. xxx" not in result, "❌ TOP 3 列表残留"
    assert "本报由" not in result, "❌ 报尾残留"
    assert "营销 1" in result, "❌ 板块内容被误删"
    print("✓ test_strips_editor_view")


def test_preserves_three_sections():
    """三个板块标题必须保留"""
    md = """# 标题

> 摘要

## 一、行业信息
- 条目

## 二、高层访谈
- 条目

## 三、品牌市场营销动作
- 条目
"""
    result = _simplify_for_wechat(md)
    assert "🏭 行业信息" in result
    assert "🎤 高层访谈" in result
    assert "📣 品牌" in result
    print("✓ test_preserves_three_sections")


def test_strips_bold_markers():
    """必须去掉 ** 加粗标记"""
    md = """# 标题

- **来源**：腾讯新闻
- **摘要**：内容
"""
    result = _simplify_for_wechat(md)
    assert "**" not in result, "❌ 加粗标记残留"
    assert "腾讯新闻" in result
    print("✓ test_strips_bold_markers")


def test_handles_empty_input():
    """空输入不崩"""
    result = _simplify_for_wechat("")
    assert result == ""
    print("✓ test_handles_empty_input")


def test_real_daily_file():
    """用真实日报文件测试，确保没截错内容"""
    real_md_path = Path("/workspace/daily_reports/embodied_ai_2026-06-30.md")
    if not real_md_path.exists():
        print("⚠️ 真实日报文件不存在，跳过")
        return
    md = real_md_path.read_text(encoding="utf-8")
    result = _simplify_for_wechat(md)
    # 必须保留三个板块
    assert "🏭" in result
    assert "🎤" in result
    assert "📣" in result
    # 必须保留优必选条目（第三板块关键）
    assert "优必选" in result
    # 不能有编辑视角 / TOP 3 / 报尾
    assert "编辑视角" not in result
    assert "TOP 3" not in result
    assert "本报由" not in result
    # 字节数应在合理范围
    bytes_count = len(result.encode("utf-8"))
    assert bytes_count < 4096, f"❌ 字节数 {bytes_count} 超企业微信限制"
    print(f"✓ test_real_daily_file ({bytes_count} 字节)")


def test_handles_oversized_input():
    """极长输入（20+ 条）也能优雅处理，不会留下 '内容过长' 标记"""
    # 模拟 7/1 真实场景：行业 19 + 访谈 1 + 营销 0 = 20 条
    items = []
    for i in range(19):
        items.append({
            "title": f"具身智能重要新闻 {i+1}：某公司完成重大融资估值突破百亿",
            "url": f"https://example.com/news/{i+1}",
            "source": "36kr.com",
            "summary": f"这是第 {i+1} 条重要新闻的摘要内容，描述了行业重要事件的核心信息和发展趋势。" * 2,
        })
    items.append({
        "title": "某创始人专访：谈具身智能未来",
        "url": "https://example.com/interview/1",
        "source": "qbitai.com",
        "summary": "创始人谈未来三年规划。",
    })

    # 模拟 run_daily.py 的处理：render + 5条/板块 + simplify
    import sys
    sys.path.insert(0, str(Path(__file__).parent))
    import importlib
    import run_daily
    importlib.reload(run_daily)
    from run_daily import render_markdown

    sections = {
        "industry": items[:19],
        "interview": items[19:],
        "marketing": [],
    }
    candidate = render_markdown("2026-07-01", "二", sections, max_items_per_section=5)
    simplified = _simplify_for_wechat(candidate)
    bytes_count = len(simplified.encode("utf-8"))
    assert bytes_count < 4096, f"❌ 字节数 {bytes_count} 超企业微信限制"
    assert "🏭" in simplified
    assert "🎤" in simplified
    assert "📣" in simplified
    assert "内容过长" not in simplified, "❌ 极长输入仍触发截断"
    print(f"✓ test_handles_oversized_input ({bytes_count} 字节 / 20 条输入)")


if __name__ == "__main__":
    tests = [
        test_strips_editor_view,
        test_preserves_three_sections,
        test_strips_bold_markers,
        test_handles_empty_input,
        test_real_daily_file,
        test_handles_oversized_input,
    ]
    failed = 0
    for t in tests:
        try:
            t()
        except AssertionError as e:
            print(f"❌ {t.__name__}: {e}")
            failed += 1
        except Exception as e:
            print(f"❌ {t.__name__}: {type(e).__name__}: {e}")
            failed += 1

    print()
    if failed == 0:
        print(f"所有 {len(tests)} 个测试通过 ✅")
        sys.exit(0)
    else:
        print(f"❌ {failed}/{len(tests)} 个测试失败")
        sys.exit(1)
