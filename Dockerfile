# 使用Python 3.9官方镜像
FROM python:3.9-slim

# 设置工作目录
WORKDIR /app

# 设置环境变量
ENV PYTHONUNBUFFERED=1
ENV FLASK_APP=app.py

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件
COPY requirements.txt .

# 安装Python依赖
RUN pip install --no-cache-dir -r requirements.txt -i https://mirrors.aliyun.com/pypi/simple/

# 复制项目文件
COPY . .

# 创建数据目录
RUN mkdir -p data logs

# 初始化数据库
RUN python init_db.py

# 暴露端口
EXPOSE 8080

# 启动命令
CMD ["python", "app.py"]

