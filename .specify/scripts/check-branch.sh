#!/bin/bash

# GitHub Flow 分支检查脚本
# 用途: 在执行 spec-kit 命令前验证当前分支是否符合规范
# 使用: bash .specify/scripts/check-branch.sh

set -e

# 颜色定义
RED='\033[0;31m'
YELLOW='\033[1;33m'
GREEN='\033[0;32m'
NC='\033[0m' # No Color

# 获取当前分支
CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD)

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  GitHub Flow 分支检查"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# 检查 1: 当前分支不能是 master
if [ "$CURRENT_BRANCH" = "master" ]; then
    echo -e "${RED}❌ 错误: 当前在 master 分支${NC}"
    echo ""
    echo "根据 GitHub Flow 规范,spec-kit 命令必须在功能分支上执行。"
    echo ""
    echo -e "${YELLOW}请执行:${NC}"
    echo "  git checkout -b {spec-id}-{feature-name}"
    echo ""
    echo -e "${YELLOW}例如:${NC}"
    echo "  git checkout -b 004-knowledge-graph-core"
    echo ""
    echo "详细说明见:"
    echo "  .specify/workflows/spec-kit-github-flow-checklist.md"
    echo ""
    exit 1
fi

# 检查 2: 功能分支命名规范
VALID_PATTERN=0

# 检查是否符合功能分支格式: {spec-id}-{feature-name}
if [[ "$CURRENT_BRANCH" =~ ^[0-9]{3}- ]]; then
    VALID_PATTERN=1
    BRANCH_TYPE="功能分支"
fi

# 检查是否符合热修复格式: hotfix/{description}
if [[ "$CURRENT_BRANCH" =~ ^hotfix/ ]]; then
    VALID_PATTERN=1
    BRANCH_TYPE="热修复分支"
fi

# 检查是否符合实验分支格式: experiment/{feature-name}
if [[ "$CURRENT_BRANCH" =~ ^experiment/ ]]; then
    VALID_PATTERN=1
    BRANCH_TYPE="实验分支"
fi

if [ $VALID_PATTERN -eq 0 ]; then
    echo -e "${YELLOW}⚠️  警告: 分支名不符合规范${NC}"
    echo ""
    echo "当前分支: $CURRENT_BRANCH"
    echo ""
    echo -e "${YELLOW}推荐格式:${NC}"
    echo "  功能分支: {spec-id}-{feature-name}  (如: 004-kg-core)"
    echo "  热修复:   hotfix/{description}      (如: hotfix/webhook-crash)"
    echo "  实验:     experiment/{name}         (如: experiment/llm-integration)"
    echo ""
    read -p "继续执行? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
    BRANCH_TYPE="自定义分支"
else
    echo -e "${GREEN}✅ 分支类型: $BRANCH_TYPE${NC}"
    echo -e "${GREEN}✅ 分支名称: $CURRENT_BRANCH${NC}"
fi

# 检查 3: 分支是否基于最新 master
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  检查分支基线"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# 获取远程 master 最新状态
echo "正在获取远程 master 分支状态..."
git fetch origin master --quiet 2>/dev/null || true

# 检查是否基于最新 master
if git merge-base --is-ancestor origin/master HEAD 2>/dev/null; then
    echo -e "${GREEN}✅ 功能分支包含最新 master 的所有提交${NC}"
else
    echo -e "${YELLOW}⚠️  警告: 功能分支可能基于过期的 master 分支${NC}"
    echo ""
    echo "建议执行以下命令同步最新 master:"
    echo "  git checkout master"
    echo "  git pull origin master"
    echo "  git checkout $CURRENT_BRANCH"
    echo "  git rebase master"
    echo ""
    echo "这样可以避免后续合并冲突。"
    echo ""
    read -p "是否继续执行? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# 检查 4: 显示分支提交历史
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  分支提交历史(相对 master)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

COMMIT_COUNT=$(git log --oneline master..HEAD 2>/dev/null | wc -l | xargs)

if [ "$COMMIT_COUNT" -eq 0 ]; then
    echo -e "${YELLOW}当前分支没有新的提交(与 master 相同)${NC}"
else
    echo -e "${GREEN}当前分支有 $COMMIT_COUNT 个新提交:${NC}"
    echo ""
    git log --oneline --color master..HEAD
fi

# 最终通过
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo -e "${GREEN}✅ 分支检查通过,可以安全执行 spec-kit 命令${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

exit 0
