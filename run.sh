#!/bin/bash

# 颜色设置
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

print_color() {
    printf "${1}%s${NC}\n" "${2}"
}

# 验证脚本是否正确下载
if [ "$(head -n1 $0)" = "404: Not Found" ]; then
    print_color $RED "错误：无法下载安装脚本。请检查仓库地址是否正确。"
    exit 1
fi

# 检查 Python 环境
print_color $YELLOW "正在检查 Python 环境..."
if ! command -v python3 &> /dev/null; then
    print_color $RED "错误：未安装 Python3。请安装 Python 3.8 或更高版本。"
    exit 1
fi

# 创建工作目录
INSTALL_DIR="$HOME/backpack-grid-bot"
print_color $GREEN "正在创建安装目录：$INSTALL_DIR..."
mkdir -p "$INSTALL_DIR"
cd "$INSTALL_DIR" || exit 1

# 创建并激活虚拟环境
print_color $GREEN "正在创建 Python 虚拟环境..."
python3 -m venv venv
source venv/bin/activate

# 安装依赖
print_color $GREEN "正在安装依赖包..."
pip install --upgrade pip
pip install aiohttp==3.9.1 python-dotenv==1.0.0 websockets==12.0 pandas==2.1.4 numpy==1.26.2 loguru==0.7.2

# 下载机器人脚本
print_color $GREEN "正在下载机器人脚本..."
BOT_URL="https://raw.githubusercontent.com/yinghao888/grid-trading-bot/main/bot.py"
if ! curl -f -s "$BOT_URL" -o bot.py; then
    print_color $RED "错误：无法从 $BOT_URL 下载机器人脚本"
    print_color $RED "请检查仓库是否存在且为公开仓库。"
    exit 1
fi

# 验证下载是否成功
if [ ! -s bot.py ]; then
    print_color $RED "错误：下载的 bot.py 文件为空。安装失败。"
    exit 1
fi

print_color $GREEN "安装完成！"
print_color $GREEN "正在启动网格交易机器人..."
python bot.py 
