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

# 设置交互式环境变量
export FORCE_INTERACTIVE=true
export TERM=xterm

# 修改tty权限，以确保交互性（可能需要root权限）
if [ -t 0 ]; then
    print_green "检测到终端环境，继续..."
else
    print_yellow "无终端环境，尝试模拟终端..."
fi

# 切换到配置目录
cd "$CONFIG_DIR" || exit 1

# 强制使用Python执行菜单
PYTHONUNBUFFERED=1 script -qc "python3 $MENU_SCRIPT" /dev/null

# 如果script命令不可用或失败，尝试其他方法
if [ $? -ne 0 ]; then
    print_yellow "使用备用方法..."
    FORCE_INTERACTIVE=true PYTHONUNBUFFERED=1 python3 "$MENU_SCRIPT"
fi 