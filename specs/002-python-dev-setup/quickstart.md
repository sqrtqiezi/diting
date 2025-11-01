# Quickstart: Python 开发环境设置

**Feature**: Python 开发环境标准化配置
**Phase**: Phase 1 - Design
**Date**: 2025-11-01
**预计时间**: 15 分钟

---

## 目标

按照本指南,新开发人员能在 15 分钟内完成 Diting 项目的 Python 开发环境配置,包括:
- ✅ Python 3.12 版本管理
- ✅ uv 依赖管理工具
- ✅ 虚拟环境创建和激活
- ✅ 开发依赖安装(Ruff, Mypy, Pytest 等)
- ✅ Pre-commit 钩子配置
- ✅ IDE(VS Code/PyCharm)集成

---

## 前置条件检查

在开始之前,请确认你的系统已安装以下工具:

### 必需工具

| 工具 | 验证命令 | 安装方法 |
|------|---------|---------|
| **Git** | `git --version` | [下载 Git](https://git-scm.com/) |
| **包管理器** | 见下方 | 见下方 |

### 包管理器安装

**macOS**:
```bash
# 安装 Homebrew(如果未安装)
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# 验证
brew --version
```

**Linux (Ubuntu/Debian)**:
```bash
# apt 是系统自带包管理器,验证即可
apt --version
```

**Windows**:
```powershell
# 安装 Chocolatey(如果未安装,以管理员运行 PowerShell)
Set-ExecutionPolicy Bypass -Scope Process -Force; [System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072; iex ((New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))

# 验证
choco --version
```

---

## 步骤 1: Python 版本管理(pyenv)

Diting 项目使用 **Python 3.12**,通过 pyenv 管理版本。

### 1.1 安装 pyenv

**macOS**:
```bash
# 使用 Homebrew 安装
brew install pyenv

# 配置 shell(添加到 ~/.zshrc 或 ~/.bash_profile)
echo 'export PYENV_ROOT="$HOME/.pyenv"' >> ~/.zshrc
echo 'export PATH="$PYENV_ROOT/bin:$PATH"' >> ~/.zshrc
echo 'eval "$(pyenv init --path)"' >> ~/.zshrc
echo 'eval "$(pyenv init -)"' >> ~/.zshrc

# 重新加载 shell 配置
source ~/.zshrc
```

**Linux (Ubuntu/Debian)**:
```bash
# 安装依赖
sudo apt update
sudo apt install -y make build-essential libssl-dev zlib1g-dev \
  libbz2-dev libreadline-dev libsqlite3-dev wget curl llvm \
  libncursesw5-dev xz-utils tk-dev libxml2-dev libxmlsec1-dev \
  libffi-dev liblzma-dev

# 安装 pyenv
curl https://pyenv.run | bash

# 配置 shell(添加到 ~/.bashrc 或 ~/.zshrc)
echo 'export PYENV_ROOT="$HOME/.pyenv"' >> ~/.bashrc
echo 'export PATH="$PYENV_ROOT/bin:$PATH"' >> ~/.bashrc
echo 'eval "$(pyenv init --path)"' >> ~/.bashrc
echo 'eval "$(pyenv init -)"' >> ~/.bashrc

# 重新加载 shell 配置
source ~/.bashrc
```

**Windows**:
```powershell
# 使用 Chocolatey 安装 pyenv-win
choco install pyenv-win

# 验证(重启 PowerShell 后)
pyenv --version
```

### 1.2 安装 Python 3.12

```bash
# 查看可用的 Python 3.12 版本
pyenv install --list | grep 3.12

# 安装最新的 Python 3.12 版本(例如 3.12.0,根据实际情况替换)
pyenv install 3.12.0

# 验证安装
pyenv versions
```

**预期输出**:
```
* system
  3.12.0
```

### 1.3 设置项目 Python 版本

```bash
# 进入项目目录
cd /path/to/diting

# 设置本地 Python 版本(创建 .python-version 文件)
pyenv local 3.12.0

# 验证
python --version
# 输出: Python 3.12.0
```

**说明**: `pyenv local` 会在项目根目录创建 `.python-version` 文件,自动切换到 Python 3.12。

---

## 步骤 2: 安装 uv 依赖管理工具

uv 是高性能的 Python 包管理器,比 pip 快 10-100 倍。

### 2.1 安装 uv

**macOS / Linux**:
```bash
# 使用官方安装脚本
curl -LsSf https://astral.sh/uv/install.sh | sh

# 验证
uv --version
```

**Windows**:
```powershell
# 使用 PowerShell 安装脚本
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"

# 验证
uv --version
```

**预期输出**: `uv 0.x.x` (版本号)

### 2.2 配置 uv(可选 - 使用 PyPI 镜像加速)

**中国用户加速配置**:
```bash
# 创建 uv 配置文件
mkdir -p ~/.config/uv

# 配置清华镜像(可选)
cat > ~/.config/uv/config.toml <<EOF
[pip]
index-url = "https://pypi.tuna.tsinghua.edu.cn/simple"
EOF
```

**说明**: 使用镜像可加速依赖下载,非必需。

---

## 步骤 3: 创建虚拟环境

使用 uv 创建项目隔离的虚拟环境。

### 3.1 创建虚拟环境

```bash
# 确保在项目根目录
cd /path/to/diting

# 使用 uv 创建虚拟环境(使用项目 Python 版本)
uv venv

# 验证虚拟环境目录
ls -la .venv
```

**预期输出**:
```
.venv/
├── bin/          (macOS/Linux)
│   ├── python
│   ├── pip
│   └── activate
└── Scripts/      (Windows)
    ├── python.exe
    ├── pip.exe
    └── activate.bat
```

### 3.2 激活虚拟环境

**macOS / Linux**:
```bash
source .venv/bin/activate
```

**Windows (PowerShell)**:
```powershell
.\.venv\Scripts\Activate.ps1
```

**Windows (CMD)**:
```cmd
.\.venv\Scripts\activate.bat
```

**验证激活**:
```bash
# 命令提示符前应显示 (.venv)
which python  # macOS/Linux
# 输出: /path/to/diting/.venv/bin/python

where python  # Windows
# 输出: C:\path\to\diting\.venv\Scripts\python.exe

# 验证 Python 版本
python --version
# 输出: Python 3.12.0
```

**说明**: 每次打开新终端,需要重新激活虚拟环境。

---

## 步骤 4: 安装依赖

使用 uv 安装项目依赖(开发工具)。

### 4.1 安装开发依赖

```bash
# 确保虚拟环境已激活(命令提示符显示 .venv)

# 安装开发依赖(从 pyproject.toml)
uv pip install -e ".[dev]"
```

**说明**:
- `-e`: 可编辑模式(editable mode),源码修改立即生效
- `.[dev]`: 安装当前项目 + 开发依赖

**预期输出**:
```
Resolved 10 packages in 2s
Installed 10 packages in 1s
  + ruff==0.1.x
  + mypy==1.7.x
  + pytest==7.4.x
  + pytest-cov==4.1.x
  + pre-commit==3.5.x
  ...
```

### 4.2 验证依赖安装

```bash
# 查看已安装依赖
uv pip list

# 验证关键工具
ruff --version
mypy --version
pytest --version
pre-commit --version
```

**预期输出**: 所有工具显示版本号,无错误。

---

## 步骤 5: 配置 Pre-commit 钩子

Pre-commit 在提交代码前自动运行代码质量检查。

### 5.1 安装 Pre-commit 钩子

```bash
# 安装 Git hooks 到 .git/hooks/
pre-commit install

# 验证
ls .git/hooks/pre-commit
```

**预期输出**:
```
Pre-commit installed at .git/hooks/pre-commit
```

### 5.2 手动运行 Pre-commit(验证配置)

```bash
# 首次运行会下载 hooks 环境(较慢,仅首次)
pre-commit run --all-files
```

**预期输出**:
```
[INFO] Initializing environment for ruff...
[INFO] Initializing environment for mypy...
Trim trailing whitespace.........................................Passed
Fix end of files.................................................Passed
Check YAML.......................................................Passed
...
Ruff linter......................................................Passed
Ruff formatter...................................................Passed
Mypy type checker................................................Passed
```

**说明**: 如果失败,Ruff 会自动修复格式问题,需要重新 `git add` 修改后的文件。

---

## 步骤 6: IDE 配置

### Option A: VS Code(推荐)

#### 6.1 安装 VS Code

[下载 VS Code](https://code.visualstudio.com/)

#### 6.2 打开项目

```bash
# 在项目根目录打开 VS Code
code .
```

#### 6.3 安装推荐插件

VS Code 会自动读取 `.vscode/extensions.json` 并提示安装推荐插件。

**手动安装**:
1. 右下角弹出推荐插件通知,点击"安装全部"
2. 或按 `Cmd+Shift+X`(macOS) / `Ctrl+Shift+X`(Windows/Linux) 打开插件面板
3. 搜索并安装:
   - Python (`ms-python.python`)
   - Pylance (`ms-python.vscode-pylance`)
   - Ruff (`charliermarsh.ruff`)
   - Mypy Type Checker (`ms-python.mypy-type-checker`)

#### 6.4 选择 Python 解释器

1. 按 `Cmd+Shift+P`(macOS) / `Ctrl+Shift+P`(Windows/Linux)
2. 输入 "Python: Select Interpreter"
3. 选择 `.venv/bin/python`

**验证**: 左下角状态栏显示 Python 版本和虚拟环境路径。

#### 6.5 验证工具集成

**格式化测试**:
1. 打开任意 `.py` 文件
2. 故意打乱格式(如删除空格、换行)
3. 保存文件(`Cmd+S` / `Ctrl+S`)
4. 文件应自动格式化

**类型检查测试**:
1. 写一段类型错误代码:
   ```python
   def add(a: int, b: int) -> int:
       return str(a + b)  # 错误:返回 str 而非 int
   ```
2. 应显示类型错误波浪线

**测试发现**:
1. 查看左侧测试面板(烧杯图标)
2. 应显示 `tests/` 目录下的测试

---

### Option B: PyCharm

#### 6.1 安装 PyCharm

[下载 PyCharm](https://www.jetbrains.com/pycharm/download/)
- Professional(付费,功能全)
- Community(免费,足够使用)

#### 6.2 打开项目

1. 启动 PyCharm
2. "Open" -> 选择项目根目录
3. PyCharm 会自动识别项目结构

#### 6.3 配置 Python 解释器

1. `File` -> `Settings`(Windows/Linux) / `PyCharm` -> `Preferences`(macOS)
2. `Project: diting` -> `Python Interpreter`
3. 点击齿轮图标 -> `Add`
4. 选择 "Existing environment"
5. 路径: `/path/to/diting/.venv/bin/python`
6. 点击 `OK`

#### 6.4 配置代码质量工具

**Ruff**:
1. `Settings` -> `Tools` -> `External Tools`
2. 点击 `+` 添加工具:
   - Name: `Ruff Format`
   - Program: `.venv/bin/ruff`
   - Arguments: `format $FilePath$`
   - Working directory: `$ProjectFileDir$`

**Mypy**:
1. `Settings` -> `Tools` -> `Mypy`(需安装 Mypy 插件)
2. Mypy executable: `.venv/bin/mypy`
3. 勾选 "Enable"

**Pytest**:
1. `Settings` -> `Tools` -> `Python Integrated Tools`
2. Testing -> Default test runner: `pytest`

---

## 步骤 7: 验证检查清单

运行以下命令验证环境配置完整性:

```bash
# 1. Python 版本检查
python --version
# 预期: Python 3.12.x

# 2. 虚拟环境检查
which python  # macOS/Linux
where python  # Windows
# 预期: 指向项目 .venv/ 目录

# 3. 依赖安装检查
uv pip list | grep -E "ruff|mypy|pytest"
# 预期: 显示 ruff, mypy, pytest, pytest-cov, pre-commit

# 4. Ruff 格式化检查
ruff check src/  # (如果 src/ 目录已创建)
# 预期: 无错误或自动修复

# 5. Mypy 类型检查
mypy src/  # (如果 src/ 目录已创建)
# 预期: 无类型错误(初期可能有警告)

# 6. Pytest 运行
pytest tests/ -v
# 预期: 所有测试通过(或无测试文件)

# 7. Pre-commit 检查
pre-commit run --all-files
# 预期: 所有 hooks 通过

# 8. 覆盖率报告
pytest --cov=src --cov-report=term-missing
# 预期: 显示覆盖率百分比(初期可能 0%)
```

**全部通过 ✅ = 环境配置成功!**

---

## 步骤 8: 常见问题排查

### 问题 1: Python 版本不是 3.12

**症状**:
```bash
python --version
# Python 2.7.x 或 Python 3.11.x
```

**解决方案**:
```bash
# 检查 pyenv 版本
pyenv versions

# 确认项目目录有 .python-version 文件
cat .python-version
# 输出: 3.12.0

# 激活虚拟环境
source .venv/bin/activate  # macOS/Linux
.\.venv\Scripts\Activate.ps1  # Windows

# 重新检查
python --version
```

---

### 问题 2: 依赖安装失败

**症状**:
```
ERROR: Could not find a version that satisfies the requirement ruff
```

**解决方案**:

**方案 1: 使用 PyPI 镜像**:
```bash
# 临时使用镜像
uv pip install -e ".[dev]" --index-url https://pypi.tuna.tsinghua.edu.cn/simple
```

**方案 2: 检查网络连接**:
```bash
# 测试网络
curl https://pypi.org/
```

**方案 3: 更新 uv**:
```bash
# 更新 uv 到最新版本
curl -LsSf https://astral.sh/uv/install.sh | sh
```

---

### 问题 3: VS Code 未识别虚拟环境

**症状**: 导入错误,代码补全不工作

**解决方案**:
1. 按 `Cmd+Shift+P`,输入 "Python: Select Interpreter"
2. 选择 `.venv/bin/python`
3. 重启 VS Code(完全退出后重新打开)
4. 检查 `.vscode/settings.json` 是否存在:
   ```json
   {
     "python.defaultInterpreterPath": "${workspaceFolder}/.venv/bin/python"
   }
   ```

---

### 问题 4: Pre-commit 钩子执行失败

**症状**:
```
[ERROR] Ruff format failed
```

**解决方案**:

**方案 1: 查看详细错误**:
```bash
pre-commit run --all-files --verbose
```

**方案 2: 手动修复格式**:
```bash
# 手动运行 Ruff 格式化
ruff format .

# 重新提交
git add .
git commit -m "message"
```

**方案 3: 更新 pre-commit 环境**:
```bash
# 清理并重新安装 pre-commit 环境
pre-commit clean
pre-commit install
pre-commit run --all-files
```

---

### 问题 5: IDE 格式化不生效

**症状**: VS Code 保存文件时未自动格式化

**解决方案**:

**VS Code**:
1. 确认已安装 Ruff 插件(`charliermarsh.ruff`)
2. 检查 `.vscode/settings.json`:
   ```json
   {
     "[python]": {
       "editor.defaultFormatter": "charliermarsh.ruff",
       "editor.formatOnSave": true
     }
   }
   ```
3. 重启 VS Code

**PyCharm**:
1. `Settings` -> `Tools` -> `External Tools` 检查 Ruff 配置
2. 手动运行: `Tools` -> `External Tools` -> `Ruff Format`

---

### 问题 6: Mypy 报告第三方库类型错误

**症状**:
```
error: Skipping analyzing "requests": module is installed, but missing library stubs
```

**解决方案**:

**方案 1: 安装类型 stub**:
```bash
# 查找类型 stub
uv pip search types-requests

# 安装
uv pip install types-requests
```

**方案 2: 忽略特定库**(临时方案):
```toml
# pyproject.toml
[tool.mypy]
ignore_missing_imports = true
```

---

## 下一步

环境配置完成后,你可以:

1. **阅读项目文档**:
   - `README.md`: 项目概述
   - `specs/*/spec.md`: 功能规格

2. **开始开发**:
   - 创建新分支: `git checkout -b feature/your-feature`
   - 编写代码: `src/` 目录
   - 编写测试: `tests/` 目录

3. **运行测试**:
   ```bash
   pytest tests/ -v --cov=src
   ```

4. **提交代码**:
   ```bash
   git add .
   git commit -m "feat: your feature"
   # Pre-commit 钩子自动运行
   ```

5. **推送代码**:
   ```bash
   git push origin feature/your-feature
   ```

---

## 附录: 快速命令参考

### 虚拟环境

```bash
# 创建虚拟环境
uv venv

# 激活虚拟环境
source .venv/bin/activate  # macOS/Linux
.\.venv\Scripts\Activate.ps1  # Windows

# 退出虚拟环境
deactivate
```

### 依赖管理

```bash
# 安装依赖
uv pip install -e ".[dev]"

# 添加新依赖
# 1. 编辑 pyproject.toml 添加依赖
# 2. 运行: uv pip install package-name

# 查看已安装依赖
uv pip list

# 更新依赖
uv pip install --upgrade package-name
```

### 代码质量

```bash
# Ruff 格式化
ruff format .

# Ruff linting
ruff check . --fix

# Mypy 类型检查
mypy src/

# Pre-commit(所有检查)
pre-commit run --all-files
```

### 测试

```bash
# 运行所有测试
pytest tests/ -v

# 运行单个测试文件
pytest tests/test_example.py -v

# 运行单个测试函数
pytest tests/test_example.py::test_function -v

# 生成覆盖率报告
pytest --cov=src --cov-report=html
# 查看报告: open htmlcov/index.html
```

---

## 成功标准

完成本指南后,你应该能够:

- ✅ 在 15 分钟内完成环境配置
- ✅ Python 版本为 3.12.x
- ✅ 虚拟环境已激活(命令提示符显示 `.venv`)
- ✅ 所有开发依赖已安装(ruff, mypy, pytest, pytest-cov, pre-commit)
- ✅ Pre-commit 钩子已配置,提交代码前自动检查
- ✅ IDE(VS Code/PyCharm)已集成 Python 工具
- ✅ 能够运行格式化、linting、类型检查、测试命令
- ✅ 验证检查清单全部通过

**欢迎加入 Diting 项目开发!** 🎉

---

**文档版本**: 1.0.0
**最后更新**: 2025-11-01
**反馈**: 如有问题或建议,请提交 Issue 或联系项目维护者
