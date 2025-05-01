#!/bin/bash

# 颜色设置
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# 安装目录
INSTALL_DIR="$HOME/backpack-grid-bot"

print_color() {
    printf "${1}%s${NC}\n" "${2}"
}

clear_screen() {
    clear
}

print_header() {
    clear_screen
    echo "=================================================="
    print_color $BLUE "Backpack 网格交易机器人管理系统"
    echo "=================================================="
    echo ""
}

initialize_environment() {
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
    print_color $GREEN "正在创建安装目录：$INSTALL_DIR..."
    mkdir -p "$INSTALL_DIR"
    cd "$INSTALL_DIR" || exit 1

    # 创建并激活虚拟环境
    if [ ! -d "venv" ]; then
        print_color $GREEN "正在创建 Python 虚拟环境..."
        python3 -m venv venv
    fi
    source venv/bin/activate

    # 安装依赖
    print_color $GREEN "正在安装依赖包..."
    pip install --upgrade pip > /dev/null
    pip install aiohttp==3.9.1 python-dotenv==1.0.0 websockets==12.0 pandas==2.1.4 numpy==1.26.2 loguru==0.7.2 > /dev/null

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
    sleep 1
}

configure_api_keys() {
    print_header
    print_color $YELLOW "配置 API 密钥"
    echo ""
    
    read -p "请输入您的 API Key: " api_key
    read -p "请输入您的 API Secret: " api_secret
    
    if [ -z "$api_key" ] || [ -z "$api_secret" ]; then
        print_color $RED "错误：API Key 和 Secret 不能为空！"
        read -n 1 -s -r -p "按任意键继续..."
        return 1
    fi
    
    # 保存到.env文件
    echo "BACKPACK_API_KEY=$api_key" > "$INSTALL_DIR/.env"
    echo "BACKPACK_API_SECRET=$api_secret" >> "$INSTALL_DIR/.env"
    
    print_color $GREEN "✅ API 密钥配置成功！"
    read -n 1 -s -r -p "按任意键继续..."
    return 0
}

configure_trading_params() {
    print_header
    print_color $YELLOW "配置交易参数"
    echo ""
    
    read -p "交易对 (默认: BTC_USDC_PERP): " symbol
    symbol=${symbol:-BTC_USDC_PERP}
    
    read -p "网格数量 (默认: 10): " grid_num
    grid_num=${grid_num:-10}
    
    read -p "总投资额 USDC (默认: 1000): " total_investment
    total_investment=${total_investment:-1000}
    
    read -p "网格间距 % (默认: 2): " grid_spread
    grid_spread=${grid_spread:-2}
    
    read -p "止损百分比 % (默认: 10): " stop_loss
    stop_loss=${stop_loss:-10}
    
    read -p "止盈百分比 % (默认: 20): " take_profit
    take_profit=${take_profit:-20}
    
    # 保存到配置文件
    echo "SYMBOL=$symbol" > "$INSTALL_DIR/config.txt"
    echo "GRID_NUM=$grid_num" >> "$INSTALL_DIR/config.txt"
    echo "TOTAL_INVESTMENT=$total_investment" >> "$INSTALL_DIR/config.txt"
    echo "GRID_SPREAD=$grid_spread" >> "$INSTALL_DIR/config.txt"
    echo "STOP_LOSS=$stop_loss" >> "$INSTALL_DIR/config.txt"
    echo "TAKE_PROFIT=$take_profit" >> "$INSTALL_DIR/config.txt"
    
    print_color $GREEN "✅ 交易参数配置成功！"
    read -n 1 -s -r -p "按任意键继续..."
    return 0
}

start_bot() {
    if [ ! -f "$INSTALL_DIR/.env" ]; then
        print_color $RED "❌ 错误：请先配置 API 密钥！"
        read -n 1 -s -r -p "按任意键继续..."
        return 1
    fi
    
    if [ ! -f "$INSTALL_DIR/config.txt" ]; then
        print_color $RED "❌ 错误：请先配置交易参数！"
        read -n 1 -s -r -p "按任意键继续..."
        return 1
    fi
    
    print_color $GREEN "正在启动机器人..."
    cd "$INSTALL_DIR" || exit 1
    source venv/bin/activate
    
    # 启动 Python 脚本
    python3 -c "
import asyncio
import sys
import os
import importlib.util

# 加载机器人模块
spec = importlib.util.spec_from_file_location('bot_module', 'bot.py')
bot_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bot_module)

# 读取配置
config_file = 'config.txt'
env_file = '.env'

# 加载环境变量
with open(env_file, 'r') as f:
    for line in f:
        if '=' in line:
            key, value = line.strip().split('=', 1)
            os.environ[key] = value

# 读取交易配置
config_values = {}
with open(config_file, 'r') as f:
    for line in f:
        if '=' in line:
            key, value = line.strip().split('=', 1)
            config_values[key] = value

# 创建配置
config = bot_module.GridConfig(
    symbol=config_values.get('SYMBOL', 'BTC_USDC_PERP'),
    grid_num=int(config_values.get('GRID_NUM', '10')),
    total_investment=float(config_values.get('TOTAL_INVESTMENT', '1000')),
    grid_spread=float(config_values.get('GRID_SPREAD', '2'))/100,
    stop_loss_pct=float(config_values.get('STOP_LOSS', '10'))/100,
    take_profit_pct=float(config_values.get('TAKE_PROFIT', '20'))/100,
)

# 创建并启动机器人
async def run_bot():
    bot = bot_module.GridTradingBot(config)
    await bot.initialize()
    await bot.start()

# 运行机器人
try:
    print('机器人已启动! 按Ctrl+C停止...')
    asyncio.run(run_bot())
except KeyboardInterrupt:
    print('接收到停止信号，正在停止机器人...')
except Exception as e:
    print(f'发生错误: {e}')
    raise
" &

    BOT_PID=$!
    echo $BOT_PID > "$INSTALL_DIR/bot.pid"
    print_color $GREEN "✅ 机器人已成功启动！(PID: $BOT_PID)"
    read -n 1 -s -r -p "按任意键继续..."
    return 0
}

stop_bot() {
    if [ -f "$INSTALL_DIR/bot.pid" ]; then
        BOT_PID=$(cat "$INSTALL_DIR/bot.pid")
        if ps -p $BOT_PID > /dev/null; then
            kill $BOT_PID
            print_color $GREEN "✅ 机器人已停止！(PID: $BOT_PID)"
        else
            print_color $RED "❌ 机器人进程未运行！"
        fi
        rm "$INSTALL_DIR/bot.pid"
    else
        print_color $RED "❌ 机器人未启动！"
    fi
    read -n 1 -s -r -p "按任意键继续..."
    return 0
}

show_stats() {
    print_header
    print_color $YELLOW "统计信息"
    echo ""
    
    if [ ! -f "$INSTALL_DIR/bot.pid" ]; then
        print_color $RED "❌ 机器人未启动，无法显示统计信息！"
        read -n 1 -s -r -p "按任意键继续..."
        return 1
    fi
    
    BOT_PID=$(cat "$INSTALL_DIR/bot.pid")
    if ! ps -p $BOT_PID > /dev/null; then
        print_color $RED "❌ 机器人进程未运行！"
        rm "$INSTALL_DIR/bot.pid"
        read -n 1 -s -r -p "按任意键继续..."
        return 1
    fi
    
    print_color $GREEN "机器人正在运行 (PID: $BOT_PID)"
    print_color $GREEN "查看日志文件获取更多信息: $INSTALL_DIR/grid_bot.log"
    read -n 1 -s -r -p "按任意键继续..."
    return 0
}

main_menu() {
    while true; do
        print_header
        echo "1. 配置 API 密钥"
        echo "2. 配置交易参数"
        echo "3. 启动机器人"
        echo "4. 停止机器人"
        echo "5. 显示统计信息"
        echo "6. 退出程序"
        echo ""
        
        read -p "请输入您的选择 (1-6): " choice
        
        case $choice in
            1) configure_api_keys ;;
            2) configure_trading_params ;;
            3) start_bot ;;
            4) stop_bot ;;
            5) show_stats ;;
            6) 
                print_color $GREEN "感谢使用！再见！"
                exit 0
                ;;
            *)
                print_color $RED "❌ 无效的选择，请重试！"
                read -n 1 -s -r -p "按任意键继续..."
                ;;
        esac
    done
}

# 初始化环境
initialize_environment

# 启动主菜单
main_menu 
