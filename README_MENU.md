# Backpack 交易机器人菜单使用指南

本文档详细介绍了交易机器人菜单系统的使用方法，包括交互式菜单和命令行参数模式。

## 菜单特性

- **交互式菜单**: 提供易用的界面配置机器人
- **命令行参数模式**: 支持通过命令行参数配置，适合自动化脚本和非交互环境
- **环境检测**: 自动检测运行环境，在非交互环境中优雅降级
- **进程管理**: 兼容PM2和systemd两种进程管理系统

## 交互式菜单使用

直接运行以下命令打开交互式菜单：

```bash
python3 menu.py
```

或者使用简化命令（如果已经安装）：

```bash
backpack-config
```

### 菜单功能

1. **快速配置向导**: 一步步引导完成所有必要配置
2. **配置交易所 API**: 设置Backpack交易所API密钥
3. **配置 Telegram 通知**: 设置Telegram通知
4. **选择交易对**: 管理要交易的加密货币对
5. **配置交易参数**: 调整仓位限制、资金费率阈值等参数
6. **查看日志**: 浏览运行日志
7. **启动/停止机器人**: 控制机器人运行状态
8. **删除机器人**: 完全移除机器人

## 命令行参数模式

在非交互环境或自动化脚本中，可以使用命令行参数：

```bash
# 设置API密钥
python3 menu.py --api-key=YOUR_KEY --api-secret=YOUR_SECRET

# 设置Telegram ID
python3 menu.py --telegram-id=YOUR_TELEGRAM_ID

# 选择交易对
python3 menu.py --trading-pairs=ETH_USDC_PERP,SOL_USDC_PERP

# 设置交易参数
python3 menu.py --position-limit=0.001 --funding-threshold=0.0001

# 启动机器人
python3 menu.py --start-bot

# 停止机器人
python3 menu.py --stop-bot

# 一次性设置多个参数
python3 menu.py --api-key=YOUR_KEY --api-secret=YOUR_SECRET --trading-pairs=ETH_USDC_PERP --start-bot
```

## 环境变量

以下环境变量可以控制菜单行为：

- `FORCE_INTERACTIVE=true`: 强制使用交互模式，即使在非交互环境中
- `NON_INTERACTIVE=true`: 强制使用非交互模式
- `DEBUG=true`: 显示调试信息

## 非交互环境使用示例

在cron作业或其他脚本中，可以这样使用：

```bash
# 配置并启动
NON_INTERACTIVE=true python3 menu.py --api-key=YOUR_KEY --api-secret=YOUR_SECRET --start-bot

# 或通过管道（在backpack-config中有更好的处理）
echo "" | backpack-config --api-key=YOUR_KEY --api-secret=YOUR_SECRET
```

## 常见问题解决

1. **菜单崩溃或输入问题**: 
   - 使用 `FORCE_INTERACTIVE=true` 强制交互模式
   - 或使用命令行参数模式

2. **"未找到PM2"错误**:
   - 安装PM2: `npm install -g pm2`
   - 或者配置systemd服务

3. **"未检测到Python3"错误**:
   - 确保安装了Python 3.7或更高版本

4. **如何在Docker或CI环境中使用**:
   - 始终使用命令行参数模式
   - 设置 `NON_INTERACTIVE=true`

## 安全建议

- 不要在共享脚本或公开仓库中存储API密钥
- 使用配置文件或环境变量管理敏感信息
- 定期更新密钥以提高安全性

希望本指南能帮助您顺利使用交易机器人菜单系统！ 