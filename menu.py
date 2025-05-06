#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import subprocess
import json
import configparser
import time
import asyncio
import re
from datetime import datetime
import argparse

# 环境检测
def check_environment():
    """检测当前环境是否适合运行交互式菜单"""
    # 直接返回交互式环境设置，忽略其他检测
    return {
        'is_terminal': True,
        'has_args': len(sys.argv) > 1,
        'non_interactive': False,
        'force_interactive': True,
        'is_interactive': True  # 强制为交互式
    }
    
    # 以下代码已被禁用，始终返回交互式模式
    """
    # 检查是否运行在终端中
    is_terminal = os.isatty(sys.stdin.fileno()) if hasattr(sys, 'stdin') and hasattr(sys.stdin, 'fileno') else False
    
    # 检查是否有命令行参数（如果有，可能是非交互式调用）
    has_args = len(sys.argv) > 1
    
    # 获取环境变量
    non_interactive = os.environ.get('NON_INTERACTIVE', 'false').lower() == 'true'
    force_interactive = os.environ.get('FORCE_INTERACTIVE', 'false').lower() == 'true'
    
    # 输出调试信息
    if os.environ.get('DEBUG', 'false').lower() == 'true':
        print(f"环境检测: 终端={is_terminal}, 命令行参数={has_args}, 非交互式={non_interactive}, 强制交互式={force_interactive}")
    
    # 返回环境信息
    return {
        'is_terminal': is_terminal,
        'has_args': has_args,
        'non_interactive': non_interactive,
        'force_interactive': force_interactive,
        'is_interactive': (is_terminal and not non_interactive) or force_interactive
    }
    """

# 全局环境状态
ENV = check_environment()

# 颜色输出函数
def print_green(text):
    print("\033[32m{}\033[0m".format(text))

def print_blue(text):
    print("\033[34m{}\033[0m".format(text))

def print_red(text):
    print("\033[31m{}\033[0m".format(text))

def print_yellow(text):
    print("\033[33m{}\033[0m".format(text))

# 获取配置目录
CONFIG_DIR = os.path.expanduser("~/.backpack_bot")
CONFIG_FILE = os.path.join(CONFIG_DIR, "config.ini")

# 确保配置目录存在
if not os.path.exists(CONFIG_DIR):
    os.makedirs(CONFIG_DIR)

# 安全输入函数，确保在任何环境下都能获取用户输入
def safe_input(prompt="", default=""):
    """增强版安全输入函数
    
    Args:
        prompt: 输入提示
        default: 非交互模式下的默认值
        
    Returns:
        用户输入或默认值
    """
    # 移除非交互式检查，强制使用交互式输入
    # if not ENV['is_interactive']:
    #     print(f"{prompt} [非交互式模式，使用默认值: '{default}']")
    #     return default
    
    try:
        # 强制刷新输出缓冲区，确保提示显示
        sys.stdout.write(prompt)
        sys.stdout.flush()
        
        # 设置超时（仅在支持的环境中）
        try:
            import signal
            
            # 检查平台，在macOS上信号处理有所不同
            if sys.platform == 'darwin':  # macOS
                # 在macOS上使用更简单的方法，不依赖信号超时
                return input()
            else:
                def timeout_handler(signum, frame):
                    raise TimeoutError("输入超时")
                
                # 设置10秒超时
                signal.signal(signal.SIGALRM, timeout_handler)
                signal.alarm(10)
                
                user_input = input()
                
                # 取消超时
                signal.alarm(0)
                return user_input
        except (ImportError, AttributeError):
            # 不支持信号模块的环境，直接尝试输入
            return input()
    except EOFError:
        # 如果发生EOFError，说明可能在非交互式环境中
        print("\n检测到输入问题 (EOFError)，采用默认值继续")
        return default
    except TimeoutError as e:
        # 输入超时
        print(f"\n{e}，采用默认值继续")
        return default
    except KeyboardInterrupt:
        # 用户中断
        print("\n用户中断，采用默认值继续")
        return default
    except Exception as e:
        print_red(f"输入错误: {str(e)}")
        return default

# 解析命令行参数
def parse_args():
    parser = argparse.ArgumentParser(description='Backpack 交易机器人配置菜单')
    parser.add_argument('--quick-setup', action='store_true', help='直接启动快速配置向导')
    parser.add_argument('--configure-api', action='store_true', help='直接配置交易所API')
    parser.add_argument('--configure-telegram', action='store_true', help='直接配置Telegram')
    parser.add_argument('--select-pairs', action='store_true', help='直接选择交易对')
    parser.add_argument('--configure-params', action='store_true', help='直接配置交易参数')
    parser.add_argument('--view-logs', action='store_true', help='查看日志')
    parser.add_argument('--start-bot', action='store_true', help='启动交易机器人')
    parser.add_argument('--stop-bot', action='store_true', help='停止交易机器人')
    parser.add_argument('--api-key', help='设置API密钥')
    parser.add_argument('--api-secret', help='设置API密钥')
    parser.add_argument('--telegram-id', help='设置Telegram ID')
    parser.add_argument('--trading-pairs', help='设置交易对，用逗号分隔')
    parser.add_argument('--position-limit', help='设置仓位限制')
    parser.add_argument('--funding-threshold', help='设置资金费率阈值')
    return parser.parse_args()

# 检查可用的进程管理工具
def get_process_manager():
    """检测可用的进程管理工具"""
    # 首先检查是否有systemd用户服务
    systemd_service = os.path.expanduser("~/.config/systemd/user/backpack-bot.service")
    if os.path.exists(systemd_service):
        # 验证systemctl命令是否可用
        try:
            subprocess.run(["systemctl", "--user", "--version"], 
                          capture_output=True, check=False)
            return "systemd"
        except (subprocess.SubprocessError, FileNotFoundError):
            pass
    
    # 然后检查PM2是否可用
    try:
        subprocess.run(["pm2", "--version"], capture_output=True, check=False)
        return "pm2"
    except (subprocess.SubprocessError, FileNotFoundError):
        pass
    
    # 最后检查Python直接运行是否可行
    return "direct"

# 检测是否使用systemd
def is_using_systemd():
    return get_process_manager() == "systemd"

# 加载配置文件
def load_config():
    config = configparser.ConfigParser()
    if os.path.exists(CONFIG_FILE):
        config.read(CONFIG_FILE)
    else:
        # 创建默认配置
        config["api"] = {
            "api_key": "YOUR_API_KEY",
            "api_secret": "YOUR_API_SECRET",
            "base_url": "https://api.backpack.exchange",
            "ws_url": "wss://ws.backpack.exchange"
        }
        config["trading"] = {
            "symbols": "ETH_USDC_PERP",
            "position_limit": "0.001",
            "funding_threshold": "0.0001",
            "check_interval": "300",
            "leverage": "20",
            "profit_target": "0.0002",  # 0.02% 手续费
            "stop_loss": "0.1",  # 10% 止损
            "cooldown_minutes": "30"  # 冷却时间（分钟）
        }
        config["telegram"] = {
            "bot_token": "7685502184:AAGxaIdwiTr0WpPDeIGmc9fgbdeSKxgXtEw",
            "chat_id": ""
        }
        # 保存默认配置
        with open(CONFIG_FILE, 'w') as f:
            config.write(f)
    
    return config

# 保存配置
def save_config(config):
    with open(CONFIG_FILE, 'w') as f:
        config.write(f)
    print_green("配置已保存")

# 配置Telegram（支持命令行参数）
def configure_telegram(telegram_id=None):
    config = load_config()
    
    print_blue("配置 Telegram")
    print_blue("机器人将使用默认令牌：7685502184:AAGxaIdwiTr0WpPDeIGmc9fgbdeSKxgXtEw")
    
    # 如果通过命令行提供了Telegram ID，直接使用
    if telegram_id:
        chat_id = telegram_id
        print_yellow(f"使用提供的Telegram ID: {chat_id}")
    else:
        print_yellow("请输入您的 Telegram 用户 ID (可通过 @userinfobot 获取):")
        chat_id = safe_input("", config.get("telegram", "chat_id", fallback="")).strip()
    
    if chat_id:
        config.set("telegram", "chat_id", chat_id)
        save_config(config)
        print_green("Telegram 配置已保存！")
    else:
        print_red("未输入 ID，Telegram 配置未更改。")
    
    if not telegram_id and ENV['is_interactive']:  # 只有在交互模式下才等待用户输入
        safe_input("按 Enter 键返回主菜单...", "")

# 配置交易所 API（支持命令行参数）
def configure_exchange_api(api_key=None, api_secret=None):
    config = load_config()
    
    print_blue("配置 Backpack 交易所 API")
    
    # 如果通过命令行提供了API密钥，直接使用
    if api_key and api_secret:
        print_yellow(f"使用提供的API密钥和密钥")
    else:
        print_yellow("请输入您的 API Key:")
        api_key = safe_input("", config.get("api", "api_key", fallback="")).strip()
        
        print_yellow("请输入您的 API Secret:")
        api_secret = safe_input("", config.get("api", "api_secret", fallback="")).strip()
    
    if api_key and api_secret:
        config.set("api", "api_key", api_key)
        config.set("api", "api_secret", api_secret)
        save_config(config)
        print_green("交易所 API 配置已保存！")
    else:
        print_red("API Key 或 Secret 不能为空！配置未更改。")
    
    if not (api_key and api_secret) and ENV['is_interactive']:  # 只有在交互模式下才等待用户输入
        safe_input("按 Enter 键返回主菜单...", "")

# 选择交易对（支持命令行参数）
def select_trading_pairs(trading_pairs=None):
    config = load_config()
    
    # 获取支持的交易对列表
    supported_pairs = [
        "BTC_USDC_PERP", 
        "ETH_USDC_PERP", 
        "SOL_USDC_PERP", 
        "NEAR_USDC_PERP",
        "AVAX_USDC_PERP",
        "DOGE_USDC_PERP"
    ]
    
    # 如果通过命令行提供了交易对，直接使用
    if trading_pairs:
        # 验证交易对是否有效
        pairs = trading_pairs.split(",")
        valid_pairs = []
        for pair in pairs:
            pair = pair.strip()
            if pair in supported_pairs:
                valid_pairs.append(pair)
            else:
                print_red(f"无效的交易对: {pair}")
        
        if valid_pairs:
            config.set("trading", "symbols", ",".join(valid_pairs))
            save_config(config)
            print_green("交易对配置已保存！")
            return
        else:
            print_red("未提供有效的交易对！")
            return
    
    # 非交互模式下，不执行下面的交互式配置
    if not ENV['is_interactive']:
        print_yellow("非交互模式下不支持交互式选择交易对")
        print_yellow("请使用命令行参数: --trading-pairs=ETH_USDC_PERP,SOL_USDC_PERP")
        return
    
    # 交互式配置
    current_pairs = config.get("trading", "symbols").split(",")
    
    while True:
        os.system('clear' if os.name != 'nt' else 'cls')
        print_blue("选择交易对")
        print_blue("当前已选择: " + config.get("trading", "symbols"))
        
        print_yellow("\n可用交易对列表:")
        for i, pair in enumerate(supported_pairs, 1):
            status = "✓" if pair in current_pairs else " "
            print(f"{i}. [{status}] {pair}")
        
        print_yellow("\n操作选项:")
        print("A. 添加交易对")
        print("R. 移除交易对")
        print("D. 设置为默认 (ETH_USDC_PERP)")
        print("S. 保存并返回")
        print("Q. 不保存返回")
        
        choice = safe_input("\n请选择操作: ", "Q").strip().upper()
        
        if choice == 'A':
            print_yellow("输入要添加的交易对编号(多个用空格分隔):")
            selections = safe_input("", "").strip().split()
            for sel in selections:
                try:
                    idx = int(sel) - 1
                    if 0 <= idx < len(supported_pairs):
                        if supported_pairs[idx] not in current_pairs:
                            current_pairs.append(supported_pairs[idx])
                except ValueError:
                    pass
        
        elif choice == 'R':
            print_yellow("输入要移除的交易对编号(多个用空格分隔):")
            selections = safe_input("", "").strip().split()
            for sel in selections:
                try:
                    idx = int(sel) - 1
                    if 0 <= idx < len(supported_pairs) and supported_pairs[idx] in current_pairs:
                        current_pairs.remove(supported_pairs[idx])
                except ValueError:
                    pass
        
        elif choice == 'D':
            current_pairs = ["ETH_USDC_PERP"]
            print_green("已重置为默认交易对")
        
        elif choice == 'S':
            # 保存配置
            if current_pairs:
                config.set("trading", "symbols", ",".join(current_pairs))
                save_config(config)
                print_green("交易对配置已保存！")
                time.sleep(1)
                break
            else:
                print_red("错误：必须至少选择一个交易对！")
                time.sleep(1)
        
        elif choice == 'Q':
            print_yellow("未保存更改")
            time.sleep(1)
            break

# 配置交易参数（支持命令行参数）
def configure_trading_params(position_limit=None, funding_threshold=None):
    config = load_config()
    
    # 如果通过命令行提供了参数，直接使用
    if position_limit or funding_threshold:
        if position_limit:
            config.set("trading", "position_limit", position_limit)
            print_green(f"仓位限制已设置为: {position_limit}")
        
        if funding_threshold:
            config.set("trading", "funding_threshold", funding_threshold)
            print_green(f"资金费率阈值已设置为: {funding_threshold}")
        
        save_config(config)
        return
    
    # 非交互模式下，不执行下面的交互式配置
    if not ENV['is_interactive']:
        print_yellow("非交互模式下不支持交互式配置交易参数")
        print_yellow("请使用命令行参数: --position-limit=0.001 --funding-threshold=0.0001")
        return
    
    # 交互式配置
    os.system('clear' if os.name != 'nt' else 'cls')
    print_blue("配置交易参数")
    
    # 显示当前配置
    print_yellow("\n当前交易参数:")
    for key, value in config["trading"].items():
        if key != "symbols":  # 交易对在另一个菜单中配置
            print(f"{key}: {value}")
    
    print_yellow("\n请选择要修改的参数:")
    print("1. 仓位限制 (position_limit)")
    print("2. 资金费率阈值 (funding_threshold)")
    print("3. 检查间隔(秒) (check_interval)")
    print("4. 杠杆倍数 (leverage)")
    print("5. 利润目标 (profit_target)")
    print("6. 止损比例 (stop_loss)")
    print("7. 冷却时间(分钟) (cooldown_minutes)")
    print("S. 保存并返回")
    print("Q. 不保存返回")
    
    choice = safe_input("\n请选择操作: ", "Q").strip().upper()
    
    if choice == '1':
        current = config.get("trading", "position_limit")
        print_yellow(f"请输入仓位限制 (例如 0.001, 当前值: {current}):")
        value = safe_input("", current).strip()
        if value:
            config.set("trading", "position_limit", value)
    elif choice == '2':
        current = config.get("trading", "funding_threshold")
        print_yellow(f"请输入资金费率阈值 (例如 0.0001, 当前值: {current}):")
        value = safe_input("", current).strip()
        if value:
            config.set("trading", "funding_threshold", value)
    elif choice == '3':
        current = config.get("trading", "check_interval")
        print_yellow(f"请输入检查间隔(秒) (例如 300, 当前值: {current}):")
        value = safe_input("", current).strip()
        if value:
            config.set("trading", "check_interval", value)
    elif choice == '4':
        current = config.get("trading", "leverage")
        print_yellow(f"请输入杠杆倍数 (例如 20, 当前值: {current}):")
        value = safe_input("", current).strip()
        if value:
            config.set("trading", "leverage", value)
    elif choice == '5':
        current = config.get("trading", "profit_target")
        print_yellow(f"请输入利润目标 (例如 0.0002, 当前值: {current}):")
        value = safe_input("", current).strip()
        if value:
            config.set("trading", "profit_target", value)
    elif choice == '6':
        current = config.get("trading", "stop_loss")
        print_yellow(f"请输入止损比例 (例如 0.1, 当前值: {current}):")
        value = safe_input("", current).strip()
        if value:
            config.set("trading", "stop_loss", value)
    elif choice == '7':
        current = config.get("trading", "cooldown_minutes")
        print_yellow(f"请输入冷却时间(分钟) (例如 30, 当前值: {current}):")
        value = safe_input("", current).strip()
        if value:
            config.set("trading", "cooldown_minutes", value)
    elif choice == 'S':
        save_config(config)
        print_green("交易参数已保存!")
        time.sleep(1)
        return
    elif choice == 'Q':
        print_yellow("未保存更改")
        time.sleep(1)
        return
    
    # 递归调用自己，直到用户选择返回
    if choice not in ['S', 'Q']:
        configure_trading_params()

# 停止脚本
def stop_bot():
    print_blue("停止交易机器人")
    
    process_manager = get_process_manager()
    
    if process_manager == "systemd":
        # 使用systemd停止
        try:
            subprocess.run(["systemctl", "--user", "stop", "backpack-bot"], check=True)
            print_green("交易机器人已停止")
        except subprocess.CalledProcessError:
            print_red("停止失败，请手动检查状态")
        except FileNotFoundError:
            print_red("未找到systemctl命令，无法使用systemd停止")
    elif process_manager == "pm2":
        # 使用PM2停止
        try:
            result = subprocess.run(["pm2", "stop", "backpack_bot"], capture_output=True, text=True)
            
            if result.returncode == 0:
                print_green("交易机器人已停止")
            else:
                print_red(f"停止失败: {result.stderr}")
                print_yellow("尝试使用备用方法停止...")
                try:
                    os.system("pm2 stop backpack_bot")
                    print_green("交易机器人可能已停止，请检查状态")
                except:
                    print_red("所有停止方法失败，请手动检查")
        except FileNotFoundError:
            print_red("未找到PM2命令，无法使用PM2停止")
    else:
        print_red("未找到支持的进程管理工具（systemd或PM2）")
        print_yellow("请手动停止交易机器人进程")
    
    safe_input("按 Enter 键返回主菜单...", "")

# 启动脚本
def start_bot():
    print_blue("启动交易机器人")
    
    # 检查配置是否完整
    config = load_config()
    if (config["api"]["api_key"] == "YOUR_API_KEY" or 
        config["api"]["api_secret"] == "YOUR_API_SECRET"):
        print_red("错误: 未配置 API 密钥，请先完成配置")
        safe_input("按 Enter 键返回主菜单...", "")
        return
    
    if not config["telegram"]["chat_id"]:
        print_yellow("警告: 未配置 Telegram ID，将无法接收通知")
        proceed = safe_input("是否继续启动? (y/n): ", "n").strip().lower()
        if proceed != 'y':
            return
    
    process_manager = get_process_manager()
    
    if process_manager == "systemd":
        # 使用systemd启动
        try:
            print_yellow("使用systemd启动机器人...")
            subprocess.run(["systemctl", "--user", "start", "backpack-bot"], check=True)
            print_green("交易机器人已启动")
            print_green("systemd将自动管理交易机器人，确保其稳定运行")
        except subprocess.CalledProcessError:
            print_red("启动失败，请手动检查错误")
        except FileNotFoundError:
            print_red("未找到systemctl命令，无法使用systemd启动")
    elif process_manager == "pm2":
        # 确保ecosystem.config.js文件存在
        ecosystem_file = os.path.join(CONFIG_DIR, "ecosystem.config.js")
        if not os.path.exists(ecosystem_file):
            print_yellow("未找到PM2配置文件，正在创建...")
            with open(ecosystem_file, 'w') as f:
                f.write(f"""module.exports = {{
  apps : [{{
    name: 'backpack_bot',
    script: `${{process.env.HOME}}/.backpack_bot/backpack_bot.py`,
    interpreter: 'python3',
    autorestart: true,
    watch: false,
    max_memory_restart: '200M',
    env: {{
      NODE_ENV: 'production'
    }},
    log_date_format: 'YYYY-MM-DD HH:mm:ss'
  }}]
}}; 
""")
        
        # 启动机器人
        try:
            print_yellow("正在使用PM2启动机器人，请稍等...")
            result = subprocess.run(["pm2", "start", ecosystem_file], 
                                  capture_output=True, text=True)
            
            if result.returncode == 0:
                print_green("交易机器人已启动")
                print_green("PM2将自动管理交易机器人，确保其稳定运行")
            else:
                print_red(f"启动失败: {result.stderr}")
                print_yellow("尝试使用备用方法启动...")
                try:
                    os.system(f"pm2 start {ecosystem_file}")
                    print_green("交易机器人可能已启动，请检查状态")
                except:
                    print_red("所有启动方法失败，请手动检查")
            
            # 保存PM2进程列表，确保开机自启
            try:
                os.system("pm2 save")
            except:
                print_yellow("无法保存PM2进程列表，可能需要手动执行 'pm2 save'")
        except FileNotFoundError:
            print_red("未找到PM2命令，无法使用PM2启动")
    else:
        print_red("未找到支持的进程管理工具（systemd或PM2）")
        print_yellow("请先安装PM2或配置systemd来管理交易机器人")
    
    safe_input("按 Enter 键返回主菜单...", "")

# 删除脚本
def remove_bot():
    print_red("警告: 此操作将删除交易机器人及其所有配置")
    confirm = safe_input("确认删除? (输入 'DELETE' 确认): ", "").strip()
    
    if confirm == "DELETE":
        use_systemd = is_using_systemd()
        
        if use_systemd:
            # 停止并禁用systemd服务
            subprocess.run(["systemctl", "--user", "stop", "backpack-bot"], capture_output=True)
            subprocess.run(["systemctl", "--user", "disable", "backpack-bot"], capture_output=True)
            
            # 删除服务文件
            service_file = os.path.expanduser("~/.config/systemd/user/backpack-bot.service")
            if os.path.exists(service_file):
                os.remove(service_file)
            
            # 重新加载systemd
            subprocess.run(["systemctl", "--user", "daemon-reload"], capture_output=True)
        else:
            # 停止机器人
            subprocess.run(["pm2", "delete", "backpack_bot"], capture_output=True)
        
        # 删除配置目录
        if os.path.exists(CONFIG_DIR):
            import shutil
            shutil.rmtree(CONFIG_DIR)
        
        print_green("交易机器人已完全删除")
        print_yellow("感谢使用，再见！")
        sys.exit(0)
    else:
        print_yellow("取消删除操作")
    
    safe_input("按 Enter 键返回主菜单...", "")

# 一键配置向导
def quick_setup_wizard():
    os.system('clear' if os.name != 'nt' else 'cls')
    print_blue("======================================")
    print_blue("      Backpack 交易机器人快速配置向导  ")
    print_blue("======================================")
    
    config = load_config()
    
    # 1. 配置API密钥
    print_blue("\n第1步：配置交易所API密钥")
    print_yellow("请输入您的 API Key:")
    api_key = safe_input("", config.get("api", "api_key", fallback="")).strip()
    
    print_yellow("请输入您的 API Secret:")
    api_secret = safe_input("", config.get("api", "api_secret", fallback="")).strip()
    
    if api_key and api_secret:
        config.set("api", "api_key", api_key)
        config.set("api", "api_secret", api_secret)
    else:
        print_red("API Key 或 Secret 不能为空！无法继续配置。")
        safe_input("按 Enter 键返回主菜单...", "")
        return
    
    # 2. 配置Telegram
    print_blue("\n第2步：配置Telegram通知")
    print_blue("机器人将使用默认令牌：7685502184:AAGxaIdwiTr0WpPDeIGmc9fgbdeSKxgXtEw")
    print_yellow("请输入您的 Telegram 用户 ID (可通过 @userinfobot 获取，若不需要可留空):")
    
    chat_id = safe_input("", config.get("telegram", "chat_id", fallback="")).strip()
    if chat_id:
        config.set("telegram", "chat_id", chat_id)
    
    # 3. 选择交易对
    print_blue("\n第3步：选择交易对")
    print_yellow("可用交易对：BTC_USDC_PERP, ETH_USDC_PERP, SOL_USDC_PERP, NEAR_USDC_PERP, AVAX_USDC_PERP, DOGE_USDC_PERP")
    print_yellow("请输入您要交易的对（用逗号分隔多个，如：ETH_USDC_PERP,SOL_USDC_PERP）:")
    
    pairs = safe_input("", config.get("trading", "symbols", fallback="ETH_USDC_PERP")).strip()
    if pairs:
        config.set("trading", "symbols", pairs)
    
    # 4. 保存配置
    save_config(config)
    print_green("配置已保存！")
    
    # 5. 询问是否立即启动
    print_yellow("\n是否立即启动交易机器人? (y/n):")
    start_now = safe_input("", "n").strip().lower()
    
    if start_now == 'y':
        # 启动机器人
        start_bot()
    else:
        print_yellow("您可以稍后通过主菜单启动机器人")
        safe_input("按 Enter 键返回主菜单...", "")

# 查看日志
def view_logs():
    print_blue("查看交易机器人日志")
    
    log_dir = os.path.expanduser("~/.backpack_bot")
    logs = [f for f in os.listdir(log_dir) if f.startswith("backpack_bot_") and f.endswith(".log")]
    
    if not logs:
        print_red("未找到日志文件")
        safe_input("按 Enter 键返回主菜单...", "")
        return
    
    # 按修改时间排序
    logs.sort(key=lambda x: os.path.getmtime(os.path.join(log_dir, x)), reverse=True)
    
    print_yellow("\n可用日志文件:")
    for i, log in enumerate(logs, 1):
        log_path = os.path.join(log_dir, log)
        log_size = os.path.getsize(log_path) / 1024  # KB
        mtime = datetime.fromtimestamp(os.path.getmtime(log_path))
        print(f"{i}. {log} - {log_size:.1f}KB, 最后修改: {mtime.strftime('%Y-%m-%d %H:%M:%S')}")
    
    print_yellow("\n请选择查看的日志文件编号 (0 表示返回):")
    selection = safe_input("", "0").strip()
    
    try:
        idx = int(selection)
        if idx == 0:
            return
        
        if 1 <= idx <= len(logs):
            log_file = os.path.join(log_dir, logs[idx-1])
            
            # 使用分页查看日志
            if os.name == 'nt':  # Windows
                os.system(f"type {log_file} | more")
            else:  # Unix/Linux/macOS
                os.system(f"cat {log_file} | less -R")
                
            print_yellow("\n日志查看完毕")
        else:
            print_red("无效的选择")
    except ValueError:
        print_red("请输入有效数字")
    
    safe_input("按 Enter 键返回主菜单...", "")

# 主菜单
def main_menu():
    # 解析命令行参数
    args = parse_args()
    
    # 如果提供了命令行参数，则直接执行相应的操作，不进入交互式菜单
    if args.api_key and args.api_secret:
        configure_exchange_api(args.api_key, args.api_secret)
    
    if args.telegram_id:
        configure_telegram(args.telegram_id)
    
    if args.trading_pairs:
        select_trading_pairs(args.trading_pairs)
    
    if args.position_limit or args.funding_threshold:
        configure_trading_params(args.position_limit, args.funding_threshold)
    
    if args.quick_setup:
        quick_setup_wizard()
        return
    
    if args.configure_api:
        configure_exchange_api()
        return
    
    if args.configure_telegram:
        configure_telegram()
        return
    
    if args.select_pairs:
        select_trading_pairs()
        return
    
    if args.configure_params:
        configure_trading_params()
        return
    
    if args.view_logs:
        view_logs()
        return
    
    if args.start_bot:
        start_bot()
        return
    
    if args.stop_bot:
        stop_bot()
        return
    
    # 检查是否有任何命令行参数被使用
    if any(vars(args).values()):
        return  # 如果使用了任何命令行参数，则不启动交互式菜单

    # 检查是否首次运行
    config = load_config()
    first_run = (config["api"]["api_key"] == "YOUR_API_KEY")
    
    if first_run:
        try:
            print_yellow("检测到首次运行，是否启动快速配置向导? (y/n):")
            start_wizard = safe_input("", "y").strip().lower()
            if start_wizard == 'y':
                quick_setup_wizard()
        except Exception as e:
            print_red(f"启动向导时出错: {e}")
            print_yellow("请手动配置您的交易机器人")
    
    while True:
        try:
            os.system('clear' if os.name != 'nt' else 'cls')
            
            print_blue("======================================")
            print_blue("        Backpack 交易机器人菜单      ")
            print_blue("======================================")
            
            # 检查机器人状态
            use_systemd = is_using_systemd()
            bot_running = False
            
            try:
                if use_systemd:
                    # 使用systemd检查状态
                    result = subprocess.run(["systemctl", "--user", "is-active", "backpack-bot"], 
                                          capture_output=True, text=True)
                    bot_running = result.stdout.strip() == "active"
                else:
                    # 使用PM2检查状态
                    result = subprocess.run(["pm2", "list"], capture_output=True, text=True)
                    bot_running = "backpack_bot" in result.stdout and "online" in result.stdout
            except:
                bot_running = False
                service_type = "systemd" if use_systemd else "PM2"
                print_red(f"无法检查{service_type}状态，可能未正确安装")
            
            status = "\033[32m运行中\033[0m" if bot_running else "\033[31m已停止\033[0m"
            service_type = "systemd" if use_systemd else "PM2"
            print_blue(f"机器人状态: {status} (使用{service_type}管理)")
            
            print_yellow("\n请选择操作:")
            print("1. 快速配置向导")
            print("2. 配置交易所 API")
            print("3. 配置 Telegram 通知")
            print("4. 选择交易对")
            print("5. 配置交易参数")
            print("6. 查看日志")
            if bot_running:
                print("7. 停止机器人")
            else:
                print("7. 启动机器人")
            print("8. 删除机器人")
            print("0. 退出")
            
            choice = safe_input("\n请输入选项: ", "0").strip()
            
            if choice == '1':
                quick_setup_wizard()
            elif choice == '2':
                configure_exchange_api()
            elif choice == '3':
                configure_telegram()
            elif choice == '4':
                select_trading_pairs()
            elif choice == '5':
                configure_trading_params()
            elif choice == '6':
                view_logs()
            elif choice == '7':
                stop_bot() if bot_running else start_bot()
            elif choice == '8':
                remove_bot()
            elif choice == '0':
                print_yellow("感谢使用，再见！")
                break
            else:
                print_red("无效选项，请重新选择")
                time.sleep(1)
        except KeyboardInterrupt:
            print_yellow("\n已检测到退出信号，正在退出...")
            break
        except Exception as e:
            print_red(f"发生错误: {e}")
            print_yellow("按Enter键继续...")
            try:
                safe_input("", "")
            except:
                pass

if __name__ == "__main__":
    main_menu() 