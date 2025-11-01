# 安全审查清单

**版本**: 1.0.0
**日期**: 2025-11-01
**用途**: 提交代码前必须检查的安全项

## 敏感信息保护

### 🔴 严禁提交的内容

以下信息**绝对不能**提交到 git 仓库:

1. **API 凭证**
   - ❌ `app_key`: 真实的 API 密钥
   - ❌ `app_secret`: 真实的 API 密钥
   - ✅ 使用占位符: `YOUR_APP_KEY_HERE`, `YOUR_APP_SECRET_HERE`

2. **设备标识**
   - ❌ 真实的设备 GUID
   - ✅ 使用占位符: `XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX`

3. **用户数据**
   - ❌ 真实的微信号、昵称、头像 URL
   - ✅ 使用测试数据: `test_user_123`, `测试用户`

4. **配置文件**
   - ❌ `config/wechat.yaml` (包含真实凭证)
   - ✅ `config/wechat.yaml.example` (仅占位符)

## 提交前检查步骤

### 步骤 1: 检查 .gitignore

确保以下文件/目录已在 `.gitignore` 中:

```gitignore
# 配置文件(包含敏感信息)
config/wechat.yaml
config/*.yaml
!config/*.yaml.example

# 日志文件
logs/

# 环境变量
.env
.env.local
.env.*.local
```

### 步骤 2: 搜索敏感信息

运行以下命令搜索 staged 文件中的敏感信息:

```bash
# 检查 app_key (真实值不应出现)
git diff --cached | grep -i "[REDACTED_APP_KEY]"

# 检查 app_secret (真实值不应出现)
git diff --cached | grep -i "[REDACTED_APP_SECRET]"

# 检查设备 GUID (真实值不应出现)
git diff --cached | grep -i "[REDACTED_DEVICE_GUID]"

# 如果以上任何命令有输出,说明有敏感信息泄露!
```

### 步骤 3: 自动化检查脚本

创建 pre-commit hook 自动检查:

```bash
# .git/hooks/pre-commit
#!/bin/bash

SECRETS=(
    "[REDACTED_APP_KEY]"
    "[REDACTED_APP_SECRET]"
    "[REDACTED_DEVICE_GUID]"
)

for secret in "${SECRETS[@]}"; do
    if git diff --cached | grep -q "$secret"; then
        echo "❌ 错误: 检测到敏感信息 '$secret'"
        echo "请在提交前移除所有真实凭证!"
        exit 1
    fi
done

echo "✅ 安全检查通过"
exit 0
```

### 步骤 4: 检查文件状态

```bash
# 查看将要提交的文件
git status

# 查看具体变更内容
git diff --cached

# 确保 config/wechat.yaml 不在 staged 状态
git ls-files --cached | grep "config/wechat.yaml"
# 应该没有输出
```

## 文档安全规范

### 文档中的占位符标准

在文档(spec, quickstart, research 等)中使用以下占位符:

| 真实类型 | 占位符 | 示例 |
|---------|--------|------|
| API Key | `YOUR_APP_KEY_HERE` | - |
| API Secret | `YOUR_APP_SECRET_HERE` | - |
| 设备 GUID | `XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX` | - |
| 微信号 | `test_user_123` | 测试用户标识 |
| 昵称 | `测试用户` | 测试用户昵称 |
| 头像 URL | `https://example.com/avatar.jpg` | 示例图片 |

### JSON Schema 和契约文件

契约文件中的示例值必须使用占位符:

```json
{
  "app_key": "YOUR_APP_KEY_HERE",
  "app_secret": "YOUR_APP_SECRET_HERE",
  "path": "/user/get_info",
  "data": {
    "guid": "XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX"
  }
}
```

## 已知敏感文件列表

### 已加入 .gitignore (安全)

- ✅ `config/wechat.yaml` - 真实配置
- ✅ `logs/` - 日志目录
- ✅ `.env*` - 环境变量

### 可以提交 (不含敏感信息)

- ✅ `config/wechat.yaml.example` - 配置模板(仅占位符)
- ✅ `specs/**/*.md` - 规格文档(已清理)
- ✅ `specs/**/contracts/*.json` - JSON Schema(已清理)
- ✅ `tests/**/*.py` - 测试代码(使用 mock 数据)

## 紧急响应流程

### 如果敏感信息已提交到 git

1. **立即停止推送**: 不要 `git push` 到远程仓库
2. **重写历史记录**:
   ```bash
   # 使用 BFG Repo-Cleaner 或 git filter-branch
   git filter-branch --force --index-filter \
     "git rm --cached --ignore-unmatch config/wechat.yaml" \
     --prune-empty --tag-name-filter cat -- --all
   ```
3. **强制推送**(仅限未分享的分支):
   ```bash
   git push --force-with-lease
   ```
4. **撤销并重新生成凭证**: 联系 API 提供商吊销旧凭证

### 如果敏感信息已推送到 GitHub

1. **立即删除远程仓库** (如果是私有仓库)
2. **重新生成所有凭证**
3. **清理历史记录后重新推送**
4. **通知团队成员**: 所有人需要重新克隆仓库

## 定期审查

每月执行一次安全审查:

```bash
# 搜索所有文件中的潜在敏感信息
git grep -i "password"
git grep -i "secret"
git grep -i "token"
git grep -i "api_key"
git grep -i "credential"

# 检查 .gitignore 是否完整
git ls-files --others --ignored --exclude-standard
```

## 参考资源

- [GitHub Secret Scanning](https://docs.github.com/en/code-security/secret-scanning)
- [Git-secrets](https://github.com/awslabs/git-secrets)
- [BFG Repo-Cleaner](https://rtyley.github.io/bfg-repo-cleaner/)

---

**重要提醒**: 安全是项目的生命线,任何疏忽都可能导致严重后果。提交前必须仔细检查!
