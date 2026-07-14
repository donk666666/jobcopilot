# Linux 常用命令速查

## 文件操作

```bash
# 查找文件
find /app -name "*.log" -mtime -7     # 最近7天修改的日志
find . -type f -size +10M              # 大于10M的文件
find . -name "*.pyc" -delete           # 删除所有 .pyc

# 文件内容
grep -r "ERROR" /app/logs/             # 递归搜索
grep -v "DEBUG" app.log                # 排除匹配行
tail -f -n 100 app.log                 # 实时跟踪末尾100行
head -n 20 data.csv                    # 查看前20行

# 文件统计
wc -l file.txt                         # 行数
du -sh /app/data/                      # 目录大小
df -h                                  # 磁盘使用情况
```

## 进程管理

```bash
ps aux | grep uvicorn                  # 查找进程
kill -9 12345                          # 强制终止
pkill -f uvicorn                       # 按名称终止
top                                    # 实时进程监控
htop                                   # 更友好的 top

# 后台运行
nohup python app.py > log.txt 2>&1 &
screen -S mysession                    # 创建命名会话
screen -r mysession                    # 恢复会话

# systemd 服务
systemctl status nginx
systemctl start docker
systemctl enable docker                # 开机自启
journalctl -u nginx -f                 # 查看服务日志
```

## 权限管理

```bash
chmod 755 script.sh                    # rwxr-xr-x
chmod 644 config.ini                   # rw-r--r--
chown user:group file.txt
chown -R appuser:appuser /app/         # 递归修改

# 权限数字含义
# 4=读 2=写 1=执行
# 755 = rwxr-xr-x (所有者全权限，组和其他人只读执行)
# 644 = rw-r--r-- (所有者读写，组和其他人只读)
```

## 网络

```bash
# 端口与连接
netstat -tlnp                          # 监听端口
ss -tlnp                               # 同上，更快
lsof -i :8000                          # 查看占用8000端口的进程

# 测试与调试
curl -X POST http://localhost:8000/api  # HTTP 请求
curl -I https://example.com             # 只看响应头
ping -c 4 google.com                    # 连通性测试
traceroute google.com                   # 路由追踪

# 防火墙（ufw）
ufw enable
ufw allow 8000
ufw status
```

## 压缩与传输

```bash
# tar
tar -czf archive.tar.gz dir/           # 打包压缩
tar -xzf archive.tar.gz                # 解压
tar -czf - dir/ | ssh user@host "tar -xzf -"  # 远程传输

# scp / rsync
scp file.txt user@host:/path/
rsync -avz ./app/ user@host:/app/      # 增量同步

# 压缩
gzip file.txt
gunzip file.txt.gz
zip -r archive.zip dir/
```

## 文本处理

```bash
# sed
sed -i 's/old/new/g' file.txt          # 全局替换
sed -i '5,10d' file.txt                # 删除5-10行

# awk
awk '{print $1, $3}' data.log          # 打印第1、3列
awk '$3 > 100' data.log                # 过滤第3列>100的行

# 管道组合
cat app.log | grep ERROR | awk '{print $1,$2}' | sort | uniq -c | sort -rn
```

## 性能诊断

```bash
top -c                                  # CPU/内存概览
free -h                                 # 内存使用
iostat -x 1                             # 磁盘 IO
vmstat 1                                # 虚拟内存统计
strace -p 12345                         # 跟踪进程系统调用
```
