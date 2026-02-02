# AI漫剧剧本生成系统 - 后端

基于 FastAPI + PostgreSQL + LlamaIndex 的 RAG 剧本生成服务

## 技术栈

- FastAPI - Web 框架
- PostgreSQL + pgvector - 向量数据库
- SQLAlchemy + asyncpg - 数据库 ORM
- LlamaIndex - RAG 框架
- Qwen2.5 / DeepSeek - LLM 模型
- BGE-M3 - Embedding 模型

## 安装依赖

```bash
cd backend
pip install -r requirements.txt
```

## 环境配置

复制 `.env.example` 为 `.env` 并配置数据库连接等信息：

```bash
cp .env.example .env
```

## 数据库准备

1. 确保已安装 PostgreSQL 并启用 pgvector 扩展
2. 创建数据库：

```sql
CREATE DATABASE ai_drama;
```

## 启动服务

```bash
cd backend
python -m app.main
```

或使用 uvicorn：

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## API 文档

启动服务后访问：
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## 主要接口

- POST /api/generate-script - 生成剧本
- POST /api/story-units/search - 检索剧情单元
- POST /api/story-units - 创建剧情单元
- GET /api/story-units/{id} - 获取剧情单元
- GET /api/story-units - 列出剧情单元

## 项目结构

```
backend/
├── app/
│   ├── api/          # API 路由
│   ├── db/           # 数据库配置
│   ├── models/       # 数据库模型
│   ├── schemas/      # Pydantic 模式
│   ├── services/     # 业务逻辑
│   ├── config.py     # 配置管理
│   └── main.py       # 应用入口
├── requirements.txt  # Python 依赖
└── .env.example      # 环境变量示例
```
