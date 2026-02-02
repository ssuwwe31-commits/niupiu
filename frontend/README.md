# AI漫剧剧本生成系统 - 前端

基于 Vue 3 + Element Plus 的剧本生成界面

## 技术栈

- Vue 3 - 前端框架
- Element Plus - UI 组件库
- Pinia - 状态管理
- Vue Router - 路由管理
- Axios - HTTP 客户端
- Vite - 构建工具

## 安装依赖

```bash
cd frontend
npm install
```

## 开发模式

```bash
npm run dev
```

访问 http://localhost:5173

## 构建生产版本

```bash
npm run build
```

## 预览生产构建

```bash
npm run preview
```

## 项目结构

```
frontend/
├── src/
│   ├── api/          # API 接口封装
│   ├── components/   # 可复用组件
│   ├── views/        # 页面组件
│   ├── router/       # 路由配置
│   ├── App.vue       # 根组件
│   └── main.js       # 应用入口
├── index.html        # HTML 模板
├── vite.config.js    # Vite 配置
└── package.json      # 依赖配置
```

## 功能说明

### 剧本生成页面

用户可以通过以下配置生成剧本：
- 剧情上下文描述
- 冲突类型选择（背叛、复仇、权力斗争等）
- 情绪类型选择（高燃、爽点、虐点等）
- 出场人物选择
- 场景设定

生成后显示：
- 生成的剧本内容
- 置信度评分
- 参考的剧情单元列表
