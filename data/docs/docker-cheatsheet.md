# Docker 速查

## 镜像管理

```bash
# 构建镜像
docker build -t myapp:v1.0 .

# 拉取/推送
docker pull python:3.11-slim
docker push myapp:v1.0

# 查看/清理
docker images
docker rmi myapp:v1.0
docker image prune -a    # 删除未使用的镜像
```

## 容器操作

```bash
# 运行容器
docker run -d --name app -p 8000:8000 -v ./data:/app/data myapp:v1.0

# 查看状态
docker ps
docker ps -a             # 含已停止的容器
docker stats             # 实时资源占用

# 进入容器
docker exec -it app bash

# 日志
docker logs -f --tail 100 app

# 停止/启动/重启
docker stop app
docker start app
docker restart app

# 删除
docker rm app
docker rm -f app         # 强制删除运行中的容器
```

## Docker Compose

```yaml
version: "3.9"
services:
  app:
    build: .
    ports:
      - "8000:8000"
    volumes:
      - ./data:/app/data
      - ./logs:/app/logs
    environment:
      - LLM_API_KEY=${LLM_API_KEY}
      - EMBEDDING_MODEL=./models/bge-small-zh-v1.5
    restart: unless-stopped
```

```bash
docker compose up -d         # 后台启动
docker compose down          # 停止并删除
docker compose logs -f       # 查看日志
docker compose ps            # 查看服务状态
docker compose exec app bash # 进入服务容器
```

## Dockerfile 最佳实践

```dockerfile
FROM python:3.11-slim
WORKDIR /app

# 1. 先复制依赖文件再安装，利用缓存层
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 2. 最后复制源码
COPY app/ ./app/

# 3. 最小权限
RUN useradd -m appuser && chown -R appuser:appuser /app
USER appuser

# 4. 健康检查
HEALTHCHECK --interval=30s CMD curl -f http://localhost:8000/health || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

## 调试命令

```bash
# 查看容器详情（环境变量、挂载、网络）
docker inspect app

# 查看资源占用
docker stats --no-stream

# 查看磁盘使用
docker system df

# 查看容器内进程
docker top app

# 临时调试容器
docker run --rm -it --entrypoint bash myapp:v1.0
```

## 网络与卷

```bash
# 创建网络
docker network create mynet
docker run --network mynet ...

# 数据卷
docker volume create mydata
docker run -v mydata:/app/data ...
docker volume ls
docker volume rm mydata
```
