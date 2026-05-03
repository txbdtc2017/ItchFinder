# ItchFinder

从 Hacker News / V2EX / Reddit 抓取"抱怨类"内容，关键词打分，帮你 10 分钟发现潜在产品机会。

## 安装

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## 运行

推荐用 Docker Compose 启动:

```bash
docker compose up -d --build
# 访问 http://127.0.0.1:18081
```

查看日志:

```bash
docker compose logs -f itchfinder
```

停止:

```bash
docker compose down
```

容器内监听 `8000`,宿主机映射到 `18081`,避免和本机已有 Docker 项目冲突。当前目录会挂载到容器 `/app`,所以 `data.db` 会继续保存在项目根目录。

本机 Python 方式仍可用于调试:

```bash
python main.py
# 访问启动时打印的地址，例如 http://127.0.0.1:8000
```

如果本机调试时 8000 端口被 Docker 等本地服务占用，程序会自动换到下一个可用端口。

启动后立即抓取一次，之后每小时自动抓取。数据存在 `data.db`，重启不丢失。

## 改关键词

编辑 `keywords.py` 里的 `PAIN_KEYWORDS_ZH` 和 `PAIN_KEYWORDS_EN` 列表，保存即可。下次抓取的新数据会用新关键词打分（已入库的不会重新打分）。

## 改 Reddit subreddit

编辑 `sources/reddit.py` 顶部的 `SUBREDDITS` 列表，保存即可。
