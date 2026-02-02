# AI漫剧剧本生成系统

基于 RAG（检索增强生成）技术的 AI 漫剧剧本生成系统，使用 FastAPI + PostgreSQL + pgvector + LlamaIndex 构建。

## 技术栈

### 后端
- FastAPI - Web 框架
- PostgreSQL + pgvector - 向量数据库
- SQLAlchemy + asyncpg - 数据库 ORM
- LlamaIndex - RAG 框架
- Qwen2.5 / DeepSeek - LLM 模型
- BGE-M3 - Embedding 模型

### 前端
- Vue 3 - 前端框架
- Element Plus - UI 组件库
- Pinia - 状态管理
- Vue Router - 路由管理
- Vite - 构建工具

## 快速启动

### 开发模式（推荐）

开发模式支持代码热更新，修改代码后无需重启服务。

1. 确保已安装 Docker 和 Docker Compose

2. 复制并配置环境变量：
```bash
cp .env.example .env
```

3. 编辑 `.env` 文件，修改以下关键配置：
```env
# Ollama 远程服务地址（必填）
OLLAMA_BASE_URL=http://your-remote-ollama-server:11434

# LLM 和 Embedding 模型（根据你的 Ollama 服务配置）
LLM_MODEL=qwen2.5:7b
EMBEDDING_MODEL=BAAI/bge-m3

# 数据库密码（生产环境请修改）
POSTGRES_PASSWORD=your-secure-password

# 后端密钥（生产环境请修改）
SECRET_KEY=your-secret-key-here-change-in-production
```

4. 启动开发环境：
```bash
docker-compose -f docker-compose-dev.yml up -d
```

5. 访问系统：
- 前端: http://localhost:5173
- 后端 API: http://localhost:8000
- API 文档: http://localhost:8000/docs

6. 停止开发环境：
```bash
docker-compose -f docker-compose-dev.yml down
```

### 本地开发（不使用 Docker）

#### 后端
```bash
cd backend
pip install -r requirements.txt
cp .env.example .env
# 修改 .env 中的 OLLAMA_BASE_URL 为你的远程 Ollama 地址
python -m app.main
```

#### 前端
```bash
cd frontend
npm install
npm run dev
```

## 项目结构

```
niupi/
├── docs/                    # 技术文档
├── backend/                 # 后端服务
│   ├── app/
│   │   ├── api/            # API 路由
│   │   ├── db/             # 数据库配置
│   │   ├── models/         # 数据库模型
│   │   ├── schemas/        # Pydantic 模式
│   │   ├── services/       # 业务逻辑（RAG 服务）
│   │   ├── config.py       # 配置管理
│   │   └── main.py         # 应用入口
│   ├── requirements.txt
│   ├── Dockerfile
│   └── .env.example
├── frontend/                # 前端服务
│   ├── src/
│   │   ├── api/            # API 接口封装
│   │   ├── views/          # 页面组件
│   │   ├── router/         # 路由配置
│   │   ├── App.vue
│   │   └── main.js
│   ├── Dockerfile          # 生产环境构建
│   ├── Dockerfile.dev      # 开发环境（热更新）
│   └── nginx.conf
├── .env.example             # 环境变量模板
└── docker-compose-dev.yml   # 开发环境配置（支持热更新）
```

## 核心功能

### 1. 剧本生成
- 基于剧情上下文生成漫剧剧本
- 支持冲突类型和情绪类型筛选
- 多角色出场配置
- RAG 检索参考剧情单元

### 2. 剧情单元管理
- 创建和管理剧情单元
- 多维度元数据标注（冲突、情绪、剧情功能）
- 基于向量相似度的智能检索
- 元数据过滤检索

### 3. RAG 检索
- 基于 LlamaIndex 的向量检索
- 混合搜索模式（语义 + 元数据过滤）
- 支持多个索引维度（冲突、情绪、人物关系、剧情功能）

## API 接口

### 剧本生成
- POST /api/generate-script - 生成剧本
- POST /api/story-units/search - 检索剧情单元

### 剧情单元管理
- POST /api/story-units - 创建剧情单元
- GET /api/story-units/{id} - 获取剧情单元
- GET /api/story-units - 列出剧情单元

## 数据库设计

### story_units（剧情单元表）
- 场景、核心冲突、情绪曲线
- 冲突类型、情绪类型、剧情功能
- 原始文本、生成结果
- 时间位置、依赖关系
- 置信度评分

### characters（角色表）
- 角色名称、角色类型
- 性格特征、背景设定
- 外貌描述、台词风格

## 配置说明

### 环境变量（.env 文件）

| 变量名 | 说明 | 默认值 |
|--------|------|--------|
| POSTGRES_USER | 数据库用户名 | postgres |
| POSTGRES_PASSWORD | 数据库密码 | postgres |
| POSTGRES_DB | 数据库名称 | ai_drama |
| POSTGRES_PORT | 数据库端口 | 5432 |
| DATABASE_URL | 数据库连接字符串 | - |
| EMBEDDING_MODEL | Embedding 模型 | BAAI/bge-m3 |
| LLM_MODEL | LLM 模型 | qwen2.5:7b |
| OLLAMA_BASE_URL | Ollama 服务地址 | - |
| BACKEND_PORT | 后端端口 | 8000 |
| SECRET_KEY | JWT 密钥 | - |
| FRONTEND_PORT | 前端端口 | 5173 |

## 开发说明

### 后端热更新
后端使用 `uvicorn --reload` 启动，修改 Python 代码后会自动重启服务。

### 前端热更新
前端使用 Vite 开发服务器，修改 Vue/JS/CSS 代码后会自动刷新页面。

### 日志查看
```bash
# 查看所有服务日志
docker-compose -f docker-compose-dev.yml logs -f

# 只查看后端日志
docker-compose -f docker-compose-dev.yml logs -f backend

# 只查看前端日志
docker-compose -f docker-compose-dev.yml logs -f frontend
```
