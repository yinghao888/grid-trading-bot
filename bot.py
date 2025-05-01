import os
import sys
import asyncio
import hmac
import hashlib
import time
import json
import numpy as np
from typing import Dict, List, Optional, Any
import aiohttp
import websockets
from datetime import datetime
from loguru import logger
from dotenv import load_dotenv, set_key

# Configuration
BASE_URL = "https://api.backpack.exchange"
WS_URL = "wss://ws.backpack.exchange"
LOG_LEVEL = "INFO"
LOG_FILE = "grid_bot.log"

# Add logger
logger.add(LOG_FILE, level=LOG_LEVEL)

class GridConfig:
    def __init__(
        self,
        symbol: str = "BTC_USDC_PERP",
        grid_num: int = 10,
        upper_price: float = None,
        lower_price: float = None,
        total_investment: float = 1000,
        grid_spread: float = 0.02,
        stop_loss_pct: float = 0.1,
        take_profit_pct: float = 0.2,
    ):
        self.symbol = symbol
        self.grid_num = grid_num
        self.upper_price = upper_price
        self.lower_price = lower_price
        self.total_investment = total_investment
        self.grid_spread = grid_spread
        self.stop_loss_pct = stop_loss_pct
        self.take_profit_pct = take_profit_pct

class BackpackAPI:
    def __init__(self, api_key: str, api_secret: str):
        self.api_key = api_key
        self.api_secret = api_secret
        self.session = None
        self.ws = None
        self.prices = {}
        self._price_callbacks = []
        
    async def _init_session(self):
        if not self.session:
            self.session = aiohttp.ClientSession()
            
    def _generate_signature(self, timestamp: int, method: str, path: str, body: str = "") -> str:
        message = f"{timestamp}{method}{path}{body}"
        signature = hmac.new(
            self.api_secret.encode(),
            message.encode(),
            hashlib.sha256
        ).hexdigest()
        return signature
        
    async def _request(self, method: str, path: str, params: dict = None, data: dict = None) -> dict:
        await self._init_session()
        timestamp = int(time.time() * 1000)
        
        headers = {
            "X-API-KEY": self.api_key,
            "X-TIMESTAMP": str(timestamp),
            "Content-Type": "application/json"
        }
        
        url = f"{BASE_URL}{path}"
        if params:
            query = "&".join([f"{k}={v}" for k, v in params.items()])
            url = f"{url}?{query}"
            
        body = json.dumps(data) if data else ""
        signature = self._generate_signature(timestamp, method, path, body)
        headers["X-SIGNATURE"] = signature
        
        try:
            async with self.session.request(method, url, headers=headers, json=data) as response:
                return await response.json()
        except Exception as e:
            logger.error(f"API 请求失败: {e}")
            raise
            
    async def get_price(self, symbol: str) -> float:
        response = await self._request("GET", f"/api/v1/ticker/price/{symbol}")
        return float(response["price"])
        
    async def get_balance(self, asset: str) -> float:
        response = await self._request("GET", "/api/v1/balance")
        for balance in response:
            if balance["asset"] == asset:
                return float(balance["available"])
        return 0.0
        
    async def place_order(
        self,
        symbol: str,
        side: str,
        order_type: str,
        quantity: float,
        price: float = None,
        reduce_only: bool = False,
        post_only: bool = False
    ) -> dict:
        data = {
            "symbol": symbol,
            "side": side.upper(),
            "type": order_type.upper(),
            "quantity": str(quantity),
            "reduceOnly": reduce_only,
            "postOnly": post_only
        }
        
        if price:
            data["price"] = str(price)
            
        return await self._request("POST", "/api/v1/order", data=data)
        
    async def cancel_order(self, symbol: str, order_id: str) -> dict:
        return await self._request("DELETE", f"/api/v1/order/{symbol}/{order_id}")
        
    async def get_position(self, symbol: str) -> Optional[dict]:
        response = await self._request("GET", "/api/v1/position")
        for position in response:
            if position["symbol"] == symbol:
                return position
        return None
        
    async def start_ws_price_stream(self):
        async def _connect():
            try:
                self.ws = await websockets.connect(WS_URL)
                await self.ws.send(json.dumps({
                    "type": "subscribe",
                    "channel": "ticker",
                    "market": "all"
                }))
                
                while True:
                    try:
                        message = await self.ws.recv()
                        data = json.loads(message)
                        
                        if data.get("type") == "ticker":
                            symbol = data["market"]
                            price = float(data["last"])
                            self.prices[symbol] = price
                            
                            for callback in self._price_callbacks:
                                await callback(symbol, price)
                    except Exception as e:
                        logger.error(f"WebSocket数据处理错误: {e}")
                        await asyncio.sleep(5)
                        await _connect()
            except Exception as e:
                logger.error(f"WebSocket连接失败: {e}")
                await asyncio.sleep(5)
                await _connect()
                    
        asyncio.create_task(_connect())
        
    def register_price_callback(self, callback):
        self._price_callbacks.append(callback)
        
    async def close(self):
        if self.session:
            await self.session.close()
        if self.ws:
            await self.ws.close()

class GridTradingBot:
    def __init__(self, config: GridConfig):
        self.config = config
        self.api = BackpackAPI(os.getenv("BACKPACK_API_KEY"), os.getenv("BACKPACK_API_SECRET"))
        self.grid_prices: List[float] = []
        self.active_orders: Dict[str, dict] = {}
        self.is_running = False
        self.initial_price = 0.0
        self.total_profit = 0.0
        self.trades_count = 0
        
    async def initialize(self):
        try:
            self.initial_price = await self.api.get_price(self.config.symbol)
            logger.info(f"交易对 {self.config.symbol} 的初始价格: {self.initial_price}")
            
            if not self.config.upper_price:
                self.config.upper_price = self.initial_price * 1.1
            if not self.config.lower_price:
                self.config.lower_price = self.initial_price * 0.9
                
            self.grid_prices = list(np.linspace(
                self.config.lower_price,
                self.config.upper_price,
                self.config.grid_num
            ))
            
            await self.api.start_ws_price_stream()
            self.api.register_price_callback(self._on_price_update)
            await self._place_grid_orders()
            
        except Exception as e:
            logger.error(f"初始化错误: {e}")
            raise
            
    async def _place_grid_orders(self):
        current_price = self.initial_price
        
        for price in self.grid_prices:
            if abs(price - current_price) / current_price < self.config.grid_spread:
                continue
                
            try:
                quantity = self.config.total_investment / self.config.grid_num / price
                side = "BUY" if price < current_price else "SELL"
                
                order = await self.api.place_order(
                    symbol=self.config.symbol,
                    side=side,
                    order_type="LIMIT",
                    quantity=quantity,
                    price=price,
                    post_only=True
                )
                
                self.active_orders[order["orderId"]] = {
                    "price": price,
                    "side": side,
                    "quantity": quantity
                }
                
                logger.info(f"已下{side}单，价格: {price}")
                
            except Exception as e:
                logger.error(f"下单错误，价格 {price}: {e}")
                
    async def _on_price_update(self, symbol: str, price: float):
        if symbol != self.config.symbol or not self.is_running:
            return
            
        try:
            position = await self.api.get_position(self.config.symbol)
            if position:
                unrealized_pnl = float(position["unrealizedPnl"])
                
                if unrealized_pnl < -self.config.total_investment * self.config.stop_loss_pct:
                    await self._close_all_positions()
                    logger.warning(f"触发止损，当前价格: {price}")
                    return
                    
                if unrealized_pnl > self.config.total_investment * self.config.take_profit_pct:
                    await self._close_all_positions()
                    logger.info(f"触发止盈，当前价格: {price}")
                    return
                    
            await self._update_grid_orders(price)
            
        except Exception as e:
            logger.error(f"处理价格更新时出错: {e}")
            
    async def _update_grid_orders(self, current_price: float):
        try:
            closest_above = min((p for p in self.grid_prices if p > current_price), default=None)
            closest_below = max((p for p in self.grid_prices if p < current_price), default=None)
            
            for order_id, order in list(self.active_orders.items()):
                price = order["price"]
                if abs(price - current_price) / current_price > self.config.grid_spread * 2:
                    await self.api.cancel_order(self.config.symbol, order_id)
                    del self.active_orders[order_id]
                    logger.info(f"已取消订单，价格: {price}")
                    
            if closest_above and not any(o["price"] == closest_above for o in self.active_orders.values()):
                await self._place_grid_orders()
                
            if closest_below and not any(o["price"] == closest_below for o in self.active_orders.values()):
                await self._place_grid_orders()
                
        except Exception as e:
            logger.error(f"更新网格订单时出错: {e}")
            
    async def _close_all_positions(self):
        try:
            for order_id in list(self.active_orders.keys()):
                await self.api.cancel_order(self.config.symbol, order_id)
                del self.active_orders[order_id]
                
            position = await self.api.get_position(self.config.symbol)
            if position:
                quantity = abs(float(position["quantity"]))
                side = "SELL" if float(position["quantity"]) > 0 else "BUY"
                
                await self.api.place_order(
                    symbol=self.config.symbol,
                    side=side,
                    order_type="MARKET",
                    quantity=quantity,
                    reduce_only=True
                )
                
            logger.info("已关闭所有持仓并取消所有订单")
            
        except Exception as e:
            logger.error(f"关闭持仓时出错: {e}")
            
    async def start(self):
        logger.info("正在启动网格交易机器人...")
        self.is_running = True
        await self.initialize()
        
        try:
            while self.is_running:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            logger.info("正在停止网格交易机器人...")
            await self.stop()
            
    async def stop(self):
        self.is_running = False
        await self._close_all_positions()
        await self.api.close()
        logger.info("网格交易机器人已停止")
        
    def get_stats(self) -> dict:
        return {
            "total_profit": self.total_profit,
            "trades_count": self.trades_count,
            "active_orders": len(self.active_orders),
            "grid_levels": len(self.grid_prices),
            "current_price": self.api.prices.get(self.config.symbol, 0),
            "is_running": self.is_running
        }

# CLI Menu Functions
def get_input(prompt: str) -> str:
    """直接从标准输入读取"""
    print(prompt, end='', flush=True)
    try:
        # 直接从标准输入读取一行
        return sys.stdin.readline().strip()
    except:
        # 如果出现任何错误，等待一秒后重试
        time.sleep(1)
        try:
            return input(prompt).strip()
        except:
            return ""

def clear_screen():
    """清理屏幕"""
    os.system('cls' if os.name == 'nt' else 'clear')

def print_header():
    """打印头部信息"""
    clear_screen()
    print("=" * 50)
    print("Backpack 网格交易机器人管理系统")
    print("=" * 50)
    print()

def configure_api_keys():
    print_header()
    print("配置 API 密钥\n")
    
    api_key = get_input("请输入您的 API Key: ")
    api_secret = get_input("请输入您的 API Secret: ")
    
    if not api_key or not api_secret:
        print("\n错误：API Key 和 Secret 不能为空！")
        return False
        
    set_key(".env", "BACKPACK_API_KEY", api_key)
    set_key(".env", "BACKPACK_API_SECRET", api_secret)
    print("\n✅ API 密钥配置成功！")
    get_input("\n按回车键继续...")
    return True

def configure_trading_params() -> Optional[GridConfig]:
    print_header()
    print("配置交易参数\n")
    
    try:
        symbol = get_input("交易对 (默认: BTC_USDC_PERP): ") or "BTC_USDC_PERP"
        grid_num = int(get_input("网格数量 (默认: 10): ") or "10")
        total_investment = float(get_input("总投资额 USDC (默认: 1000): ") or "1000")
        grid_spread = float(get_input("网格间距 % (默认: 2): ") or "2") / 100
        stop_loss_pct = float(get_input("止损百分比 % (默认: 10): ") or "10") / 100
        take_profit_pct = float(get_input("止盈百分比 % (默认: 20): ") or "20") / 100
        
        config = GridConfig(
            symbol=symbol,
            grid_num=grid_num,
            total_investment=total_investment,
            grid_spread=grid_spread,
            stop_loss_pct=stop_loss_pct,
            take_profit_pct=take_profit_pct
        )
        
        print("\n✅ 交易参数配置成功！")
        get_input("\n按回车键继续...")
        return config
        
    except ValueError as e:
        print(f"\n❌ 输入错误：{str(e)}")
        get_input("\n按回车键继续...")
        return None

def run_menu():
    """运行菜单的主函数"""
    import select
    
    def is_input_available():
        """检查是否有输入可用"""
        return select.select([sys.stdin], [], [], 0.1)[0] != []
    
    async def menu_loop():
        bot = None
        config = None
        
        while True:
            print_header()
            print("1. 配置 API 密钥")
            print("2. 配置交易参数")
            print("3. 启动机器人")
            print("4. 停止机器人")
            print("5. 显示统计信息")
            print("6. 退出程序")
            print()
            
            sys.stdout.write("请输入您的选择 (1-6): ")
            sys.stdout.flush()
            
            while not is_input_available():
                time.sleep(0.1)
            
            try:
                choice = sys.stdin.readline().strip()
            except:
                continue
            
            if choice == "1":
                if configure_api_keys():
                    print("API 密钥已更新")
                    time.sleep(1)
                    
            elif choice == "2":
                config = configure_trading_params()
                if config:
                    bot = GridTradingBot(config)
                    print("交易参数已更新")
                    time.sleep(1)
                    
            elif choice == "3":
                if not os.getenv("BACKPACK_API_KEY") or not os.getenv("BACKPACK_API_SECRET"):
                    print("\n❌ 错误：请先配置 API 密钥！")
                    time.sleep(2)
                    continue
                    
                if not config or not bot:
                    print("\n❌ 错误：请先配置交易参数！")
                    time.sleep(2)
                    continue
                    
                print("\n正在启动机器人...")
                await bot.initialize()
                await bot.start()
                print("✅ 机器人已启动！")
                time.sleep(2)
                
            elif choice == "4":
                if bot and bot.is_running:
                    print("\n正在停止机器人...")
                    await bot.stop()
                    print("✅ 机器人已停止！")
                else:
                    print("\n❌ 错误：机器人未在运行！")
                time.sleep(2)
                
            elif choice == "5":
                if bot:
                    stats = bot.get_stats()
                    print("\n统计信息:")
                    print(f"总收益: {stats['total_profit']:.4f} USDC")
                    print(f"交易次数: {stats['trades_count']}")
                    print(f"当前价格: {stats['current_price']:.2f} USDC")
                    print(f"运行状态: {'运行中' if stats['is_running'] else '已停止'}")
                else:
                    print("\n❌ 错误：机器人未初始化！")
                time.sleep(3)
                
            elif choice == "6":
                sys.stdout.write("\n确认要退出吗？(y/n): ")
                sys.stdout.flush()
                
                while not is_input_available():
                    time.sleep(0.1)
                
                try:
                    confirm = sys.stdin.readline().strip().lower()
                    if confirm == 'y':
                        if bot:
                            await bot.stop()
                            await bot.api.close()
                        print("\n感谢使用！再见！")
                        return
                except:
                    continue
                
            else:
                print("\n❌ 无效的选择，请重试！")
                time.sleep(1)

if __name__ == "__main__":
    try:
        # 确保标准输入是可读的
        if not sys.stdin.isatty():
            # 如果不是终端，尝试重新打开标准输入
            try:
                sys.stdin = open('/dev/tty')
            except:
                print("错误：无法访问终端。请确保在终端环境中运行此程序。")
                sys.exit(1)
        
        # 运行主程序
        asyncio.run(run_menu())
    except KeyboardInterrupt:
        print("\n\n程序已被用户中断")
    except Exception as e:
        print(f"\n\n程序运行出错：{str(e)}")
        logger.exception("程序异常退出")
    finally:
        print("\n感谢使用！再见！") 
