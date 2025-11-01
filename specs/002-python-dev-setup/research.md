# Research: Python 开发环境工具选型

**Feature**: Python 开发环境标准化配置
**Phase**: Phase 0 - Research
**Date**: 2025-11-01

## 研究目标

为 Diting 项目选择最合适的 Python 开发工具,确保工具链现代化、性能优秀、社区支持良好,并符合项目宪章原则(尤其是 Privacy First 和 Observability & Testability)。

## 1. 代码格式化工具选择

### 候选方案

#### Option A: Ruff (推荐)

**简介**: 用 Rust 编写的极速 Python linter 和 formatter,兼容 Black 格式化风格。

**优势**:
- **性能**: 比 Black 快 10-100 倍,比 Flake8 快 10-100 倍
- **功能整合**: 集成了格式化、linting、import 排序,替代多个工具(Black + Flake8 + isort + pydocstyle 等)
- **现代化**: 活跃维护,快速迭代,支持最新 Python 特性
- **配置简单**: 单一配置文件,默认值合理
- **兼容性**: 格式化输出与 Black 兼容,迁移成本低

**劣势**:
- 相对较新(2022 年发布),但已被广泛采用(Pandas, FastAPI 等)
- 配置选项比 Black 多,需要明确项目标准

**社区支持**:
- GitHub Stars: 30k+
- 维护状态: 非常活跃,每周多次发布
- 采用者: Pandas, FastAPI, Pydantic, Hugging Face 等

**宪章符合性**:
- ✅ Privacy First: 完全本地运行,无外部服务
- ✅ Observability: 输出详细的格式化和检查报告

#### Option B: Black

**简介**: 流行的 Python 代码格式化工具,强调"零配置"哲学。

**优势**:
- **成熟稳定**: 2018 年发布,广泛采用,事实标准
- **零配置**: 默认配置适用大多数项目
- **社区认可**: Python 社区广泛接受的格式标准

**劣势**:
- **性能**: 比 Ruff 慢 10-100 倍,大项目格式化耗时长
- **功能单一**: 仅格式化,需配合 Flake8/isort 使用
- **配置受限**: 强调零配置,自定义选项少

**社区支持**:
- GitHub Stars: 38k+
- 维护状态: 活跃,但更新频率低于 Ruff
- 采用者: 大量 Python 项目

#### Option C: autopep8

**简介**: 基于 PEP 8 标准的自动格式化工具。

**优势**:
- 严格遵循 PEP 8
- 历史悠久,稳定

**劣势**:
- **性能**: 远慢于 Ruff
- **功能受限**: 格式化能力弱于 Black/Ruff
- **社区趋势**: 逐渐被 Black/Ruff 取代

**不推荐**: 已被更现代的工具超越。

### 决策: Ruff ✅

**理由**:
1. **性能**: Ruff 的极速性能确保 pre-commit 钩子不会拖慢开发流程
2. **工具整合**: 单一工具替代多个工具,降低配置复杂度
3. **现代化**: 活跃维护,支持最新 Python 3.12 特性
4. **Black 兼容**: 格式化输出与 Black 兼容,未来迁移成本低
5. **行业趋势**: FastAPI、Pydantic 等现代项目均已采用 Ruff

**配置策略**:
- 行长度: 100 字符(平衡可读性和屏幕利用率)
- 引号: 双引号(Python 社区主流)
- 启用 Ruff 推荐的 linting 规则集

---

## 2. 类型检查工具选择

### 候选方案

#### Option A: mypy (推荐)

**简介**: Python 官方推荐的静态类型检查工具,由 Python 之父 Guido van Rossum 支持。

**优势**:
- **官方认可**: PEP 484 类型注解标准的参考实现
- **成熟稳定**: 2012 年启动,长期维护
- **社区支持**: 最广泛使用的类型检查工具
- **灵活配置**: 支持逐步采用类型注解,严格度可调
- **插件生态**: 丰富的第三方库类型 stub(typeshed)

**劣势**:
- **性能**: 比 pyright 略慢(但仍可接受)
- **错误信息**: 有时不如 pyright 清晰

**社区支持**:
- GitHub Stars: 18k+
- 维护状态: 活跃,定期更新
- 采用者: 几乎所有大型 Python 项目

**宪章符合性**:
- ✅ Privacy First: 完全本地运行
- ✅ Observability: 详细的类型错误报告

#### Option B: pyright

**简介**: Microsoft 开发的 Python 类型检查工具,用 TypeScript 编写。

**优势**:
- **性能**: 比 mypy 快(并行检查)
- **错误信息**: 更清晰的错误提示
- **IDE 集成**: VS Code Pylance 基于 pyright

**劣势**:
- **依赖 Node.js**: 需要 Node.js 运行环境,增加依赖
- **社区认可度**: 虽然性能好,但 mypy 仍是主流选择
- **配置复杂**: 某些高级特性配置复杂

**社区支持**:
- GitHub Stars: 13k+
- 维护状态: 活跃,Microsoft 支持
- 采用者: VS Code 用户、部分现代项目

#### Option C: pyre

**简介**: Facebook 开发的类型检查工具。

**优势**:
- 性能优秀

**劣势**:
- **社区支持弱**: 主要 Facebook 内部使用
- **维护状态**: 更新频率低
- **配置复杂**: 企业级配置,对小项目过重

**不推荐**: 非主流选择,社区支持弱。

### 决策: mypy ✅

**理由**:
1. **官方标准**: PEP 484 参考实现,最符合 Python 类型注解标准
2. **社区认可**: 最广泛使用,生态最成熟(typeshed)
3. **无额外依赖**: 纯 Python 工具,无需 Node.js
4. **灵活性**: 支持逐步采用,适合项目初期边开发边加类型注解
5. **稳定性**: 长期维护,向后兼容性好

**配置策略**:
- 初期: 中等严格度(warn_return_any, warn_unused_configs)
- 逐步提升: 随代码成熟度增加严格度
- 第三方库: 优先使用 typeshed stub,必要时忽略特定库

---

## 3. 测试框架选择

### 候选方案

#### Option A: pytest (推荐)

**简介**: Python 社区事实标准的测试框架。

**优势**:
- **简洁语法**: 使用 assert 语句,无需学习特殊 API
- **强大 fixtures**: 依赖注入机制,测试数据管理优雅
- **插件生态**: 丰富插件(pytest-cov, pytest-mock, pytest-asyncio 等)
- **参数化测试**: 内置 @pytest.mark.parametrize 支持
- **详细输出**: 失败时显示详细上下文和差异
- **社区认可**: 几乎所有现代 Python 项目的选择

**劣势**:
- 相比 unittest 稍重(但可接受)

**社区支持**:
- GitHub Stars: 11k+
- 维护状态: 非常活跃
- 采用者: FastAPI, Django, Flask, Pandas 等

**宪章符合性**:
- ✅ Observability & Testability: 完美支持单元、集成、契约测试
- ✅ Privacy First: 本地运行

#### Option B: unittest

**简介**: Python 标准库内置测试框架。

**优势**:
- 标准库,无需安装
- 熟悉 JUnit 风格的开发者易上手

**劣势**:
- **语法冗长**: 需要继承 TestCase,使用 self.assertEqual 等
- **功能受限**: fixtures、参数化测试需要额外库
- **社区趋势**: 新项目普遍选择 pytest

**不推荐**: pytest 在所有方面优于 unittest。

### 决策: pytest ✅

**理由**:
1. **社区标准**: Python 测试框架的事实标准
2. **开发效率**: 简洁语法和强大 fixtures 提升测试编写效率
3. **插件生态**: 覆盖率(pytest-cov)、异步(pytest-asyncio)等需求均有插件
4. **宪章要求**: 完美支持宪章 V 原则要求的三类测试(单元、集成、契约)
5. **可维护性**: 清晰的测试代码,易于长期维护

**配置策略**:
- testpaths: tests/
- 测试文件命名: test_*.py
- 测试函数命名: test_*
- 输出: 彩色、详细模式,显示覆盖率

---

## 4. 覆盖率工具选择

### 候选方案

#### Option A: pytest-cov (推荐)

**简介**: pytest 的覆盖率插件,基于 coverage.py。

**优势**:
- **无缝集成**: pytest --cov 一条命令运行测试和覆盖率
- **功能完整**: 继承 coverage.py 全部功能
- **输出友好**: 终端彩色输出,HTML 报告

**劣势**:
- 依赖 pytest

**社区支持**:
- GitHub Stars: 1.7k+
- 维护状态: 活跃
- 采用者: 所有使用 pytest 的项目

#### Option B: coverage.py

**简介**: Python 覆盖率测试的底层库。

**优势**:
- 独立工具,不依赖测试框架
- 功能强大

**劣势**:
- 需要单独运行(coverage run -m pytest)
- 使用相对繁琐

**不推荐**: pytest-cov 是更好的选择(基于 coverage.py)。

### 决策: pytest-cov ✅

**理由**:
1. **集成简洁**: 与 pytest 无缝集成,一条命令完成测试和覆盖率
2. **功能完整**: 支持分支覆盖率、多文件合并、HTML 报告
3. **配置简单**: pyproject.toml 统一配置
4. **宪章要求**: 满足 SC-003 覆盖率报告生成要求(≥ 80%)

**配置策略**:
- 最低覆盖率: 80%(初期),逐步提升至 90%
- 排除路径: tests/, .venv/, __pycache__
- 报告格式: 终端 + HTML(详细分析)

---

## 5. Pre-commit 钩子框架

### 候选方案

#### Option A: pre-commit (推荐)

**简介**: 多语言 Git pre-commit 钩子管理框架。

**优势**:
- **多语言支持**: 支持 Python、JS、Rust 等,未来扩展方便
- **丰富生态**: 大量现成 hooks(ruff, mypy, prettier 等)
- **配置简单**: YAML 配置文件,声明式定义
- **隔离环境**: 每个 hook 独立虚拟环境,避免依赖冲突
- **社区认可**: Git hooks 管理的标准工具

**劣势**:
- 需要额外安装 pre-commit 框架

**社区支持**:
- GitHub Stars: 12k+
- 维护状态: 非常活跃
- 采用者: 数万个开源项目

**宪章符合性**:
- ✅ Privacy First: 本地运行
- ✅ Observability: 详细的钩子执行日志

#### Option B: 自定义 Git hooks

**简介**: 手动编写 .git/hooks/pre-commit 脚本。

**优势**:
- 无需额外框架
- 完全自定义

**劣势**:
- **不可版本控制**: .git/hooks/ 不入版本控制,团队同步困难
- **维护成本**: 需手动管理依赖和执行逻辑
- **缺乏隔离**: 依赖冲突风险

**不推荐**: pre-commit 框架是更成熟的解决方案。

### 决策: pre-commit ✅

**理由**:
1. **团队协作**: 配置文件版本控制,确保所有开发人员使用相同钩子
2. **生态丰富**: ruff, mypy 等都有官方 pre-commit hooks
3. **隔离安全**: 独立虚拟环境,避免依赖污染
4. **维护简单**: 声明式配置,更新工具版本只需修改配置
5. **行业标准**: 几乎所有现代 Python 项目的选择

**配置策略**:
- 钩子: ruff(格式化和 linting)、mypy(类型检查)
- 阶段: pre-commit(快速检查)
- 跳过测试: 测试放在 CI,pre-commit 仅代码质量检查(避免过慢)

---

## 6. Python 版本管理工具

### 候选方案

#### Option A: pyenv (推荐)

**简介**: Python 版本管理工具,类似 nvm(Node.js)。

**优势**:
- **专注 Python**: 专为 Python 设计,功能完整
- **简单易用**: 安装和切换版本简单
- **广泛采用**: Python 社区标准工具
- **跨平台**: macOS, Linux, Windows(pyenv-win)

**劣势**:
- 仅管理 Python(不管理其他语言)

**社区支持**:
- GitHub Stars: 38k+
- 维护状态: 活跃
- 采用者: 大量 Python 开发者

#### Option B: asdf

**简介**: 多语言版本管理工具。

**优势**:
- **多语言**: 统一管理 Python, Node.js, Ruby 等
- **插件生态**: 丰富的语言插件

**劣势**:
- **复杂度**: 对仅 Python 项目过重
- **配置**: 需要配置插件

**适用场景**: 多语言项目(如前端 + Python)

#### Option C: mise (原 rtx)

**简介**: asdf 的 Rust 实现,更快。

**优势**:
- 性能优于 asdf
- 多语言支持

**劣势**:
- 相对较新,社区小于 pyenv/asdf

### 决策: pyenv ✅

**理由**:
1. **专注性**: Diting 是纯 Python 项目,pyenv 专注 Python 足够
2. **成熟度**: 长期维护,社区认可度高
3. **简洁性**: 无需多语言管理的复杂度
4. **文档丰富**: 新人上手资料完善
5. **跨平台**: 支持 macOS/Linux/Windows

**配置策略**:
- 使用 .python-version 文件固定项目 Python 版本(3.12)
- Quickstart 提供 pyenv 安装和使用指南

**备选方案**: 如果未来 Diting 增加前端组件,可考虑迁移到 asdf/mise。

---

## 7. 配置文件组织策略

### 候选方案

#### Option A: pyproject.toml 统一配置 (推荐)

**简介**: PEP 518/621 标准化的 Python 项目配置文件。

**优势**:
- **标准化**: Python 社区推荐的项目配置标准
- **统一管理**: 一个文件配置所有工具(ruff, mypy, pytest, coverage)
- **减少文件**: 避免 setup.py, setup.cfg, requirements.txt 等多文件混乱
- **工具支持**: uv, pip, ruff, mypy, pytest 均支持 pyproject.toml

**劣势**:
- 单文件过大时可读性下降(但可通过注释分节)

**社区趋势**:
- 新项目普遍采用 pyproject.toml
- 旧项目逐步迁移到 pyproject.toml

#### Option B: 多文件配置

**简介**: 每个工具独立配置文件(如 ruff.toml, mypy.ini, pytest.ini)。

**优势**:
- 配置隔离,文件更小

**劣势**:
- **文件碎片化**: 根目录多个配置文件,维护复杂
- **重复配置**: 路径、排除规则等需在多处定义
- **趋势落后**: 社区趋向统一配置

**不推荐**: pyproject.toml 是更现代的选择。

### 决策: pyproject.toml 统一配置 ✅

**理由**:
1. **标准化**: 遵循 PEP 518/621,符合 Python 社区最佳实践
2. **简洁性**: 单文件管理,减少配置碎片
3. **工具支持**: 所有选定工具(uv, ruff, mypy, pytest)均完美支持
4. **可维护性**: 集中配置,修改和审查更方便
5. **版本控制友好**: 单文件更改,Git diff 清晰

**配置组织**:
```toml
[project]  # 项目元数据和依赖
[project.optional-dependencies]  # 开发依赖

[tool.uv]  # uv 配置
[tool.ruff]  # ruff 格式化和 linting
[tool.mypy]  # mypy 类型检查
[tool.pytest.ini_options]  # pytest 配置
[tool.coverage.run]  # 覆盖率配置
```

**例外情况**:
- `.pre-commit-config.yaml`: Pre-commit 要求 YAML 格式,独立文件
- `.python-version`: pyenv 要求独立文件
- `.vscode/settings.json`: IDE 配置,独立文件

---

## 研究结论总结

| 工具类别 | 选定工具 | 主要理由 |
|---------|---------|---------|
| 代码格式化和 Linting | **Ruff** | 极速性能,工具整合,现代化,Black 兼容 |
| 类型检查 | **mypy** | 官方标准,社区认可,成熟稳定,无额外依赖 |
| 测试框架 | **pytest** | 社区标准,简洁语法,强大 fixtures,插件丰富 |
| 覆盖率工具 | **pytest-cov** | pytest 无缝集成,功能完整 |
| Pre-commit 框架 | **pre-commit** | 团队协作,生态丰富,隔离安全 |
| Python 版本管理 | **pyenv** | 专注 Python,成熟度高,简洁易用 |
| 配置文件组织 | **pyproject.toml** | 标准化,统一管理,工具支持好 |

## 宪章符合性检查

所有选定工具均符合 Diting 宪章原则:

✅ **Privacy First (原则 I)**: 所有工具本地运行,无代码上传外部服务
✅ **Observability & Testability (原则 V)**: pytest 完美支持三类测试,覆盖率监控完备
✅ **无复杂度违规**: 工具选型遵循"简单优于复杂"原则,无过度工程

## 后续行动

1. ✅ 研究完成,工具选型确定
2. ⏭️ 填写 `data-model.md` - 定义配置实体模型
3. ⏭️ 创建 `contracts/` - 定义配置文件模式
4. ⏭️ 编写 `quickstart.md` - 环境设置指南
5. ⏭️ 生成 `tasks.md` - 实施任务清单

---

**研究完成日期**: 2025-11-01
**下一阶段**: Phase 1 - Design (data-model.md, contracts/, quickstart.md)
