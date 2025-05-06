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
        response = await self._make_request("GET", "/api/v1/capital")
        if "error" in response:
            return []
        return response

    async def get_price(self, symbol: str) -> float:
        """获取当前价格"""
        try:
            response = await self._make_request("GET", "/api/v1/ticker/price", {"symbol": symbol})
            if "price" in response:
                return float(response["price"])
            return 0
        except Exception as e:
            self.logger.error(f"获取价格错误: {e}")
            return 0

    async def get_position(self, symbol: str) -> Optional[Dict]:
        """获取特定交易对的仓位"""
        positions = await self.get_positions()
        for position in positions:
            if position["symbol"] == symbol and float(position["quantity"]) != 0:
                return position
        return None

    async def get_positions(self) -> List[Dict]:
        """获取所有持仓"""
        response = await self._make_request("GET", "/api/v1/positions")
        if isinstance(response, list):
            return response
        return []

    async def place_order(self, symbol: str, side: str, quantity: float, 
                         order_type: str = "MARKET", price: float = None,
                         post_only: bool = False, reduce_only: bool = False) -> Dict:
        """下单"""
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

        response = await self._make_request("POST", "/api/v1/order", None, order_data)
        return response

    async def cancel_order(self, symbol: str, order_id: str) -> Dict:
        """取消特定订单"""
        params = {
            "symbol": symbol,
            "orderId": order_id
        }
        response = await self._make_request("DELETE", "/api/v1/order", params)
        return response

    async def cancel_all_orders(self, symbol: str = None) -> Dict:
        """取消所有订单，可选指定交易对"""
        params = {}
        if symbol:
            params["symbol"] = symbol
        response = await self._make_request("DELETE", "/api/v1/orders", params)
        return response

    async def start_ws_price_stream(self):
        """启动WebSocket价格数据流"""
        pass  # 简化版本，我们将使用REST API获取价格

class TelegramBot:
    def __init__(self, token: str, chat_id: str):
        self.token = token
        self.chat_id = chat_id
        self.base_url = f"https://api.telegram.org/bot{token}"

    async def send_message(self, text: str) -> bool:
        """发送消息到Telegram"""
        try:
            if not self.chat_id:
                logger.warning("Telegram未配置chat_id，无法发送消息")
                return False
                
            url = f"{self.base_url}/sendMessage"
            params = {
                "chat_id": self.chat_id,
                "text": text,
                "parse_mode": "HTML"
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(url, params=params) as response:
                    if response.status == 200:
                        return True
                    else:
                        response_text = await response.text()
                        logger.error(f"发送Telegram消息失败: {response.status} - {response_text}")
                        return False
        except Exception as e:
            logger.error(f"发送Telegram消息异常: {e}")
            return False

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

    async def initialize(self):
        """初始化交易机器人"""
        await self.backpack_api.initialize()
        await self.telegram.send_message("🤖 交易机器人已启动")

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

    async def get_usable_balance(self) -> float:
        """获取可用的USDC余额"""
        balances = await self.backpack_api.get_balances()
        for balance in balances:
            if balance["asset"] == "USDC":
                return float(balance["available"])
        return 0

    async def calculate_position_size(self, balance: float, price: float) -> float:
        """计算开仓数量，使用杠杆"""
        # 使用全部余额的杠杆倍数
        usdc_value = balance * self.leverage
        # 转换为ETH数量
        eth_amount = usdc_value / price
        # 保留6位小数
        return round(eth_amount, 6)

    async def open_long_position(self):
        """开多仓"""
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
        if quantity <= 0:
            await self.telegram.send_message("❌ 计算开仓数量失败，数量为0")
            return False

        # 开仓
        order_result = await self.backpack_api.place_order(
            symbol=self.symbol,
            side="BUY",
            quantity=quantity,
            order_type="MARKET"
        )

        if "orderId" in order_result:
            self.entry_price = price
            self.position_size = quantity
            await self.telegram.send_message(
                f"✅ 开多成功\n"
                f"📊 {self.symbol} @ {price} USDC\n"
                f"💰 数量: {quantity}\n"
                f"💵 使用余额: {balance} USDC\n"
                f"🔼 止盈: {price * (1 + self.profit_percentage/100)} USDC (+{self.profit_percentage}%)\n"
                f"🔽 止损: {price * (1 - self.stop_loss_percentage/100)} USDC (-{self.stop_loss_percentage}%)"
            )
            return True
        else:
            error_msg = order_result.get("error", "未知错误")
            await self.telegram.send_message(f"❌ 开仓失败: {error_msg}")
            return False

    async def close_position(self, reason: str):
        """平仓"""
        position = await self.backpack_api.get_position(self.symbol)
        if not position or float(position["quantity"]) == 0:
            await self.telegram.send_message(f"ℹ️ 没有持仓，无需平仓")
            return False

        quantity = abs(float(position["quantity"]))
        
        # 获取当前价格
        current_price = await self.backpack_api.get_price(self.symbol)
        
        # 平仓
        order_result = await self.backpack_api.place_order(
            symbol=self.symbol,
            side="SELL",  # 卖出平多
            quantity=quantity,
            order_type="MARKET",
            reduce_only=True
        )

        if "orderId" in order_result:
            profit_loss = (current_price - self.entry_price) / self.entry_price * 100
            await self.telegram.send_message(
                f"✅ 平仓成功 ({reason})\n"
                f"📊 {self.symbol} @ {current_price} USDC\n"
                f"💰 数量: {quantity}\n"
                f"📈 入场价: {self.entry_price} USDC\n"
                f"📉 出场价: {current_price} USDC\n"
                f"💹 盈亏: {profit_loss:.2f}%"
            )
            
            # 如果是止损触发，进入冷静期
            if reason == "止损":
                self.in_cooldown = True
                self.cooldown_until = time.time() + self.cooldown_minutes * 60
                await self.telegram.send_message(
                    f"⏳ 进入冷静期，{self.cooldown_minutes}分钟内不开仓\n"
                    f"⏱️ 冷静期结束时间: {datetime.datetime.fromtimestamp(self.cooldown_until).strftime('%Y-%m-%d %H:%M:%S')}"
                )
            
            # 重置仓位信息
            self.entry_price = 0
            self.position_size = 0
            return True
        else:
            error_msg = order_result.get("error", "未知错误")
            await self.telegram.send_message(f"❌ 平仓失败: {error_msg}")
            return False

    async def trading_loop(self):
        """交易主循环"""
        await self.initialize()
        self.is_running = True
        
        await self.telegram.send_message(
            f"🔄 交易机器人运行中\n"
            f"📈 交易对: {self.symbol}\n"
            f"⚙️ 杠杆倍数: {self.leverage}x\n"
            f"🔼 止盈比例: {self.profit_percentage}%\n"
            f"🔽 止损比例: {self.stop_loss_percentage}%\n"
            f"⏱️ 冷静期: {self.cooldown_minutes}分钟"
        )
        
        has_position = False
        
        while self.is_running:
            try:
                # 检查是否在冷静期
                if self.in_cooldown:
                    current_time = time.time()
                    if current_time >= self.cooldown_until:
                        self.in_cooldown = False
                        await self.telegram.send_message("✅ 冷静期结束，恢复交易")
                    else:
                        remaining_minutes = int((self.cooldown_until - current_time) / 60)
                        logger.info(f"冷静期中，剩余{remaining_minutes}分钟")
                        await asyncio.sleep(60)  # 每分钟检查一次
                        continue
                
                # 检查是否有持仓
                position = await self.backpack_api.get_position(self.symbol)
                has_position = position and float(position["quantity"]) > 0
                
                if not has_position:
                    # 没有持仓，开仓
                    logger.info("没有持仓，准备开仓...")
                    success = await self.open_long_position()
                    if success:
                        has_position = True
                    await asyncio.sleep(5)  # 等待订单成交
                else:
                    # 有持仓，检查止盈止损
                    current_price = await self.backpack_api.get_price(self.symbol)
                    entry_price = float(position["entryPrice"]) if "entryPrice" in position else self.entry_price
                    
                    # 如果没有记录入场价，更新它
                    if self.entry_price == 0:
                        self.entry_price = entry_price
                        self.position_size = float(position["quantity"])
                    
                    # 计算盈亏比例
                    profit_percentage = (current_price - entry_price) / entry_price * 100
                    
                    # 日志记录当前状态
                    logger.info(f"当前持仓: {self.symbol}, 入场价: {entry_price}, 当前价: {current_price}, 盈亏: {profit_percentage:.2f}%")
                    
                    # 检查止盈
                    if profit_percentage >= self.profit_percentage:
                        logger.info(f"达到止盈条件，准备平仓...")
                        await self.close_position("止盈")
                        has_position = False
                        await asyncio.sleep(5)  # 等待订单成交
                    
                    # 检查止损
                    elif profit_percentage <= -self.stop_loss_percentage:
                        logger.info(f"达到止损条件，准备平仓...")
                        await self.close_position("止损")
                        has_position = False
                        await asyncio.sleep(5)  # 等待订单成交
                
                # 每10秒检查一次
                await asyncio.sleep(10)
                
            except Exception as e:
                logger.error(f"交易循环异常: {e}")
                await self.telegram.send_message(f"⚠️ 交易异常: {str(e)}")
                await asyncio.sleep(30)  # 发生异常后等待30秒
        
        logger.info("交易循环已停止")

    def start(self):
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
        
    def load_config(self) -> dict:
        """加载配置文件"""
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r") as f:
                    return json.load(f)
            except:
                logger.error("配置文件损坏，使用默认配置")
                return DEFAULT_CONFIG.copy()
        else:
            return DEFAULT_CONFIG.copy()
            
    def save_config(self):
        """保存配置到文件"""
        with open(CONFIG_FILE, "w") as f:
            json.dump(self.config, f, indent=4)
    
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
        
    def start_bot(self):
        """启动交易机器人"""
        if not self.config['telegram']['chat_id']:
            print("❌ 错误: 请先配置Telegram Chat ID")
            return
            
        if not self.config['backpack']['api_key'] or not self.config['backpack']['api_secret']:
            print("❌ 错误: 请先配置Backpack API")
            return
        
        # 检查机器人是否已在运行
        result = subprocess.run(["pm2", "list"], capture_output=True, text=True)
        if "backpack_bot" in result.stdout:
            print("❌ 错误: 交易机器人已经在运行中")
            return
            
        # 使用PM2启动机器人
        result = subprocess.run(["pm2", "start", "backpack_bot.py", "--name", "backpack_bot", "--interpreter", "python3", "--", "--run"], capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✅ 交易机器人已成功启动")
            print("📊 使用 'pm2 logs backpack_bot' 查看日志")
        else:
            print(f"❌ 启动失败: {result.stderr}")
    
    def stop_bot(self):
        """停止交易机器人"""
        result = subprocess.run(["pm2", "stop", "backpack_bot"], capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✅ 交易机器人已停止")
        else:
            print(f"❌ 停止失败: {result.stderr}")
    
    def delete_bot(self):
        """删除交易机器人进程"""
        result = subprocess.run(["pm2", "delete", "backpack_bot"], capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✅ 交易机器人已删除")
        else:
            print(f"❌ 删除失败: {result.stderr}")
    
    def show_menu(self):
        """显示主菜单"""
        while True:
            print("\n==== Backpack 交易机器人 ====")
            print("1. 配置Telegram")
            print("2. 配置Backpack API")
            print("3. 启动交易机器人")
            print("4. 停止交易机器人")
            print("5. 删除交易机器人")
            print("6. 退出")
            
            choice = input("\n请选择操作: ")
            
            if choice == "1":
                self.configure_telegram()
            elif choice == "2":
                self.configure_backpack()
            elif choice == "3":
                self.start_bot()
            elif choice == "4":
                self.stop_bot()
            elif choice == "5":
                self.delete_bot()
            elif choice == "6":
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
    except:
        logger.error("无法加载配置文件")
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

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--run":
        # 直接运行交易机器人
        run_trading_bot()
    else:
        # 运行配置菜单
        app = App()
        app.show_menu()
