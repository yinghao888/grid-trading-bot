#!/bin/bash

# 颜色设置
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_color() {
    printf "${1}%s${NC}\n" "${2}"
}

# 安装目录
INSTALL_DIR="$HOME/backpack-grid-bot"

# 显示帮助
show_help() {
    echo "Backpack 网格交易机器人 - 使用说明"
    echo "=================================="
    echo "直接运行: ./run.sh"
    echo "配置API密钥: ./run.sh --api API_KEY API_SECRET"
    echo "配置交易参数: ./run.sh --config SYMBOL GRID_NUM INVESTMENT GRID_SPREAD STOP_LOSS TAKE_PROFIT"
    echo "启动机器人: ./run.sh --start"
    echo "显示状态: ./run.sh --status"
    echo "停止机器人: ./run.sh --stop"
    echo "帮助: ./run.sh --help"
    echo ""
    echo "示例:"
    echo "  ./run.sh --api your_api_key your_api_secret"
    echo "  ./run.sh --config BTC_USDC_PERP 10 1000 2 10 20"
    echo "  ./run.sh --start"
}

# 安装基本依赖
install() {
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
    pip install --upgrade pip >/dev/null 2>&1
    pip install aiohttp==3.9.1 python-dotenv==1.0.0 websockets==12.0 pandas==2.1.4 numpy==1.26.2 loguru==0.7.2 >/dev/null 2>&1

    # 下载机器人脚本
    print_color $GREEN "正在下载机器人脚本..."
    BOT_URL="https://raw.githubusercontent.com/yinghao888/grid-trading-bot/main/bot.py"
    if ! curl -f -s "$BOT_URL" -o "$INSTALL_DIR/grid_bot.py"; then
        print_color $RED "错误：无法从 $BOT_URL 下载机器人脚本"
        print_color $RED "请检查仓库是否存在且为公开仓库。"
        exit 1
    fi

    # 验证下载是否成功
    if [ ! -s "$INSTALL_DIR/grid_bot.py" ]; then
        print_color $RED "错误：下载的 grid_bot.py 文件为空。安装失败。"
        exit 1
    fi

    # 创建配置文件
    if [ ! -f "$INSTALL_DIR/config.json" ]; then
        # 默认配置
        cat > "$INSTALL_DIR/config.json" << EOF
{
    "symbol": "BTC_USDC_PERP",
    "grid_num": 10,
    "total_investment": 1000,
    "grid_spread": 0.02,
    "stop_loss_pct": 0.1,
    "take_profit_pct": 0.2
}
EOF
    fi

    # 创建守护进程脚本
    cat > "$INSTALL_DIR/daemon.py" << 'EOF'
#!/usr/bin/env python3
import os
import sys
import json
import time
import signal
import asyncio
import importlib.util
from pathlib import Path
import argparse

# 执行目录
BASE_DIR = Path(__file__).parent
CONFIG_FILE = BASE_DIR / "config.json"
ENV_FILE = BASE_DIR / ".env"
PID_FILE = BASE_DIR / "bot.pid"
LOG_FILE = BASE_DIR / "grid_bot.log"

# 加载grid_bot.py模块
def load_bot_module():
    bot_path = BASE_DIR / "grid_bot.py"
    if not bot_path.exists():
        print(f"错误：找不到grid_bot.py文件 ({bot_path})")
        sys.exit(1)
    
    spec = importlib.util.spec_from_file_location("grid_bot", bot_path)
    grid_bot = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(grid_bot)
    return grid_bot

# 加载配置
def load_config():
    if not CONFIG_FILE.exists():
        return None
    
    try:
        with open(CONFIG_FILE, "r") as f:
            return json.load(f)
    except Exception as e:
        print(f"加载配置失败: {e}")
        return None

# 保存配置
def save_config(config_data):
    with open(CONFIG_FILE, "w") as f:
        json.dump(config_data, f, indent=4)
    print("✅ 配置已保存")

# 加载API密钥
def load_api_keys():
    if not ENV_FILE.exists():
        return None, None
    
    try:
        with open(ENV_FILE, "r") as f:
            lines = f.readlines()
        
        api_key = None
        api_secret = None
        
        for line in lines:
            if "=" in line:
                key, value = line.strip().split("=", 1)
                if key == "BACKPACK_API_KEY":
                    api_key = value
                elif key == "BACKPACK_API_SECRET":
                    api_secret = value
        
        return api_key, api_secret
    except Exception as e:
        print(f"加载API密钥失败: {e}")
        return None, None

# 保存API密钥
def save_api_keys(api_key, api_secret):
    with open(ENV_FILE, "w") as f:
        f.write(f"BACKPACK_API_KEY={api_key}\n")
        f.write(f"BACKPACK_API_SECRET={api_secret}\n")
    print("✅ API密钥已保存")

# 检查机器人是否正在运行
def is_bot_running():
    if not PID_FILE.exists():
        return False
    
    try:
        with open(PID_FILE, "r") as f:
            pid = int(f.read().strip())
        
        # 尝试发送信号0来检查进程是否存在
        os.kill(pid, 0)
        return True
    except (ProcessLookupError, ValueError):
        # 进程不存在或PID文件内容无效
        return False
    except Exception:
        # 其他错误
        return False

# 停止机器人
def stop_bot():
    if not PID_FILE.exists():
        print("❌ 机器人未运行")
        return
    
    try:
        with open(PID_FILE, "r") as f:
            pid = int(f.read().strip())
        
        # 尝试终止进程
        os.kill(pid, signal.SIGTERM)
        print(f"已发送终止信号到机器人进程(PID: {pid})")
        
        # 等待进程终止
        for _ in range(10):
            try:
                os.kill(pid, 0)  # 检查进程是否存在
                time.sleep(0.5)
            except ProcessLookupError:
                # 进程已终止
                break
        
        # 如果进程仍然存在，强制终止
        try:
            os.kill(pid, 0)
            os.kill(pid, signal.SIGKILL)
            print("已强制终止机器人进程")
        except ProcessLookupError:
            # 进程已终止
            pass
        
        # 删除PID文件
        PID_FILE.unlink(missing_ok=True)
        print("✅ 机器人已停止")
    except Exception as e:
        print(f"停止机器人时出错: {e}")

# 启动机器人
async def start_bot():
    if is_bot_running():
        print("❌ 机器人已在运行中")
        return
    
    # 加载配置
    config_data = load_config()
    if not config_data:
        print("❌ 配置加载失败")
        return
    
    # 加载API密钥
    api_key, api_secret = load_api_keys()
    if not api_key or not api_secret:
        print("❌ API密钥未配置或无效")
        return
    
    # 设置环境变量
    os.environ["BACKPACK_API_KEY"] = api_key
    os.environ["BACKPACK_API_SECRET"] = api_secret
    
    # 加载机器人模块
    grid_bot = load_bot_module()
    
    # 创建配置
    bot_config = grid_bot.GridConfig(
        symbol=config_data.get("symbol", "BTC_USDC_PERP"),
        grid_num=int(config_data.get("grid_num", 10)),
        upper_price=config_data.get("upper_price"),
        lower_price=config_data.get("lower_price"),
        total_investment=float(config_data.get("total_investment", 1000)),
        grid_spread=float(config_data.get("grid_spread", 0.02)),
        stop_loss_pct=float(config_data.get("stop_loss_pct", 0.1)),
        take_profit_pct=float(config_data.get("take_profit_pct", 0.2)),
    )
    
    # 分叉子进程
    pid = os.fork()
    if pid > 0:
        # 父进程
        with open(PID_FILE, "w") as f:
            f.write(str(pid))
        print(f"✅ 机器人已在后台启动 (PID: {pid})")
        return
    
    # 子进程
    try:
        # 关闭标准输入/输出/错误
        sys.stdin.close()
        sys.stdout = open(LOG_FILE, "a")
        sys.stderr = open(LOG_FILE, "a")
        
        # 创建机器人
        bot = grid_bot.GridTradingBot(bot_config)
        
        print(f"\n--- 机器人启动于 {time.strftime('%Y-%m-%d %H:%M:%S')} ---")
        await bot.initialize()
        await bot.start()
    except Exception as e:
        print(f"机器人运行错误: {e}")
    finally:
        print(f"--- 机器人停止于 {time.strftime('%Y-%m-%d %H:%M:%S')} ---\n")
        sys.exit(0)

# 显示状态
def show_status():
    if not is_bot_running():
        print("❌ 机器人未运行")
        return
    
    # 读取PID
    with open(PID_FILE, "r") as f:
        pid = f.read().strip()
    
    # 读取配置
    config_data = load_config()
    if not config_data:
        print("❌ 配置加载失败")
        return
    
    # 显示状态
    print("\n--- 机器人状态 ---")
    print(f"进程ID: {pid}")
    print(f"交易对: {config_data.get('symbol', 'BTC_USDC_PERP')}")
    print(f"网格数量: {config_data.get('grid_num', 10)}")
    print(f"总投资额: {config_data.get('total_investment', 1000)} USDC")
    print(f"网格间距: {float(config_data.get('grid_spread', 0.02))*100}%")
    print(f"止损百分比: {float(config_data.get('stop_loss_pct', 0.1))*100}%")
    print(f"止盈百分比: {float(config_data.get('take_profit_pct', 0.2))*100}%")
    print(f"日志文件: {LOG_FILE}")
    
    # 显示最近的日志
    if LOG_FILE.exists():
        print("\n--- 最近日志 ---")
        os.system(f"tail -n 10 {LOG_FILE}")

# 主函数
async def main():
    parser = argparse.ArgumentParser(description="Backpack 网格交易机器人")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--api", nargs=2, metavar=("API_KEY", "API_SECRET"), help="配置API密钥")
    group.add_argument("--config", nargs=6, metavar=("SYMBOL", "GRID_NUM", "INVESTMENT", "GRID_SPREAD", "STOP_LOSS", "TAKE_PROFIT"), help="配置交易参数")
    group.add_argument("--start", action="store_true", help="启动机器人")
    group.add_argument("--stop", action="store_true", help="停止机器人")
    group.add_argument("--status", action="store_true", help="显示机器人状态")
    group.add_argument("--help", action="store_true", help="显示帮助")
    
    args = parser.parse_args()
    
    if args.api:
        api_key, api_secret = args.api
        save_api_keys(api_key, api_secret)
    elif args.config:
        symbol, grid_num, investment, grid_spread, stop_loss, take_profit = args.config
        try:
            config_data = {
                "symbol": symbol,
                "grid_num": int(grid_num),
                "total_investment": float(investment),
                "grid_spread": float(grid_spread) / 100,
                "stop_loss_pct": float(stop_loss) / 100,
                "take_profit_pct": float(take_profit) / 100
            }
            save_config(config_data)
        except ValueError as e:
            print(f"❌ 参数错误: {e}")
    elif args.start:
        await start_bot()
    elif args.stop:
        stop_bot()
    elif args.status:
        show_status()
    elif args.help:
        parser.print_help()
    else:
        # 默认显示帮助
        parser.print_help()

if __name__ == "__main__":
    asyncio.run(main())
EOF

    # 使脚本可执行
    chmod +x "$INSTALL_DIR/daemon.py"
    
    print_color $GREEN "安装完成！"
}

# 配置API密钥
configure_api() {
    if [ $# -ne 2 ]; then
        print_color $RED "错误：需要提供API Key和API Secret"
        show_help
        exit 1
    fi
    
    api_key=$1
    api_secret=$2
    
    # 保存到.env文件
    cd "$INSTALL_DIR" || exit 1
    echo "BACKPACK_API_KEY=$api_key" > .env
    echo "BACKPACK_API_SECRET=$api_secret" >> .env
    
    print_color $GREEN "✅ API密钥配置成功！"
}

# 配置交易参数
configure_trading() {
    if [ $# -ne 6 ]; then
        print_color $RED "错误：需要提供所有交易参数"
        show_help
        exit 1
    fi
    
    symbol=$1
    grid_num=$2
    investment=$3
    grid_spread=$4
    stop_loss=$5
    take_profit=$6
    
    # 保存到配置文件
    cd "$INSTALL_DIR" || exit 1
    cat > config.json << EOF
{
    "symbol": "$symbol",
    "grid_num": $grid_num,
    "total_investment": $investment,
    "grid_spread": $(echo "scale=4; $grid_spread/100" | bc),
    "stop_loss_pct": $(echo "scale=4; $stop_loss/100" | bc),
    "take_profit_pct": $(echo "scale=4; $take_profit/100" | bc)
}
EOF
    
    print_color $GREEN "✅ 交易参数配置成功！"
}

# 启动机器人
start_bot() {
    cd "$INSTALL_DIR" || exit 1
    source venv/bin/activate
    
    python3 daemon.py --start
}

# 停止机器人
stop_bot() {
    cd "$INSTALL_DIR" || exit 1
    source venv/bin/activate
    
    python3 daemon.py --stop
}

# 显示状态
show_status() {
    cd "$INSTALL_DIR" || exit 1
    source venv/bin/activate
    
    python3 daemon.py --status
}

# 执行安装
if [ ! -f "$INSTALL_DIR/daemon.py" ]; then
    install
fi

# 解析命令行参数
case "$1" in
    --api)
        configure_api "$2" "$3"
        ;;
    --config)
        configure_trading "$2" "$3" "$4" "$5" "$6" "$7"
        ;;
    --start)
        start_bot
        ;;
    --stop)
        stop_bot
        ;;
    --status)
        show_status
        ;;
    --help)
        show_help
        ;;
    *)
        # 如果没有参数或参数不匹配，显示使用帮助
        print_color $GREEN "Backpack 网格交易机器人已安装完成！"
        print_color $YELLOW "以下是可用的命令:"
        echo ""
        show_help
        ;;
esac 
