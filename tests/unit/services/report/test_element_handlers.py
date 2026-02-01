"""ElementHandlers 单元测试"""

from unittest.mock import MagicMock

import pytest
from diting.services.report.element_handlers import (
    BulletHandler,
    CategoryHandler,
    DateHandler,
    EmojiMetaHandler,
    HotMetricsHandler,
    KickerHandler,
    NumberedHandler,
    ParagraphHandler,
    RenderContext,
    SectionHandler,
    SubsectionHandler,
    SummaryHandler,
    TableHandler,
    TimeRangeHandler,
    TitleHandler,
    create_default_handlers,
)
from diting.services.report.pdf_renderer import PdfRenderOptions
from reportlab.lib.styles import ParagraphStyle


@pytest.fixture
def mock_emoji_processor() -> MagicMock:
    """创建 mock emoji 处理器"""
    processor = MagicMock()
    processor.format_text = lambda text, size: text
    return processor


@pytest.fixture
def mock_styles() -> dict[str, ParagraphStyle]:
    """创建 mock 样式"""
    return {
        "title": ParagraphStyle(name="Title", fontSize=28),
        "kicker": ParagraphStyle(name="Kicker", fontSize=19),
        "section": ParagraphStyle(name="Section", fontSize=23),
        "subsection": ParagraphStyle(name="Subsection", fontSize=22),
        "body": ParagraphStyle(name="Body", fontSize=20),
        "meta": ParagraphStyle(name="Meta", fontSize=18),
        "meta_small": ParagraphStyle(name="MetaSmall", fontSize=16),
        "summary": ParagraphStyle(name="Summary", fontSize=20),
        "date": ParagraphStyle(name="Date", fontSize=20),
        "bullet": ParagraphStyle(name="Bullet", fontSize=20),
        "numbered": ParagraphStyle(name="Numbered", fontSize=20),
        "table_header": ParagraphStyle(name="TableHeader", fontSize=14),
        "table_cell": ParagraphStyle(name="TableCell", fontSize=14),
    }


@pytest.fixture
def render_context(
    mock_styles: dict[str, ParagraphStyle], mock_emoji_processor: MagicMock
) -> RenderContext:
    """创建渲染上下文"""
    return RenderContext(
        styles=mock_styles,
        options=PdfRenderOptions(),
        emoji_processor=mock_emoji_processor,
        lines=[],
        current_index=0,
    )


class TestTitleHandler:
    """TitleHandler 测试"""

    def test_can_handle_title(self, render_context: RenderContext) -> None:
        handler = TitleHandler()
        assert handler.can_handle("# 标题", render_context) is True
        assert handler.can_handle("## 二级标题", render_context) is False
        assert handler.can_handle("普通文本", render_context) is False

    def test_handle_returns_paragraph(self, render_context: RenderContext) -> None:
        handler = TitleHandler()
        result = handler.handle("# 测试标题", render_context)
        assert len(result) == 1
        assert handler.lines_consumed() == 1


class TestKickerHandler:
    """KickerHandler 测试"""

    def test_can_handle_kicker(self, render_context: RenderContext) -> None:
        handler = KickerHandler()
        assert handler.can_handle("热门话题 Top 10", render_context) is True
        assert handler.can_handle("  热门话题 Top 10  ", render_context) is True
        assert handler.can_handle("其他文本", render_context) is False


class TestSectionHandler:
    """SectionHandler 测试"""

    def test_can_handle_section(self, render_context: RenderContext) -> None:
        handler = SectionHandler()
        assert handler.can_handle("## 二级标题", render_context) is True
        assert handler.can_handle("# 一级标题", render_context) is False

    def test_handle_adds_hr_after_first(self, render_context: RenderContext) -> None:
        handler = SectionHandler()

        # 第一个话题，不添加分隔线
        result1 = handler.handle("## 话题1", render_context)
        assert len(result1) == 1

        # 第二个话题，添加分隔线
        result2 = handler.handle("## 话题2", render_context)
        assert len(result2) == 2  # HR + Paragraph


class TestSubsectionHandler:
    """SubsectionHandler 测试"""

    def test_can_handle_subsection(self, render_context: RenderContext) -> None:
        handler = SubsectionHandler()
        assert handler.can_handle("### 三级标题", render_context) is True
        assert handler.can_handle("## 二级标题", render_context) is False


class TestBulletHandler:
    """BulletHandler 测试"""

    def test_can_handle_bullet(self, render_context: RenderContext) -> None:
        handler = BulletHandler()
        assert handler.can_handle("- 列表项", render_context) is True
        assert handler.can_handle("- 日期: 2024-01-01", render_context) is False
        assert handler.can_handle("1. 有序列表", render_context) is False


class TestDateHandler:
    """DateHandler 测试"""

    def test_can_handle_date(self, render_context: RenderContext) -> None:
        handler = DateHandler()
        assert handler.can_handle("- 日期: 2024-01-01", render_context) is True
        assert handler.can_handle("- 其他内容", render_context) is False


class TestNumberedHandler:
    """NumberedHandler 测试"""

    def test_can_handle_numbered(self, render_context: RenderContext) -> None:
        handler = NumberedHandler()
        assert handler.can_handle("1. 第一项", render_context) is True
        assert handler.can_handle("10. 第十项", render_context) is True
        assert handler.can_handle("- 无序列表", render_context) is False


class TestTableHandler:
    """TableHandler 测试"""

    def test_can_handle_table(self, render_context: RenderContext) -> None:
        handler = TableHandler()
        assert handler.can_handle("| 列1 | 列2 |", render_context) is True
        assert handler.can_handle("普通文本", render_context) is False

    def test_handle_consumes_multiple_lines(self, render_context: RenderContext) -> None:
        render_context.lines = [
            "| 标题1 | 标题2 |",
            "|---|---|",
            "| 数据1 | 数据2 |",
            "普通文本",
        ]
        render_context.current_index = 0

        handler = TableHandler()
        result = handler.handle("| 标题1 | 标题2 |", render_context)

        assert handler.lines_consumed() == 3
        assert len(result) == 2  # Table + Spacer


class TestEmojiMetaHandler:
    """EmojiMetaHandler 测试"""

    def test_can_handle_tag_emoji(self, render_context: RenderContext) -> None:
        handler = EmojiMetaHandler()
        assert handler.can_handle("🏷️ 标签内容", render_context) is True

    def test_can_handle_clock_emoji(self, render_context: RenderContext) -> None:
        handler = EmojiMetaHandler()
        assert handler.can_handle("🕒 时间内容", render_context) is True


class TestMetadataHandlers:
    """元数据处理器测试"""

    def test_category_handler(self, render_context: RenderContext) -> None:
        handler = CategoryHandler()
        assert handler.can_handle("分类: 技术讨论", render_context) is True
        assert handler.can_handle("其他内容", render_context) is False

    def test_time_range_handler(self, render_context: RenderContext) -> None:
        handler = TimeRangeHandler()
        assert handler.can_handle("时间范围: 10:00 - 12:00", render_context) is True

    def test_hot_metrics_handler(self, render_context: RenderContext) -> None:
        handler = HotMetricsHandler()
        assert handler.can_handle("热门度/消息数/参与人数: 100/50/10", render_context) is True

    def test_summary_handler(self, render_context: RenderContext) -> None:
        handler = SummaryHandler()
        assert handler.can_handle("话题摘要: 这是摘要内容", render_context) is True


class TestParagraphHandler:
    """ParagraphHandler 测试"""

    def test_can_handle_always_true(self, render_context: RenderContext) -> None:
        handler = ParagraphHandler()
        assert handler.can_handle("任何文本", render_context) is True
        assert handler.can_handle("", render_context) is True


class TestCreateDefaultHandlers:
    """create_default_handlers 测试"""

    def test_returns_all_handlers(self) -> None:
        handlers = create_default_handlers()
        assert len(handlers) == 14

    def test_paragraph_handler_is_last(self) -> None:
        handlers = create_default_handlers()
        assert isinstance(handlers[-1], ParagraphHandler)
