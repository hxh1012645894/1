# 药品注册批件智能管理系统

## 项目结构

```
批件注册/
├── backend/          # 后端 FastAPI 项目
│   ├── main.py       # FastAPI 入口文件
│   ├── processor.py  # 核心处理逻辑
│   ├── requirements.txt
│   └── venv/         # Python 虚拟环境
└── frontend/         # 前端 Vue 3 项目
    ├── src/
    ├── package.json
    └── vite.config.js
```

## 快速开始

### 1. 配置后端

进入 backend 目录并激活虚拟环境：

```bash
cd backend
# Windows
venv\Scripts\activate
```

配置 API 密钥（编辑 `processor.py` 文件）：
```python
LLM_API_KEY = "你的真实API密钥"
LLM_API_URL = "https://coding.dashscope.aliyuncs.com/apps/anthropic"
LLM_MODEL = "qwen3-coder-next"
TEXTIN_APP_ID = "你的TEXTIN_APP_ID"
TEXTIN_SECRET_CODE = "你的TEXTIN_SECRET_CODE"
```

启动后端服务：
```bash
python main.py
# 或者
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### 2. 配置前端

进入 frontend 目录：
```bash
cd ../frontend
npm run dev
```

访问 http://localhost:5173 即可使用。

## 功能说明

1. **批量上传解析**：支持 PDF 或 JPG/PNG 文件上传，系统自动拆分、OCR 和智能提取
2. **批件台账查看**：查看所有已入库的批件记录，支持展开详情和 PDF 预览

## 数据库

系统使用 SQLite 存储数据，数据库文件为 `records.db`，位于 backend 目录下。

## 注意事项

- 前端通过 Vite 代理访问后端 API（/api 路径代理到 http://localhost:8000）
- 确保后端服务在 8000 端口运行
- 确保前端服务在 5173 端口运行
