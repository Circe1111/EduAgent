# 我的教材文档

## 使用方法

将你的教材文档放入此目录，支持以下格式：

| 格式 | 说明 |
|------|------|
| `.md` | Markdown 文件（推荐） |
| `.txt` | 纯文本文件 |
| `.pdf` | PDF 文档（需安装 PyMuPDF） |

## 组织建议

按知识点组织文件，例如：

```
my_docs/
├── 01-变量与数据类型.md
├── 02-控制流.md
├── 03-函数.md
├── 04-列表与字典.md
└── 习题集.pdf
```

## 导入命令

```bash
# 在 docker 容器内执行
docker exec -it eduagent-backend python scripts/ingest.py \
  --dir docs/my_docs \
  --collection course_materials \
  --rebuild   # 首次导入或需要重建索引时加此参数
```
