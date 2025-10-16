#!/bin/bash

echo "=================================================="
echo "  呼叫中心管理系统 - CloudBase 快速部署脚本"
echo "=================================================="
echo ""

# 检查是否安装了tcb CLI
if ! command -v tcb &> /dev/null; then
    echo "❌ 未检测到 CloudBase CLI"
    echo "请先安装: npm install -g @cloudbase/cli"
    echo "然后运行: tcb login"
    exit 1
fi

echo "✅ CloudBase CLI 已安装"
echo ""

# 检查是否已登录
echo "检查登录状态..."
tcb env:list &> /dev/null
if [ $? -ne 0 ]; then
    echo "❌ 未登录 CloudBase"
    echo "请先运行: tcb login"
    exit 1
fi

echo "✅ 已登录 CloudBase"
echo ""

# 提示输入环境ID
echo "=================================================="
read -p "请输入你的 CloudBase 环境ID: " ENV_ID

if [ -z "$ENV_ID" ]; then
    echo "❌ 环境ID不能为空"
    exit 1
fi

echo ""
echo "开始部署到环境: $ENV_ID"
echo ""

# 更新cloudbaserc.json
echo "更新配置文件..."
sed -i.bak "s/{{env.ENV_ID}}/$ENV_ID/g" cloudbaserc.json
echo "✅ 配置文件已更新"
echo ""

# 执行部署
echo "=================================================="
echo "开始部署..."
echo "=================================================="
echo ""

tcb framework deploy

if [ $? -eq 0 ]; then
    echo ""
    echo "=================================================="
    echo "✅ 部署成功！"
    echo "=================================================="
    echo ""
    echo "下一步："
    echo "1. 访问上面显示的URL测试应用"
    echo "2. 在CloudBase控制台配置自定义域名"
    echo "3. 配置数据持久化（云数据库或CFS）"
    echo ""
else
    echo ""
    echo "=================================================="
    echo "❌ 部署失败"
    echo "=================================================="
    echo ""
    echo "请检查："
    echo "1. 环境ID是否正确"
    echo "2. 是否有足够的权限"
    echo "3. 查看详细错误信息"
    echo ""
    echo "恢复配置文件..."
    mv cloudbaserc.json.bak cloudbaserc.json
    exit 1
fi

echo "部署脚本执行完成"

