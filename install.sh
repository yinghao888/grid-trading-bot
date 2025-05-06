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

# 检查是否安装了必要的软件
check_dependencies() {
    print_blue "检查系统依赖..."
    
    # 检查 wget
    if ! command -v wget &> /dev/null; then
        print_red "未检测到 wget，正在安装..."
        if [[ "$OSTYPE" == "linux-gnu"* ]]; then
            sudo apt-get update
            sudo apt-get install -y wget
        elif [[ "$OSTYPE" == "darwin"* ]]; then
            # macOS
            brew install wget
        else
            print_red "不支持的操作系统，请手动安装 wget"
            exit 1
        fi
    fi
    
    # 检查 Python 3.7+
    if ! command -v python3 &> /dev/null; then
        print_red "未检测到 Python 3，正在安装..."
        if [[ "$OSTYPE" == "linux-gnu"* ]]; then
            sudo apt-get update
            sudo apt-get install -y python3 python3-pip
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
            sudo apt-get install -y python3-pip
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
            curl -sL https://deb.nodesource.com/setup_16.x | sudo -E bash -
            sudo apt-get install -y nodejs
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
        sudo npm install -g pm2
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
    
    # 下载所有必要文件
    wget -O $HOME/.backpack_bot/backpack_bot.py $REPO_URL/backpack_bot.py
    wget -O $HOME/.backpack_bot/backpack_api_impl.py $REPO_URL/backpack_api_impl.py
    wget -O $HOME/.backpack_bot/menu.py $REPO_URL/menu.py
    wget -O $HOME/.backpack_bot/telegram_handler.py $REPO_URL/telegram_handler.py
    wget -O $HOME/.backpack_bot/ecosystem.config.js $REPO_URL/ecosystem.config.js
    wget -O $HOME/.backpack_bot/config.ini $REPO_URL/config.ini
    
    # 设置启动脚本
    cat > $HOME/.backpack_bot/start.sh << EOF
#!/bin/bash
cd $HOME/.backpack_bot
python3 menu.py
EOF
    
    # 设置执行权限
    chmod +x $HOME/.backpack_bot/start.sh
    
    print_green "项目文件下载完成！"
}

# 设置 PM2 管理
setup_pm2() {
    print_blue "设置 PM2 管理..."
    
    # 设置 PM2 开机自启
    pm2 startup
    
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
    
    print_green "========================================"
    print_green "      安装完成！启动机器人菜单:        "
    print_green "      cd $HOME/.backpack_bot           "
    print_green "      ./start.sh                       "
    print_green "========================================"
}

# 执行主函数
main
