#!/usr/bin/env python3
"""
Backpack 交易所网格交易机器人
=============================
整合API和网格交易逻辑的核心模块
"""

import asyncio
import json
import hmac
import hashlib
import time
import os
import signal
import sys
import numpy as np
from typing import Dict, List, Optional, Union, Any
from datetime import datetime
import aiohttp
import websockets
from loguru import logger
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# API 配置
API_KEY = os.getenv("BACKPACK_API_KEY")
API_SECRET = os.getenv("BACKPACK_API_SECRET")
BASE_URL = "https://api.backpack.exchange"
WS_URL = "wss://ws.backpack.exchange"

# 日志配置
LOG_LEVEL = "INFO"
LOG_FILE = "grid_bot.log"
logger.add(LOG_FILE, level=LOG_LEVEL)

# 风险管理
MAX_POSITION_SIZE = 0.1  # 最大仓位大小（占总投资的比例）
MAX_LEVERAGE = 3  # 最大杠杆倍数
MIN_GRID_DISTANCE = 0.005  # 网格之间的最小距离（0.5%）

# 交易配置类
class GridConfig:
    def __init__(
        self,
        symbol: str = "BTC_USDC_PERP",  # 交易对
        grid_num: int = 10,  # 网格数量
        upper_price: float = None,  # 上限价格，如果为None，将设置为当前价格 * 1.1
        lower_price: float = None,  # 下限价格，如果为None，将设置为当前价格 * 0.9
        total_investment: float = 1000,  # 总投资金额（USDC）
        grid_spread: float = 0.02,  # 网格间距（2%）
        stop_loss_pct: float = 0.1,  # 止损百分比（10%）
        take_profit_pct: float = 0.2,  # 止盈百分比（20%）
    ):
        self.symbol = symbol
        self.grid_num = grid_num
        self.upper_price = upper_price
        self.lower_price = lower_price
        self.total_investment = total_investment
        self.grid_spread = grid_spread
        self.stop_loss_pct = stop_loss_pct
        self.take_profit_pct = take_profit_pct
        
    def to_dict(self) -> Dict[str, Any]:
        return {
            "symbol": self.symbol,
            "grid_num": self.grid_num,
            "upper_price": self.upper_price,
            "lower_price": self.lower_price,
            "total_investment": self.total_investment,
            "grid_spread": self.grid_spread,
            "stop_loss_pct": self.stop_loss_pct,
            "take_profit_pct": self.take_profit_pct,
        }

# Backpack API 类
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
            logger.error(f"API请求失败: {e}")
            raise
            
    async def get_price(self, symbol: str) -> float:
        """获取交易对当前价格"""
        response = await self._request("GET", f"/api/v1/ticker/price/{symbol}")
        return float(response["price"])
        
    async def get_balances(self) -> List[dict]:
        """获取所有资产余额"""
        return await self._request("GET", "/api/v1/balance")
        
    async def get_balance(self, asset: str) -> float:
        """获取特定资产余额"""
        response = await self.get_balances()
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
        """下单"""
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
        """取消订单"""
        return await self._request("DELETE", f"/api/v1/order/{symbol}/{order_id}")
        
    async def cancel_all_orders(self, symbol: str = None) -> dict:
        """取消所有订单，可选按交易对过滤"""
        path = "/api/v1/order/all"
        if symbol:
            path = f"{path}/{symbol}"
        return await self._request("DELETE", path)
        
    async def get_order_status(self, symbol: str, order_id: str) -> dict:
        """获取特定订单状态"""
        return await self._request("GET", f"/api/v1/order/{symbol}/{order_id}")
        
    async def get_open_orders(self, symbol: str = None) -> List[dict]:
        """获取所有未成交订单，可选按交易对过滤"""
        path = "/api/v1/order"
        if symbol:
            path = f"{path}/{symbol}"
        return await self._request("GET", path)
        
    async def get_position(self, symbol: str) -> Optional[dict]:
        """获取特定交易对的持仓"""
        response = await self.get_positions()
        for position in response:
            if position["symbol"] == symbol:
                return position
        return None
        
    async def get_positions(self) -> List[dict]:
        """获取所有持仓"""
        return await self._request("GET", "/api/v1/position")
        
    async def get_funding_rate(self, symbol: str) -> float:
        """获取特定交易对的资金费率"""
        response = await self._request("GET", f"/api/v1/contract/funding-rate/{symbol}")
        return float(response["fundingRate"])
        
    async def get_all_funding_rates(self) -> Dict[str, float]:
        """获取所有永续合约的资金费率"""
        response = await self._request("GET", "/api/v1/contract/funding-rate")
        return {item["symbol"]: float(item["fundingRate"]) for item in response}
        
    async def get_orderbook(self, symbol: str) -> dict:
        """获取交易对的订单簿"""
        return await self._request("GET", f"/api/v1/depth/{symbol}")
        
    async def get_account_info(self) -> dict:
        """获取账户信息"""
        return await self._request("GET", "/api/v1/account")
        
    async def start_ws_price_stream(self):
        """启动WebSocket价格数据流"""
        async def _connect():
            try:
                self.ws = await websockets.connect(WS_URL)
                
                # 订阅行情数据
                subscribe_message = {
                    "type": "subscribe",
                    "channel": "ticker",
                    "market": "all"
                }
                await self.ws.send(json.dumps(subscribe_message))
                
                while True:
                    try:
                        message = await self.ws.recv()
                        data = json.loads(message)
                        
                        if data.get("type") == "ticker":
                            symbol = data["market"]
                            price = float(data["last"])
                            self.prices[symbol] = price
                            
                            # 触发回调
                            for callback in self._price_callbacks:
                                asyncio.create_task(callback(symbol, price))
                    except Exception as e:
                        logger.error(f"WebSocket消息处理错误: {e}")
                        await asyncio.sleep(1)
            except Exception as e:
                logger.error(f"WebSocket连接错误: {e}")
                await asyncio.sleep(5)
                asyncio.create_task(_connect())
                    
        asyncio.create_task(_connect())
        
    def register_price_callback(self, callback):
        """注册价格更新回调"""
        self._price_callbacks.append(callback)
        
    async def close(self):
        """关闭所有连接"""
        if self.session:
            await self.session.close()
        if self.ws:
            await self.ws.close()

# 网格交易机器人类
class GridTradingBot:
    def __init__(self, config: GridConfig):
        self.config = config
        self.api = BackpackAPI(API_KEY, API_SECRET)
        self.grid_prices: List[float] = []
        self.active_orders: Dict[str, dict] = {}
        self.is_running = False
        self.initial_price = 0.0
        self.total_profit = 0.0
        self.trades_count = 0
        
    async def initialize(self):
        """初始化网格交易机器人"""
        try:
            # 获取当前价格
            self.initial_price = await self.api.get_price(self.config.symbol)
            logger.info(f"初始价格 {self.config.symbol}: {self.initial_price}")
            
            # 设置网格边界
            if not self.config.upper_price:
                self.config.upper_price = self.initial_price * 1.1
            if not self.config.lower_price:
                self.config.lower_price = self.initial_price * 0.9
                
            # 计算网格价格
            self.grid_prices = self._calculate_grid_prices()
            logger.info(f"网格价格: {self.grid_prices}")
            
            # 启动WebSocket连接
            await self.api.start_ws_price_stream()
            self.api.register_price_callback(self._on_price_update)
            
            # 下初始网格订单
            await self._place_grid_orders()
            
        except Exception as e:
            logger.error(f"初始化错误: {e}")
            raise
            
    def _calculate_grid_prices(self) -> List[float]:
        """计算网格价格等级"""
        return list(np.linspace(
            self.config.lower_price,
            self.config.upper_price,
            self.config.grid_num
        ))
        
    async def _place_grid_orders(self):
        """下初始网格订单"""
        current_price = self.initial_price
        
        for price in self.grid_prices:
            # 跳过离当前价格太近的价格
            if abs(price - current_price) / current_price < self.config.grid_spread:
                continue
                
            try:
                # 计算订单数量
                quantity = self.config.total_investment / self.config.grid_num / price
                
                # 确定订单方向
                side = "BUY" if price < current_price else "SELL"
                
                # 下限价单
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
                
                logger.info(f"下单 {side} 价格 {price}: {order}")
                
            except Exception as e:
                logger.error(f"下网格订单错误，价格 {price}: {e}")
                
    async def _on_price_update(self, symbol: str, price: float):
        """处理WebSocket价格更新"""
        if symbol != self.config.symbol or not self.is_running:
            return
            
        try:
            # 检查止损和止盈
            position = await self.api.get_position(self.config.symbol)
            if position:
                entry_price = float(position["entryPrice"])
                unrealized_pnl = float(position["unrealizedPnl"])
                
                # 检查止损
                if unrealized_pnl < -self.config.total_investment * self.config.stop_loss_pct:
                    await self._close_all_positions()
                    logger.warning(f"止损触发，价格 {price}")
                    return
                    
                # 检查止盈
                if unrealized_pnl > self.config.total_investment * self.config.take_profit_pct:
                    await self._close_all_positions()
                    logger.info(f"止盈触发，价格 {price}")
                    return
                    
            # 更新网格订单
            await self._update_grid_orders(price)
            
        except Exception as e:
            logger.error(f"处理价格更新错误: {e}")
            
    async def _update_grid_orders(self, current_price: float):
        """基于当前价格更新网格订单"""
        try:
            # 找到最近的网格价格
            closest_above = min((p for p in self.grid_prices if p > current_price), default=None)
            closest_below = max((p for p in self.grid_prices if p < current_price), default=None)
            
            # 取消离当前价格太远的订单
            for order_id, order in list(self.active_orders.items()):
                price = order["price"]
                if abs(price - current_price) / current_price > self.config.grid_spread * 2:
                    await self.api.cancel_order(self.config.symbol, order_id)
                    del self.active_orders[order_id]
                    logger.info(f"取消订单，价格 {price}")
                    
            # 在最近的价格等级下新订单
            if closest_above and not any(o["price"] == closest_above for o in self.active_orders.values()):
                await self._place_grid_orders()
                
            if closest_below and not any(o["price"] == closest_below for o in self.active_orders.values()):
                await self._place_grid_orders()
                
        except Exception as e:
            logger.error(f"更新网格订单错误: {e}")
            
    async def _close_all_positions(self):
        """关闭所有持仓并取消所有订单"""
        try:
            # 取消所有活跃订单
            for order_id in list(self.active_orders.keys()):
                await self.api.cancel_order(self.config.symbol, order_id)
                del self.active_orders[order_id]
                
            # 用市价单平仓
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
            logger.error(f"关闭持仓错误: {e}")
            
    async def start(self):
        """启动网格交易机器人"""
        logger.info("启动网格交易机器人...")
        self.is_running = True
        await self.initialize()
        
        try:
            # 保持机器人运行
            while self.is_running:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            logger.info("正在停止网格交易机器人...")
            await self.stop()
            
    async def stop(self):
        """停止网格交易机器人"""
        logger.info("正在停止网格交易机器人...")
        self.is_running = False
        await self._close_all_positions()
        await self.api.close()
        logger.info("网格交易机器人已停止")
        
    def get_stats(self) -> dict:
        """获取当前交易统计信息"""
        return {
            "total_profit": self.total_profit,
            "trades_count": self.trades_count,
            "active_orders": len(self.active_orders),
            "grid_levels": len(self.grid_prices),
            "current_price": self.api.prices.get(self.config.symbol, 0)
        }

# 辅助函数
def load_config_from_file():
    """从JSON文件加载配置"""
    try:
        config_path = os.path.join(os.path.dirname(__file__), 'configs', 'grid_config.json')
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                config_data = json.load(f)
                
            return GridConfig(
                symbol=config_data.get('symbol', "BTC_USDC_PERP"),
                grid_num=config_data.get('grid_num', 10),
                upper_price=config_data.get('upper_price'),
                lower_price=config_data.get('lower_price'),
                total_investment=config_data.get('total_investment', 1000),
                grid_spread=config_data.get('grid_spread', 0.02),
                stop_loss_pct=config_data.get('stop_loss_pct', 0.1),
                take_profit_pct=config_data.get('take_profit_pct', 0.2)
            )
    except Exception as e:
        logger.error(f"加载配置错误: {e}")
    
    # 如果文件不存在或有错误，返回默认配置
    return GridConfig()

def handle_exit(signum, frame):
    """优雅处理退出信号"""
    logger.info(f"收到信号 {signum}。正在关闭...")
    # 我们需要设置一个标志来停止机器人在主循环中
    if 'bot' in globals() and bot is not None:
        bot.is_running = False

async def main():
    """主函数"""
    # 设置信号处理程序，以便优雅关闭
    signal.signal(signal.SIGINT, handle_exit)
    signal.signal(signal.SIGTERM, handle_exit)
    
    # 加载配置
    config = load_config_from_file()
    logger.info(f"已加载配置: {config.to_dict()}")
    
    global bot
    bot = GridTradingBot(config)
    
    try:
        # 启动机器人
        await bot.start()
    except Exception as e:
        logger.error(f"机器人错误: {e}")
    finally:
        # 确保正确清理
        await bot.stop()
        logger.info("机器人已停止")

if __name__ == "__main__":
    # 初始化事件循环并运行主函数
    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(main())
    except KeyboardInterrupt:
        logger.info("程序被用户中断")
    finally:
        # 关闭事件循环
        loop.close() 
