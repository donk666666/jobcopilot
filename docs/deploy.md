# 部署指南

## 前置条件
- 腾讯云轻量服务器 2C4G，Ubuntu 22.04
- 已连接 SSH

## 1. 服务器初始化

```bash
ssh root@<服务器IP>

apt update && apt upgrade -y
apt install -y docker.io docker-compose nginx certbot python3-certbot-nginx

systemctl enable docker --now
```

## 2. 上传项目

```bash
# 在本地
scp -r . root@<服务器IP>:/opt/smart-doc-qa/
```

## 3. 配置环境变量

```bash
ssh root@<服务器IP>
cd /opt/smart-doc-qa
cp .env.example .env
vim .env  # 填入 API Key 等信息
```

## 4. 启动服务

```bash
docker compose up -d --build
# 验证
curl http://localhost:8000/health
```

## 5. 配置 Nginx + SSL

创建 Nginx 配置：

```nginx
server {
    listen 80;
    server_name <你的域名>;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_read_timeout 120s;
    }
}
```

```bash
ln -s /etc/nginx/sites-available/qa-bot /etc/nginx/sites-enabled/
nginx -t && systemctl reload nginx

# SSL 证书
certbot --nginx -d <你的域名>
```

## 6. 配置飞书回调

1. 飞书开放平台 → 创建企业自建应用
2. 添加"机器人"能力
3. 事件订阅 → 请求网址填 `https://<域名>/feishu/callback`
4. 订阅 `im.message.receive_v1` 事件
5. 发布应用

## 7. 导入知识库

```bash
# 手动上传文档
curl -X POST https://<域名>/api/knowledge/upload -F "file=@文档.pdf"

# 或放到 data/docs 目录批量导入
```

## 故障排查

```bash
docker compose logs -f --tail 100
tail -f logs/app.log
```
