# Backpack ETH交易机器人一键安装指南

这个脚本提供了一键安装和配置Backpack交易机器人的功能，自动处理所有依赖安装并直接进入配置界面，无需额外命令，支持ETH永续合约的自动化交易策略。

## 一键安装方法

只需在终端中运行以下命令：

```bash
curl -s https://raw.githubusercontent.com/yinghao888/grid-trading-bot/main/install.sh | bash
```

或者，如果您已经克隆了仓库：

```bash
cd backpack_api_guide
chmod +x install.sh
./install.sh
```

安装脚本会自动完成所有设置，并在安装结束后**自动进入配置菜单**，无需额外操作。

## 安装过程中需要准备

在开始安装之前，请确保您已准备好：

1. Telegram Chat ID - 可以通过在Telegram中搜索`@userinfobot`并发送消息获取
2. Backpack交易所API密钥 - 请在Backpack交易所创建API密钥和密钥
3. 系统管理员权限 - 安装过程需要使用`sudo`安装依赖包

## 安装内容

脚本会自动安装以下内容：

- Python 3和必要的Python包(aiohttp, requests)
- Node.js和PM2(用于管理机器人进程)
- jq工具(用于处理JSON配置)
- 交易机器人主程序和配置工具
- 自定义命令：backpack-config和backpack-start

## 全自动安装流程

1. 运行安装脚本
2. 自动检测并安装所需依赖
3. 自动设置配置文件和目录结构
4. 安装完成后自动进入交互式配置菜单
5. 在菜单中配置您的Telegram和Backpack API信息
6. 直接从菜单中启动交易机器人

## 机器人功能

- 自动使用账户USDC余额的20倍杠杆开ETH多单
- 盈利2%自动平仓获利
- 亏损10%自动止损并进入冷静期
- Telegram实时通知交易状态

## 安装后的额外命令

安装完成后，您可以使用以下命令：

1. `backpack-config` - 随时重新打开配置菜单
2. `backpack-start` - 直接启动交易机器人

查看日志：
```bash
pm2 logs backpack_bot
```

停止机器人：
```bash
backpack-config stop
```

## 命令详解

- `backpack-config` - 打开配置菜单
- `backpack-config config` - 直接编辑配置文件
- `backpack-config start` - 启动交易机器人
- `backpack-config stop` - 停止交易机器人
- `backpack-config restart` - 重启交易机器人
- `backpack-config status` - 查看交易机器人状态
- `backpack-config logs` - 查看交易机器人日志

## 卸载方法

如需卸载，请运行以下命令：

```bash
pm2 delete backpack_bot
rm -rf ~/.backpack_bot
rm ~/.local/bin/backpack-config
rm ~/.local/bin/backpack-start
```

## 注意事项

- 请确保Backpack API密钥具有交易权限
- 初次运行前建议使用小额资金测试
- 交易涉及风险，请根据自己的风险承受能力调整交易参数
- 如有问题，请查看 `~/.backpack_bot/backpack_bot.log` 日志文件 