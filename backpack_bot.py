import asyncio
import logging
import os
import signal
import sys
from datetime import datetime, timedelta
from configparser import ConfigParser
import math

# 配置日志
log_path = os.path.expanduser(f"~/.backpack_bot/backpack_bot_{datetime.now().strftime('%Y%m%d')}.log")
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(log_path)
    ]
)
logger = logging.getLogger("backpack_bot")

# 导入Backpack API
# 假设API类已在指定的模块中实现
try:
    from backpack_api import BackpackAPI
except ImportError:
    # 如果未找到，我们将在本文件中实现简化版
    logger.warning("未找到backpack_api模块，将使用内置API实现")
    try:
        from backpack_api_impl import BackpackAPI
    except ImportError:
        logger.error("无法导入backpack_api_impl模块，请确保文件存在")
        sys.exit(1)

# 导入Telegram处理模块
try:
    from telegram_handler import TelegramHandler
except ImportError:
    logger.warning("未找到telegram_handler模块，将禁用Telegram通知")
    TelegramHandler = None


class BackpackTradingBot:
    def __init__(self, config_file=None):
        """初始化交易机器人"""
        self.logger = logger
        # 如果没有指定配置文件，使用默认路径
        if config_file is None:
            config_file = os.path.expanduser("~/.backpack_bot/config.ini")
        
        self.config = self._load_config(config_file)
        self.api = None
        self.telegram = None
        self.symbols = self.config.get("trading", "symbols").split(",")
        self.leverage = float(self.config.get("trading", "leverage", fallback="20"))
        self.profit_target = float(self.config.get("trading", "profit_target", fallback="0.0002"))  # 0.02% 手续费
        self.stop_loss = float(self.config.get("trading", "stop_loss", fallback="0.1"))  # 10% 止损
        self.cooldown_minutes = int(self.config.get("trading", "cooldown_minutes", fallback="30"))
        self.check_interval = int(self.config.get("trading", "check_interval", fallback="10"))  # 检查间隔（秒）
        self.positions = {}
        self.running = False
        self.last_check_time = None
        self.cooldown_until = {}  # 用于跟踪每个交易对的冷却期
        self.entry_prices = {}  # 用于跟踪每个交易对的入场价格
        self.account_balance = 0  # 账户余额
        self.initial_balance = 0  # 初始余额

    def _load_config(self, config_file):
        """加载配置文件"""
        config = ConfigParser()
        
        if not os.path.exists(config_file):
            self.logger.error(f"配置文件不存在: {config_file}")
            sys.exit(1)
        
        config.read(config_file)
        return config

    async def initialize(self):
        """初始化API客户端并开始数据流"""
        self.logger.info("正在初始化Backpack API客户端...")
        
        self.api = BackpackAPI(
            api_key=self.config.get("api", "api_key"),
            api_secret=self.config.get("api", "api_secret"),
            base_url=self.config.get("api", "base_url"),
            ws_url=self.config.get("api", "ws_url"),
            logger=self.logger
        )
        
        # 初始化Telegram处理程序
        if TelegramHandler is not None:
            bot_token = self.config.get("telegram", "bot_token")
            chat_id = self.config.get("telegram", "chat_id")
            if bot_token and chat_id:
                self.telegram = TelegramHandler(bot_token, chat_id, self.logger)
                await self.telegram.send_start_notification()
            else:
                self.logger.warning("未配置Telegram信息，禁用通知功能")
        
        # 启动价格数据流
        await self.api.start_ws_price_stream()
        self.logger.info("价格数据流启动成功")
        
        # 获取账户信息和余额
        await self.update_account_info()
        
        # 加载当前持仓信息
        await self.sync_positions()
        
        # 设置价格更新回调，实时监控价格变化
        self.api.register_price_callback(self.price_update_callback)

    async def update_account_info(self):
        """更新账户信息和余额"""
        try:
            # 获取账户信息
            account_info = await self.api.get_account_info()
            self.logger.info(f"账户状态: {account_info.get('status', 'unknown')}")
            
            # 获取账户余额
            balances = await self.api.get_balances()
            usdc_balance = 0
            for balance in balances:
                if balance['asset'] == 'USDC':
                    usdc_balance = float(balance['available'])
                    self.logger.info(f"USDC 余额: {usdc_balance}")
                elif float(balance['available']) > 0:
                    self.logger.info(f"{balance['asset']} 余额: {balance['available']}")
            
            self.account_balance = usdc_balance
            if self.initial_balance == 0:
                self.initial_balance = usdc_balance
            
            # 如果配置了Telegram，发送余额信息
            if self.telegram:
                balance_dict = {b['asset']: {'available': b['available'], 'locked': b['locked']} 
                                for b in balances if float(b['available']) > 0 or float(b['locked']) > 0}
                await self.telegram.send_balance_notification(balance_dict)
            
            return account_info
        except Exception as e:
            self.logger.error(f"获取账户信息失败: {e}")
            if self.telegram:
                await self.telegram.send_error_notification(f"获取账户信息失败: {e}")
            return None

    async def sync_positions(self):
        """同步当前持仓信息"""
        try:
            positions = await self.api.get_positions()
            self.positions = {}
            
            for position in positions:
                if float(position['quantity']) != 0:  # 只记录有持仓的交易对
                    symbol = position['symbol']
                    quantity = float(position['quantity'])
                    entry_price = float(position['entryPrice'])
                    unrealized_profit = float(position['unrealizedProfit'])
                    
                    self.positions[symbol] = {
                        'quantity': quantity,
                        'entry_price': entry_price,
                        'unrealized_profit': unrealized_profit
                    }
                    
                    # 更新入场价格记录
                    self.entry_prices[symbol] = entry_price
                    
                    self.logger.info(
                        f"{symbol} 持仓: "
                        f"方向: {'多' if quantity > 0 else '空'}, "
                        f"数量: {abs(quantity)}, "
                        f"入场价: {entry_price}, "
                        f"未实现盈亏: {unrealized_profit}"
                    )
            
            return positions
        except Exception as e:
            self.logger.error(f"同步持仓信息失败: {e}")
            if self.telegram:
                await self.telegram.send_error_notification(f"同步持仓信息失败: {e}")
            return []

    async def price_update_callback(self, symbol, price):
        """价格更新回调函数，用于实时监控价格并处理止盈止损"""
        # 如果该交易对在我们的持仓中，检查是否需要平仓
        if symbol in self.positions and symbol in self.symbols:
            position = self.positions[symbol]
            entry_price = position['entry_price']
            quantity = position['quantity']
            
            # 计算当前盈亏比例
            if quantity > 0:  # 多仓
                profit_percent = (price / entry_price - 1)
            else:  # 空仓
                profit_percent = (1 - price / entry_price)
            
            # 检查是否达到止盈目标
            if profit_percent >= self.profit_target:
                self.logger.info(f"{symbol} 达到止盈目标 ({profit_percent:.4f}), 准备平仓")
                # 使用异步任务执行平仓，避免阻塞价格回调
                asyncio.create_task(self.close_position(
                    symbol, quantity, price, 
                    f"达到止盈目标 {profit_percent:.4f} > {self.profit_target:.4f}"
                ))
            
            # 检查是否触发止损
            elif profit_percent <= -self.stop_loss:
                self.logger.warning(f"{symbol} 触发止损 ({profit_percent:.4f}), 准备平仓")
                # 使用异步任务执行平仓，避免阻塞价格回调
                asyncio.create_task(self.close_position(
                    symbol, quantity, price, 
                    f"触发止损 {profit_percent:.4f} < -{self.stop_loss:.4f}"
                ))

    async def check_trading_opportunities(self):
        """检查所有交易对的交易机会"""
        self.logger.info("正在检查交易机会...")
        self.last_check_time = datetime.now()
        
        # 更新账户信息和余额
        await self.update_account_info()
        
        try:
            for symbol in self.symbols:
                # 检查是否在冷却期
                if symbol in self.cooldown_until and datetime.now() < self.cooldown_until[symbol]:
                    cooldown_remaining = (self.cooldown_until[symbol] - datetime.now()).total_seconds() / 60
                    self.logger.info(f"{symbol} 在冷却期内，剩余 {cooldown_remaining:.1f} 分钟")
                    continue
                
                # 获取当前价格
                current_price = self.api.prices.get(symbol, 0)
                if current_price == 0:
                    self.logger.warning(f"{symbol} 价格不可用，跳过处理")
                    continue
                
                # 获取当前持仓
                current_position = self.positions.get(symbol, None)
                
                # 如果没有持仓，考虑开新仓
                if current_position is None or current_position.get('quantity', 0) == 0:
                    await self.open_new_position(symbol, current_price)
        
        except Exception as e:
            self.logger.error(f"检查交易机会时发生错误: {e}")
            if self.telegram:
                await self.telegram.send_error_notification(f"检查交易机会时发生错误: {e}")

    async def open_new_position(self, symbol, current_price):
        """开新仓位"""
        try:
            # 确定开仓方向，随机选择或根据市场趋势
            # 这里我们简单地基于奇偶秒数决定方向
            if datetime.now().second % 2 == 0:
                side = "BUY"  # 做多
            else:
                side = "SELL"  # 做空
            
            # 计算开仓数量，使用账户余额的全部资金开20倍杠杆
            position_value = self.account_balance * self.leverage
            position_size = position_value / current_price
            
            # 对仓位大小进行四舍五入，确保符合交易所要求
            # 不同交易对有不同的最小交易量要求，这里使用简化处理
            decimal_places = 3 if symbol.startswith("BTC") else 2
            position_size = round(position_size, decimal_places)
            
            if position_size <= 0:
                self.logger.warning(f"{symbol} 计算的仓位大小为0，跳过开仓")
                return
            
            self.logger.info(f"{symbol} 尝试以 {current_price} 价格开{side}仓，数量: {position_size}")
            
            # 下单
            order_result = await self.api.place_order(
                symbol=symbol,
                side=side,
                quantity=position_size,
                order_type="LIMIT",
                price=current_price * (0.9999 if side == "BUY" else 1.0001),  # 稍微调整价格确保成为maker
                post_only=True  # 确保只做挂单，降低手续费
            )
            
            if "error" in order_result:
                self.logger.error(f"开仓失败: {order_result['error']}")
                if self.telegram:
                    await self.telegram.send_error_notification(f"{symbol} 开仓失败: {order_result['error']}")
                return
            
            self.logger.info(f"开仓订单已提交: {order_result}")
            
            # 记录入场价格
            self.entry_prices[symbol] = current_price
            
            # 如果配置了Telegram，发送通知
            if self.telegram:
                await self.telegram.send_trade_notification(
                    action="开仓",
                    symbol=symbol,
                    side=side,
                    quantity=position_size,
                    price=current_price,
                    reason=f"新开仓，使用{self.leverage}倍杠杆"
                )
            
            # 下单后等待一段时间并同步仓位
            await asyncio.sleep(5)
            await self.sync_positions()
            
            return order_result
        except Exception as e:
            self.logger.error(f"开仓操作失败: {e}")
            if self.telegram:
                await self.telegram.send_error_notification(f"{symbol} 开仓操作失败: {e}")
            return None

    async def close_position(self, symbol, current_quantity, current_price, reason="用户操作"):
        """平仓"""
        try:
            if current_quantity == 0:
                return
            
            # 根据当前持仓方向确定平仓方向
            side = "SELL" if current_quantity > 0 else "BUY"
            quantity = abs(current_quantity)
            
            self.logger.info(f"平仓 {symbol}: {side} {quantity}，原因: {reason}")
            
            # 计算盈亏
            entry_price = self.entry_prices.get(symbol, 0)
            if entry_price > 0:
                if side == "SELL":  # 平多
                    profit_loss = (current_price - entry_price) * quantity
                else:  # 平空
                    profit_loss = (entry_price - current_price) * quantity
            else:
                profit_loss = None
            
            # 提交平仓订单
            order = await self.api.place_order(
                symbol=symbol,
                side=side,
                quantity=quantity,
                order_type="MARKET",  # 使用市价单快速平仓
                reduce_only=True  # 确保只会平仓不会开仓
            )
            
            self.logger.info(f"平仓订单已提交: {order}")
            
            # 如果配置了Telegram，发送通知
            if self.telegram:
                await self.telegram.send_trade_notification(
                    action="平仓",
                    symbol=symbol,
                    side=side,
                    quantity=quantity,
                    price=current_price,
                    profit_loss=profit_loss,
                    reason=reason
                )
            
            # 如果是因为止损而平仓，设置冷却期
            if "止损" in reason:
                self.cooldown_until[symbol] = datetime.now() + timedelta(minutes=self.cooldown_minutes)
                self.logger.info(f"{symbol} 进入冷却期，直到 {self.cooldown_until[symbol]}")
            
            # 下单后等待一段时间并同步仓位
            await asyncio.sleep(2)
            await self.sync_positions()
            
            # 更新账户信息
            await self.update_account_info()
            
            return order
        except Exception as e:
            self.logger.error(f"平仓失败: {e}")
            if self.telegram:
                await self.telegram.send_error_notification(f"{symbol} 平仓失败: {e}")
            return None

    async def run(self):
        """运行交易机器人"""
        self.running = True
        
        # 注册信号处理器，用于优雅关闭
        for sig in (signal.SIGINT, signal.SIGTERM):
            signal.signal(sig, self._handle_signal)
        
        self.logger.info("交易机器人启动")
        
        try:
            # 初始化API
            await self.initialize()
            
            while self.running:
                # 检查交易机会并执行交易
                await self.check_trading_opportunities()
                
                # 输出当前仓位概况
                self.logger.info("当前持仓概况:")
                for symbol, pos in self.positions.items():
                    direction = "多" if pos['quantity'] > 0 else "空"
                    self.logger.info(f"{symbol}: {direction} {abs(pos['quantity'])}")
                
                # 等待指定时间间隔
                self.logger.info(f"等待 {self.check_interval} 秒后进行下一次检查...")
                await asyncio.sleep(self.check_interval)
        
        except Exception as e:
            self.logger.error(f"运行过程中发生错误: {e}")
            if self.telegram:
                await self.telegram.send_error_notification(f"运行过程中发生错误: {e}")
        finally:
            # 发送停止通知
            if self.telegram:
                await self.telegram.send_stop_notification()
                await self.telegram.close()
            
            # 关闭API连接
            if self.api:
                await self.api.close()
            
            self.logger.info("交易机器人停止")
    
    def _handle_signal(self, sig, frame):
        """处理终止信号"""
        self.logger.info(f"收到信号 {sig}，准备停止交易机器人...")
        self.running = False

    async def stop(self):
        """停止交易机器人"""
        self.running = False
        
        # 等待所有异步任务完成
        tasks = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
        for task in tasks:
            task.cancel()
        
        # 关闭API连接
        if self.api:
            await self.api.close()
        
        # 关闭Telegram连接
        if self.telegram:
            await self.telegram.close()
        
        self.logger.info("交易机器人已安全停止")


async def main():
    """主函数"""
    bot = BackpackTradingBot()
    await bot.run()


if __name__ == "__main__":
    # 运行主函数
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("程序被用户中断")
    except Exception as e:
        print(f"发生错误: {e}") 