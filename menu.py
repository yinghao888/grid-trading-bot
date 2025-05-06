# 主菜单
def main_menu():
    # 检查是否首次运行
    config = load_config()
    first_run = (config["api"]["api_key"] == "YOUR_API_KEY")
    
    if first_run:
        try:
            print_yellow("检测到首次运行，是否启动快速配置向导? (y/n):")
            # 设置超时，避免在非交互环境中无限等待
            import signal
            
            def timeout_handler(signum, frame):
                raise TimeoutError("输入超时")
            
            # 设置5秒超时
            signal.signal(signal.SIGALRM, timeout_handler)
            signal.alarm(5)
            
            try:
                start_wizard = input().strip().lower()
                signal.alarm(0)  # 取消超时
                if start_wizard == 'y':
                    quick_setup_wizard()
            except (TimeoutError, EOFError):
                print_yellow("非交互式环境或输入超时，跳过快速配置向导")
                signal.alarm(0)  # 确保取消超时
        except Exception as e:
            print_red(f"启动向导时出错: {e}")
            print_yellow("请手动配置您的交易机器人")
    
    while True:
        try:
            os.system('clear' if os.name != 'nt' else 'cls')
            
            print_blue("======================================")
            print_blue("        Backpack 交易机器人菜单      ")
            print_blue("======================================")
            
            # 检查机器人状态
            try:
                result = subprocess.run(["pm2", "list"], capture_output=True, text=True)
                bot_running = "backpack_bot" in result.stdout and "online" in result.stdout
            except:
                bot_running = False
                print_red("无法检查PM2状态，可能未正确安装")
            
            status = "\033[32m运行中\033[0m" if bot_running else "\033[31m已停止\033[0m"
            print_blue(f"机器人状态: {status}")
            
            print_yellow("\n请选择操作:")
            print("1. 快速配置向导")
            print("2. 配置交易所 API")
            print("3. 配置 Telegram 通知")
            print("4. 选择交易对")
            print("5. 配置交易参数")
            print("6. 查看日志")
            if bot_running:
                print("7. 停止机器人")
            else:
                print("7. 启动机器人")
            print("8. 删除机器人")
            print("0. 退出")
            
            try:
                # 设置输入超时
                signal.signal(signal.SIGALRM, timeout_handler)
                signal.alarm(60)  # 60秒超时
                
                choice = input("\n请输入选项: ").strip()
                signal.alarm(0)  # 取消超时
            except (TimeoutError, EOFError):
                print_yellow("输入超时或非交互环境，退出菜单")
                break
            
            if choice == '1':
                quick_setup_wizard()
            elif choice == '2':
                configure_exchange_api()
            elif choice == '3':
                configure_telegram()
            elif choice == '4':
                select_trading_pairs()
            elif choice == '5':
                configure_trading_params()
            elif choice == '6':
                view_logs()
            elif choice == '7':
                stop_bot() if bot_running else start_bot()
            elif choice == '8':
                remove_bot()
            elif choice == '0':
                print_yellow("感谢使用，再见！")
                break
            else:
                print_red("无效选项，请重新选择")
                time.sleep(1)
        except KeyboardInterrupt:
            print_yellow("\n已检测到退出信号，正在退出...")
            break
        except Exception as e:
            print_red(f"发生错误: {e}")
            print_yellow("按Enter键继续...")
            try:
                input()
            except:
                pass
