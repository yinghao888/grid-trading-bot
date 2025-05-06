# Backpack 网格交易机器人

这是一个自动化的网格交易机器人系统，专为Backpack交易所设计。该系统支持全自动配置和启动，可以监控资金费率，并在适当时机进行交易。

## 主要特点

- **全自动安装与配置**：一键完成所有安装与配置步骤
- **多种启动方式**：支持PM2和systemd两种启动管理方式
- **环境变量支持**：可以通过环境变量预设配置，实现完全无交互式部署
- **多币种支持**：支持多种永续合约的交易
- **资金费率策略**：基于资金费率的交易策略，自动选择最佳交易时机
- **自动止盈止损**：内置止盈止损机制，保护资金安全
- **Telegram通知**：实时接收交易和系统状态通知

## 快速开始

### 方法1：一键安装（交互式）

```bash
curl -s https://raw.githubusercontent.com/yinghao888/grid-trading-bot/main/improved_install.sh | bash
```

安装完成后，使用以下命令进入配置菜单：

```bash
backpack-config
```

### 方法2：预设配置（非交互式）

可以通过环境变量预设所有配置，实现完全无交互式安装：

```bash
export API_KEY="your_api_key"
export API_SECRET="your_api_secret"
export SYMBOLS="ETH_USDC_PERP,SOL_USDC_PERP"
export POSITION_LIMIT="0.001"
export FUNDING_THRESHOLD="0.0001"
export TELEGRAM_CHAT_ID="your_telegram_id"
export AUTO_START="true"
export USE_SYSTEMD="false"  # 是否使用systemd而非PM2

curl -s https://raw.githubusercontent.com/yinghao888/grid-trading-bot/main/improved_install.sh | bash
```

## 使用systemd代替PM2

如果您希望使用systemd代替PM2来管理交易机器人服务（这会避免安装Node.js和PM2），可以设置：

```bash
export USE_SYSTEMD="true"
```

## 命令说明

安装完成后，系统提供以下命令：

### 1. backpack-config

交易机器人的主要配置工具，支持以下参数：

- `backpack-config` - 启动交互式配置菜单
- `backpack-config config` - 直接编辑配置文件
- `backpack-config start` - 启动交易机器人
- `backpack-config stop` - 停止交易机器人
- `backpack-config status` - 查看交易机器人状态
- `backpack-config logs` - 查看交易机器人日志

### 2. backpack-start

直接启动交易机器人，无需进入配置菜单

## 配置文件说明

配置文件位于 `~/.backpack_bot/config.ini`，包含以下主要设置：

### API 设置
```
[api]
api_key = YOUR_API_KEY
api_secret = YOUR_API_SECRET
base_url = https://api.backpack.exchange
ws_url = wss://ws.backpack.exchange
```

### 交易设置
```
[trading]
symbols = ETH_USDC_PERP        # 交易对，多个用逗号分隔
position_limit = 0.001         # 每次交易的仓位大小
funding_threshold = 0.0001     # 资金费率阈值
check_interval = 300           # 检查间隔(秒)
leverage = 20                  # 杠杆倍数
profit_target = 0.0002         # 利润目标
stop_loss = 0.1                # 止损比例
cooldown_minutes = 30          # 交易冷却时间(分钟)
```

### Telegram设置
```
[telegram]
bot_token = TOKEN              # 默认已配置
chat_id = YOUR_CHAT_ID         # 您的Telegram用户ID
```

## 系统要求

- Python 3.7+
- 对于PM2模式：Node.js 14+ 和 PM2
- 对于systemd模式：系统支持systemd用户服务

## 日志查看

### PM2模式
```bash
pm2 logs backpack_bot
```

### systemd模式
```bash
journalctl --user -u backpack-bot -f
```

## 安全建议

1. 使用API密钥时，建议只启用交易权限，不要启用提现权限
2. 定期检查日志确保系统正常运行
3. 设置合理的仓位限制，避免过大风险

## 问题排查

如果遇到问题，可以：

1. 检查日志：`backpack-config logs`
2. 查看机器人状态：`backpack-config status`
3. 尝试重启机器人：`backpack-config stop` 然后 `backpack-config start`

## 卸载

如需完全卸载机器人：

1. 进入配置菜单：`backpack-config`
2. 选择选项 `8. 删除机器人`
3. 输入 `DELETE` 确认删除

也可以手动删除目录：
```bash
# 对于PM2模式，还需要删除PM2中的服务
pm2 delete backpack_bot

# 对于systemd模式，需要禁用并删除服务
systemctl --user disable backpack-bot
systemctl --user stop backpack-bot
rm ~/.config/systemd/user/backpack-bot.service
systemctl --user daemon-reload

# 然后删除配置目录
rm -rf ~/.backpack_bot
``` 