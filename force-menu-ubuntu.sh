#!/bin/bash

# 颜色输出函数
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

CONFIG_DIR="$HOME/.backpack_bot"
MENU_SCRIPT="$CONFIG_DIR/menu.py"

# 检查脚本是否存在
if [ ! -f "$MENU_SCRIPT" ]; then
    print_red "菜单脚本不存在: $MENU_SCRIPT"
    print_yellow "请先执行安装脚本"
    exit 1
fi

print_blue "强制启动交互式菜单..."

# 设置必要的环境变量
export FORCE_INTERACTIVE=true
export TERM=xterm-256color
export PYTHONUNBUFFERED=1
export PYTHONIOENCODING=utf-8

# 确保配置目录存在
if [ ! -d "$CONFIG_DIR" ]; then
    mkdir -p "$CONFIG_DIR"
fi

# 先修改menu.py文件，确保检测函数返回交互式状态
if [ -f "$MENU_SCRIPT" ]; then
    print_yellow "修改menu.py文件强制交互式模式..."
    # 使用sed修改check_environment函数
    sed -i 's/def check_environment():/def check_environment():\n    """检测当前环境是否适合运行交互式菜单"""\n    # 直接返回交互式环境设置，忽略其他检测\n    return {\n        "is_terminal": True,\n        "has_args": len(sys.argv) > 1,\n        "non_interactive": False,\n        "force_interactive": True,\n        "is_interactive": True  # 强制为交互式\n    }\n    /' "$MENU_SCRIPT"
    
    # 检查修改是否成功
    if grep -q "is_interactive: True" "$MENU_SCRIPT"; then
        print_green "成功修改menu.py为强制交互式模式"
    else
        print_red "修改menu.py失败，继续尝试其他方法..."
    fi
fi

# 切换到配置目录
cd "$CONFIG_DIR" || exit 1

# 方法1: 使用script命令模拟终端
print_yellow "尝试使用script命令模拟终端..."
script -qec "python3 $MENU_SCRIPT" /dev/null

# 如果上面的方法失败，尝试其他方法
if [ $? -ne 0 ]; then
    print_yellow "script命令失败，尝试使用expect..."
    
    # 检查是否安装expect
    if ! command -v expect &> /dev/null; then
        print_yellow "安装expect..."
        apt-get update && apt-get install -y expect
    fi
    
    # 使用expect自动处理交互
    expect -c "
    set timeout -1
    spawn python3 $MENU_SCRIPT
    expect {
        \"退出\" { send \"0\r\"; exp_continue }
        eof { exit }
    }
    "
fi

# 如果上面两种方法都失败，直接使用环境变量
if [ $? -ne 0 ]; then
    print_yellow "使用直接方法运行菜单..."
    FORCE_INTERACTIVE=true python3 "$MENU_SCRIPT"
fi

print_green "菜单执行完成！" 