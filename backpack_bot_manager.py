#!/usr/bin/env python3
"""
Backpack 交易所网格交易机器人管理器
=================================
提供菜单界面和命令行工具管理网格交易机器人
"""

import os
import sys
import json
import asyncio
import subprocess
from typing import Optional, Dict, Any, List
from dotenv import load_dotenv, set_key
from backpack_grid_bot import GridTradingBot, GridConfig, load_config_from_file
from loguru import logger

# 全局变量
bot: Optional[GridTradingBot] = None
config: Optional[GridConfig] = None
PM2_CONFIG_FILE = "pm2_config.json"

def clear_screen():
    """清屏"""
    os.system('cls' if os.name == 'nt' else 'clear')

def print_header():
    """打印标题"""
    clear_screen()
    print("=" * 60)
    print("     Backpack 交易所网格交易机器人管理器     ")
    print("=" * 60)
    print()

def print_banner():
    """打印横幅"""
    print("\n" + "=" * 60)
    print("        Backpack 交易所网格交易机器人")
    print("        版本 1.0.0")
    print("=" * 60)
    print("\n一个为 Backpack 交易所设计的全自动网格交易机器人\n")

def show_usage():
    """显示使用帮助"""
    print("用法:")
    print("  python backpack_bot_manager.py start    - 启动网格交易机器人")
    print("  python backpack_bot_manager.py menu     - 打开交互式菜单")
    print("  python backpack_bot_manager.py status   - 显示机器人状态")
    print("  python backpack_bot_manager.py stop     - 停止运行的机器人")
    print("  python backpack_bot_manager.py logs     - 查看机器人日志")
    print("  python backpack_bot_manager.py pm2      - 使用PM2启动机器人")
    print("  python backpack_bot_manager.py help     - 显示此帮助信息")
    print("\n详细说明请参阅 README.md")

def check_pm2_installed():
    """检查PM2是否已安装"""
    try:
        subprocess.run(["pm2", "--version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
        return True
    except (subprocess.SubprocessError, FileNotFoundError):
        return False

def install_pm2():
    """如果未安装则安装PM2"""
    print("PM2未安装。正在安装PM2...")
    try:
        subprocess.run(["npm", "install", "-g", "pm2"], check=True)
        print("PM2已成功安装！")
        return True
    except subprocess.SubprocessError:
        print("安装PM2失败。请手动安装：'npm install -g pm2'")
        return False

def configure_api_keys():
    """配置API密钥"""
    print_header()
    print("配置API密钥")
    print("-" * 60)
    
    current_key = os.getenv("BACKPACK_API_KEY", "")
    current_secret = os.getenv("BACKPACK_API_SECRET", "")
    
    print(f"当前API密钥: {'*' * 8 + current_key[-4:] if current_key else '未设置'}")
    print(f"当前API密钥: {'*' * 12 + current_secret[-4:] if current_secret else '未设置'}")
    print()
    
    change = input("是否要更改API凭据? (y/n): ").strip().lower()
    if change != 'y':
        input("\nAPI密钥未更改。按Enter继续...")
        return
    
    api_key = input("\n输入您的Backpack API密钥: ").strip()
    api_secret = input("输入您的Backpack API密钥: ").strip()
    
    # 更新.env文件
    env_path = os.path.join(os.path.dirname(__file__), '.env')
    
    # 如果.env不存在则创建
    if not os.path.exists(env_path):
        with open(env_path, 'w') as f:
            f.write("")
    
    set_key(env_path, "BACKPACK_API_KEY", api_key)
    set_key(env_path, "BACKPACK_API_SECRET", api_secret)
    
    # 重新加载环境变量
    load_dotenv(override=True)
    
    print("\nAPI密钥已成功保存！")
    input("\n按Enter继续...")

def view_trading_params():
    """查看当前交易参数"""
    print_header()
    print("当前交易参数")
    print("-" * 60)
    
    global config
    if not config:
        config = GridConfig()
    
    params = config.to_dict()
    
    print(f"交易对: {params['symbol']}")
    print(f"网格数量: {params['grid_num']}")
    print(f"总投资: {params['total_investment']} USDC")
    print(f"网格间距: {params['grid_spread'] * 100}%")
    print(f"止损: {params['stop_loss_pct'] * 100}%")
    print(f"止盈: {params['take_profit_pct'] * 100}%")
    
    if params['upper_price']:
        print(f"上限价格: {params['upper_price']}")
    else:
        print("上限价格: 自动 (当前价格 + 10%)")
        
    if params['lower_price']:
        print(f"下限价格: {params['lower_price']}")
    else:
        print("下限价格: 自动 (当前价格 - 10%)")
    
    input("\n按Enter继续...")

def configure_trading_params():
    """配置交易参数"""
    print_header()
    print("配置交易参数")
    print("-" * 60)
    
    global config
    if not config:
        config = GridConfig()
    
    # 显示当前值
    view_trading_params()
    
    print_header()
    print("配置交易参数")
    print("-" * 60)
    print("输入新值（按Enter保留当前值）")
    print()
    
    try:
        # 获取当前值作为默认值
        current = config.to_dict()
        
        symbol = input(f"交易对 ({current['symbol']}): ").strip() or current['symbol']
        grid_num = int(input(f"网格数量 ({current['grid_num']}): ").strip() or current['grid_num'])
        total_investment = float(input(f"总投资金额 USDC ({current['total_investment']}): ").strip() or current['total_investment'])
        grid_spread = float(input(f"网格间距百分比 ({current['grid_spread'] * 100}): ").strip() or current['grid_spread'] * 100) / 100
        stop_loss_pct = float(input(f"止损百分比 ({current['stop_loss_pct'] * 100}): ").strip() or current['stop_loss_pct'] * 100) / 100
        take_profit_pct = float(input(f"止盈百分比 ({current['take_profit_pct'] * 100}): ").strip() or current['take_profit_pct'] * 100) / 100
        
        # 价格边界设置
        set_custom_boundaries = input("\n设置自定义价格边界? (y/n): ").strip().lower() == 'y'
        
        upper_price = None
        lower_price = None
        
        if set_custom_boundaries:
            upper_price = float(input("上限价格: ").strip())
            lower_price = float(input("下限价格: ").strip())
        
        config = GridConfig(
            symbol=symbol,
            grid_num=grid_num,
            upper_price=upper_price,
            lower_price=lower_price,
            total_investment=total_investment,
            grid_spread=grid_spread,
            stop_loss_pct=stop_loss_pct,
            take_profit_pct=take_profit_pct
        )
        
        # 保存配置到文件，供PM2使用
        save_config_to_file()
        
        print("\n交易参数已成功保存！")
        
    except ValueError as e:
        print(f"\n错误: 无效输入 - {e}")
    
    input("\n按Enter继续...")

def save_config_to_file():
    """保存当前配置到JSON文件"""
    global config
    if not config:
        config = GridConfig()
    
    config_data = config.to_dict()
    
    # 如果不存在则创建configs目录
    os.makedirs('configs', exist_ok=True)
    
    # 保存配置到文件
    with open('configs/grid_config.json', 'w') as f:
        json.dump(config_data, f, indent=4)

def create_pm2_config():
    """创建PM2配置文件"""
    # 获取脚本的绝对路径
    script_path = os.path.abspath("backpack_grid_bot.py")
    
    pm2_config = {
        "apps": [
            {
                "name": "backpack-grid-bot",
                "script": script_path,
                "interpreter": "python3",
                "exec_mode": "fork",
                "autorestart": True,
                "watch": False,
                "max_memory_restart": "500M",
                "env": {
                    "NODE_ENV": "production"
                },
                "log_date_format": "YYYY-MM-DD HH:mm:ss"
            }
        ]
    }
    
    with open(PM2_CONFIG_FILE, 'w') as f:
        json.dump(pm2_config, f, indent=4)
    
    return PM2_CONFIG_FILE

def start_bot_with_pm2():
    """使用PM2启动机器人"""
    print_header()
    print("使用PM2启动机器人...")
    
    if not os.getenv("BACKPACK_API_KEY") or not os.getenv("BACKPACK_API_SECRET"):
        print("错误: API密钥未配置！请先配置API密钥。")
        input("\n按Enter继续...")
        return
    
    # 确保配置已保存
    save_config_to_file()
    
    # 如果不存在则创建PM2配置
    pm2_config_path = create_pm2_config()
    
    try:
        result = subprocess.run(
            ["pm2", "start", pm2_config_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True
        )
        print("\n机器人已使用PM2成功启动！")
        print("查看日志，运行: pm2 logs backpack-grid-bot")
    except subprocess.SubprocessError as e:
        print(f"\n使用PM2启动机器人错误: {e}")
        logger.error(f"PM2启动错误: {e}")
    
    input("\n按Enter继续...")

async def start_bot_interactive():
    """交互模式启动机器人（非PM2）"""
    print_header()
    print("交互模式启动机器人...")
    
    if not os.getenv("BACKPACK_API_KEY") or not os.getenv("BACKPACK_API_SECRET"):
        print("错误: API密钥未配置！请先配置API密钥。")
        input("\n按Enter继续...")
        return
    
    global bot, config
    if not config:
        if not load_config_from_file():
            config = GridConfig()  # 使用默认参数
    
    try:
        bot = GridTradingBot(config)
        await bot.start()
    except KeyboardInterrupt:
        print("\n机器人被用户停止。")
    except Exception as e:
        print(f"启动机器人错误: {e}")
        logger.error(f"机器人错误: {e}")
    
    input("\n按Enter继续...")

async def stop_bot():
    """停止机器人（PM2和交互式）"""
    print_header()
    print("正在停止机器人...")
    
    # 如果正在运行则停止PM2版本
    try:
        result = subprocess.run(
            ["pm2", "stop", "backpack-grid-bot"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        if result.returncode == 0:
            print("机器人在PM2中已成功停止！")
    except subprocess.SubprocessError:
        pass
    
    # 如果正在运行则停止交互式版本
    global bot
    if bot:
        await bot.stop()
        bot = None
        print("机器人在交互模式中已成功停止！")
    
    input("\n按Enter继续...")

def get_pm2_bot_status():
    """获取PM2中机器人的状态"""
    try:
        result = subprocess.run(
            ["pm2", "jlist"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True
        )
        
        data = json.loads(result.stdout)
        for app in data:
            if app['name'] == 'backpack-grid-bot':
                return {
                    'status': app['pm2_env']['status'],
                    'uptime': app['pm2_env'].get('pm_uptime', 0),
                    'restarts': app['pm2_env']['restart_time'],
                    'memory': app['monit']['memory'] / 1024 / 1024,  # 转换为MB
                    'cpu': app['monit']['cpu']
                }
        return None
    except (subprocess.SubprocessError, json.JSONDecodeError):
        return None

def show_bot_status():
    """显示当前机器人状态"""
    print_header()
    print("机器人状态")
    print("-" * 60)
    
    # 检查PM2状态
    pm2_status = get_pm2_bot_status()
    
    if pm2_status:
        status = pm2_status['status']
        uptime_ms = pm2_status.get('uptime', 0)
        uptime_hr = uptime_ms / 1000 / 60 / 60
        
        print("PM2机器人状态:")
        print(f"  状态: {status}")
        print(f"  运行时间: {uptime_hr:.2f} 小时")
        print(f"  重启次数: {pm2_status['restarts']}")
        print(f"  内存使用: {pm2_status['memory']:.2f} MB")
        print(f"  CPU使用率: {pm2_status['cpu']}%")
    else:
        print("PM2机器人状态: 未运行或PM2不可用")
    
    # 检查交互式机器人状态
    global bot
    if bot:
        print("\n交互式机器人状态: 运行中")
        print("机器人统计信息:")
        stats = bot.get_stats()
        print(f"  总利润: {stats['total_profit']:.2f} USDC")
        print(f"  总交易次数: {stats['trades_count']}")
        print(f"  活跃订单: {stats['active_orders']}")
        print(f"  网格层级: {stats['grid_levels']}")
        print(f"  当前价格: {stats['current_price']:.2f}")
    else:
        print("\n交互式机器人状态: 未运行")
    
    input("\n按Enter继续...")

def view_pm2_logs():
    """查看PM2日志"""
    print_header()
    print("查看PM2日志（按Ctrl+C退出）")
    print("-" * 60)
    
    try:
        subprocess.run(["pm2", "logs", "backpack-grid-bot"], check=True)
    except (subprocess.SubprocessError, KeyboardInterrupt):
        pass
    
    input("\n按Enter继续...")

async def start_bot():
    """启动交易机器人"""
    try:
        # 从文件加载配置
        config = load_config_from_file()
        # 创建并启动机器人
        global bot
        bot = GridTradingBot(config)
        await bot.start()
    except ImportError:
        print("错误: 无法导入grid_bot模块。")
        print("请确保所有依赖已安装。")
        print("运行 'python install.py' 来安装依赖。")
        sys.exit(1)
    except Exception as e:
        print(f"启动机器人错误: {e}")
        sys.exit(1)

def start_menu():
    """启动交互式菜单"""
    try:
        # 使用子进程运行菜单
        asyncio.run(main_menu())
    except Exception as e:
        print(f"启动菜单错误: {e}")
        sys.exit(1)

def run_pm2_start():
    """使用PM2启动机器人"""
    # 检查PM2是否已安装
    if not check_pm2_installed():
        install_success = install_pm2()
        if not install_success:
            print("错误: PM2未安装且无法自动安装。")
            sys.exit(1)
    
    # 启动机器人
    if not os.getenv("BACKPACK_API_KEY") or not os.getenv("BACKPACK_API_SECRET"):
        print("错误: API密钥未配置！请先运行 'python backpack_bot_manager.py menu' 配置API密钥。")
        sys.exit(1)
    
    # 确保配置已保存
    if not os.path.exists('configs/grid_config.json'):
        # 创建默认配置
        config = GridConfig()
        os.makedirs('configs', exist_ok=True)
        with open('configs/grid_config.json', 'w') as f:
            json.dump(config.to_dict(), f, indent=4)
    
    # 创建PM2配置
    pm2_config_path = create_pm2_config()
    
    try:
        result = subprocess.run(
            ["pm2", "start", pm2_config_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True
        )
        print("机器人已使用PM2成功启动！")
        print("查看日志，运行: pm2 logs backpack-grid-bot")
    except subprocess.SubprocessError as e:
        print(f"使用PM2启动机器人错误: {e}")
        sys.exit(1)

def show_status():
    """显示机器人状态"""
    # 检查PM2状态
    pm2_status = get_pm2_bot_status()
    
    if pm2_status:
        status = pm2_status['status']
        uptime_ms = pm2_status.get('uptime', 0)
        uptime_hr = uptime_ms / 1000 / 60 / 60
        
        print("PM2机器人状态:")
        print(f"  状态: {status}")
        print(f"  运行时间: {uptime_hr:.2f} 小时")
        print(f"  重启次数: {pm2_status['restarts']}")
        print(f"  内存使用: {pm2_status['memory']:.2f} MB")
        print(f"  CPU使用率: {pm2_status['cpu']}%")
    else:
        print("PM2机器人状态: 未运行或PM2不可用")

def stop_bot_command():
    """停止运行的机器人"""
    try:
        result = subprocess.run(
            ["pm2", "stop", "backpack-grid-bot"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        if result.returncode == 0:
            print("机器人已成功停止。")
        else:
            print("停止机器人错误。机器人是否正在运行?")
            print(result.stderr)
    except Exception as e:
        print(f"停止机器人错误: {e}")
        sys.exit(1)

def view_logs():
    """查看机器人日志"""
    try:
        subprocess.run(["pm2", "logs", "backpack-grid-bot"])
    except (subprocess.SubprocessError, KeyboardInterrupt):
        pass

async def main_menu():
    """主菜单"""
    # 检查PM2是否已安装
    if not check_pm2_installed():
        install_success = install_pm2()
        if not install_success:
            print("警告: PM2未安装。某些功能可能无法正常工作。")
    
    # 加载配置
    global config
    load_dotenv()
    config = load_config_from_file()
    
    while True:
        print_header()
        print("1. 配置API密钥")
        print("2. 查看交易参数")
        print("3. 配置交易参数")
        print("4. 使用PM2启动机器人（后台运行）")
        print("5. 交互模式启动机器人")
        print("6. 停止机器人")
        print("7. 查看机器人状态")
        print("8. 查看PM2日志")
        print("9. 退出")
        print()
        
        choice = input("输入选择 (1-9): ").strip()
        
        if choice == "1":
            configure_api_keys()
        elif choice == "2":
            view_trading_params()
        elif choice == "3":
            configure_trading_params()
        elif choice == "4":
            start_bot_with_pm2()
        elif choice == "5":
            await start_bot_interactive()
        elif choice == "6":
            await stop_bot()
        elif choice == "7":
            show_bot_status()
        elif choice == "8":
            view_pm2_logs()
        elif choice == "9":
            if bot:
                await stop_bot()
            print("\n再见！")
            sys.exit(0)
        else:
            print("\n无效的选择！请重试。")
            input("\n按Enter继续...")

def main():
    """主函数"""
    print_banner()
    
    if len(sys.argv) < 2:
        show_usage()
        return
    
    command = sys.argv[1].lower()
    
    if command == "start":
        asyncio.run(start_bot())
    elif command == "menu":
        start_menu()
    elif command == "status":
        show_status()
    elif command == "stop":
        stop_bot_command()
    elif command == "logs":
        view_logs()
    elif command == "pm2":
        run_pm2_start()
    elif command == "help":
        show_usage()
    else:
        print(f"未知命令: {command}")
        show_usage()

if __name__ == "__main__":
    # 加载环境变量
    load_dotenv()
    main() 
