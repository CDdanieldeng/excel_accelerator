# API Key 配置指南

## 如何设置 OpenAI API Key

Chat with Data 功能需要 OpenAI API Key 才能工作。有以下几种方式设置：

### 方式 1: 使用 .env 文件（推荐）

1. 在项目根目录创建 `.env` 文件：

```bash
# 在项目根目录下
touch .env
```

2. 编辑 `.env` 文件，添加你的 API Key：

```env
OPENAI_API_KEY=sk-your-actual-api-key-here
```

3. 可选：修改使用的模型（默认是 `gpt-4o-mini`）：

```env
OPENAI_API_KEY=sk-your-actual-api-key-here
OPENAI_MODEL=gpt-4o-mini
```

### 方式 2: 使用环境变量

#### Linux/macOS:

```bash
export OPENAI_API_KEY=sk-your-actual-api-key-here
```

#### Windows (PowerShell):

```powershell
$env:OPENAI_API_KEY="sk-your-actual-api-key-here"
```

#### Windows (CMD):

```cmd
set OPENAI_API_KEY=sk-your-actual-api-key-here
```

### 方式 3: 在启动命令中设置

```bash
# Linux/macOS
OPENAI_API_KEY=sk-your-actual-api-key-here uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload

# Windows PowerShell
$env:OPENAI_API_KEY="sk-your-actual-api-key-here"; uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```

## 获取 OpenAI API Key

1. 访问 [OpenAI Platform](https://platform.openai.com/)
2. 登录或注册账号
3. 进入 [API Keys 页面](https://platform.openai.com/api-keys)
4. 点击 "Create new secret key"
5. 复制生成的 API Key（格式类似：`sk-...`）

⚠️ **注意**: API Key 只显示一次，请妥善保管！

## 验证配置

启动后端服务后，检查日志中是否有以下信息：

- ✅ 如果看到 "Loaded environment variables from ..." 说明 .env 文件已加载
- ⚠️ 如果看到 "OPENAI_API_KEY not set, LLM features will not work" 说明 API Key 未设置

## 常见问题

### Q: 如何检查 API Key 是否设置成功？

A: 启动后端服务，尝试使用 Chat with Data 功能。如果 API Key 未设置，会返回错误信息。

### Q: 可以使用其他 LLM 模型吗？

A: 目前代码使用 OpenAI 的模型。可以通过设置 `OPENAI_MODEL` 环境变量来切换模型，例如：
- `gpt-4o-mini` (默认，成本较低)
- `gpt-4o`
- `gpt-4-turbo`

### Q: API Key 安全吗？

A: 
- ✅ `.env` 文件已在 `.gitignore` 中，不会被提交到 Git
- ⚠️ 不要将 API Key 提交到代码仓库
- ⚠️ 不要在前端代码中暴露 API Key

