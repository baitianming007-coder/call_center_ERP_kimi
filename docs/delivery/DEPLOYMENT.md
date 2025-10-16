# 呼叫中心职场管理系统 - 部署指南

## 快速开始（开发环境）

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 初始化数据库

```bash
python init_db.py
```

这将创建：
- 数据库表结构
- 测试团队（A组、B组、C组）
- 测试员工数据（35名员工）
- 测试业绩数据（最近30天）
- 默认管理员账号

### 3. 启动应用

```bash
python app.py
```

或使用启动脚本（Mac/Linux）：

```bash
chmod +x run.sh
./run.sh
```

### 4. 访问系统

浏览器访问：http://127.0.0.1:5000

**默认账号：**
- 管理员：`admin` / `admin123`
- 经理：`manager` / `manager123`
- 员工：`a001` / `emp123`

---

## 生产环境部署

### 方案一：使用 Gunicorn + Nginx

#### 1. 安装 Gunicorn

```bash
pip install gunicorn
```

#### 2. 创建 Gunicorn 配置

创建 `gunicorn_config.py`：

```python
bind = "127.0.0.1:8000"
workers = 4
worker_class = "sync"
timeout = 30
keepalive = 2
accesslog = "logs/access.log"
errorlog = "logs/error.log"
loglevel = "info"
```

#### 3. 启动 Gunicorn

```bash
gunicorn -c gunicorn_config.py app:app
```

#### 4. 配置 Nginx

创建 `/etc/nginx/sites-available/callcenter`：

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /static {
        alias /path/to/callcenter/static;
        expires 30d;
    }
}
```

启用配置：

```bash
sudo ln -s /etc/nginx/sites-available/callcenter /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

### 方案二：使用 Docker

#### 1. 创建 Dockerfile

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN python init_db.py

EXPOSE 5000

CMD ["gunicorn", "-b", "0.0.0.0:5000", "app:app"]
```

#### 2. 构建镜像

```bash
docker build -t callcenter:latest .
```

#### 3. 运行容器

```bash
docker run -d \
  -p 5000:5000 \
  -v $(pwd)/data:/app/data \
  --name callcenter \
  callcenter:latest
```

---

## 数据库配置

### 切换到 MySQL

修改 `config.py`：

```python
# SQLite（开发）
# DATABASE = os.path.join(BASE_DIR, 'data', 'callcenter.db')

# MySQL（生产）
DATABASE_URI = 'mysql://user:password@localhost/callcenter?charset=utf8mb4'
```

修改 `core/database.py` 使用 MySQL 连接。

### 切换到 PostgreSQL

```python
DATABASE_URI = 'postgresql://user:password@localhost/callcenter'
```

---

## 安全配置

### 1. 修改密钥

**生产环境必须修改！**

```bash
# 生成随机密钥
python -c "import secrets; print(secrets.token_hex(32))"
```

修改 `config.py`：

```python
SECRET_KEY = 'your-random-secret-key-here'
ENCRYPTION_KEY = b'your-32-byte-encryption-key'
```

### 2. 配置 HTTPS

推荐使用 Let's Encrypt 免费证书：

```bash
sudo certbot --nginx -d your-domain.com
```

### 3. 限制访问

在 Nginx 中添加 IP 白名单：

```nginx
location / {
    allow 192.168.1.0/24;  # 允许内网
    deny all;               # 拒绝其他
    proxy_pass http://127.0.0.1:8000;
}
```

---

## 维护

### 备份数据库

SQLite：

```bash
cp data/callcenter.db data/callcenter_backup_$(date +%Y%m%d).db
```

MySQL：

```bash
mysqldump -u user -p callcenter > backup_$(date +%Y%m%d).sql
```

### 查看日志

```bash
tail -f logs/access.log
tail -f logs/error.log
```

### 更新系统

```bash
git pull
pip install -r requirements.txt
sudo systemctl restart callcenter
```

---

## 性能优化

### 1. 启用缓存

安装 Redis：

```bash
pip install redis flask-caching
```

### 2. 数据库索引

已在 `schema.sql` 中创建必要索引。

### 3. 静态文件 CDN

将 `static/` 目录部署到 CDN。

### 4. 负载均衡

使用 Nginx 配置多个 Gunicorn 实例：

```nginx
upstream callcenter {
    server 127.0.0.1:8001;
    server 127.0.0.1:8002;
    server 127.0.0.1:8003;
    server 127.0.0.1:8004;
}
```

---

## 监控

### 系统监控

- **Prometheus + Grafana**: 监控系统指标
- **Sentry**: 错误追踪
- **New Relic**: 性能监控

### 健康检查

添加健康检查路由：

```python
@app.route('/health')
def health():
    return {'status': 'ok', 'timestamp': datetime.now().isoformat()}
```

---

## 故障排除

### 问题：数据库连接失败

```bash
# 检查数据库文件权限
ls -la data/callcenter.db

# 检查目录权限
chmod 755 data
chmod 644 data/callcenter.db
```

### 问题：端口被占用

```bash
# 查找占用进程
lsof -i :5000

# 杀死进程
kill -9 <PID>
```

### 问题：依赖安装失败

```bash
# 使用国内镜像
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
```

---

## 技术支持

如有问题请联系开发团队。



