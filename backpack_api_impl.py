import asyncio
import hmac
import hashlib
import json
import logging
import time
from typing import Dict, List, Optional, Any, Callable, Union
import aiohttp
import websockets


class PriceCache:
    """价格缓存类，用于存储和获取最新价格"""
    def __init__(self):
        self._prices = {}
        
    def update(self, symbol: str, price: float):
        """更新特定交易对的价格"""
        self._prices[symbol] = price
        
    def get(self, symbol: str, default: float = 0) -> float:
        """获取特定交易对的价格"""
        return self._prices.get(symbol, default)
    
    def get_all(self) -> Dict[str, float]:
        """获取所有交易对的价格"""
        return self._prices.copy()


class BackpackAPI:
    """Backpack交易所API封装类"""
    def __init__(
        self, 
        api_key: str, 
        api_secret: str, 
        base_url: str = "https://api.backpack.exchange",
        ws_url: str = "wss://ws.backpack.exchange", 
        logger: Optional[logging.Logger] = None
    ):
        """初始化API客户端
        
        Args:
            api_key: API密钥
            api_secret: API密钥对应的秘密
            base_url: API基础URL，默认为正式网
            ws_url: WebSocket URL
            logger: 日志记录器，如果为None则创建新的
        """
        self.api_key = api_key
        self.api_secret = api_secret.encode()
        self.base_url = base_url
        self.ws_url = ws_url
        self.logger = logger or logging.getLogger("backpack_api")
        
        # 价格缓存
        self.prices = PriceCache()
        
        # WebSocket连接
        self.ws_connection = None
        self.ws_task = None
        self.price_callbacks = []
        
        # 会话
        self._session = None
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """获取或创建HTTP会话"""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session
    
    async def close(self):
        """关闭所有连接"""
        if self._session and not self._session.closed:
            await self._session.close()
        
        # 关闭WebSocket连接
        if self.ws_task and not self.ws_task.done():
            self.ws_task.cancel()
            try:
                await self.ws_task
            except asyncio.CancelledError:
                pass
        
        if self.ws_connection:
            try:
                await self.ws_connection.close()
            except Exception:
                pass
    
    def _generate_signature(self, timestamp: int, method: str, path: str, body: str = "") -> str:
        """生成请求签名
        
        Args:
            timestamp: 时间戳（毫秒）
            method: HTTP方法（GET/POST等）
            path: 请求路径（例如'/api/v1/orders'）
            body: 请求体字符串，默认为空
            
        Returns:
            签名字符串
        """
        message = f"{timestamp}{method}{path}{body}"
        signature = hmac.new(
            self.api_secret,
            message.encode(),
            hashlib.sha256
        ).hexdigest()
        return signature
    
    def _get_headers(self, method: str, path: str, data: str = "") -> Dict[str, str]:
        """获取请求头
        
        Args:
            method: HTTP方法（GET/POST等）
            path: 请求路径
            data: 请求数据字符串
            
        Returns:
            包含认证信息的请求头字典
        """
        timestamp = int(time.time() * 1000)
        signature = self._generate_signature(timestamp, method, path, data)
        
        return {
            "X-API-KEY": self.api_key,
            "X-TIMESTAMP": str(timestamp),
            "X-SIGNATURE": signature,
            "Content-Type": "application/json"
        }
    
    async def _request(
        self, 
        method: str, 
        endpoint: str, 
        params: Optional[Dict] = None, 
        data: Optional[Dict] = None
    ) -> Any:
        """发送HTTP请求到Backpack API
        
        Args:
            method: HTTP方法（GET/POST等）
            endpoint: API端点（例如'/api/v1/orders'）
            params: URL参数
            data: 请求体数据
            
        Returns:
            响应数据（通常为字典或列表）
        """
        session = await self._get_session()
        url = f"{self.base_url}{endpoint}"
        
        # 对于GET请求，数据通过URL参数传递
        # 对于POST等请求，数据通过请求体传递
        json_data = json.dumps(data) if data else ""
        headers = self._get_headers(method, endpoint, json_data)
        
        try:
            async with session.request(
                method, 
                url, 
                params=params, 
                json=data if data else None, 
                headers=headers
            ) as response:
                result = await response.json()
                
                # 检查API响应是否包含错误
                if isinstance(result, dict) and "code" in result and result["code"] != 0:
                    self.logger.error(f"API错误: {result}")
                
                return result
        except Exception as e:
            self.logger.error(f"请求失败: {e}")
            raise
    
    # ----------- 市场数据接口 -----------
    
    async def get_price(self, symbol: str) -> float:
        """获取单个交易对的最新价格
        
        Args:
            symbol: 交易对名称（例如'BTC_USDC_PERP'）
            
        Returns:
            最新价格
        """
        try:
            # 首先尝试从缓存中获取
            cached_price = self.prices.get(symbol)
            if cached_price > 0:
                return cached_price
            
            # 如果缓存中没有，则通过API获取
            result = await self._request("GET", f"/api/v1/ticker/price?symbol={symbol}")
            if "price" in result:
                price = float(result["price"])
                # 更新缓存
                self.prices.update(symbol, price)
                return price
            return 0
        except Exception as e:
            self.logger.error(f"获取价格失败: {e}")
            return 0
    
    async def get_orderbook(self, symbol: str, limit: int = 10) -> Dict:
        """获取交易对的订单簿（深度）数据
        
        Args:
            symbol: 交易对名称
            limit: 返回的价格档位数量，默认10
            
        Returns:
            订单簿数据，包含bids和asks
        """
        endpoint = f"/api/v1/depth?symbol={symbol}&limit={limit}"
        try:
            result = await self._request("GET", endpoint)
            return result
        except Exception as e:
            self.logger.error(f"获取订单簿失败: {e}")
            return {"bids": [], "asks": []}
    
    async def get_funding_rate(self, symbol: str) -> float:
        """获取单个交易对的资金费率
        
        Args:
            symbol: 交易对名称
            
        Returns:
            资金费率
        """
        try:
            endpoint = f"/api/v1/funding/current-rate?symbol={symbol}"
            result = await self._request("GET", endpoint)
            if "fundingRate" in result:
                return float(result["fundingRate"])
            return 0
        except Exception as e:
            self.logger.error(f"获取资金费率失败: {e}")
            return 0
    
    async def get_all_funding_rates(self) -> Dict[str, float]:
        """获取所有交易对的资金费率
        
        Returns:
            交易对和对应资金费率的字典
        """
        try:
            endpoint = "/api/v1/funding/current-rates"
            result = await self._request("GET", endpoint)
            
            # 处理返回结果为字典
            rates = {}
            for item in result:
                if "symbol" in item and "fundingRate" in item:
                    rates[item["symbol"]] = float(item["fundingRate"])
            
            return rates
        except Exception as e:
            self.logger.error(f"获取所有资金费率失败: {e}")
            return {}
    
    # ----------- 订单接口 -----------
    
    async def place_order(
        self, 
        symbol: str, 
        side: str, 
        quantity: float,
        order_type: str = "MARKET",
        price: Optional[float] = None,
        post_only: bool = False,
        reduce_only: bool = False
    ) -> Dict:
        """下单
        
        Args:
            symbol: 交易对名称
            side: 交易方向，'BUY'或'SELL'
            quantity: 交易数量
            order_type: 订单类型，'MARKET'或'LIMIT'
            price: 价格，LIMIT单必须指定
            post_only: 是否只做Maker
            reduce_only: 是否只减仓
            
        Returns:
            下单结果
        """
        data = {
            "symbol": symbol,
            "side": side,
            "type": order_type,
            "quantity": str(quantity)  # API要求数量为字符串
        }
        
        if order_type == "LIMIT" and price is not None:
            data["price"] = str(price)
        
        if post_only:
            data["postOnly"] = True
        
        if reduce_only:
            data["reduceOnly"] = True
        
        try:
            result = await self._request("POST", "/api/v1/order", data=data)
            return result
        except Exception as e:
            self.logger.error(f"下单失败: {e}")
            return {"error": str(e)}
    
    async def place_order_with_depth(
        self, 
        symbol: str, 
        side: str, 
        quantity: float,
        order_type: str = "LIMIT",
        depth_tolerance: float = 0.001
    ) -> Dict:
        """使用订单簿深度数据下单，以获得更好的成交价格
        
        Args:
            symbol: 交易对名称
            side: 交易方向，'BUY'或'SELL'
            quantity: 交易数量
            order_type: 订单类型，默认为'LIMIT'
            depth_tolerance: 价格容忍度
            
        Returns:
            下单结果
        """
        # 获取深度数据
        orderbook = await self.get_orderbook(symbol)
        
        if not orderbook["bids"] or not orderbook["asks"]:
            self.logger.warning(f"订单簿为空，使用市价单")
            return await self.place_order(symbol, side, quantity, "MARKET")
        
        # 根据交易方向确定参考价格
        if side == "BUY":
            # 买入使用卖单价格作为参考
            reference_price = float(orderbook["asks"][0][0])
            # 添加价格容忍度，价格略高于卖一价
            price = reference_price * (1 + depth_tolerance)
        else:
            # 卖出使用买单价格作为参考
            reference_price = float(orderbook["bids"][0][0])
            # 添加价格容忍度，价格略低于买一价
            price = reference_price * (1 - depth_tolerance)
        
        self.logger.info(f"深度下单 - 参考价: {reference_price}, 下单价: {price}")
        
        # 下限价单
        return await self.place_order(
            symbol=symbol,
            side=side,
            quantity=quantity,
            order_type="LIMIT",
            price=price
        )
    
    async def cancel_order(self, symbol: str, order_id: str) -> Dict:
        """取消订单
        
        Args:
            symbol: 交易对名称
            order_id: 订单ID
            
        Returns:
            取消结果
        """
        data = {
            "symbol": symbol,
            "orderId": order_id
        }
        
        try:
            result = await self._request("DELETE", "/api/v1/order", data=data)
            return result
        except Exception as e:
            self.logger.error(f"取消订单失败: {e}")
            return {"error": str(e)}
    
    async def cancel_all_orders(self, symbol: Optional[str] = None) -> Dict:
        """取消所有订单或特定交易对的所有订单
        
        Args:
            symbol: 交易对名称，可选
            
        Returns:
            取消结果
        """
        data = {}
        if symbol:
            data["symbol"] = symbol
        
        try:
            result = await self._request("DELETE", "/api/v1/orders", data=data)
            return result
        except Exception as e:
            self.logger.error(f"取消所有订单失败: {e}")
            return {"error": str(e)}
    
    async def get_order_status(self, symbol: str, order_id: str) -> Dict:
        """查询订单状态
        
        Args:
            symbol: 交易对名称
            order_id: 订单ID
            
        Returns:
            订单状态
        """
        params = {
            "symbol": symbol,
            "orderId": order_id
        }
        
        try:
            result = await self._request("GET", "/api/v1/order", params=params)
            return result
        except Exception as e:
            self.logger.error(f"查询订单状态失败: {e}")
            return {"error": str(e)}
    
    async def get_open_orders(self, symbol: Optional[str] = None) -> List[Dict]:
        """查询未成交订单
        
        Args:
            symbol: 交易对名称，可选
            
        Returns:
            未成交订单列表
        """
        params = {}
        if symbol:
            params["symbol"] = symbol
        
        try:
            result = await self._request("GET", "/api/v1/open-orders", params=params)
            return result
        except Exception as e:
            self.logger.error(f"查询未成交订单失败: {e}")
            return []
    
    # ----------- 账户接口 -----------
    
    async def get_account_info(self) -> Dict:
        """获取账户信息
        
        Returns:
            账户信息
        """
        try:
            result = await self._request("GET", "/api/v1/account")
            return result
        except Exception as e:
            self.logger.error(f"获取账户信息失败: {e}")
            return {"error": str(e)}
    
    async def get_balances(self) -> List[Dict]:
        """获取账户余额
        
        Returns:
            余额信息列表
        """
        try:
            result = await self._request("GET", "/api/v1/balance")
            return result
        except Exception as e:
            self.logger.error(f"获取余额失败: {e}")
            return []
    
    async def get_positions(self) -> List[Dict]:
        """获取持仓信息
        
        Returns:
            持仓信息列表
        """
        try:
            result = await self._request("GET", "/api/v1/positions")
            return result
        except Exception as e:
            self.logger.error(f"获取持仓信息失败: {e}")
            return []
    
    async def get_position(self, symbol: str) -> Optional[Dict]:
        """获取单个交易对的持仓信息
        
        Args:
            symbol: 交易对名称
            
        Returns:
            持仓信息或None
        """
        try:
            positions = await self.get_positions()
            for position in positions:
                if position["symbol"] == symbol:
                    return position
            return None
        except Exception as e:
            self.logger.error(f"获取单个持仓信息失败: {e}")
            return None
    
    # ----------- WebSocket接口 -----------
    
    def register_price_callback(self, callback: Callable[[str, float], None]):
        """注册价格更新回调函数
        
        Args:
            callback: 回调函数，接收交易对名称和价格
        """
        self.price_callbacks.append(callback)
    
    async def _handle_price_update(self, symbol: str, price: float):
        """处理价格更新
        
        Args:
            symbol: 交易对名称
            price: 最新价格
        """
        # 更新价格缓存
        self.prices.update(symbol, price)
        
        # 调用所有回调函数
        for callback in self.price_callbacks:
            try:
                await callback(symbol, price)
            except Exception as e:
                self.logger.error(f"调用价格回调失败: {e}")
    
    async def _ws_price_listener(self):
        """WebSocket价格监听器"""
        self.logger.info("启动WebSocket价格监听器...")
        
        while True:
            try:
                # 连接WebSocket
                async with websockets.connect(f"{self.ws_url}/stream") as websocket:
                    self.ws_connection = websocket
                    
                    # 发送订阅请求
                    subscribe_msg = {
                        "method": "SUBSCRIBE",
                        "params": ["!ticker@arr"],
                        "id": int(time.time() * 1000)
                    }
                    await websocket.send(json.dumps(subscribe_msg))
                    
                    # 处理返回数据
                    while True:
                        response = await websocket.recv()
                        data = json.loads(response)
                        
                        # 处理价格更新
                        if "data" in data and isinstance(data["data"], list):
                            for ticker in data["data"]:
                                if "s" in ticker and "c" in ticker:  # s: symbol, c: close price
                                    symbol = ticker["s"]
                                    price = float(ticker["c"])
                                    await self._handle_price_update(symbol, price)
            
            except Exception as e:
                self.logger.error(f"WebSocket连接错误: {e}")
                self.ws_connection = None
                
                # 如果连接断开，等待5秒后重连
                await asyncio.sleep(5)
    
    async def start_ws_price_stream(self):
        """启动价格数据流"""
        if self.ws_task is None or self.ws_task.done():
            self.ws_task = asyncio.create_task(self._ws_price_listener())
            self.logger.info("价格数据流已启动")
        else:
            self.logger.info("价格数据流已在运行中") 