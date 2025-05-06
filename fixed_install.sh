#!/bin/bash

# 强制成功下载和直接进入菜单的安装脚本

# 定义GitHub仓库URL和分支
REPO="yinghao888/grid-trading-bot"
BRANCH="main"
RAW_URL="https://raw.githubusercontent.com/$REPO/$BRANCH"
GITHUB_API_URL="https://api.github.com/repos/$REPO/contents"

# 输出带颜色的文字函数
print_green() {
    echo -e "\033[32m$1\033[0m"
}

print_blue() {
    echo -e "\033[34m$1\033[0m"
}

print_red() {
    echo -e "\033[31m$1\033[0m"
}

print_yellow() {
    echo -e "\033[33m$1\033[0m"
}

# 清理日志并显示错误信息
clean_and_show_error() {
    print_red "发生错误: $1"
    print_red "===================================="
    print_red "请向开发者报告此错误"
    print_red "===================================="
    exit 1
}

# 检查是否安装了必要的软件
check_dependencies() {
    print_blue "检查系统依赖..."
    
    # 检查 curl
    if ! command -v curl &> /dev/null; then
        print_yellow "未检测到 curl，正在安装..."
        if [[ "$OSTYPE" == "linux-gnu"* ]] || [ -f /etc/os-release ]; then
            apt-get update && apt-get install -y curl || clean_and_show_error "无法安装curl"
        elif [[ "$OSTYPE" == "darwin"* ]]; then
            # macOS
            brew install curl || clean_and_show_error "无法安装curl"
        else
            clean_and_show_error "不支持的操作系统，请手动安装 curl"
        fi
    fi
    
    # 检查 Python 3.7+
    if ! command -v python3 &> /dev/null; then
        print_yellow "未检测到 Python 3，正在安装..."
        if [[ "$OSTYPE" == "linux-gnu"* ]] || [ -f /etc/os-release ]; then
            apt-get update && apt-get install -y python3 python3-pip || clean_and_show_error "无法安装Python3"
        elif [[ "$OSTYPE" == "darwin"* ]]; then
            # macOS
            brew install python3 || clean_and_show_error "无法安装Python3"
        else
            clean_and_show_error "不支持的操作系统，请手动安装 Python 3.7 或更高版本"
        fi
    fi
    
    # 检查 pip
    if ! command -v pip3 &> /dev/null; then
        print_yellow "未检测到 pip3，正在安装..."
        if [[ "$OSTYPE" == "linux-gnu"* ]] || [ -f /etc/os-release ]; then
            apt-get install -y python3-pip || clean_and_show_error "无法安装pip3"
        elif [[ "$OSTYPE" == "darwin"* ]]; then
            # macOS
            curl https://bootstrap.pypa.io/get-pip.py -o get-pip.py
            python3 get-pip.py
            rm get-pip.py
        else
            clean_and_show_error "不支持的操作系统，请手动安装 pip3"
        fi
    fi
    
    # 检查 Node.js 和 npm
    if ! command -v node &> /dev/null; then
        print_yellow "未检测到 Node.js，正在安装..."
        if [[ "$OSTYPE" == "linux-gnu"* ]] || [ -f /etc/os-release ]; then
            curl -sL https://deb.nodesource.com/setup_16.x | bash -
            apt-get install -y nodejs || clean_and_show_error "无法安装Node.js"
        elif [[ "$OSTYPE" == "darwin"* ]]; then
            # macOS
            brew install node || clean_and_show_error "无法安装Node.js"
        else
            clean_and_show_error "不支持的操作系统，请手动安装 Node.js"
        fi
    fi
    
    # 检查 PM2
    if ! command -v pm2 &> /dev/null; then
        print_yellow "未检测到 PM2，正在安装..."
        npm install -g pm2 || clean_and_show_error "无法安装PM2"
    fi
    
    print_green "所有系统依赖已安装完成！"
}

# 检查网络连接
check_network() {
    print_blue "检查网络连接..."
    
    # 检查GitHub连接
    if ! curl -s --head --connect-timeout 10 https://raw.githubusercontent.com > /dev/null; then
        print_red "无法连接到GitHub，请检查您的网络连接"
        return 1
    fi
    
    # 检查仓库是否存在
    if ! curl -s --head --connect-timeout 10 "$RAW_URL/README.md" > /dev/null; then
        print_red "无法连接到指定仓库，请检查仓库地址是否正确"
        return 1
    fi
    
    print_green "网络连接正常！"
    return 0
}

# 安装 Python 依赖
install_python_dependencies() {
    print_blue "安装 Python 依赖..."
    
    # 使用pip安装必要的包
    pip3 install aiohttp websockets python-telegram-bot configparser asyncio || clean_and_show_error "安装Python依赖失败"
    
    print_green "Python 依赖安装完成！"
}

# 下载单个文件的函数
download_file() {
    local filename="$1"
    local output_path="$2"
    local attempt=1
    local max_attempts=3
    
    while [ $attempt -le $max_attempts ]; do
        print_yellow "下载 $filename... (尝试 $attempt/$max_attempts)"
        
        # 尝试从raw.githubusercontent.com下载
        curl -s -L -o "$output_path" "$RAW_URL/$filename"
        
        # 检查文件是否存在且非空
        if [ -f "$output_path" ] && [ -s "$output_path" ]; then
            print_green "$filename 下载成功!"
            return 0
        fi
        
        print_red "$filename 下载失败，尝试备用方式..."
        
        # 尝试使用GitHub API获取文件内容
        if [ $attempt -eq 2 ]; then
            content_url=$(curl -s "$GITHUB_API_URL/$filename?ref=$BRANCH" | grep "download_url" | cut -d '"' -f 4)
            if [ -n "$content_url" ]; then
                curl -s -L -o "$output_path" "$content_url"
                if [ -f "$output_path" ] && [ -s "$output_path" ]; then
                    print_green "$filename 使用API下载成功!"
                    return 0
                fi
            fi
        fi
        
        # 最后尝试使用clone整个仓库
        if [ $attempt -eq 3 ]; then
            print_yellow "尝试克隆整个仓库..."
            
            # 检查是否安装了git
            if ! command -v git &> /dev/null; then
                print_yellow "未检测到git，正在安装..."
                apt-get update && apt-get install -y git || clean_and_show_error "无法安装git"
            fi
            
            # 创建临时目录并克隆仓库
            local temp_dir=$(mktemp -d)
            if git clone --depth 1 "https://github.com/$REPO.git" "$temp_dir"; then
                # 从克隆的仓库复制文件
                if [ -f "$temp_dir/$filename" ]; then
                    cp "$temp_dir/$filename" "$output_path"
                    rm -rf "$temp_dir"  # 清理临时目录
                    
                    if [ -f "$output_path" ] && [ -s "$output_path" ]; then
                        print_green "$filename 通过克隆仓库获取成功!"
                        return 0
                    fi
                fi
                rm -rf "$temp_dir"  # 清理临时目录
            fi
        fi
        
        attempt=$((attempt+1))
    done
    
    print_red "$filename 所有下载方式均失败."
    return 1
}

# 下载项目文件
download_project_files() {
    print_blue "正在下载项目文件..."
    
    # 确保配置目录存在
    mkdir -p "$HOME/.backpack_bot"
    cd "$HOME/.backpack_bot" || clean_and_show_error "无法进入安装目录"
    
    # 要下载的文件列表
    local files=(
        "backpack_bot.py"
        "backpack_api_impl.py"
        "menu.py"
        "telegram_handler.py"
        "ecosystem.config.js"
        "config.ini"
    )
    
    # 下载每个文件
    for file in "${files[@]}"; do
        download_file "$file" "./$file" || clean_and_show_error "无法下载 $file"
    done
    
    # 创建启动脚本
    cat > start.sh << 'EOF'
#!/bin/bash
cd "$HOME/.backpack_bot"
python3 menu.py
EOF
    
    # 设置执行权限
    chmod +x start.sh || clean_and_show_error "无法设置执行权限"
    
    print_green "所有项目文件下载完成！"
}

# 创建并安装自定义菜单启动器（防止menu.py有问题）
create_menu_launcher() {
    print_blue "创建菜单启动器..."
    
    # 创建菜单启动器文件
    cat > "$HOME/.backpack_bot/menu_launcher.py" << 'EOF'
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import subprocess
import time

def print_color(text, color_code):
    print(f"\033[{color_code}m{text}\033[0m")

def print_red(text):
    print_color(text, "31")

def print_green(text):
    print_color(text, "32")

def print_blue(text):
    print_color(text, "34")

def print_yellow(text):
    print_color(text, "33")

def clear_screen():
    os.system('clear' if os.name != 'nt' else 'cls')

def main_menu():
    while True:
        clear_screen()
        print_blue("======================================")
        print_blue("        Backpack 交易机器人菜单      ")
        print_blue("======================================")
        
        print_yellow("\n请选择操作:")
        print("1. 尝试启动原始菜单")
        print("2. 配置 API 密钥")
        print("3. 启动交易机器人")
        print("4. 停止交易机器人")
        print("5. 查看日志")
        print("6. 退出")
        
        choice = input("\n请输入选项: ").strip()
        
        if choice == '1':
            try:
                subprocess.run([sys.executable, os.path.join(os.path.expanduser("~"), ".backpack_bot", "menu.py")])
            except Exception as e:
                print_red(f"启动原始菜单失败: {e}")
                input("按 Enter 键继续...")
        
        elif choice == '2':
            edit_config()
        
        elif choice == '3':
            start_bot()
        
        elif choice == '4':
            stop_bot()
        
        elif choice == '5':
            view_logs()
        
        elif choice == '6':
            print_yellow("感谢使用，再见！")
            break
        
        else:
            print_red("无效选项，请重新选择")
            time.sleep(1)

def edit_config():
    config_path = os.path.join(os.path.expanduser("~"), ".backpack_bot", "config.ini")
    
    if not os.path.exists(config_path):
        print_red(f"配置文件不存在: {config_path}")
        input("按 Enter 键继续...")
        return
    
    try:
        # 读取现有配置
        with open(config_path, 'r') as f:
            config_content = f.readlines()
        
        clear_screen()
        print_blue("配置 Backpack 交易所 API")
        print_yellow("请输入您的 API Key:")
        api_key = input().strip()
        
        print_yellow("请输入您的 API Secret:")
        api_secret = input().strip()
        
        if api_key and api_secret:
            # 修改配置
            new_content = []
            for line in config_content:
                if line.strip().startswith("api_key ="):
                    new_content.append(f"api_key = {api_key}\n")
                elif line.strip().startswith("api_secret ="):
                    new_content.append(f"api_secret = {api_secret}\n")
                else:
                    new_content.append(line)
            
            # 保存修改
            with open(config_path, 'w') as f:
                f.writelines(new_content)
            
            print_green("交易所 API 配置已保存！")
        else:
            print_red("API Key 或 Secret 不能为空！配置未更改。")
        
        input("按 Enter 键继续...")
    
    except Exception as e:
        print_red(f"配置编辑失败: {e}")
        input("按 Enter 键继续...")

def start_bot():
    try:
        print_blue("启动交易机器人")
        result = subprocess.run(["pm2", "start", os.path.join(os.path.expanduser("~"), ".backpack_bot", "ecosystem.config.js")], 
                                capture_output=True, text=True)
        
        if result.returncode == 0:
            print_green("交易机器人已启动")
        else:
            print_red(f"启动失败: {result.stderr}")
        
        input("按 Enter 键继续...")
    except Exception as e:
        print_red(f"启动机器人失败: {e}")
        input("按 Enter 键继续...")

def stop_bot():
    try:
        print_blue("停止交易机器人")
        result = subprocess.run(["pm2", "stop", "backpack_bot"], capture_output=True, text=True)
        
        if result.returncode == 0:
            print_green("交易机器人已停止")
        else:
            print_red(f"停止失败: {result.stderr}")
        
        input("按 Enter 键继续...")
    except Exception as e:
        print_red(f"停止机器人失败: {e}")
        input("按 Enter 键继续...")

def view_logs():
    try:
        # 查找最新日志文件
        log_dir = os.path.expanduser("~/.backpack_bot")
        log_files = [f for f in os.listdir(log_dir) if f.endswith('.log')]
        
        if not log_files:
            print_red("未找到日志文件")
            input("按 Enter 键继续...")
            return
        
        # 按修改时间排序
        log_files.sort(key=lambda x: os.path.getmtime(os.path.join(log_dir, x)), reverse=True)
        latest_log = os.path.join(log_dir, log_files[0])
        
        # 显示日志
        if os.name != 'nt':
            subprocess.run(["tail", "-f", latest_log])
        else:
            # Windows版本
            with open(latest_log, 'r') as f:
                lines = f.readlines()
                for line in lines[-20:]:
                    print(line.strip())
            
            input("按 Enter 键继续...")
    except Exception as e:
        print_red(f"查看日志失败: {e}")
        input("按 Enter 键继续...")

if __name__ == "__main__":
    main_menu()
EOF
    
    # 设置执行权限
    chmod +x "$HOME/.backpack_bot/menu_launcher.py" || clean_and_show_error "无法设置菜单启动器执行权限"
    
    # 更新启动脚本指向备用菜单
    cat > "$HOME/.backpack_bot/start.sh" << 'EOF'
#!/bin/bash
cd "$HOME/.backpack_bot"
if [ -f menu.py ] && [ -s menu.py ]; then
    python3 menu.py
else
    python3 menu_launcher.py
fi
EOF
    
    chmod +x "$HOME/.backpack_bot/start.sh" || clean_and_show_error "无法设置启动脚本执行权限"
    
    print_green "菜单启动器创建完成！"
}

# 设置 PM2 管理
setup_pm2() {
    print_blue "设置 PM2 管理..."
    
    # 设置 PM2 开机自启
    pm2 startup 2>/dev/null || true
    
    print_green "PM2 配置完成！"
}

# 主函数
main() {
    print_blue "========================================"
    print_blue "      Backpack 交易机器人安装程序       "
    print_blue "========================================"
    
    # 检查网络连接
    check_network || clean_and_show_error "网络连接检查失败"
    
    # 检查和安装依赖
    check_dependencies
    
    # 安装 Python 依赖
    install_python_dependencies
    
    # 下载项目文件
    download_project_files
    
    # 创建备用菜单启动器
    create_menu_launcher
    
    # 设置 PM2
    setup_pm2
    
    # 显示安装完成信息
    print_green "========================================"
    print_green "      安装完成！正在启动机器人菜单...   "
    print_green "========================================"
    
    # 启动菜单
    cd "$HOME/.backpack_bot" || clean_and_show_error "无法进入安装目录"
    exec ./start.sh  # 使用exec替代，确保正确启动菜单
}

# 执行主函数
main
