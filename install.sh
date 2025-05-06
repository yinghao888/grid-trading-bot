#!/bin/bash

YELLOW='\033[1;33m'
GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m' # No Color

# 错误处理函数
error_exit() {
    echo -e "${RED}错误: $1${NC}" >&2
    echo -e "${YELLOW}安装过程失败，请检查错误信息并重试。${NC}"
    exit 1
}

# 清屏并显示标题
clear
echo -e "${YELLOW}==============================================${NC}"
echo -e "${YELLOW}      Backpack ETH自动交易机器人安装程序       ${NC}"
echo -e "${YELLOW}==============================================${NC}"
echo ""

# 检测是否为root用户，但不阻止运行
IS_ROOT=0
if [ "$EUID" -eq 0 ]; then
    IS_ROOT=1
    echo -e "${YELLOW}⚠ 您正在使用root用户运行此脚本${NC}"
    echo -e "${YELLOW}⚠ 将自动进行所有系统级操作${NC}"
    echo ""
else
    echo -e "${YELLOW}⚠ 您正在使用普通用户运行此脚本${NC}"
    echo -e "${YELLOW}⚠ 系统级操作将使用sudo命令${NC}"
    echo ""
fi

# 定义sudo命令
SUDO_CMD=""
if [ $IS_ROOT -eq 0 ]; then
    SUDO_CMD="sudo"
fi

# 检查系统
echo -e "${BLUE}[1/5] 正在检查系统...${NC}"

if [ -f /etc/os-release ]; then
    . /etc/os-release
    OS=$NAME
    VER=$VERSION_ID
    echo -e "  ✓ 检测到系统: $OS $VER"
    
    # 验证系统版本
    if [[ "$OS" == *"Ubuntu"* ]]; then
        echo -e "  ✓ 系统兼容性: 良好"
    elif [[ "$OS" == *"Debian"* ]]; then
        echo -e "  ✓ 系统兼容性: 良好 (Debian 与 Ubuntu 命令兼容)"
    else
        echo -e "  ${YELLOW}⚠ 警告: 此脚本主要针对Ubuntu系统优化，您的系统是 $OS${NC}"
        echo -e "    但我们会尝试继续安装..."
    fi
else
    echo -e "  ${YELLOW}⚠ 警告: 无法检测系统类型，将尝试继续安装...${NC}"
    OS="Unknown"
fi

# 检查互联网连接
echo -e "  正在检查网络连接..."
if ! ping -c 1 google.com &> /dev/null && ! ping -c 1 baidu.com &> /dev/null; then
    error_exit "无法连接到互联网，请检查您的网络连接后重试。"
else
    echo -e "  ✓ 网络连接正常"
fi

# 创建必要的目录
echo ""
echo -e "${BLUE}[2/5] 正在准备安装环境...${NC}"

# 创建临时目录
TEMP_DIR=$(mktemp -d)
echo -e "  ✓ 创建临时目录: $TEMP_DIR"

# 确保脚本退出时清理临时文件
trap 'rm -rf "$TEMP_DIR"' EXIT

# 下载最新的机器人代码
echo -e "  正在下载最新版本的机器人代码..."
curl -s -L -o "$TEMP_DIR/backpack_bot.py" https://raw.githubusercontent.com/yinghao888/grid-trading-bot/main/backpack_bot.py || error_exit "下载机器人代码失败"
echo -e "  ✓ 机器人代码下载完成"

# 创建配置目录
CONFIG_DIR="$HOME/.backpack_bot"
CONFIG_FILE="$CONFIG_DIR/config.json"

# 如果配置目录不存在，创建它
if [ ! -d "$CONFIG_DIR" ]; then
    mkdir -p "$CONFIG_DIR"
    echo -e "  ✓ 已创建配置目录: $CONFIG_DIR"
fi

echo ""
echo -e "${BLUE}[3/5] 正在安装依赖...${NC}"

# 更新软件包列表
echo -e "  正在更新软件包列表..."
$SUDO_CMD apt-get update -qq || error_exit "更新软件包列表失败"

# 安装必要的系统包
echo -e "  正在安装必要的系统包..."
$SUDO_CMD apt-get install -y python3 python3-pip nodejs npm curl jq -qq || error_exit "安装系统依赖失败"

# 检查Python版本
PYTHON_VER=$(python3 --version 2>/dev/null)
if [ $? -eq 0 ]; then
    echo -e "  ✓ 已安装Python: $PYTHON_VER"
else
    error_exit "Python安装失败"
fi

# 安装PM2
echo -e "  正在安装PM2..."
$SUDO_CMD npm install pm2 -g -s || error_exit "安装PM2失败"
PM2_VER=$(pm2 --version 2>/dev/null)
echo -e "  ✓ 已安装PM2: $PM2_VER"

# 安装必要的Python包
echo -e "  正在安装Python依赖..."
pip3 install --no-cache-dir --quiet aiohttp requests || error_exit "安装Python依赖失败"
echo -e "  ✓ Python依赖安装成功"

# 配置选项
echo ""
echo -e "${BLUE}[4/5] 正在设置文件...${NC}"

# 复制主程序文件到配置目录
cp "$TEMP_DIR/backpack_bot.py" "$CONFIG_DIR/"
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

# 创建启动脚本
echo -e "  正在创建启动和配置脚本..."

# 创建目录
mkdir -p "$HOME/.local/bin"

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

# 检查配置文件
if [ ! -f "$CONFIG_DIR/config.json" ]; then
    echo "错误: 配置文件不存在!"
    exit 1
fi

# 验证配置文件格式
if ! jq . "$CONFIG_DIR/config.json" > /dev/null 2>&1; then
    echo "错误: 配置文件格式不正确，请检查JSON格式!"
    exit 1
fi

# 检查API密钥是否配置
API_KEY=$(jq -r '.backpack.api_key' "$CONFIG_DIR/config.json")
API_SECRET=$(jq -r '.backpack.api_secret' "$CONFIG_DIR/config.json")
TELEGRAM_CHAT_ID=$(jq -r '.telegram.chat_id' "$CONFIG_DIR/config.json")

if [ -z "$API_KEY" ] || [ "$API_KEY" == "null" ]; then
    echo "错误: Backpack API Key 未配置，请先运行 'backpack-config' 进行配置!"
    exit 1
fi

if [ -z "$API_SECRET" ] || [ "$API_SECRET" == "null" ]; then
    echo "错误: Backpack API Secret 未配置，请先运行 'backpack-config' 进行配置!"
    exit 1
fi

if [ -z "$TELEGRAM_CHAT_ID" ] || [ "$TELEGRAM_CHAT_ID" == "null" ]; then
    echo "错误: Telegram Chat ID 未配置，请先运行 'backpack-config' 进行配置!"
    exit 1
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

# 颜色定义
YELLOW='\033[1;33m'
GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

function show_help {
    echo -e "${YELLOW}============================================${NC}"
    echo -e "${YELLOW}      Backpack 交易机器人配置工具         ${NC}"
    echo -e "${YELLOW}============================================${NC}"
    echo ""
    echo -e "${BLUE}用法:${NC}"
    echo -e "  ${GREEN}backpack-config${NC}             启动配置菜单"
    echo -e "  ${GREEN}backpack-config config${NC}      编辑配置文件"
    echo -e "  ${GREEN}backpack-config start${NC}       启动交易机器人"
    echo -e "  ${GREEN}backpack-config stop${NC}        停止交易机器人"
    echo -e "  ${GREEN}backpack-config restart${NC}     重启交易机器人"
    echo -e "  ${GREEN}backpack-config status${NC}      查看交易机器人状态"
    echo -e "  ${GREEN}backpack-config logs${NC}        查看交易机器人日志"
    echo -e "  ${GREEN}backpack-config help${NC}        显示此帮助信息"
}

function edit_config {
    if [ -f "$CONFIG_FILE" ]; then
        # 检查是否有可用的编辑器
        if command -v nano &> /dev/null; then
            nano "$CONFIG_FILE"
        elif command -v vim &> /dev/null; then
            vim "$CONFIG_FILE"
        else
            echo -e "${RED}无法找到文本编辑器(nano或vim)，请使用其他方式编辑配置文件:${NC} $CONFIG_FILE"
        fi
        
        # 验证配置文件格式
        if ! jq . "$CONFIG_FILE" > /dev/null 2>&1; then
            echo -e "${RED}警告: 配置文件格式不正确，请检查JSON格式!${NC}"
        else
            echo -e "${GREEN}✓ 配置文件格式正确${NC}"
        fi
    else
        echo -e "${RED}错误: 配置文件不存在:${NC} $CONFIG_FILE"
    fi
}

function start_bot {
    # 检查配置文件
    if [ ! -f "$CONFIG_FILE" ]; then
        echo -e "${RED}错误: 配置文件不存在!${NC}"
        return 1
    fi
    
    # 检查配置文件是否有效
    if ! jq . "$CONFIG_FILE" > /dev/null 2>&1; then
        echo -e "${RED}错误: 配置文件格式不正确，请检查JSON格式!${NC}"
        return 1
    fi
    
    # 检查必要的配置项是否存在
    API_KEY=$(jq -r '.backpack.api_key' "$CONFIG_FILE")
    API_SECRET=$(jq -r '.backpack.api_secret' "$CONFIG_FILE")
    TELEGRAM_CHAT_ID=$(jq -r '.telegram.chat_id' "$CONFIG_FILE")
    
    if [ -z "$API_KEY" ] || [ "$API_KEY" == "null" ]; then
        echo -e "${RED}错误: Backpack API Key 未配置，请先配置!${NC}"
        return 1
    fi
    
    if [ -z "$API_SECRET" ] || [ "$API_SECRET" == "null" ]; then
        echo -e "${RED}错误: Backpack API Secret 未配置，请先配置!${NC}"
        return 1
    fi
    
    if [ -z "$TELEGRAM_CHAT_ID" ] || [ "$TELEGRAM_CHAT_ID" == "null" ]; then
        echo -e "${RED}错误: Telegram Chat ID 未配置，请先配置!${NC}"
        return 1
    fi
    
    # 启动机器人
    cd "$CONFIG_DIR"
    pm2 start backpack_bot.py --name backpack_bot --interpreter python3 -- --run
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓ 交易机器人已启动!${NC}"
        echo -e "使用 '${CYAN}pm2 logs backpack_bot${NC}' 查看日志"
    else
        echo -e "${RED}错误: 启动交易机器人失败!${NC}"
        return 1
    fi
}

function stop_bot {
    pm2 stop backpack_bot
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓ 交易机器人已停止${NC}"
    else
        echo -e "${RED}错误: 停止交易机器人失败!${NC}"
    fi
}

function restart_bot {
    pm2 restart backpack_bot
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓ 交易机器人已重启${NC}"
    else
        echo -e "${RED}错误: 重启交易机器人失败!${NC}"
    fi
}

function status_bot {
    echo -e "${BLUE}交易机器人状态:${NC}"
    pm2 list | grep backpack_bot
    
    if [ $? -ne 0 ]; then
        echo -e "${YELLOW}⚠ 交易机器人未运行${NC}"
    fi
}

function logs_bot {
    pm2 logs backpack_bot
}

function show_menu {
    # 检查配置文件
    if [ ! -f "$CONFIG_FILE" ]; then
        echo -e "${YELLOW}警告: 配置文件不存在，将使用默认配置!${NC}"
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

# 将路径添加到PATH
if [[ ":$PATH:" != *":$HOME/.local/bin:"* ]]; then
    echo 'export PATH="$HOME/.local/bin:$PATH"' >> "$HOME/.bashrc"
    echo 'export PATH="$HOME/.local/bin:$PATH"' >> "$HOME/.profile"
    
    # 检查是否使用zsh
    if [ -f "$HOME/.zshrc" ]; then
        echo 'export PATH="$HOME/.local/bin:$PATH"' >> "$HOME/.zshrc"
    fi
    
    export PATH="$HOME/.local/bin:$PATH"
    echo -e "  ✓ 已将命令添加到PATH"
fi

echo ""
echo -e "${BLUE}[5/5] 安装完成，正在启动配置菜单...${NC}"
echo -e "${GREEN}✓ 所有组件安装完成!${NC}"
echo -e "${GREEN}✓ 交易机器人已准备就绪!${NC}"
echo ""
echo -e "${CYAN}可用命令:${NC}"
echo -e "  ${CYAN}backpack-config${NC} - 配置交易机器人"
echo -e "  ${CYAN}backpack-start${NC}  - 启动交易机器人"
echo ""
echo -e "${YELLOW}现在将自动打开配置菜单，请按照提示设置您的API密钥和Telegram ID${NC}"
echo ""
sleep 2

clear
echo -e "${YELLOW}==============================================${NC}"
echo -e "${YELLOW}            交易机器人配置向导             ${NC}"
echo -e "${YELLOW}==============================================${NC}"
echo ""
echo -e "${BLUE}请在下面的菜单中完成以下配置:${NC}"
echo -e "1. 配置Telegram Chat ID (可以通过Telegram中的@userinfobot获取)"
echo -e "2. 配置Backpack交易所API密钥"
echo -e "3. 然后您可以直接从菜单中启动机器人"
echo ""
echo -e "${YELLOW}====== 菜单将在3秒后自动启动 ======${NC}"
sleep 3

# 直接运行配置菜单
cd "$CONFIG_DIR"
python3 backpack_bot.py 
