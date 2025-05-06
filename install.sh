#!/bin/bash

YELLOW='\033[1;33m'
GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${YELLOW}==============================================${NC}"
echo -e "${YELLOW}      Backpack ETH自动交易机器人安装程序       ${NC}"
echo -e "${YELLOW}==============================================${NC}"
echo ""

# 检查系统
echo -e "${BLUE}[1/6] 正在检查系统...${NC}"

if [ -f /etc/os-release ]; then
    . /etc/os-release
    OS=$NAME
    VER=$VERSION_ID
    echo -e "  ✓ 检测到系统: $OS $VER"
    
    # 验证系统版本
    if [[ "$OS" == *"Ubuntu"* ]]; then
        echo -e "  ✓ 系统兼容性: 良好"
    else
        echo -e "  ${RED}⚠ 警告: 此脚本主要针对Ubuntu系统优化，您的系统是 $OS${NC}"
        echo -e "    但我们会尝试继续安装..."
    fi
else
    echo -e "  ${RED}⚠ 警告: 无法检测系统类型，将尝试继续安装...${NC}"
    OS="Unknown"
fi

# 创建必要的目录
echo ""
echo -e "${BLUE}[2/6] 正在准备环境...${NC}"

# 检查和升级Python
PYTHON_VER=$(python3 --version 2>/dev/null)
if [ $? -ne 0 ]; then
    echo -e "  ${RED}✗ 未检测到Python 3，正在安装...${NC}"
    sudo apt-get update
    sudo apt-get install -y python3 python3-pip
else
    echo -e "  ✓ 已安装Python: $PYTHON_VER"
fi

# 检查Node.js和PM2
NODE_VER=$(node --version 2>/dev/null)
if [ $? -ne 0 ]; then
    echo -e "  ${RED}✗ 未检测到Node.js，正在安装...${NC}"
    sudo apt-get update
    sudo apt-get install -y nodejs npm
else
    echo -e "  ✓ 已安装Node.js: $NODE_VER"
fi

PM2_VER=$(pm2 --version 2>/dev/null)
if [ $? -ne 0 ]; then
    echo -e "  ${RED}✗ 未检测到PM2，正在安装...${NC}"
    sudo npm install pm2 -g
else
    echo -e "  ✓ 已安装PM2: $PM2_VER"
fi

# 安装必要的Python包
echo ""
echo -e "${BLUE}[3/6] 正在安装依赖包...${NC}"
echo -e "  正在安装Python依赖..."
pip3 install aiohttp requests

if [ $? -ne 0 ]; then
    echo -e "  ${RED}✗ 安装Python依赖失败，请检查错误信息${NC}"
    exit 1
else
    echo -e "  ✓ Python依赖安装成功"
fi

# 配置选项
echo ""
echo -e "${BLUE}[4/6] 正在配置交易机器人...${NC}"

CONFIG_DIR="$HOME/.backpack_bot"
CONFIG_FILE="$CONFIG_DIR/config.json"

# 如果配置目录不存在，创建它
if [ ! -d "$CONFIG_DIR" ]; then
    mkdir -p "$CONFIG_DIR"
    echo -e "  ✓ 已创建配置目录: $CONFIG_DIR"
fi

# 复制主程序文件到配置目录
cp backpack_bot.py "$CONFIG_DIR/"
chmod +x "$CONFIG_DIR/backpack_bot.py"
echo -e "  ✓ 已复制主程序文件到配置目录"

# 创建默认配置文件
if [ ! -f "$CONFIG_FILE" ]; then
    cat > "$CONFIG_FILE" << 'EOF'
{
    "telegram": {
        "token": "7685502184:AAGxaIdwiTr0WpPDeIGmc9fgbdeSKxgXtEw",
        "chat_id": ""
    },
    "backpack": {
        "api_key": "",
        "api_secret": "",
        "base_url": "https://api.backpack.exchange",
        "ws_url": "wss://ws.backpack.exchange"
    },
    "trading": {
        "leverage": 20,
        "profit_percentage": 2,
        "stop_loss_percentage": 10,
        "cooldown_minutes": 30,
        "symbol": "ETH_USDC_PERP"
    }
}
EOF
    echo -e "  ✓ 已创建默认配置文件: $CONFIG_FILE"
fi

# 交互式配置
echo ""
echo -e "${YELLOW}===== 交易机器人配置 =====${NC}"

# Telegram配置
echo -e "${BLUE}Telegram配置${NC}"
echo -e "请输入您的Telegram Chat ID（使用@userinfobot获取）:"
read -p "> " TELEGRAM_CHAT_ID

# Backpack API配置
echo -e "${BLUE}Backpack API配置${NC}"
echo -e "请输入您的Backpack API Key:"
read -p "> " API_KEY
echo -e "请输入您的Backpack API Secret:"
read -p "> " API_SECRET

# 更新配置文件
TEMP_CONFIG=$(mktemp)
cat "$CONFIG_FILE" | jq --arg chat_id "$TELEGRAM_CHAT_ID" '.telegram.chat_id = $chat_id' > "$TEMP_CONFIG"
cat "$TEMP_CONFIG" | jq --arg api_key "$API_KEY" '.backpack.api_key = $api_key' > "$CONFIG_FILE"
cat "$CONFIG_FILE" | jq --arg api_secret "$API_SECRET" '.backpack.api_secret = $api_secret' > "$TEMP_CONFIG"
cp "$TEMP_CONFIG" "$CONFIG_FILE"
rm "$TEMP_CONFIG"

echo -e "  ✓ 配置已保存到: $CONFIG_FILE"

# 创建启动脚本
echo ""
echo -e "${BLUE}[5/6] 正在创建启动脚本...${NC}"

# 创建启动脚本
cat > "$HOME/.local/bin/backpack-start" << 'EOF'
#!/bin/bash

# 确保配置目录存在
CONFIG_DIR="$HOME/.backpack_bot"
if [ ! -d "$CONFIG_DIR" ]; then
    echo "错误: 配置目录不存在!"
    exit 1
fi

# 检查PM2是否运行backpack_bot
PM2_STATUS=$(pm2 list | grep backpack_bot)
if [[ "$PM2_STATUS" == *"online"* ]]; then
    echo "交易机器人已经在运行中!"
    echo "使用 'pm2 logs backpack_bot' 查看日志"
    exit 0
fi

# 启动机器人
cd "$CONFIG_DIR"
pm2 start backpack_bot.py --name backpack_bot --interpreter python3 -- --run
echo "交易机器人已启动!"
echo "使用 'pm2 logs backpack_bot' 查看日志"
EOF

chmod +x "$HOME/.local/bin/backpack-start"

# 创建配置工具脚本
cat > "$HOME/.local/bin/backpack-config" << 'EOF'
#!/bin/bash

CONFIG_DIR="$HOME/.backpack_bot"
CONFIG_FILE="$CONFIG_DIR/config.json"

function show_help {
    echo "Backpack 交易机器人配置工具"
    echo ""
    echo "用法:"
    echo "  backpack-config             启动配置菜单"
    echo "  backpack-config config      编辑配置文件"
    echo "  backpack-config start       启动交易机器人"
    echo "  backpack-config stop        停止交易机器人"
    echo "  backpack-config restart     重启交易机器人"
    echo "  backpack-config status      查看交易机器人状态"
    echo "  backpack-config logs        查看交易机器人日志"
    echo "  backpack-config help        显示此帮助信息"
}

function edit_config {
    if [ -f "$CONFIG_FILE" ]; then
        # 检查是否有可用的编辑器
        if command -v nano &> /dev/null; then
            nano "$CONFIG_FILE"
        elif command -v vim &> /dev/null; then
            vim "$CONFIG_FILE"
        else
            echo "无法找到文本编辑器(nano或vim)，请使用其他方式编辑配置文件: $CONFIG_FILE"
        fi
    else
        echo "错误: 配置文件不存在: $CONFIG_FILE"
    fi
}

function start_bot {
    # 检查配置文件
    if [ ! -f "$CONFIG_FILE" ]; then
        echo "错误: 配置文件不存在!"
        return 1
    fi
    
    # 检查配置文件是否有效
    API_KEY=$(cat "$CONFIG_FILE" | grep -o '"api_key": *"[^"]*"' | cut -d'"' -f4)
    if [ -z "$API_KEY" ]; then
        echo "错误: API密钥未配置，请先配置!"
        return 1
    fi
    
    # 启动机器人
    cd "$CONFIG_DIR"
    pm2 start backpack_bot.py --name backpack_bot --interpreter python3 -- --run
    echo "交易机器人已启动!"
    echo "使用 'pm2 logs backpack_bot' 查看日志"
}

function stop_bot {
    pm2 stop backpack_bot
    echo "交易机器人已停止"
}

function restart_bot {
    pm2 restart backpack_bot
    echo "交易机器人已重启"
}

function status_bot {
    pm2 list | grep backpack_bot
}

function logs_bot {
    pm2 logs backpack_bot
}

function show_menu {
    # 检查配置文件
    if [ ! -f "$CONFIG_FILE" ]; then
        echo "警告: 配置文件不存在，将使用默认配置!"
    fi
    
    # 运行配置菜单
    cd "$CONFIG_DIR"
    python3 backpack_bot.py
}

# 主程序逻辑
case "$1" in
    config)
        edit_config
        ;;
    start)
        start_bot
        ;;
    stop)
        stop_bot
        ;;
    restart)
        restart_bot
        ;;
    status)
        status_bot
        ;;
    logs)
        logs_bot
        ;;
    help)
        show_help
        ;;
    *)
        show_menu
        ;;
esac
EOF

chmod +x "$HOME/.local/bin/backpack-config"

# 确保路径存在
if [ ! -d "$HOME/.local/bin" ]; then
    mkdir -p "$HOME/.local/bin"
fi

# 将路径添加到PATH
if [[ ":$PATH:" != *":$HOME/.local/bin:"* ]]; then
    echo 'export PATH="$HOME/.local/bin:$PATH"' >> "$HOME/.bashrc"
    echo 'export PATH="$HOME/.local/bin:$PATH"' >> "$HOME/.profile"
    export PATH="$HOME/.local/bin:$PATH"
    echo -e "  ✓ 已将命令添加到PATH"
fi

# 打印安装完成信息
echo ""
echo -e "${BLUE}[6/6] 安装完成!${NC}"
echo -e "${GREEN}Backpack ETH自动交易机器人已成功安装!${NC}"
echo ""
echo -e "${YELLOW}可用命令:${NC}"
echo -e "  ${GREEN}backpack-config${NC} - 打开配置菜单"
echo -e "  ${GREEN}backpack-start${NC}  - 启动交易机器人"
echo ""
echo -e "${YELLOW}交易机器人配置文件:${NC}"
echo -e "  ${GREEN}$CONFIG_FILE${NC}"
echo ""
echo -e "${YELLOW}日志文件:${NC}"
echo -e "  查看日志: ${GREEN}pm2 logs backpack_bot${NC}"
echo ""

# 询问是否立即启动机器人
echo -e "${YELLOW}是否立即启动交易机器人? (y/n)${NC}"
read -p "> " START_CHOICE

if [[ $START_CHOICE =~ ^[Yy]$ ]]; then
    echo -e "${BLUE}正在启动交易机器人...${NC}"
    cd "$CONFIG_DIR"
    pm2 start backpack_bot.py --name backpack_bot --interpreter python3 -- --run
    echo -e "${GREEN}交易机器人已启动!${NC}"
    echo -e "使用 '${GREEN}pm2 logs backpack_bot${NC}' 查看日志"
else
    echo -e "${BLUE}您可以稍后使用 '${GREEN}backpack-start${NC}' 命令启动交易机器人${NC}"
fi

echo ""
echo -e "${YELLOW}感谢使用Backpack ETH自动交易机器人!${NC}"
echo -e "${YELLOW}==============================================${NC}" 