#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import json
import asyncio
import logging
import time
import signal
import sys
import requests
from typing import Dict, List, Optional, Tuple, Any
import hmac
import hashlib
import base64
import urllib.parse
import uuid
import datetime
import aiohttp
import re
import subprocess
import traceback

# 设置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("backpack_bot.log")
    ]
)
logger = logging.getLogger("BackpackBot")

# 配置文件路径
CONFIG_FILE = "config.json"

# 默认配置
DEFAULT_CONFIG = {
    "telegram": {
        "token": "7685502184:AAGxaIdwiTr0WpPDeIGmc9fgbdeSKxgXtEw",
        "chat_id": ""
    },
    "backpack": {
        "api_key": "",
        "api_secret": "",
        "base_url": "https://api.backpack.exchange",
        "ws_url": "wss://ws.backpack.exchange"
    },
    "trading": {
        "leverage": 20,
        "profit_percentage": 2,
        "stop_loss_percentage": 10,
        "cooldown_minutes": 30,
        "symbol": "ETH_USDC_PERP"
    }
}

class BackpackAPI:
    def __init__(self, api_key: str, api_secret: str, base_url: str, ws_url: str, logger):
        self.api_key = api_key
        self.api_secret = api_secret
        self.base_url = base_url
        self.ws_url = ws_url
        self.logger = logger
        self.session = None
        self.ws = None
        self.prices = {}

    async def initialize(self):
        """初始化HTTP会话"""
        if self.session is None:
            self.session = aiohttp.ClientSession()
        return self

    async def close(self):
        """关闭HTTP会话"""
        if self.session:
            await self.session.close()
            self.session = None

    def _generate_signature(self, timestamp: int, method: str, request_path: str, body: dict = None) -> str:
        """生成API请求的签名"""
        body_str = "" if body is None else json.dumps(body)
        message = f"{timestamp}{method}{request_path}{body_str}"
        signature = hmac.new(
            self.api_secret.encode('utf-8'),
            message.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        return signature

    async def _make_request(self, method: str, endpoint: str, params: dict = None, data: dict = None) -> dict:
        """发送API请求"""
        await self.initialize()
        url = f"{self.base_url}{endpoint}"
        timestamp = int(time.time() * 1000)
        headers = {
            "X-API-KEY": self.api_key,
            "X-TIMESTAMP": str(timestamp),
            "Content-Type": "application/json"
        }

        # 添加查询参数到URL
        if params:
            query_string = urllib.parse.urlencode(params)
            url = f"{url}?{query_string}"
            request_path = f"{endpoint}?{query_string}"
        else:
            request_path = endpoint

        # 添加签名
        signature = self._generate_signature(timestamp, method, request_path, data)
        headers["X-SIGNATURE"] = signature

        try:
            async with getattr(self.session, method.lower())(
                url,
                headers=headers,
                json=data
            ) as response:
                response_data = await response.json()
                if response.status != 200:
                    self.logger.error(f"API请求失败: {response.status} - {response_data}")
                return response_data
        except Exception as e:
            self.logger.error(f"请求异常: {e}")
            return {"error": str(e)}

    async def get_balances(self) -> List[Dict]:
        """获取账户余额"""
        try:
            response = await self._make_request("GET", "/api/v1/capital")
            if "error" in response:
                self.logger.error(f"获取余额失败: {response['error']}")
                return []
            return response
        except Exception as e:
            self.logger.error(f"获取余额异常: {str(e)}")
            self.logger.error(traceback.format_exc())
            return []

    async def get_price(self, symbol: str) -> float:
        """获取当前价格"""
        try:
            response = await self._make_request("GET", "/api/v1/ticker/price", {"symbol": symbol})
            if "price" in response:
                return float(response["price"])
            
            if "error" in response:
                self.logger.error(f"获取价格错误: {response['error']}")
            return 0
        except Exception as e:
            self.logger.error(f"获取价格异常: {str(e)}")
            self.logger.error(traceback.format_exc())
            return 0

    async def get_position(self, symbol: str) -> Optional[Dict]:
        """获取特定交易对的仓位"""
        try:
            positions = await self.get_positions()
            for position in positions:
                if position["symbol"] == symbol and float(position["quantity"]) != 0:
                    return position
            return None
        except Exception as e:
            self.logger.error(f"获取仓位异常: {str(e)}")
            self.logger.error(traceback.format_exc())
            return None

    async def get_positions(self) -> List[Dict]:
        """获取所有持仓"""
        try:
            response = await self._make_request("GET", "/api/v1/positions")
            if isinstance(response, list):
                return response
            if "error" in response:
                self.logger.error(f"获取持仓失败: {response['error']}")
            return []
        except Exception as e:
            self.logger.error(f"获取持仓异常: {str(e)}")
            self.logger.error(traceback.format_exc())
            return []

    async def place_order(self, symbol: str, side: str, quantity: float, 
                         order_type: str = "MARKET", price: float = None,
                         post_only: bool = False, reduce_only: bool = False) -> Dict:
        """下单"""
        try:
            # 验证参数
            if not symbol or not side or quantity <= 0:
                self.logger.error(f"下单参数无效: symbol={symbol}, side={side}, quantity={quantity}")
                return {"error": "参数无效"}
                
            order_data = {
                "symbol": symbol,
                "side": side,
                "type": order_type,
                "quantity": str(quantity)
            }

            if price and order_type == "LIMIT":
                order_data["price"] = str(price)
            if post_only:
                order_data["postOnly"] = "true"
            if reduce_only:
                order_data["reduceOnly"] = "true"

            client_id = str(uuid.uuid4())
            order_data["clientId"] = client_id

            self.logger.info(f"发送订单: {order_data}")
            response = await self._make_request("POST", "/api/v1/order", None, order_data)
            
            if "error" in response:
                self.logger.error(f"下单失败: {response['error']}")
            else:
                self.logger.info(f"订单已提交: {response}")
                
            return response
        except Exception as e:
            self.logger.error(f"下单异常: {str(e)}")
            self.logger.error(traceback.format_exc())
            return {"error": str(e)}

    async def cancel_order(self, symbol: str, order_id: str) -> Dict:
        """取消特定订单"""
        try:
            params = {
                "symbol": symbol,
                "orderId": order_id
            }
            self.logger.info(f"取消订单: {params}")
            response = await self._make_request("DELETE", "/api/v1/order", params)
            
            if "error" in response:
                self.logger.error(f"取消订单失败: {response['error']}")
            else:
                self.logger.info(f"订单已取消: {response}")
                
            return response
        except Exception as e:
            self.logger.error(f"取消订单异常: {str(e)}")
            self.logger.error(traceback.format_exc())
            return {"error": str(e)}

    async def cancel_all_orders(self, symbol: str = None) -> Dict:
        """取消所有订单，可选指定交易对"""
        try:
            params = {}
            if symbol:
                params["symbol"] = symbol
                
            self.logger.info(f"取消所有订单: {params if symbol else '所有交易对'}")
            response = await self._make_request("DELETE", "/api/v1/orders", params)
            
            if "error" in response:
                self.logger.error(f"取消所有订单失败: {response['error']}")
            else:
                self.logger.info(f"所有订单已取消: {response}")
                
            return response
        except Exception as e:
            self.logger.error(f"取消所有订单异常: {str(e)}")
            self.logger.error(traceback.format_exc())
            return {"error": str(e)}

    async def start_ws_price_stream(self):
        """启动WebSocket价格数据流"""
        # 这是一个简化版本的实现
        pass

class TelegramBot:
    def __init__(self, token: str, chat_id: str):
        self.token = token
        self.chat_id = chat_id
        self.base_url = f"https://api.telegram.org/bot{token}"
        self.timeout = 10  # 请求超时时间(秒)
        self.max_retries = 3
        self.retry_delay = 2

    async def send_message(self, text: str, parse_mode: str = "HTML") -> bool:
        """发送消息到Telegram"""
        if not self.chat_id:
            logger.warning("Telegram未配置chat_id，无法发送消息")
            return False
            
        attempts = 0
        while attempts < self.max_retries:
            try:
                url = f"{self.base_url}/sendMessage"
                params = {
                    "chat_id": self.chat_id,
                    "text": text,
                    "parse_mode": parse_mode
                }
                
                async with aiohttp.ClientSession() as session:
                    async with session.post(url, params=params, timeout=self.timeout) as response:
                        if response.status == 200:
                            return True
                        else:
                            response_text = await response.text()
                            logger.error(f"发送Telegram消息失败 [{response.status}]: {response_text}")
                            
                            # 对于一些错误，不再重试
                            if response.status in [400, 401, 403]:
                                return False
                                
                            attempts += 1
                            if attempts < self.max_retries:
                                await asyncio.sleep(self.retry_delay * attempts)
            except aiohttp.ClientError as e:
                logger.error(f"Telegram API请求异常 (尝试 {attempts+1}/{self.max_retries}): {str(e)}")
                attempts += 1
                if attempts < self.max_retries:
                    await asyncio.sleep(self.retry_delay * attempts)
            except Exception as e:
                logger.error(f"发送Telegram消息异常: {str(e)}")
                logger.error(traceback.format_exc())
                return False
                
        logger.error(f"发送Telegram消息达到最大重试次数")
        return False
        
    async def send_error_message(self, error_title: str, error_details: str = None) -> bool:
        """发送错误消息到Telegram"""
        message = f"❌ <b>{error_title}</b>"
        if error_details:
            message += f"\n<pre>{error_details}</pre>"
        return await self.send_message(message)
    
    async def send_success_message(self, title: str, details: str = None) -> bool:
        """发送成功消息到Telegram"""
        message = f"✅ <b>{title}</b>"
        if details:
            message += f"\n{details}"
        return await self.send_message(message)
    
    async def send_warning_message(self, title: str, details: str = None) -> bool:
        """发送警告消息到Telegram"""
        message = f"⚠️ <b>{title}</b>"
        if details:
            message += f"\n{details}"
        return await self.send_message(message)
        
    async def send_trade_notification(self, action: str, position: dict, price: float, reason: str = None) -> bool:
        """发送交易通知到Telegram"""
        symbol = position.get("symbol", "未知")
        quantity = position.get("quantity", "0")
        entry_price = position.get("entryPrice", "0")
        
        if action == "开仓":
            icon = "🔼" if quantity and float(quantity) > 0 else "🔽"
            message = (
                f"{icon} <b>开仓 {symbol}</b>\n"
                f"📊 价格: {price} USDC\n"
                f"💰 数量: {quantity}\n"
            )
            if reason:
                message += f"📝 原因: {reason}\n"
                
        elif action == "平仓":
            pnl = 0
            if entry_price and price:
                entry_price_float = float(entry_price)
                if quantity and float(quantity) > 0:  # 多仓
                    pnl = (price - entry_price_float) / entry_price_float * 100
                else:  # 空仓
                    pnl = (entry_price_float - price) / entry_price_float * 100
                    
            pnl_icon = "📈" if pnl >= 0 else "📉"
            message = (
                f"✅ <b>平仓 {symbol}</b>\n"
                f"📊 价格: {price} USDC\n"
                f"💰 数量: {abs(float(quantity)) if quantity else 0}\n"
                f"📈 入场价: {entry_price} USDC\n"
                f"📉 出场价: {price} USDC\n"
                f"{pnl_icon} 盈亏: {pnl:.2f}%\n"
            )
            if reason:
                message += f"📝 原因: {reason}\n"
                
        else:
            message = f"🔄 <b>{action} {symbol}</b>\n"
            if reason:
                message += f"📝 原因: {reason}\n"
                
        return await self.send_message(message)

class TradingBot:
    def __init__(self, config: dict):
        self.config = config
        self.backpack_api = BackpackAPI(
            api_key=config["backpack"]["api_key"],
            api_secret=config["backpack"]["api_secret"],
            base_url=config["backpack"]["base_url"],
            ws_url=config["backpack"]["ws_url"],
            logger=logger
        )
        self.telegram = TelegramBot(
            token=config["telegram"]["token"],
            chat_id=config["telegram"]["chat_id"]
        )
        self.symbol = config["trading"]["symbol"]
        self.leverage = config["trading"]["leverage"]
        self.profit_percentage = config["trading"]["profit_percentage"]
        self.stop_loss_percentage = config["trading"]["stop_loss_percentage"]
        self.cooldown_minutes = config["trading"]["cooldown_minutes"]
        self.is_running = False
        self.task = None
        self.entry_price = 0
        self.position_size = 0
        self.in_cooldown = False
        self.cooldown_until = 0
        self.check_interval = 10  # 默认检查间隔(秒)
        self.last_price_check = 0
        self.last_position_check = 0
        self.last_balance_check = 0
        self.health_check_interval = 300  # 健康检查间隔(秒)
        self.last_health_check = time.time()

    async def initialize(self):
        """初始化交易机器人"""
        try:
            await self.backpack_api.initialize()
            logger.info("交易机器人已初始化")
            await self.telegram.send_message("🤖 交易机器人已启动")
            return True
        except Exception as e:
            logger.error(f"初始化交易机器人异常: {str(e)}")
            logger.error(traceback.format_exc())
            await self.telegram.send_error_message("交易机器人初始化失败", str(e))
            return False

    async def stop(self):
        """停止交易机器人"""
        self.is_running = False
        if self.task:
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass
        await self.backpack_api.close()
        await self.telegram.send_message("🛑 交易机器人已停止")
        logger.info("交易机器人已停止")

    async def health_check(self) -> bool:
        """健康检查，确保API连接正常"""
        try:
            # 检查账户余额
            balances = await self.backpack_api.get_balances()
            if not balances and not isinstance(balances, list):
                logger.warning("健康检查: 获取余额失败")
                return False
                
            # 检查市场价格
            price = await self.backpack_api.get_price(self.symbol)
            if price <= 0:
                logger.warning(f"健康检查: 获取{self.symbol}价格失败")
                return False
                
            # 检查持仓信息
            positions = await self.backpack_api.get_positions()
            if not isinstance(positions, list):
                logger.warning("健康检查: 获取持仓信息失败")
                return False
                
            logger.info("健康检查: API连接正常")
            return True
            
        except Exception as e:
            logger.error(f"健康检查异常: {str(e)}")
            logger.error(traceback.format_exc())
            return False

    async def get_usable_balance(self) -> float:
        """获取可用的USDC余额"""
        try:
            current_time = time.time()
            # 限制API请求频率
            if current_time - self.last_balance_check < 10:  # 至少10秒检查一次
                return 0
                
            self.last_balance_check = current_time
            balances = await self.backpack_api.get_balances()
            for balance in balances:
                if balance["asset"] == "USDC":
                    return float(balance["available"])
            return 0
        except Exception as e:
            logger.error(f"获取余额异常: {str(e)}")
            logger.error(traceback.format_exc())
            return 0

    async def calculate_position_size(self, balance: float, price: float) -> float:
        """计算开仓数量，使用杠杆"""
        try:
            if balance <= 0 or price <= 0:
                return 0
                
            # 使用全部余额的杠杆倍数
            usdc_value = balance * self.leverage
            # 转换为ETH数量
            eth_amount = usdc_value / price
            # 保留6位小数
            return round(eth_amount, 6)
        except Exception as e:
            logger.error(f"计算仓位大小异常: {str(e)}")
            logger.error(traceback.format_exc())
            return 0

    async def open_long_position(self) -> bool:
        """开多仓"""
        try:
            # 获取余额和价格
            balance = await self.get_usable_balance()
            if balance <= 0:
                await self.telegram.send_message("❌ 账户余额不足，无法开仓")
                return False

            price = await self.backpack_api.get_price(self.symbol)
            if price <= 0:
                await self.telegram.send_message(f"❌ 获取{self.symbol}价格失败")
                return False

            # 计算仓位大小
            quantity = await self.calculate_position_size(balance, price)
            if quantity <= 0.000001:  # 添加最小交易量检查
                await self.telegram.send_message("❌ 计算开仓数量过小，无法开仓")
                return False

            # 开仓
            logger.info(f"准备开多仓: {self.symbol}, 数量: {quantity}, 价格: {price}")
            order_result = await self.backpack_api.place_order(
                symbol=self.symbol,
                side="BUY",
                quantity=quantity,
                order_type="MARKET"
            )

            if "orderId" in order_result:
                self.entry_price = price
                self.position_size = quantity
                
                # 构建通知消息
                message = (
                    f"✅ 开多成功\n"
                    f"📊 {self.symbol} @ {price} USDC\n"
                    f"💰 数量: {quantity}\n"
                    f"💵 使用余额: {balance} USDC\n"
                    f"🔼 止盈: {price * (1 + self.profit_percentage/100):.2f} USDC (+{self.profit_percentage}%)\n"
                    f"🔽 止损: {price * (1 - self.stop_loss_percentage/100):.2f} USDC (-{self.stop_loss_percentage}%)"
                )
                await self.telegram.send_message(message)
                logger.info(f"开多成功: {self.symbol}, 价格: {price}, 数量: {quantity}")
                return True
            else:
                error_msg = order_result.get("error", "未知错误")
                await self.telegram.send_error_message(f"开仓失败", error_msg)
                logger.error(f"开仓失败: {error_msg}")
                return False
                
        except Exception as e:
            logger.error(f"开仓异常: {str(e)}")
            logger.error(traceback.format_exc())
            await self.telegram.send_error_message("开仓过程中发生异常", str(e))
            return False

    async def close_position(self, reason: str) -> bool:
        """平仓"""
        try:
            position = await self.backpack_api.get_position(self.symbol)
            if not position or float(position.get("quantity", 0)) == 0:
                await self.telegram.send_message(f"ℹ️ 没有持仓，无需平仓")
                return False

            quantity = abs(float(position["quantity"]))
            
            # 获取当前价格
            current_price = await self.backpack_api.get_price(self.symbol)
            if current_price <= 0:
                await self.telegram.send_error_message(f"平仓失败", f"获取{self.symbol}价格失败")
                return False
                
            # 存储入场价格
            entry_price = float(position.get("entryPrice", self.entry_price))
            if entry_price <= 0:
                entry_price = self.entry_price
            
            # 平仓
            logger.info(f"准备平仓: {self.symbol}, 数量: {quantity}, 原因: {reason}")
            order_result = await self.backpack_api.place_order(
                symbol=self.symbol,
                side="SELL",  # 卖出平多
                quantity=quantity,
                order_type="MARKET",
                reduce_only=True
            )

            if "orderId" in order_result:
                # 计算盈亏
                profit_loss = (current_price - entry_price) / entry_price * 100 if entry_price > 0 else 0
                
                # 构建通知消息
                message = (
                    f"✅ 平仓成功 ({reason})\n"
                    f"📊 {self.symbol} @ {current_price} USDC\n"
                    f"💰 数量: {quantity}\n"
                    f"📈 入场价: {entry_price} USDC\n"
                    f"📉 出场价: {current_price} USDC\n"
                    f"💹 盈亏: {profit_loss:.2f}%"
                )
                await self.telegram.send_message(message)
                logger.info(f"平仓成功: {self.symbol}, 价格: {current_price}, 盈亏: {profit_loss:.2f}%")
                
                # 如果是止损触发，进入冷静期
                if reason == "止损":
                    self.in_cooldown = True
                    self.cooldown_until = time.time() + self.cooldown_minutes * 60
                    cooldown_end_time = datetime.datetime.fromtimestamp(self.cooldown_until).strftime('%Y-%m-%d %H:%M:%S')
                    
                    await self.telegram.send_message(
                        f"⏳ 进入冷静期，{self.cooldown_minutes}分钟内不开仓\n"
                        f"⏱️ 冷静期结束时间: {cooldown_end_time}"
                    )
                    logger.info(f"进入冷静期，结束时间: {cooldown_end_time}")
                
                # 重置仓位信息
                self.entry_price = 0
                self.position_size = 0
                return True
            else:
                error_msg = order_result.get("error", "未知错误")
                await self.telegram.send_error_message(f"平仓失败", error_msg)
                logger.error(f"平仓失败: {error_msg}")
                return False
                
        except Exception as e:
            logger.error(f"平仓异常: {str(e)}")
            logger.error(traceback.format_exc())
            await self.telegram.send_error_message("平仓过程中发生异常", str(e))
            return False

    async def trading_loop(self):
        """交易主循环"""
        if not await self.initialize():
            logger.error("交易机器人初始化失败，无法启动交易循环")
            return
            
        self.is_running = True
        
        # 发送启动通知
        startup_message = (
            f"🔄 交易机器人运行中\n"
            f"📈 交易对: {self.symbol}\n"
            f"⚙️ 杠杆倍数: {self.leverage}x\n"
            f"🔼 止盈比例: {self.profit_percentage}%\n"
            f"🔽 止损比例: {self.stop_loss_percentage}%\n"
            f"⏱️ 冷静期: {self.cooldown_minutes}分钟"
        )
        await self.telegram.send_message(startup_message)
        
        has_position = False
        consecutive_errors = 0
        
        while self.is_running:
            try:
                current_time = time.time()
                
                # 定期健康检查
                if current_time - self.last_health_check >= self.health_check_interval:
                    health_status = await self.health_check()
                    if not health_status:
                        logger.warning("健康检查失败，但将继续运行")
                        consecutive_errors += 1
                        
                        if consecutive_errors >= 3:
                            await self.telegram.send_warning_message(
                                "API连接问题", 
                                "连续3次健康检查失败，但机器人将继续尝试运行。请检查API状态和网络连接。"
                            )
                            # 增加检查间隔，避免频繁失败通知
                            self.check_interval = min(60, self.check_interval * 2)
                    else:
                        consecutive_errors = 0
                        # 恢复正常检查间隔
                        self.check_interval = 10
                        
                    self.last_health_check = current_time
                
                # 检查是否在冷静期
                if self.in_cooldown:
                    if current_time >= self.cooldown_until:
                        self.in_cooldown = False
                        await self.telegram.send_message("✅ 冷静期结束，恢复交易")
                        logger.info("冷静期结束，恢复交易")
                    else:
                        remaining_minutes = int((self.cooldown_until - current_time) / 60)
                        if remaining_minutes % 5 == 0:  # 每5分钟记录一次
                            logger.info(f"冷静期中，剩余{remaining_minutes}分钟")
                        await asyncio.sleep(60)  # 每分钟检查一次
                        continue
                
                # 检查是否有持仓
                if current_time - self.last_position_check >= 30:  # 每30秒检查一次持仓
                    position = await self.backpack_api.get_position(self.symbol)
                    has_position = position and float(position.get("quantity", 0)) > 0
                    self.last_position_check = current_time
                    
                    # 如果API返回了持仓信息，更新本地记录
                    if has_position:
                        self.entry_price = float(position.get("entryPrice", self.entry_price))
                        self.position_size = float(position.get("quantity", self.position_size))
                
                if not has_position:
                    # 没有持仓，且不在冷静期，开仓
                    if not self.in_cooldown:
                        logger.info("没有持仓，准备开仓...")
                        success = await self.open_long_position()
                        if success:
                            has_position = True
                        await asyncio.sleep(5)  # 等待订单成交
                else:
                    # 有持仓，检查止盈止损
                    if current_time - self.last_price_check >= self.check_interval:
                        current_price = await self.backpack_api.get_price(self.symbol)
                        self.last_price_check = current_time
                        
                        if current_price <= 0:
                            logger.warning(f"获取{self.symbol}价格失败，跳过本次检查")
                            continue
                        
                        # 确保有有效的入场价
                        if self.entry_price <= 0:
                            position = await self.backpack_api.get_position(self.symbol)
                            if position and "entryPrice" in position:
                                self.entry_price = float(position["entryPrice"])
                            else:
                                logger.warning("无法获取有效的入场价格，跳过本次检查")
                                continue
                        
                        # 计算盈亏比例
                        profit_percentage = (current_price - self.entry_price) / self.entry_price * 100
                        
                        # 日志记录当前状态
                        logger.info(f"当前持仓: {self.symbol}, 入场价: {self.entry_price}, 当前价: {current_price}, 盈亏: {profit_percentage:.2f}%")
                        
                        # 检查止盈
                        if profit_percentage >= self.profit_percentage:
                            logger.info(f"达到止盈条件 (+{profit_percentage:.2f}%)，准备平仓...")
                            await self.close_position("止盈")
                            has_position = False
                            await asyncio.sleep(5)  # 等待订单成交
                        
                        # 检查止损
                        elif profit_percentage <= -self.stop_loss_percentage:
                            logger.info(f"达到止损条件 ({profit_percentage:.2f}%)，准备平仓...")
                            await self.close_position("止损")
                            has_position = False
                            await asyncio.sleep(5)  # 等待订单成交
                
                # 等待下一次检查
                await asyncio.sleep(self.check_interval)
                
            except Exception as e:
                logger.error(f"交易循环异常: {str(e)}")
                logger.error(traceback.format_exc())
                
                consecutive_errors += 1
                if consecutive_errors >= 3:
                    await self.telegram.send_error_message(
                        "交易循环异常", 
                        f"连续{consecutive_errors}次出现异常: {str(e)}\n机器人将继续尝试运行。"
                    )
                    # 减少通知频率
                    consecutive_errors = 0
                
                # 发生异常后增加等待时间
                await asyncio.sleep(30)
        
        logger.info("交易循环已停止")

    def start(self) -> bool:
        """启动交易机器人"""
        if self.task and not self.task.done():
            logger.warning("交易机器人已经在运行")
            return False
        
        self.task = asyncio.create_task(self.trading_loop())
        return True

class App:
    def __init__(self):
        self.config = self.load_config()
        self.trading_bot = None
        self.version = "1.2.0"  # 版本号
        
    def load_config(self) -> dict:
        """加载配置文件"""
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r") as f:
                    config = json.load(f)
                    logger.info("配置文件加载成功")
                    return config
            except json.JSONDecodeError as e:
                logger.error(f"配置文件JSON格式错误: {str(e)}")
                logger.error("使用默认配置")
                return DEFAULT_CONFIG.copy()
            except Exception as e:
                logger.error(f"配置文件加载异常: {str(e)}")
                logger.error("使用默认配置")
                return DEFAULT_CONFIG.copy()
        else:
            logger.info("配置文件不存在，创建默认配置")
            return DEFAULT_CONFIG.copy()
            
    def save_config(self) -> bool:
        """保存配置到文件"""
        try:
            # 确保配置目录存在
            os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
            
            with open(CONFIG_FILE, "w") as f:
                json.dump(self.config, f, indent=4)
            logger.info("配置文件保存成功")
            return True
        except Exception as e:
            logger.error(f"保存配置文件异常: {str(e)}")
            logger.error(traceback.format_exc())
            return False
    
    def validate_config(self) -> Tuple[bool, List[str]]:
        """验证配置文件，返回(是否有效, 错误列表)"""
        errors = []
        
        # 检查Telegram配置
        if not self.config.get('telegram', {}).get('token'):
            errors.append("Telegram token未配置")
        
        if not self.config.get('telegram', {}).get('chat_id'):
            errors.append("Telegram chat_id未配置")
        
        # 检查Backpack API配置
        if not self.config.get('backpack', {}).get('api_key'):
            errors.append("Backpack API Key未配置")
            
        if not self.config.get('backpack', {}).get('api_secret'):
            errors.append("Backpack API Secret未配置")
            
        # 检查交易配置
        trading_config = self.config.get('trading', {})
        
        if not trading_config.get('symbol'):
            errors.append("交易对未配置")
            
        # 检查数值参数
        try:
            leverage = float(trading_config.get('leverage', 0))
            if leverage <= 0:
                errors.append("杠杆倍数必须大于0")
                
            profit_percentage = float(trading_config.get('profit_percentage', 0))
            if profit_percentage <= 0:
                errors.append("止盈比例必须大于0")
                
            stop_loss_percentage = float(trading_config.get('stop_loss_percentage', 0))
            if stop_loss_percentage <= 0:
                errors.append("止损比例必须大于0")
                
            cooldown_minutes = float(trading_config.get('cooldown_minutes', 0))
            if cooldown_minutes < 0:
                errors.append("冷静期必须大于等于0")
        except (ValueError, TypeError):
            errors.append("交易参数格式错误，请确保是有效的数字")
            
        return len(errors) == 0, errors
    
    def configure_telegram(self):
        """配置Telegram设置"""
        print("\n==== Telegram配置 ====")
        print(f"当前Token: {self.config['telegram']['token']} (固定不可修改)")
        
        while True:
            chat_id = input(f"请输入您的Telegram Chat ID [{self.config['telegram']['chat_id']}]: ")
            if not chat_id and self.config['telegram']['chat_id']:
                break
            
            if not chat_id:
                print("错误: 必须提供Chat ID")
                continue
                
            # 验证Chat ID格式
            if re.match(r'^-?\d+$', chat_id):
                self.config['telegram']['chat_id'] = chat_id
                self.save_config()
                print("✅ Telegram配置已保存")
                break
            else:
                print("错误: Chat ID必须是数字")
    
    def configure_backpack(self):
        """配置Backpack API设置"""
        print("\n==== Backpack API配置 ====")
        api_key = input(f"请输入API Key [{self.config['backpack']['api_key']}]: ")
        if api_key:
            self.config['backpack']['api_key'] = api_key
            
        api_secret = input(f"请输入API Secret [{self.config['backpack']['api_secret']}]: ")
        if api_secret:
            self.config['backpack']['api_secret'] = api_secret
            
        self.save_config()
        print("✅ Backpack API配置已保存")
        
    def configure_trading(self):
        """配置交易参数"""
        print("\n==== 交易参数配置 ====")
        
        # 交易对配置
        symbol = input(f"请输入交易对 [{self.config['trading']['symbol']}]: ")
        if symbol:
            self.config['trading']['symbol'] = symbol.upper()
            
        # 杠杆倍数
        while True:
            leverage_str = input(f"请输入杠杆倍数 (1-125) [{self.config['trading']['leverage']}]: ")
            if not leverage_str:
                break
                
            try:
                leverage = int(leverage_str)
                if 1 <= leverage <= 125:
                    self.config['trading']['leverage'] = leverage
                    break
                else:
                    print("错误: 杠杆倍数必须在1-125之间")
            except ValueError:
                print("错误: 请输入有效的数字")
                
        # 止盈比例
        while True:
            profit_str = input(f"请输入止盈比例 (%) [{self.config['trading']['profit_percentage']}]: ")
            if not profit_str:
                break
                
            try:
                profit = float(profit_str)
                if profit > 0:
                    self.config['trading']['profit_percentage'] = profit
                    break
                else:
                    print("错误: 止盈比例必须大于0")
            except ValueError:
                print("错误: 请输入有效的数字")
                
        # 止损比例
        while True:
            stop_loss_str = input(f"请输入止损比例 (%) [{self.config['trading']['stop_loss_percentage']}]: ")
            if not stop_loss_str:
                break
                
            try:
                stop_loss = float(stop_loss_str)
                if stop_loss > 0:
                    self.config['trading']['stop_loss_percentage'] = stop_loss
                    break
                else:
                    print("错误: 止损比例必须大于0")
            except ValueError:
                print("错误: 请输入有效的数字")
                
        # 冷静期
        while True:
            cooldown_str = input(f"请输入冷静期 (分钟) [{self.config['trading']['cooldown_minutes']}]: ")
            if not cooldown_str:
                break
                
            try:
                cooldown = int(cooldown_str)
                if cooldown >= 0:
                    self.config['trading']['cooldown_minutes'] = cooldown
                    break
                else:
                    print("错误: 冷静期必须大于等于0")
            except ValueError:
                print("错误: 请输入有效的数字")
                
        self.save_config()
        print("✅ 交易参数配置已保存")
    
    def start_bot(self):
        """启动交易机器人"""
        # 验证配置
        is_valid, errors = self.validate_config()
        if not is_valid:
            print("❌ 错误: 配置无效")
            for error in errors:
                print(f"  - {error}")
            return
            
        # 检查机器人是否已在运行
        result = subprocess.run(["pm2", "list"], capture_output=True, text=True)
        if "backpack_bot" in result.stdout and "online" in result.stdout:
            print("❌ 错误: 交易机器人已经在运行中")
            print("📊 使用 'pm2 logs backpack_bot' 查看日志")
            print("⚠️ 如需重启，请先使用 'pm2 stop backpack_bot' 停止后再启动")
            return
            
        # 使用PM2启动机器人
        try:
            result = subprocess.run(
                ["pm2", "start", os.path.join(CONFIG_DIR, "backpack_bot.py"), 
                 "--name", "backpack_bot", 
                 "--interpreter", "python3", 
                 "--", "--run"],
                capture_output=True, 
                text=True,
                check=True
            )
            
            print("✅ 交易机器人已成功启动")
            print("📊 使用 'pm2 logs backpack_bot' 查看日志")
            print("⚠️ 使用 'pm2 stop backpack_bot' 停止机器人")
        except subprocess.CalledProcessError as e:
            print(f"❌ 启动失败: {e.stderr}")
        except Exception as e:
            print(f"❌ 启动异常: {str(e)}")
    
    def stop_bot(self):
        """停止交易机器人"""
        try:
            result = subprocess.run(["pm2", "stop", "backpack_bot"], capture_output=True, text=True)
            
            if result.returncode == 0:
                print("✅ 交易机器人已停止")
            else:
                print(f"❌ 停止失败: {result.stderr}")
        except Exception as e:
            print(f"❌ 停止异常: {str(e)}")
    
    def delete_bot(self):
        """删除交易机器人进程"""
        try:
            result = subprocess.run(["pm2", "delete", "backpack_bot"], capture_output=True, text=True)
            
            if result.returncode == 0:
                print("✅ 交易机器人已删除")
            else:
                print(f"❌ 删除失败: {result.stderr}")
        except Exception as e:
            print(f"❌ 删除异常: {str(e)}")
            
    def check_bot_status(self):
        """检查机器人状态"""
        try:
            result = subprocess.run(["pm2", "list"], capture_output=True, text=True)
            
            if "backpack_bot" in result.stdout:
                if "online" in result.stdout:
                    print("✅ 交易机器人状态: 运行中")
                elif "stopped" in result.stdout:
                    print("⚠️ 交易机器人状态: 已停止")
                else:
                    print("⚠️ 交易机器人状态: 异常")
            else:
                print("❌ 交易机器人未启动")
        except Exception as e:
            print(f"❌ 检查状态异常: {str(e)}")
    
    def test_api_connection(self):
        """测试API连接"""
        print("\n==== 测试API连接 ====")
        
        # 验证配置
        is_valid, errors = self.validate_config()
        if not is_valid:
            print("❌ 错误: 配置无效")
            for error in errors:
                print(f"  - {error}")
            return
            
        async def run_test():
            api = BackpackAPI(
                api_key=self.config["backpack"]["api_key"],
                api_secret=self.config["backpack"]["api_secret"],
                base_url=self.config["backpack"]["base_url"],
                ws_url=self.config["backpack"]["ws_url"],
                logger=logger
            )
            
            try:
                await api.initialize()
                print("✅ API初始化成功")
                
                # 测试获取余额
                print("📊 正在获取账户余额...")
                balances = await api.get_balances()
                if isinstance(balances, list):
                    print(f"✅ 账户余额获取成功，共 {len(balances)} 个资产")
                    # 显示USDC余额
                    for balance in balances:
                        if balance["asset"] == "USDC":
                            print(f"💰 USDC余额: {balance['available']} (可用), {balance['total']} (总计)")
                else:
                    print(f"❌ 获取余额失败: {balances}")
                    return
                
                # 测试获取价格
                symbol = self.config["trading"]["symbol"]
                print(f"📈 正在获取 {symbol} 价格...")
                price = await api.get_price(symbol)
                if price > 0:
                    print(f"✅ 当前价格: {price} USDC")
                else:
                    print(f"❌ 获取价格失败")
                    return
                    
                # 测试获取持仓
                print("🔍 正在获取持仓信息...")
                positions = await api.get_positions()
                if isinstance(positions, list):
                    print(f"✅ 持仓信息获取成功，共 {len(positions)} 个持仓")
                    # 显示当前交易对的持仓
                    current_position = None
                    for position in positions:
                        if position["symbol"] == symbol and float(position["quantity"]) != 0:
                            current_position = position
                            break
                            
                    if current_position:
                        quantity = float(current_position["quantity"])
                        entry_price = float(current_position["entryPrice"])
                        pnl = float(current_position["unrealizedPnl"])
                        
                        position_type = "多" if quantity > 0 else "空"
                        print(f"📌 当前持有 {symbol} {position_type}单:")
                        print(f"   数量: {abs(quantity)}")
                        print(f"   入场价: {entry_price} USDC")
                        print(f"   未实现盈亏: {pnl} USDC")
                    else:
                        print(f"📌 当前没有 {symbol} 持仓")
                else:
                    print(f"❌ 获取持仓失败: {positions}")
                    return
                
                # 测试Telegram
                print("💬 正在测试Telegram通知...")
                telegram = TelegramBot(
                    token=self.config["telegram"]["token"],
                    chat_id=self.config["telegram"]["chat_id"]
                )
                
                success = await telegram.send_message(
                    f"🤖 Backpack交易机器人连接测试\n"
                    f"⏱️ 时间: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
                    f"✅ API连接正常\n"
                    f"💰 USDC余额: {next((b['available'] for b in balances if b['asset'] == 'USDC'), '0')} USDC\n"
                    f"📈 {symbol} 当前价格: {price} USDC"
                )
                
                if success:
                    print("✅ Telegram通知发送成功，请检查您的Telegram")
                else:
                    print("❌ Telegram通知发送失败，请检查您的Chat ID和网络")
                
            except Exception as e:
                print(f"❌ 测试过程中发生异常: {str(e)}")
                logger.error(f"API测试异常: {str(e)}")
                logger.error(traceback.format_exc())
            finally:
                await api.close()
        
        # 运行异步测试
        asyncio.run(run_test())
    
    def show_menu(self):
        """显示主菜单"""
        while True:
            print("\n" + "=" * 50)
            print(f"     Backpack 交易机器人 v{self.version}      ")
            print("=" * 50)
            print("1. 配置Telegram")
            print("2. 配置Backpack API")
            print("3. 配置交易参数")
            print("4. 测试API连接")
            print("5. 启动交易机器人")
            print("6. 停止交易机器人")
            print("7. 查看机器人状态")
            print("8. 删除交易机器人")
            print("9. 退出")
            
            choice = input("\n请选择操作: ")
            
            if choice == "1":
                self.configure_telegram()
            elif choice == "2":
                self.configure_backpack()
            elif choice == "3":
                self.configure_trading()
            elif choice == "4":
                self.test_api_connection()
            elif choice == "5":
                self.start_bot()
            elif choice == "6":
                self.stop_bot()
            elif choice == "7":
                self.check_bot_status()
            elif choice == "8":
                self.delete_bot()
            elif choice == "9":
                print("退出程序")
                break
            else:
                print("无效选择，请重试")

def run_trading_bot():
    """直接运行交易机器人（用于PM2）"""
    loop = asyncio.get_event_loop()
    config = {}
    
    try:
        with open(CONFIG_FILE, "r") as f:
            config = json.load(f)
    except Exception as e:
        logger.error(f"无法加载配置文件: {str(e)}")
        logger.error(traceback.format_exc())
        return
    
    bot = TradingBot(config)
    
    async def shutdown(signal, loop):
        """优雅关闭"""
        logger.info(f"收到信号 {signal.name}...")
        await bot.stop()
        tasks = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
        [task.cancel() for task in tasks]
        await asyncio.gather(*tasks, return_exceptions=True)
        loop.stop()
    
    # 注册信号处理
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, lambda s=sig: asyncio.create_task(shutdown(s, loop)))
    
    try:
        loop.create_task(bot.trading_loop())
        loop.run_forever()
    finally:
        loop.close()
        logger.info("交易机器人已关闭")

def parse_args():
    """解析命令行参数"""
    if len(sys.argv) <= 1:
        return {"mode": "menu"}
        
    if sys.argv[1] == "--run":
        return {"mode": "run"}
        
    return {"mode": "menu"}

if __name__ == "__main__":
    args = parse_args()
    
    if args["mode"] == "run":
        # 直接运行交易机器人
        try:
            run_trading_bot()
        except Exception as e:
            logger.error(f"运行交易机器人时发生异常: {str(e)}")
            logger.error(traceback.format_exc())
            sys.exit(1)
    else:
        # 运行配置菜单
        try:
            app = App()
            app.show_menu()
        except KeyboardInterrupt:
            print("\n程序已被用户中断")
        except Exception as e:
            logger.error(f"运行配置菜单时发生异常: {str(e)}")
            logger.error(traceback.format_exc())
            print(f"\n❌ 程序异常: {str(e)}")
            sys.exit(1)
