"""测试 LangChain 导入路径

验证项目使用 langchain_core 而非 langchain 的导入路径。
这是 LangChain 1.x 的最佳实践。
"""

from __future__ import annotations

import ast
from pathlib import Path


def get_imports_from_file(file_path: Path) -> list[tuple[str, str]]:
    """从 Python 文件中提取所有 import 语句

    Args:
        file_path: Python 文件路径

    Returns:
        (模块名, 导入项) 元组列表
    """
    with open(file_path, encoding="utf-8") as f:
        tree = ast.parse(f.read())

    imports = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            for alias in node.names:
                imports.append((node.module, alias.name))
    return imports


class TestLangChainImports:
    """测试 LangChain 导入路径符合 1.x 最佳实践"""

    def test_analysis_uses_langchain_core(self) -> None:
        """analysis.py 应使用 langchain_core 而非 langchain"""
        file_path = Path("src/diting/services/llm/analysis.py")
        imports = get_imports_from_file(file_path)

        # 检查是否有 langchain.prompts 导入（不应该有）
        langchain_prompts = [
            (module, name) for module, name in imports if module == "langchain.prompts"
        ]
        assert langchain_prompts == [], (
            f"analysis.py 不应使用 'from langchain.prompts import ...'，"
            f"应改为 'from langchain_core.prompts import ...'\n"
            f"发现: {langchain_prompts}"
        )

        # 检查是否使用了 langchain_core.prompts（应该有）
        langchain_core_prompts = [
            (module, name) for module, name in imports if module == "langchain_core.prompts"
        ]
        assert any(
            name == "ChatPromptTemplate" for _, name in langchain_core_prompts
        ), "analysis.py 应使用 'from langchain_core.prompts import ChatPromptTemplate'"

    def test_topic_summarizer_uses_langchain_core(self) -> None:
        """topic_summarizer.py 应使用 langchain_core 而非 langchain"""
        file_path = Path("src/diting/services/llm/topic_summarizer.py")
        imports = get_imports_from_file(file_path)

        # 检查是否有 langchain.prompts 导入（不应该有）
        langchain_prompts = [
            (module, name) for module, name in imports if module == "langchain.prompts"
        ]
        assert langchain_prompts == [], (
            f"topic_summarizer.py 不应使用 'from langchain.prompts import ...'，"
            f"应改为 'from langchain_core.prompts import ...'\n"
            f"发现: {langchain_prompts}"
        )

        # 检查是否使用了 langchain_core.prompts（应该有）
        langchain_core_prompts = [
            (module, name) for module, name in imports if module == "langchain_core.prompts"
        ]
        assert any(
            name == "ChatPromptTemplate" for _, name in langchain_core_prompts
        ), "topic_summarizer.py 应使用 'from langchain_core.prompts import ChatPromptTemplate'"

    def test_chatprompttemplate_functionality(self) -> None:
        """验证 ChatPromptTemplate 从 langchain_core 导入后功能正常"""
        from langchain_core.prompts import ChatPromptTemplate

        # 创建一个简单的 prompt template
        prompt = ChatPromptTemplate.from_messages(
            [
                ("system", "你是一个助手"),
                ("human", "你好，{name}"),
            ]
        )

        # 验证 format_messages 方法可用
        messages = prompt.format_messages(name="测试用户")
        assert len(messages) == 2
        assert "测试用户" in str(messages[1].content)
