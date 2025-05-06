#!/bin/bash

echo "=== Backpack 交易机器人安装脚本 ==="
echo "适用于 Ubuntu 系统"
echo ""

# 检查系统
if [ -f /etc/os-release ]; then
    . /etc/os-release
    OS=$NAME
    VER=$VERSION_ID
    echo "检测到系统: $OS $VER"
else
    echo "无法检测系统类型，将尝试继续安装..."
    OS="Unknown"
fi

# 检查是否是Ubuntu
if [[ "$OS" != *"Ubuntu"* ]] && [[ "$OS" != "Unknown" ]]; then
    echo "警告: 此脚本主要针对Ubuntu系统优化，您的系统是 $OS"
    read -p "是否继续安装? (y/n): " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "安装已取消"
        exit 1
    fi
fi

echo "=== 安装依赖包 ==="
# 更新软件源
sudo apt-get update

# 安装Python和pip
echo "正在安装Python和pip..."
sudo apt-get install -y python3 python3-pip

# 安装PM2
echo "正在安装PM2..."
sudo apt-get install -y nodejs npm
sudo npm install pm2 -g

# 安装Python依赖
echo "正在安装Python依赖..."
pip3 install aiohttp requests

# 检查安装结果
if [ $? -ne 0 ]; then
    echo "安装Python依赖失败，请检查错误信息"
    exit 1
fi

# 给脚本添加执行权限
chmod +x backpack_bot.py

echo "=== 安装完成 ==="
echo "现在可以运行交易机器人了"
echo ""
echo "正在启动配置菜单..."
echo ""

# 启动配置菜单
python3 backpack_bot.py

# 完成
echo "安装和配置完成。"
echo "您可以随时运行 'python3 backpack_bot.py' 打开配置菜单"
echo "或者运行 'pm2 start backpack_bot.py --name backpack_bot --interpreter python3 -- --run' 启动交易机器人"
