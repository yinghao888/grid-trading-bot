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

    # 创建启动脚本
    cat > "$INSTALL_DIR/simple_bot.py" << 'EOF'
#!/usr/bin/env python3
import os
import sys
import json
import asyncio
import importlib.util
from pathlib import Path

# 加载grid_bot.py模块
bot_path = Path(__file__).parent / "grid_bot.py"
if not bot_path.exists():
    print("错误：找不到grid_bot.py文件")
    sys.exit(1)

# 动态导入模块
spec = importlib.util.spec_from_file_location("grid_bot", bot_path)
grid_bot = importlib.util.module_from_spec(spec)
spec.loader.exec_module(grid_bot)

# 配置路径
config_dir = Path(__file__).parent
env_file = config_dir / ".env"
config_file = config_dir / "config.json"

# 函数：加载配置
def load_config():
    if not config_file.exists():
        return grid_bot.GridConfig()
    
    try:
        with open(config_file, "r") as f:
            config_data = json.load(f)
        
        return grid_bot.GridConfig(
            symbol=config_data.get("symbol", "BTC_USDC_PERP"),
            grid_num=int(config_data.get("grid_num", 10)),
            upper_price=config_data.get("upper_price"),
            lower_price=config_data.get("lower_price"),
            total_investment=float(config_data.get("total_investment", 1000)),
            grid_spread=float(config_data.get("grid_spread", 0.02)),
            stop_loss_pct=float(config_data.get("stop_loss_pct", 0.1)),
            take_profit_pct=float(config_data.get("take_profit_pct", 0.2)),
        )
    except Exception as e:
        print(f"加载配置出错: {e}")
        return grid_bot.GridConfig()

# 函数：保存配置
def save_config(config):
    config_data = {
        "symbol": config.symbol,
        "grid_num": config.grid_num,
        "upper_price": config.upper_price,
        "lower_price": config.lower_price,
        "total_investment": config.total_investment,
        "grid_spread": config.grid_spread,
        "stop_loss_pct": config.stop_loss_pct,
        "take_profit_pct": config.take_profit_pct,
    }
    
    with open(config_file, "w") as f:
        json.dump(config_data, f, indent=4)

# 函数：加载API密钥
def load_api_keys():
    if not env_file.exists():
        return None, None
    
    try:
        with open(env_file, "r") as f:
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
    except:
        return None, None

# 函数：保存API密钥
def save_api_keys(api_key, api_secret):
    with open(env_file, "w") as f:
        f.write(f"BACKPACK_API_KEY={api_key}\n")
        f.write(f"BACKPACK_API_SECRET={api_secret}\n")
    
    # 同时设置环境变量
    os.environ["BACKPACK_API_KEY"] = api_key
    os.environ["BACKPACK_API_SECRET"] = api_secret

# 函数：配置API密钥
def configure_api_keys():
    print("\n配置 API 密钥")
    print("-" * 40)
    
    api_key = input("请输入您的 API Key: ").strip()
    api_secret = input("请输入您的 API Secret: ").strip()
    
    if not api_key or not api_secret:
        print("\n❌ 错误：API Key 和 Secret 不能为空！")
        return False
    
    save_api_keys(api_key, api_secret)
    print("\n✅ API 密钥配置成功！")
    return True

# 函数：配置交易参数
def configure_trading_params():
    print("\n配置交易参数")
    print("-" * 40)
    
    current_config = load_config()
    
    try:
        symbol = input(f"交易对 (默认: {current_config.symbol}): ").strip() or current_config.symbol
        grid_num = int(input(f"网格数量 (默认: {current_config.grid_num}): ").strip() or str(current_config.grid_num))
        total_investment = float(input(f"总投资额 USDC (默认: {current_config.total_investment}): ").strip() or str(current_config.total_investment))
        grid_spread = float(input(f"网格间距 % (默认: {current_config.grid_spread*100}): ").strip() or str(current_config.grid_spread*100)) / 100
        stop_loss_pct = float(input(f"止损百分比 % (默认: {current_config.stop_loss_pct*100}): ").strip() or str(current_config.stop_loss_pct*100)) / 100
        take_profit_pct = float(input(f"止盈百分比 % (默认: {current_config.take_profit_pct*100}): ").strip() or str(current_config.take_profit_pct*100)) / 100
        
        new_config = grid_bot.GridConfig(
            symbol=symbol,
            grid_num=grid_num,
            total_investment=total_investment,
            grid_spread=grid_spread,
            stop_loss_pct=stop_loss_pct,
            take_profit_pct=take_profit_pct
        )
        
        save_config(new_config)
        print("\n✅ 交易参数配置成功！")
        return True
    except ValueError as e:
        print(f"\n❌ 输入错误：{e}")
        return False

# 运行机器人函数
async def run_bot(config):
    api_key, api_secret = load_api_keys()
    if not api_key or not api_secret:
        print("\n❌ 错误: 未配置API密钥或密钥无效")
        return
    
    # 设置环境变量
    os.environ["BACKPACK_API_KEY"] = api_key
    os.environ["BACKPACK_API_SECRET"] = api_secret
    
    # 创建机器人
    bot = grid_bot.GridTradingBot(config)
    
    try:
        print("\n正在初始化机器人...")
        await bot.initialize()
        print("✅ 机器人初始化成功！")
        print("✅ 机器人已启动！按 Ctrl+C 停止...")
        await bot.start()
    except KeyboardInterrupt:
        print("\n收到终止信号，正在停止机器人...")
    except Exception as e:
        print(f"\n❌ 错误: {str(e)}")
    finally:
        if hasattr(bot, 'stop'):
            await bot.stop()
        print("机器人已停止")

# 主菜单函数
def display_menu():
    print("\n" + "="*50)
    print("Backpack 网格交易机器人管理系统")
    print("="*50)
    print("\n1. 配置 API 密钥")
    print("2. 配置交易参数")
    print("3. 启动机器人")
    print("4. 退出程序")
    
    while True:
        try:
            choice = input("\n请输入您的选择 (1-4): ").strip()
            if not choice:
                continue
                
            if choice == "1":
                configure_api_keys()
                input("\n按回车键返回主菜单...")
                return True
            elif choice == "2":
                configure_trading_params()
                input("\n按回车键返回主菜单...")
                return True
            elif choice == "3":
                config = load_config()
                asyncio.run(run_bot(config))
                input("\n按回车键返回主菜单...")
                return True
            elif choice == "4":
                return False
            else:
                print("\n❌ 无效的选择，请重试")
        except KeyboardInterrupt:
            print("\n\n收到中断信号，退出程序...")
            return False
        except Exception as e:
            print(f"\n❌ 发生错误: {e}")
            return True

# 主函数
def main():
    try:
        while display_menu():
            pass
        print("\n感谢使用！再见！")
    except KeyboardInterrupt:
        print("\n\n收到中断信号，退出程序...")
    except Exception as e:
        print(f"\n\n发生错误: {e}")
    finally:
        print("\n感谢使用！再见！")

if __name__ == "__main__":
    main()
EOF

    # 使启动脚本可执行
    chmod +x "$INSTALL_DIR/simple_bot.py"

    print_color $GREEN "安装完成！"
}

# 执行安装
install

# 运行机器人
print_color $GREEN "现在将启动机器人..."
cd "$INSTALL_DIR" || exit 1
source venv/bin/activate
python3 simple_bot.py 
