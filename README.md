# EduAgent 2.0

> 基于大模型的个性化 Python 学习助手 — 智能出题、答疑解惑、规划学习路径

---

## 快速启动（5 分钟上手）

### 你需要准备什么

- 一台电脑（Windows / Mac / Linux 都可以）
- 安装了 **Docker Desktop**（[点此下载](https://www.docker.com/products/docker-desktop/)）
- 一个 **DeepSeek API Key**（[点此申请](https://platform.deepseek.com/)）

### 第 1 步：下载项目

```bash
git clone https://github.com/Circe1111/EduAgent.git
cd EduAgent
```

### 第 2 步：配置密钥

```bash
# 复制环境变量模板
cp .env.example .env
```

然后用记事本打开 `.env` 文件，找到这一行：

```
LLM_API_KEY=sk-your-api-key-here
```

替换成你的 DeepSeek API Key，例如：

```
LLM_API_KEY=sk-1234567890abcdef
```

### 第 3 步：一键启动

```bash
docker compose up -d
```

> 首次启动需要下载镜像，耗时 3-5 分钟。耐心等待即可。

### 第 4 步：打开浏览器

访问 **http://localhost:3000**

使用默认账号登录：

| 用户名 | 密码 |
|--------|------|
| `stu` | `123456` |

---

## 常见问题

**启动后页面显示空白或报错？**

等待 1-2 分钟让数据库初始化完成，然后刷新页面。

**如何关闭系统？**

```bash
docker compose down
```

**如何导入自己的教材？**

把 `.md` / `.txt` / `.pdf` / `.docx` 文件放进 `backend/docs/my_docs/`，然后运行：

```bash
docker exec eduagent-backend python scripts/ingest.py \
  --dir docs/my_docs --collection course_materials --provider local
```

**如何查看后台日志？**

```bash
docker compose logs -f backend
```

---

## 功能一览

| 功能 | 说明 |
|------|------|
| AI 对话 | 流式输出，支持 Markdown / 代码 / LaTeX 渲染 |
| 知识库检索 | 上传教材后自动检索相关内容生成回答 |
| 学习路径 | 可视化学习路线，点击节点查看资源 |
| AI 测验 | 每节点可"AI测一测"，自动评分 + 错题本 |
| 专注计时器 | 番茄钟 25 分钟，自动记录学习时长 |
| 学习日历 | 热力图展示学习活跃度 |
| 成就徽章 | 破晓者 / 连击达人 / 学霸，自动颁发 |
| 收藏夹 | AI 回答可收藏 |
| 暗色主题 | 支持亮色 / 暗色 / 跟随系统 |

---

## 项目结构

```
EduAgent/
├── backend/                  # 后端（Python + FastAPI）
│   ├── app/
│   │   ├── core/            # 配置、数据库连接
│   │   ├── agents/          # AI Agent 编排
│   │   ├── rag/             # 知识库检索
│   │   ├── api/             # REST API
│   │   └── db/              # 数据库模型
│   └── Dockerfile
├── frontend/                 # 前端（Vue 3）
│   ├── src/
│   │   ├── views/           # 页面
│   │   ├── components/      # 组件
│   │   └── api/             # API 调用
│   └── Dockerfile
├── docker-compose.yml        # Docker 一键启动配置
├── deploy/                   # 生产部署用配置文件
├── .env.example              # 环境变量模板
└── README.md
```

## 技术栈

| 层级 | 技术 |
|------|------|
| 前端 | Vue 3 + TypeScript + Element Plus |
| 后端 | Python 3.11 + FastAPI |
| 数据库 | MySQL 8.0 |
| 向量检索 | Qdrant |
| 缓存 | Redis |
| LLM | DeepSeek / OpenAI 兼容接口 |
| 容器化 | Docker Compose |

## 许可

MIT
