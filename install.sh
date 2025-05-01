#!/bin/bash

# Backpack 交易所网格交易机器人安装脚本

echo "====================================="
echo "Backpack 交易所网格交易机器人安装程序"
echo "====================================="

# 检查Python是否已安装
if ! command -v python3 &> /dev/null; then
    echo "错误: 未安装Python 3。请先安装Python 3。"
    exit 1
fi

# 检查pip是否已安装
if ! command -v pip3 &> /dev/null; then
    echo "错误: 未安装pip3。请先安装pip3。"
    exit 1
fi

# 创建虚拟环境（可选）
read -p "是否创建虚拟环境? (y/n): " create_venv
if [[ $create_venv == "y" || $create_venv == "Y" ]]; then
    # 检查venv模块是否可用
    if ! python3 -c "import venv" &> /dev/null; then
        echo "错误: Python venv模块不可用。请先安装。"
        exit 1
    fi
    
    echo "创建虚拟环境..."
    python3 -m venv venv
    
    # 激活虚拟环境
    source venv/bin/activate
    echo "虚拟环境已激活。"
else
    echo "跳过虚拟环境创建。"
fi

# 安装Python依赖
echo "安装Python依赖..."
pip3 install -r requirements.txt

# 检查Node.js是否已安装
if ! command -v node &> /dev/null; then
    echo "警告: 未安装Node.js。PM2需要Node.js。"
    echo "如果要使用PM2进行后台进程，请安装Node.js。"
else
    # 检查PM2是否已安装
    if ! command -v pm2 &> /dev/null; then
        echo "PM2未安装。正在安装PM2..."
        npm install -g pm2
        
        if [ $? -eq 0 ]; then
            echo "PM2安装成功。"
        else
            echo "安装PM2出错。请手动安装：'npm install -g pm2'。"
        fi
    else
        echo "PM2已安装。"
    fi
fi

# 创建必要的目录
mkdir -p configs

# 为API密钥创建.env文件
if [ ! -f .env ]; then
    echo "为API密钥创建.env文件..."
    echo "BACKPACK_API_KEY=" > .env
    echo "BACKPACK_API_SECRET=" >> .env
    echo ".env文件已创建。您需要添加您的API密钥。"
else
    echo ".env文件已存在。"
fi

echo ""
echo "安装完成！"
echo ""
echo "开始使用机器人:"
echo "1. 通过运行以下命令配置API密钥: python backpack_bot_manager.py menu"
echo "2. 通过菜单设置交易参数"
echo "3. 使用PM2或交互模式启动机器人"
echo ""
echo "享受自动化网格交易！" 
