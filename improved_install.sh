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
    
    # 创建一键配置命令
    create_config_command
    
    # 运行菜单
    print_green "========================================"
    print_green "      安装完成！                      "
    print_green "========================================"
    print_green "您可以随时使用 'backpack-config' 命令进入配置菜单"
    print_green "交易机器人将通过 PM2 管理，确保其稳定运行"
    print_green "========================================"
    
    # 提示用户手动运行菜单，避免在非交互环境中出现EOF错误
    print_yellow "请运行以下命令开始配置："
    print_yellow "source ~/.bashrc && backpack-config"
    
    # 不再自动启动菜单，避免非交互式环境下的问题
    # cd $HOME/.backpack_bot
    # ./start.sh
}

# 执行主函数
main
