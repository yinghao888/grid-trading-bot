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

# 打印标题
print_blue "================================================="
print_blue "    Backpack 交易机器人 - 安装并强制交互式配置    "
print_blue "================================================="

# 设置强制交互式环境变量
export FORCE_INTERACTIVE=true
export AUTO_CONFIG=true
export TERM=xterm
export PYTHONUNBUFFERED=1

# 下载并执行安装脚本
print_yellow "正在下载安装脚本..."
curl -s -o improved_install.sh https://raw.githubusercontent.com/yinghao888/grid-trading-bot/main/improved_install.sh

if [ ! -f "improved_install.sh" ]; then
    print_red "下载安装脚本失败"
    exit 1
fi

# 修改安装脚本以确保交互式
print_yellow "修改安装脚本以确保交互式..."
sed -i 's/AUTO_CONFIG=${AUTO_CONFIG:-"true"}/AUTO_CONFIG="true"\n# 强制交互式模式\nFORCE_INTERACTIVE="true"/g' improved_install.sh 2>/dev/null || \
sed -i '' 's/AUTO_CONFIG=${AUTO_CONFIG:-"true"}/AUTO_CONFIG="true"\n# 强制交互式模式\nFORCE_INTERACTIVE="true"/g' improved_install.sh

# 赋予执行权限
chmod +x improved_install.sh

# 执行安装脚本
print_yellow "执行安装脚本..."
bash improved_install.sh

# 检查菜单是否已运行，如果没有则手动启动
if [ $? -ne 0 ]; then
    print_yellow "安装脚本执行完成，尝试手动启动菜单..."
    
    # 确保配置目录存在
    CONFIG_DIR="$HOME/.backpack_bot"
    MENU_SCRIPT="$CONFIG_DIR/menu.py"
    
    if [ -f "$MENU_SCRIPT" ]; then
        print_green "找到菜单脚本，启动交互式菜单..."
        cd "$CONFIG_DIR" && FORCE_INTERACTIVE=true python3 menu.py
    else
        print_red "未找到菜单脚本，安装可能未成功完成"
        print_yellow "请尝试手动运行："
        print_yellow "FORCE_INTERACTIVE=true backpack-config"
    fi
fi 