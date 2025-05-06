# Backpack交易机器人

基于Backpack交易所API的自动交易机器人，主要实现了基于资金费率的套利策略。

## 功能特点

- 自动监控资金费率变化
- 基于资金费率阈值自动开仓和平仓
- 支持多个交易对同时运行
- 实时价格监控
- 断线自动重连
- 详细的日志记录

## 安装步骤

1. 确保已安装Python 3.7或以上版本
2. 安装所需依赖包：

```bash
pip install aiohttp websockets
```

## 配置文件

编辑`config.ini`文件，设置您的API密钥和交易参数：

```ini
[api]
api_key = YOUR_API_KEY  # 替换为您的API密钥
api_secret = YOUR_API_SECRET  # 替换为您的API密钥
base_url = https://api.backpack.exchange
ws_url = wss://ws.backpack.exchange

[trading]
symbols = BTC_USDC_PERP,ETH_USDC_PERP,SOL_USDC_PERP  # 要交易的永续合约
position_limit = 0.001  # BTC最大持仓量
funding_threshold = 0.0001  # 资金费率阈值（正负）
check_interval = 300  # 检查间隔（秒）
```

## 使用方法

1. 编辑配置文件，设置您的API密钥和交易参数
2. 运行机器人：

```bash
python backpack_bot.py
```

## 工作原理

1. 机器人会定期检查配置的交易对的资金费率
2. 当资金费率超过设定的阈值时：
   - 如果资金费率为正且高于阈值，机器人会做空（因为持有空仓可以收取资金费）
   - 如果资金费率为负且低于负阈值，机器人会做多（因为持有多仓可以收取资金费）
   - 如果资金费率在阈值范围内，机器人会平掉现有仓位
3. 机器人使用WebSocket连接实时监控价格变化
4. 所有交易活动都会记录在日志文件中

## 风险管理

- 仓位大小根据交易对价格自动调整，保持合理风险水平
- 使用`reduce_only`参数确保平仓操作不会反向开仓
- 异常情况有完整的错误捕获和处理机制

## 高级用法

### 自定义策略

如果您想调整或扩展交易策略，请修改`backpack_bot.py`中的`handle_position`方法。

### 添加新交易对

在配置文件的`symbols`参数中添加新的交易对，格式为`XXX_USDC_PERP`。

### 设置风险参数

调整`position_limit`参数控制最大仓位大小。系统会自动根据不同交易对的价格比例调整实际仓位。

## 注意事项

- 交易涉及资金风险，请谨慎使用
- 建议先使用小仓位测试系统稳定性
- 确保您的API密钥具有交易权限
- 定期检查日志文件监控系统运行状态

## 日志文件

系统会自动创建日志文件，格式为`backpack_bot_YYYYMMDD.log`，包含所有交易决策和执行记录。 