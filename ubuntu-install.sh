#!/bin/bash

# Backpack交易机器人 - Ubuntu 22.04 专用安装脚本
# 此脚本会强制启用交互式菜单，解决非交互式环境问题

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
print_blue "    Backpack 交易机器人 - Ubuntu 22.04 安装脚本   "
print_blue "================================================="

# 检查Ubuntu版本
if [ -f /etc/lsb-release ]; then
    source /etc/lsb-release
    if [ "$DISTRIB_ID" != "Ubuntu" ]; then
        print_yellow "警告: 此脚本为Ubuntu 22.04设计，当前系统为: $DISTRIB_ID"
        read -p "是否继续? (y/n): " continue_install
        if [ "$continue_install" != "y" ]; then
            exit 1
        fi
    elif [ "$DISTRIB_RELEASE" != "22.04" ]; then
        print_yellow "警告: 此脚本为Ubuntu 22.04设计，当前版本为: $DISTRIB_RELEASE"
        read -p "是否继续? (y/n): " continue_install
        if [ "$continue_install" != "y" ]; then
            exit 1
        fi
    else
        print_green "检测到Ubuntu 22.04，继续安装..."
    fi
fi

# 安装必要的软件包
print_yellow "安装必要的软件包..."
apt-get update
apt-get install -y python3 python3-pip curl expect

# 设置强制交互式环境变量
export FORCE_INTERACTIVE=true
export TERM=xterm-256color
export PYTHONUNBUFFERED=1
export PYTHONIOENCODING=utf-8

# 使用systemd启动服务
export USE_SYSTEMD=true

# 下载最新的安装脚本
print_yellow "下载安装脚本..."
curl -s -o improved_install.sh https://raw.githubusercontent.com/yinghao888/grid-trading-bot/main/improved_install.sh

if [ ! -f "improved_install.sh" ]; then
    print_red "下载安装脚本失败"
    exit 1
fi

# 修改安装脚本确保强制交互式
print_yellow "修改安装脚本为强制交互式..."
sed -i 's/AUTO_CONFIG=${AUTO_CONFIG:-"true"}/AUTO_CONFIG="true"\n# 强制交互式模式\nFORCE_INTERACTIVE="true"/g' improved_install.sh

# 下载强制菜单脚本
print_yellow "下载强制菜单脚本..."
curl -s -o force-menu-ubuntu.sh https://raw.githubusercontent.com/yinghao888/grid-trading-bot/main/force-menu-ubuntu.sh
chmod +x force-menu-ubuntu.sh

# 执行安装脚本
print_yellow "执行安装脚本..."
bash improved_install.sh

# 创建一个启动菜单的别名
echo 'alias backpack-menu="bash $HOME/.backpack_bot/force-menu-ubuntu.sh"' >> ~/.bashrc
source ~/.bashrc

print_green "安装完成！"
print_green "使用 'backpack-config' 启动配置菜单"
print_green "如果菜单出现问题，请使用 'backpack-menu' 强制启动交互式菜单" 