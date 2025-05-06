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
print_blue "============ 环境测试脚本 ============"
echo "当前终端状态: $([ -t 0 ] && echo "交互式" || echo "非交互式")"
echo "当前Python版本: $(python3 --version)"

# 测试正常运行
print_yellow "测试1: 正常启动菜单 (5秒后自动退出)"
timeout 5 python3 menu.py || echo "正常中断"

# 测试非交互模式但强制交互
print_yellow "测试2: 强制交互模式"
FORCE_INTERACTIVE=true timeout 5 python3 menu.py || echo "正常中断"

# 测试命令行参数
print_yellow "测试3: 使用命令行参数"
python3 menu.py --api-key=TEST_KEY --api-secret=TEST_SECRET

# 测试通过管道输入（模拟非交互环境）
print_yellow "测试4: 通过管道运行（非交互模式）"
echo "0" | python3 menu.py

# 测试完全非交互环境
print_yellow "测试5: 完全非交互环境"
NON_INTERACTIVE=true python3 menu.py

# 测试带参数的非交互环境
print_yellow "测试6: 非交互环境 + 命令行参数"
NON_INTERACTIVE=true python3 menu.py --api-key=TEST_KEY --api-secret=TEST_SECRET

print_green "所有测试完成!" 