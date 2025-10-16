#!/bin/bash

# 呼叫中心职场管理系统启动脚本

echo "========================================"
echo "  呼叫中心职场管理系统"
echo "========================================"

# 检查 Python 环境
if ! command -v python3 &> /dev/null
then
    echo "错误: 未找到 python3，请先安装 Python 3"
    exit 1
fi

# 检查依赖
echo "检查依赖..."
python3 -c "import flask" 2>/dev/null || {
    echo "安装依赖..."
    pip3 install -r requirements.txt
}

# 检查数据库
if [ ! -f "data/callcenter.db" ]; then
    echo "数据库不存在，正在初始化..."
    python3 init_db.py
else
    echo "数据库已存在"
fi

# 启动应用
echo "========================================"
echo "启动应用..."
echo "========================================"
python3 app.py



