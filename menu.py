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

# 配置 Telegram
def configure_telegram():
    config = load_config()
    
    print_blue("配置 Telegram")
    print_blue("机器人将使用默认令牌：7685502184:AAGxaIdwiTr0WpPDeIGmc9fgbdeSKxgXtEw")
    print_yellow("请输入您的 Telegram 用户 ID (可通过 @userinfobot 获取):")
    
    chat_id = input().strip()
    
    if chat_id:
        config.set("telegram", "chat_id", chat_id)
        save_config(config)
        print_green("Telegram 配置已保存！")
    else:
        print_red("未输入 ID，Telegram 配置未更改。")
    
    input("按 Enter 键返回主菜单...")

# 配置交易所 API
def configure_exchange_api():
    config = load_config()
    
    print_blue("配置 Backpack 交易所 API")
    print_yellow("请输入您的 API Key:")
    api_key = input().strip()
    
    print_yellow("请输入您的 API Secret:")
    api_secret = input().strip()
    
    if api_key and api_secret:
        config.set("api", "api_key", api_key)
        config.set("api", "api_secret", api_secret)
        save_config(config)
        print_green("交易所 API 配置已保存！")
    else:
        print_red("API Key 或 Secret 不能为空！配置未更改。")
    
    input("按 Enter 键返回主菜单...")

# 选择交易对
def select_trading_pairs():
    config = load_config()
    
    # 获取支持的交易对列表
    # 在实际情况中，这可能需要从交易所 API 获取
    supported_pairs = [
        "BTC_USDC_PERP", 
        "ETH_USDC_PERP", 
        "SOL_USDC_PERP", 
        "NEAR_USDC_PERP",
        "AVAX_USDC_PERP",
        "DOGE_USDC_PERP"
    ]
    
    # 当前已配置的交易对
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
        
        choice = input("\n请选择操作: ").strip().upper()
        
        if choice == 'A':
            print_yellow("输入要添加的交易对编号(多个用空格分隔):")
            selections = input().strip().split()
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
            selections = input().strip().split()
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

# 查看日志
def view_logs():
    os.system('clear' if os.name != 'nt' else 'cls')
    print_blue("查看日志")
    
    # 查找最新日志文件
    log_pattern = re.compile(r'backpack_bot_(\d{8})\.log')
    logs = []
    
    for file in os.listdir(CONFIG_DIR):
        match = log_pattern.match(file)
        if match:
            logs.append((file, match.group(1)))
    
    if not logs:
        print_red("未找到日志文件")
        input("按 Enter 键返回主菜单...")
        return
    
    # 按日期排序
    logs.sort(key=lambda x: x[1], reverse=True)
    
    # 显示最新的日志
    latest_log = os.path.join(CONFIG_DIR, logs[0][0])
    
    while True:
        os.system('clear' if os.name != 'nt' else 'cls')
        print_blue(f"显示日志文件: {logs[0][0]}")
        
        # 使用 tail 命令显示最新日志
        if os.name != 'nt':
            os.system(f"tail -n 20 {latest_log}")
        else:
            # Windows 版本
            with open(latest_log, 'r') as f:
                lines = f.readlines()
                for line in lines[-20:]:
                    print(line.strip())
        
        print_yellow("\n操作选项:")
        print("1. 刷新")
        print("2. 查看全部日志")
        print("Q. 返回主菜单")
        
        choice = input("\n请选择操作: ").strip().upper()
        
        if choice == '1':
            continue
        elif choice == '2':
            if os.name != 'nt':
                os.system(f"less {latest_log}")
            else:
                # Windows 版本
                os.system(f"type {latest_log} | more")
        elif choice == 'Q':
            break

# 停止脚本
def stop_bot():
    print_blue("停止交易机器人")
    result = subprocess.run(["pm2", "stop", "backpack_bot"], capture_output=True, text=True)
    
    if result.returncode == 0:
        print_green("交易机器人已停止")
    else:
        print_red(f"停止失败: {result.stderr}")
    
    input("按 Enter 键返回主菜单...")

# 启动脚本
def start_bot():
    print_blue("启动交易机器人")
    
    # 检查配置是否完整
    config = load_config()
    if (config["api"]["api_key"] == "YOUR_API_KEY" or 
        config["api"]["api_secret"] == "YOUR_API_SECRET"):
        print_red("错误: 未配置 API 密钥，请先完成配置")
        input("按 Enter 键返回主菜单...")
        return
    
    if not config["telegram"]["chat_id"]:
        print_yellow("警告: 未配置 Telegram ID，将无法接收通知")
        proceed = input("是否继续启动? (y/n): ").strip().lower()
        if proceed != 'y':
            return
    
    # 启动机器人
    result = subprocess.run(["pm2", "start", os.path.join(CONFIG_DIR, "ecosystem.config.js")], 
                            capture_output=True, text=True)
    
    if result.returncode == 0:
        print_green("交易机器人已启动")
    else:
        print_red(f"启动失败: {result.stderr}")
    
    input("按 Enter 键返回主菜单...")

# 删除脚本
def remove_bot():
    print_red("警告: 此操作将删除交易机器人及其所有配置")
    confirm = input("确认删除? (输入 'DELETE' 确认): ").strip()
    
    if confirm == "DELETE":
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
    
    input("按 Enter 键返回主菜单...")

# 主菜单
def main_menu():
    while True:
        os.system('clear' if os.name != 'nt' else 'cls')
        
        print_blue("======================================")
        print_blue("        Backpack 交易机器人菜单      ")
        print_blue("======================================")
        
        # 检查机器人状态
        result = subprocess.run(["pm2", "list"], capture_output=True, text=True)
        bot_running = "backpack_bot" in result.stdout and "online" in result.stdout
        
        status = "\033[32m运行中\033[0m" if bot_running else "\033[31m已停止\033[0m"
        print_blue(f"机器人状态: {status}")
        
        print_yellow("\n请选择操作:")
        print("1. 配置 Telegram 通知")
        print("2. 配置交易所 API")
        print("3. 选择交易对")
        print("4. 查看日志")
        print("5. 停止机器人") if bot_running else print("5. 启动机器人")
        print("6. 删除机器人")
        print("7. 退出")
        
        choice = input("\n请输入选项: ").strip()
        
        if choice == '1':
            configure_telegram()
        elif choice == '2':
            configure_exchange_api()
        elif choice == '3':
            select_trading_pairs()
        elif choice == '4':
            view_logs()
        elif choice == '5':
            stop_bot() if bot_running else start_bot()
        elif choice == '6':
            remove_bot()
        elif choice == '7':
            print_yellow("感谢使用，再见！")
            break
        else:
            print_red("无效选项，请重新选择")
            time.sleep(1)

if __name__ == "__main__":
    main_menu() 