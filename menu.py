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
import signal

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

# 检测是否使用systemd
def is_using_systemd():
    systemd_service = os.path.expanduser("~/.config/systemd/user/backpack-bot.service")
    return os.path.exists(systemd_service)

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
    
    # 使用systemd还是PM2
    use_systemd = is_using_systemd()
    
    if use_systemd:
        try:
            # 使用systemd日志
            print_blue("正在获取systemd日志...")
            os.system("journalctl --user -u backpack-bot -n 20")
            
            print_yellow("\n操作选项:")
            print("1. 刷新")
            print("2. 查看更多日志")
            print("Q. 返回主菜单")
            
            choice = input("\n请选择操作: ").strip().upper()
            
            if choice == '1':
                view_logs()  # 刷新
                return
            elif choice == '2':
                os.system("journalctl --user -u backpack-bot")
            elif choice == 'Q':
                return
        except Exception as e:
            print_red(f"获取systemd日志失败: {e}")
            input("按 Enter 键返回主菜单...")
        return
    
    # 查找最新日志文件
    log_pattern = re.compile(r'backpack_bot_(\d{8})\.log')
    pm2_logs = []
    
    try:
        # 首先尝试获取PM2日志
        pm2_log_dir = os.path.expanduser("~/.pm2/logs")
        if os.path.exists(pm2_log_dir):
            for file in os.listdir(pm2_log_dir):
                if file.startswith("backpack_bot"):
                    pm2_logs.append(os.path.join(pm2_log_dir, file))
    except:
        pass
    
    # 检查本地日志目录
    logs = []
    for file in os.listdir(CONFIG_DIR):
        match = log_pattern.match(file)
        if match:
            logs.append((file, match.group(1)))
    
    if not logs and not pm2_logs:
        print_red("未找到日志文件")
        input("按 Enter 键返回主菜单...")
        return
    
    # 按日期排序本地日志
    logs.sort(key=lambda x: x[1], reverse=True)
    
    # 显示最新的日志
    log_file = ""
    if pm2_logs:
        # 优先显示PM2日志
        log_file = pm2_logs[0]
        log_name = os.path.basename(log_file)
    elif logs:
        log_file = os.path.join(CONFIG_DIR, logs[0][0])
        log_name = logs[0][0]
    
    while True:
        os.system('clear' if os.name != 'nt' else 'cls')
        print_blue(f"显示日志文件: {log_name}")
        
        # 使用 tail 命令显示最新日志
        if os.name != 'nt':
            os.system(f"tail -n 20 {log_file}")
        else:
            # Windows 版本
            try:
                with open(log_file, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                    for line in lines[-20:]:
                        print(line.strip())
            except:
                print_red("读取日志文件失败")
        
        print_yellow("\n操作选项:")
        print("1. 刷新")
        print("2. 查看全部日志")
        print("Q. 返回主菜单")
        
        choice = input("\n请选择操作: ").strip().upper()
        
        if choice == '1':
            continue
        elif choice == '2':
            if os.name != 'nt':
                os.system(f"less {log_file}")
            else:
                # Windows 版本
                os.system(f"type {log_file} | more")
        elif choice == 'Q':
            break

# 配置交易参数
def configure_trading_params():
    config = load_config()
    
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
    
    choice = input("\n请选择操作: ").strip().upper()
    
    if choice == '1':
        print_yellow("请输入仓位限制 (例如 0.001):")
        value = input().strip()
        if value:
            config.set("trading", "position_limit", value)
    elif choice == '2':
        print_yellow("请输入资金费率阈值 (例如 0.0001):")
        value = input().strip()
        if value:
            config.set("trading", "funding_threshold", value)
    elif choice == '3':
        print_yellow("请输入检查间隔(秒) (例如 300):")
        value = input().strip()
        if value:
            config.set("trading", "check_interval", value)
    elif choice == '4':
        print_yellow("请输入杠杆倍数 (例如 20):")
        value = input().strip()
        if value:
            config.set("trading", "leverage", value)
    elif choice == '5':
        print_yellow("请输入利润目标 (例如 0.0002):")
        value = input().strip()
        if value:
            config.set("trading", "profit_target", value)
    elif choice == '6':
        print_yellow("请输入止损比例 (例如 0.1):")
        value = input().strip()
        if value:
            config.set("trading", "stop_loss", value)
    elif choice == '7':
        print_yellow("请输入冷却时间(分钟) (例如 30):")
        value = input().strip()
        if value:
            config.set("trading", "cooldown_minutes", value)
    elif choice == 'S':
        save_config(config)
        print_green("交易参数已保存!")
        time.sleep(1)
    elif choice == 'Q':
        print_yellow("未保存更改")
        time.sleep(1)
    
    # 递归调用自己，直到用户选择返回
    if choice not in ['S', 'Q']:
        configure_trading_params()

# 停止脚本
def stop_bot():
    print_blue("停止交易机器人")
    
    use_systemd = is_using_systemd()
    
    if use_systemd:
        # 使用systemd停止
        try:
            subprocess.run(["systemctl", "--user", "stop", "backpack-bot"], check=True)
            print_green("交易机器人已停止")
        except subprocess.CalledProcessError:
            print_red("停止失败，请手动检查状态")
    else:
        # 使用PM2停止
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
    
    use_systemd = is_using_systemd()
    
    if use_systemd:
        # 使用systemd启动
        try:
            print_yellow("使用systemd启动机器人...")
            subprocess.run(["systemctl", "--user", "start", "backpack-bot"], check=True)
            print_green("交易机器人已启动")
            print_green("systemd将自动管理交易机器人，确保其稳定运行")
        except subprocess.CalledProcessError:
            print_red("启动失败，请手动检查错误")
    else:
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
    
    input("按 Enter 键返回主菜单...")

# 删除脚本
def remove_bot():
    print_red("警告: 此操作将删除交易机器人及其所有配置")
    confirm = input("确认删除? (输入 'DELETE' 确认): ").strip()
    
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
    
    input("按 Enter 键返回主菜单...")

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
    api_key = input().strip()
    
    print_yellow("请输入您的 API Secret:")
    api_secret = input().strip()
    
    if api_key and api_secret:
        config.set("api", "api_key", api_key)
        config.set("api", "api_secret", api_secret)
    else:
        print_red("API Key 或 Secret 不能为空！无法继续配置。")
        input("按 Enter 键返回主菜单...")
        return
    
    # 2. 配置Telegram
    print_blue("\n第2步：配置Telegram通知")
    print_blue("机器人将使用默认令牌：7685502184:AAGxaIdwiTr0WpPDeIGmc9fgbdeSKxgXtEw")
    print_yellow("请输入您的 Telegram 用户 ID (可通过 @userinfobot 获取，若不需要可留空):")
    
    chat_id = input().strip()
    if chat_id:
        config.set("telegram", "chat_id", chat_id)
    
    # 3. 选择交易对
    print_blue("\n第3步：选择交易对")
    print_yellow("可用交易对：BTC_USDC_PERP, ETH_USDC_PERP, SOL_USDC_PERP, NEAR_USDC_PERP, AVAX_USDC_PERP, DOGE_USDC_PERP")
    print_yellow("请输入您要交易的对（用逗号分隔多个，如：ETH_USDC_PERP,SOL_USDC_PERP）:")
    
    pairs = input().strip()
    if pairs:
        config.set("trading", "symbols", pairs)
    
    # 4. 保存配置
    save_config(config)
    print_green("配置已保存！")
    
    # 5. 询问是否立即启动
    print_yellow("\n是否立即启动交易机器人? (y/n):")
    start_now = input().strip().lower()
    
    if start_now == 'y':
        # 启动机器人
        start_bot()
    else:
        print_yellow("您可以稍后通过主菜单启动机器人")
        input("按 Enter 键返回主菜单...")

# 主菜单
def main_menu():
    # 检查是否首次运行
    config = load_config()
    first_run = (config["api"]["api_key"] == "YOUR_API_KEY")
    
    if first_run:
        try:
            print_yellow("检测到首次运行，是否启动快速配置向导? (y/n):")
            # 设置超时，避免在非交互环境中无限等待
            
            def timeout_handler(signum, frame):
                raise TimeoutError("输入超时")
            
            # 设置5秒超时
            signal.signal(signal.SIGALRM, timeout_handler)
            signal.alarm(5)
            
            try:
                start_wizard = input().strip().lower()
                signal.alarm(0)  # 取消超时
                if start_wizard == 'y':
                    quick_setup_wizard()
            except (TimeoutError, EOFError):
                print_yellow("非交互式环境或输入超时，跳过快速配置向导")
                signal.alarm(0)  # 确保取消超时
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
            
            try:
                # 设置输入超时
                signal.signal(signal.SIGALRM, timeout_handler)
                signal.alarm(60)  # 60秒超时
                
                choice = input("\n请输入选项: ").strip()
                signal.alarm(0)  # 取消超时
            except (TimeoutError, EOFError):
                print_yellow("输入超时或非交互环境，退出菜单")
                break
            
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
                input()
            except:
                pass

if __name__ == "__main__":
    main_menu() 