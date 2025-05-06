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

# 测试环境变量
print_blue "============ 环境测试脚本 (MacOS) ============"
echo "当前终端状态: $([ -t 0 ] && echo "交互式" || echo "非交互式")"
echo "当前Python版本: $(python3 --version)"

# 测试使用命令行参数（非交互模式）
print_yellow "测试: 使用命令行参数配置 API 和 Telegram"
python3 menu.py --api-key=TEST_KEY --api-secret=TEST_SECRET --telegram-id=123456

# 测试启动机器人
print_yellow "测试: 启动机器人指令"
python3 menu.py --start-bot

# 测试停止机器人
print_yellow "测试: 停止机器人指令"
python3 menu.py --stop-bot

# 测试通过管道输入
print_yellow "测试: 通过管道运行（非交互模式）"
echo "0" | python3 menu.py

print_green "测试完成，请检查上述测试结果！"
print_green "现在可以用常规方式启动菜单：python3 menu.py" 