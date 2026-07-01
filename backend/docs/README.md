# 教材文档目录

## 目录结构

```
docs/
├── test_data/       # 测试用教材（Python 基础教学材料）
│   ├── 01-python-basics.md
│   ├── 02-control-flow.md
│   └── 03-functions.md
├── my_docs/         # 【入口】放入你自己的教材文档
│   └── README.md    # 使用说明
└── README.md        # 本文件
```

## 快速导入测试数据

```bash
# 进入后端容器
docker exec -it eduagent-backend bash

# 导入测试数据到 Qdrant + MySQL
python scripts/ingest.py --dir docs/test_data --collection course_materials

# 查看导入结果
python scripts/ingest.py --stats
```

## 接入你自己的教材

1. 将你的文档（支持 `.md`、`.txt`、`.pdf`）放入 `docs/my_docs/`
2. 运行导入命令即可
