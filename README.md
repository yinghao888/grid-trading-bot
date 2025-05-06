# Backpack ETH自动交易机器人

![Version](https://img.shields.io/badge/版本-1.2.0-blue)
![Platform](https://img.shields.io/badge/平台-Ubuntu%20|%20Debian-green)

一个专为Backpack交易所设计的ETH自动交易机器人，支持杠杆交易、止盈止损、Telegram通知等功能。优化于Ubuntu/Debian环境，可一键安装。

## 功能特点

- **自动化交易策略**：
  - 使用账户USDC余额的20倍杠杆开ETH多单
  - 当ETH价格上涨2%时自动平仓获利
  - 当ETH价格下跌10%时自动止损
  - 止损后进入冷静期，避免连续交易亏损

- **实时监控**：
  - Telegram实时通知交易状态
  - 提供详细的交易日志
  - 实时显示盈亏情况

- **高可靠性**：
  - 完善的错误处理机制
  - 自动重试与恢复
  - 服务器断电后自动恢复交易

- **易于使用**：
  - 一键安装脚本
  - 交互式配置菜单
  - 完整的命令行工具

## 一键安装方法

### 方法一：直接从网络安装（推荐）

只需在终端中运行以下命令：

```bash
curl -s https://raw.githubusercontent.com/yinghao888/grid-trading-bot/main/install.sh | bash
```

### 方法二：克隆仓库后安装

```bash
git clone https://github.com/yinghao888/grid-trading-bot.git
cd grid-trading-bot
chmod +x install.sh
./install.sh
```

## 安装说明

安装过程包括以下步骤：

1. 检查系统兼容性
2. 安装所需依赖（Python3、Node.js、PM2、jq等）
3. 下载和配置交易机器人
4. 设置自动启动脚本
5. 启动配置菜单

安装完成后，您需要在配置菜单中设置：

1. Telegram Chat ID - 用于接收交易通知
2. Backpack交易所API密钥 - 用于执行交易
3. 交易参数 - 可选自定义杠杆倍数、止盈止损比例等

## 配置说明

### Telegram配置

1. 在Telegram中搜索 `@userinfobot` 并发送任意消息获取您的Chat ID
2. 在配置菜单中输入您的Chat ID

### Backpack API配置

1. 登录Backpack交易所官网
2. 进入API管理页面创建API密钥
3. 确保API密钥具有交易权限
4. 在配置菜单中输入API Key和API Secret

### 交易参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| 交易对 | ETH_USDC_PERP | 交易的加密货币对 |
| 杠杆倍数 | 20 | 交易使用的杠杆倍数 |
| 止盈比例 | 2% | 达到此盈利比例时自动平仓 |
| 止损比例 | 10% | 达到此亏损比例时自动止损 |
| 冷静期 | 30分钟 | 止损后等待的时间 |

## 使用方法

安装完成后，您可以使用以下命令：

### 基本命令

```bash
backpack-config         # 打开配置菜单
backpack-start          # 启动交易机器人
```

### 高级命令

```bash
backpack-config config   # 编辑配置文件
backpack-config start    # 启动交易机器人
backpack-config stop     # 停止交易机器人
backpack-config restart  # 重启交易机器人
backpack-config status   # 查看交易机器人状态
backpack-config logs     # 查看交易机器人日志
```

### 日志查看

```bash
pm2 logs backpack_bot    # 查看实时日志
```

日志文件位置：`~/.backpack_bot/logs/backpack_bot.log`

## 交易策略说明

本机器人采用以下交易策略：

1. **开仓条件**：
   - 使用USDC余额的20倍杠杆
   - 仅在没有现有持仓且不在冷静期时开仓
   - 优先使用ETH_USDC_PERP交易对

2. **平仓条件**：
   - **止盈**：当持仓盈利达到2%时自动平仓
   - **止损**：当持仓亏损达到10%时自动平仓

3. **冷静期**：
   - 在触发止损后，机器人进入30分钟冷静期
   - 冷静期内不会开启新的交易
   - 冷静期结束后，机器人自动恢复交易

## 风险提示

- 加密货币交易具有高风险，请谨慎使用
- 建议使用少量资金进行测试
- 过去的收益不代表未来的表现
- 请根据个人风险承受能力调整交易参数

## 故障排除

### 常见问题

1. **机器人无法启动**
   - 检查配置文件是否正确
   - 确保API密钥具有交易权限
   - 查看日志文件获取详细错误信息

2. **没有收到Telegram通知**
   - 确认Chat ID是否正确
   - 检查是否已与官方Bot建立对话
   - 确保网络连接正常

3. **交易执行失败**
   - 检查账户余额是否充足
   - 确认API权限是否正确
   - 查看日志文件获取详细错误信息

## 卸载方法

如需卸载机器人，请运行以下命令：

```bash
pm2 delete backpack_bot
rm -rf ~/.backpack_bot
rm ~/.local/bin/backpack-config
rm ~/.local/bin/backpack-start
```

## 更新日志

### v1.2.0
- 增强错误处理和恢复机制
- 优化安装脚本，支持更多Linux发行版
- 改进交易逻辑，提高交易成功率
- 添加API连接测试功能

### v1.1.0
- 添加交易参数自定义配置
- 改进Telegram通知的内容和格式
- 优化内存使用和性能

### v1.0.0
- 首次发布
- 基本的自动交易功能
- Telegram通知
- 一键安装脚本

## 许可证

MIT

## 免责声明

本软件仅供学习和研究使用，作者不对使用本软件产生的任何直接或间接损失负责。使用本软件进行交易时，请您自行承担风险。 