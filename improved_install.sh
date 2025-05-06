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

# 默认配置值，可以通过环境变量修改
API_KEY=${API_KEY:-""}
API_SECRET=${API_SECRET:-""}
SYMBOLS=${SYMBOLS:-"ETH_USDC_PERP"}
POSITION_LIMIT=${POSITION_LIMIT:-"0.001"}
FUNDING_THRESHOLD=${FUNDING_THRESHOLD:-"0.0001"}
TELEGRAM_CHAT_ID=${TELEGRAM_CHAT_ID:-""}
AUTO_START=${AUTO_START:-"true"}
USE_SYSTEMD=${USE_SYSTEMD:-"false"}

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
    
    # 如果不使用systemd，则安装Node.js和PM2
    if [ "$USE_SYSTEMD" != "true" ]; then
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
    
    print_yellow "下载一键配置脚本..."
    curl -s -o backpack-config $REPO_URL/backpack-config
    
    # 如果使用systemd，下载服务文件
    if [ "$USE_SYSTEMD" = "true" ]; then
        print_yellow "下载systemd服务文件..."
        curl -s -o backpack-bot.service $REPO_URL/backpack-bot.service
    fi
    
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
    for file in backpack_bot.py backpack_api_impl.py telegram_handler.py backpack-config; do
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
    
    # 设置执行权限
    chmod +x backpack-config
    
    # 创建直接启动脚本，根据使用systemd还是PM2来创建不同的脚本
    if [ "$USE_SYSTEMD" = "true" ]; then
        cat > direct-start.sh << 'EOF'
#!/bin/bash
cd "$HOME/.backpack_bot"

# 使用systemd启动交易机器人
systemctl --user start backpack-bot
echo "交易机器人已启动！"
echo "查看状态: systemctl --user status backpack-bot"
echo "查看日志: journalctl --user -u backpack-bot -f"
echo "停止机器人: systemctl --user stop backpack-bot"
EOF
    else
        cat > direct-start.sh << 'EOF'
#!/bin/bash
cd "$HOME/.backpack_bot"

# 直接启动交易机器人，无需交互
pm2 start ecosystem.config.js
echo "交易机器人已启动！"
echo "查看状态: pm2 status"
echo "查看日志: pm2 logs backpack_bot"
echo "停止机器人: pm2 stop backpack_bot"
EOF
    fi
    
    chmod +x direct-start.sh
    
    # 将配置命令移动到系统路径
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        if [ -d "/usr/local/bin" ]; then
            print_yellow "安装backpack-config命令到系统..."
            sudo cp backpack-config /usr/local/bin/
            sudo chmod +x /usr/local/bin/backpack-config
        else
            print_yellow "无法找到合适的系统路径，将在本地目录使用命令"
        fi
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        if [ -d "/usr/local/bin" ]; then
            print_yellow "安装backpack-config命令到系统..."
            sudo cp backpack-config /usr/local/bin/
            sudo chmod +x /usr/local/bin/backpack-config
        else
            print_yellow "无法找到合适的系统路径，将在本地目录使用命令"
        fi
    else
        print_yellow "无法安装全局命令。您可以通过以下方式启动配置菜单："
        print_yellow "$HOME/.backpack_bot/backpack-config"
    fi
    
    print_green "项目文件下载完成！"
}

# 设置 PM2 管理或systemd服务
setup_startup_service() {
    if [ "$USE_SYSTEMD" = "true" ]; then
        print_blue "设置 systemd 服务..."
        
        # 创建用户systemd目录
        mkdir -p $HOME/.config/systemd/user/
        
        # 复制并定制服务文件
        sed "s|%h|$HOME|g" $HOME/.backpack_bot/backpack-bot.service > $HOME/.config/systemd/user/backpack-bot.service
        
        # 启用服务（但不立即启动）
        systemctl --user daemon-reload
        systemctl --user enable backpack-bot.service
        
        print_green "systemd 服务配置完成！"
    else
        print_blue "设置 PM2 管理..."
        
        # 确保 PM2 配置文件正确，只用于交易机器人
        cat > $HOME/.backpack_bot/ecosystem.config.js << 'EOF'
module.exports = {
  apps : [{
    name: 'backpack_bot',
    script: `${process.env.HOME}/.backpack_bot/backpack_bot.py`,
    interpreter: 'python3',
    autorestart: true,
    watch: false,
    max_memory_restart: '200M',
    env: {
      NODE_ENV: 'production'
    },
    log_date_format: 'YYYY-MM-DD HH:mm:ss'
  }]
}; 
EOF
        
        # 设置 PM2 开机自启
        pm2 startup | grep -v "sudo" || true
        
        print_green "PM2 配置完成！"
    fi
}

# 创建配置文件
create_config_file() {
    print_blue "创建配置文件..."
    
    # 如果没有提供API密钥，询问用户
    if [ -z "$API_KEY" ]; then
        print_yellow "未提供API密钥。请输入Backpack API密钥 (按Enter跳过): "
        read -r API_KEY
    fi
    
    if [ -z "$API_SECRET" ]; then
        print_yellow "未提供API密钥。请输入Backpack API密钥 (按Enter跳过): "
        read -r API_SECRET
    fi
    
    # 创建配置文件
    cat > $HOME/.backpack_bot/config.ini << EOF
[api]
api_key = ${API_KEY}
api_secret = ${API_SECRET}
base_url = https://api.backpack.exchange
ws_url = wss://ws.backpack.exchange

[trading]
symbols = ${SYMBOLS}
position_limit = ${POSITION_LIMIT}
funding_threshold = ${FUNDING_THRESHOLD}
check_interval = 300
leverage = 20
profit_target = 0.0002
stop_loss = 0.1
cooldown_minutes = 30

[telegram]
bot_token = 7685502184:AAGxaIdwiTr0WpPDeIGmc9fgbdeSKxgXtEw
chat_id = ${TELEGRAM_CHAT_ID}
EOF
    
    print_green "配置文件已创建！"
}

# 创建一键配置命令
create_config_command() {
    print_blue "创建一键配置命令..."
    
    # 创建别名命令
    SHELL_RC=""
    if [ -f "$HOME/.bashrc" ]; then
        SHELL_RC="$HOME/.bashrc"
    elif [ -f "$HOME/.zshrc" ]; then
        SHELL_RC="$HOME/.zshrc"
    fi
    
    if [ -n "$SHELL_RC" ]; then
        # 检查是否已存在别名
        if ! grep -q "alias backpack-config=" "$SHELL_RC"; then
            echo "# Backpack Grid Trading Bot 命令" >> "$SHELL_RC"
            echo "alias backpack-config='$HOME/.backpack_bot/backpack-config'" >> "$SHELL_RC"
            echo "alias backpack-start='$HOME/.backpack_bot/direct-start.sh'" >> "$SHELL_RC"
        fi
        print_green "命令别名已添加到 $SHELL_RC"
    else
        print_yellow "无法找到 shell 配置文件，请手动添加以下命令到你的 shell 配置文件："
        print_yellow "alias backpack-config='$HOME/.backpack_bot/backpack-config'"
        print_yellow "alias backpack-start='$HOME/.backpack_bot/direct-start.sh'"
    fi
    
    print_green "一键配置命令创建完成！"
}

# 自动启动交易机器人
auto_start_bot() {
    if [ "$AUTO_START" = "true" ] && [ -n "$API_KEY" ] && [ -n "$API_SECRET" ]; then
        print_blue "自动启动交易机器人..."
        cd $HOME/.backpack_bot
        
        if [ "$USE_SYSTEMD" = "true" ]; then
            systemctl --user start backpack-bot
            print_green "交易机器人已启动！"
            print_green "查看状态: systemctl --user status backpack-bot"
            print_green "查看日志: journalctl --user -u backpack-bot -f"
            print_green "停止机器人: systemctl --user stop backpack-bot"
        else
            pm2 start ecosystem.config.js
            pm2 save
            print_green "交易机器人已启动！"
            print_green "查看状态: pm2 status"
            print_green "查看日志: pm2 logs backpack_bot"
            print_green "停止机器人: pm2 stop backpack_bot"
        fi
    else
        if [ "$AUTO_START" = "true" ]; then
            print_yellow "未配置API密钥，无法自动启动交易机器人"
        fi
    fi
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
    
    # 设置启动服务（PM2或systemd）
    setup_startup_service
    
    # 创建配置文件
    create_config_file
    
    # 创建一键配置命令
    create_config_command
    
    # 自动启动交易机器人（如果配置了API密钥）
    auto_start_bot
    
    # 显示安装完成消息
    print_green "========================================"
    print_green "        安装完成！                    "
    print_green "========================================"
    print_green "配置文件已创建: $HOME/.backpack_bot/config.ini"
    
    if [ "$AUTO_START" = "true" ] && [ -n "$API_KEY" ] && [ -n "$API_SECRET" ]; then
        print_green "交易机器人已自动启动！"
    else
        print_green "要手动配置交易机器人，运行:"
        print_green "   source $SHELL_RC && backpack-config"
        print_green ""
        print_green "配置完成后，启动机器人:"
        print_green "   backpack-start"
    fi
    print_green "========================================"
}

# 执行主函数
main 
