#!/bin/bash

# 定义GitHub仓库URL
REPO_URL="https://raw.githubusercontent.com/yinghao888/grid-trading-bot/main"

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

# 检查是否安装了必要的软件
check_dependencies() {
    print_blue "检查系统依赖..."
    
    # 检查 curl
    if ! command -v curl &> /dev/null; then
        print_red "未检测到 curl，正在安装..."
        if [[ "$OSTYPE" == "linux-gnu"* ]]; then
            apt-get update
            apt-get install -y curl
        elif [[ "$OSTYPE" == "darwin"* ]]; then
            # macOS
            brew install curl
        else
            print_red "不支持的操作系统，请手动安装 curl"
            exit 1
        fi
    fi
    
    # 检查 Python 3.7+
    if ! command -v python3 &> /dev/null; then
        print_red "未检测到 Python 3，正在安装..."
        if [[ "$OSTYPE" == "linux-gnu"* ]]; then
            apt-get update
            apt-get install -y python3 python3-pip
        elif [[ "$OSTYPE" == "darwin"* ]]; then
            # macOS
            brew install python3
        else
            print_red "不支持的操作系统，请手动安装 Python 3.7 或更高版本"
            exit 1
        fi
    fi
    
    # 检查 pip
    if ! command -v pip3 &> /dev/null; then
        print_red "未检测到 pip3，正在安装..."
        if [[ "$OSTYPE" == "linux-gnu"* ]]; then
            apt-get install -y python3-pip
        elif [[ "$OSTYPE" == "darwin"* ]]; then
            # macOS
            curl https://bootstrap.pypa.io/get-pip.py -o get-pip.py
            python3 get-pip.py
            rm get-pip.py
        else
            print_red "不支持的操作系统，请手动安装 pip3"
            exit 1
        fi
    fi
    
    # 检查 Node.js 和 npm
    if ! command -v node &> /dev/null; then
        print_red "未检测到 Node.js，正在安装..."
        if [[ "$OSTYPE" == "linux-gnu"* ]]; then
            curl -sL https://deb.nodesource.com/setup_16.x | bash -
            apt-get install -y nodejs
        elif [[ "$OSTYPE" == "darwin"* ]]; then
            # macOS
            brew install node
        else
            print_red "不支持的操作系统，请手动安装 Node.js"
            exit 1
        fi
    fi
    
    # 检查 PM2
    if ! command -v pm2 &> /dev/null; then
        print_red "未检测到 PM2，正在安装..."
        npm install -g pm2
    fi
    
    print_green "所有系统依赖已安装完成！"
}

# 安装 Python 依赖
install_python_dependencies() {
    print_blue "安装 Python 依赖..."
    pip3 install aiohttp websockets python-telegram-bot configparser asyncio
    print_green "Python 依赖安装完成！"
}

# 下载项目文件
download_project_files() {
    print_blue "下载项目文件..."
    
    # 确保配置目录存在
    mkdir -p $HOME/.backpack_bot
    cd $HOME/.backpack_bot
    
    # 下载所有必要文件
    print_yellow "下载 backpack_bot.py..."
    curl -s -o backpack_bot.py $REPO_URL/backpack_bot.py
    
    print_yellow "下载 backpack_api_impl.py..."
    curl -s -o backpack_api_impl.py $REPO_URL/backpack_api_impl.py
    
    print_yellow "下载 menu.py..."
    curl -s -o menu.py $REPO_URL/menu.py
    
    print_yellow "下载 telegram_handler.py..."
    curl -s -o telegram_handler.py $REPO_URL/telegram_handler.py
    
    print_yellow "下载 ecosystem.config.js..."
    curl -s -o ecosystem.config.js $REPO_URL/ecosystem.config.js
    
    print_yellow "下载 config.ini..."
    curl -s -o config.ini $REPO_URL/config.ini
    
    # 验证文件是否正确下载
    if [ ! -f menu.py ] || [ ! -s menu.py ]; then
        print_red "menu.py 下载失败或文件为空！"
        print_yellow "尝试备用方式下载..."
        curl -L -o menu.py $REPO_URL/menu.py
        if [ ! -f menu.py ] || [ ! -s menu.py ]; then
            print_red "menu.py 二次下载失败，请手动检查网络连接或仓库地址！"
            exit 1
        fi
    fi
    
    # 检查其他重要文件
    for file in backpack_bot.py backpack_api_impl.py telegram_handler.py ecosystem.config.js config.ini; do
        if [ ! -f "$file" ] || [ ! -s "$file" ]; then
            print_red "$file 下载失败或文件为空！"
            print_yellow "尝试备用方式下载..."
            curl -L -o "$file" "$REPO_URL/$file"
            if [ ! -f "$file" ] || [ ! -s "$file" ]; then
                print_red "$file 二次下载失败，请手动检查网络连接或仓库地址！"
                exit 1
            fi
        fi
    done
    
    # 设置启动脚本
    cat > start.sh << 'EOF'
#!/bin/bash
cd "$HOME/.backpack_bot"
python3 menu.py
EOF
    
    # 设置执行权限
    chmod +x start.sh
    
    print_green "项目文件下载完成！"
}

# 设置 PM2 管理
setup_pm2() {
    print_blue "设置 PM2 管理..."
    
    # 设置 PM2 开机自启
    pm2 startup | grep -v "sudo" || true
    
    print_green "PM2 配置完成！"
}

# 主函数
main() {
    print_blue "========================================"
    print_blue "      Backpack 交易机器人安装程序       "
    print_blue "========================================"
    
    # 检查和安装依赖
    check_dependencies
    
    # 安装 Python 依赖
    install_python_dependencies
    
    # 下载项目文件
    download_project_files
    
    # 设置 PM2
    setup_pm2
    
    # 运行菜单
    print_green "========================================"
    print_green "      安装完成！自动启动机器人菜单...   "
    print_green "========================================"
    
    # 自动启动菜单
    cd $HOME/.backpack_bot
    ./start.sh
}

# 执行主函数
main 
