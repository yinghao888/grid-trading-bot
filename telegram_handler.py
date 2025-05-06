#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import asyncio
import aiohttp
import logging
from datetime import datetime
from typing import Optional, Dict, Any

class TelegramHandler:
    def __init__(self, bot_token: str, chat_id: str, logger: Optional[logging.Logger] = None):
        """初始化 Telegram 处理程序
        
        Args:
            bot_token: Telegram 机器人令牌
            chat_id: 目标聊天 ID
            logger: 日志记录器，如果为None则创建新的
        """
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.logger = logger or logging.getLogger("telegram_handler")
        self.api_url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        self.session = None
    
    async def get_session(self) -> aiohttp.ClientSession:
        """获取或创建HTTP会话"""
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession()
        return self.session
    
    async def close(self):
        """关闭HTTP会话"""
        if self.session and not self.session.closed:
            await self.session.close()
    
    async def send_message(self, text: str) -> bool:
        """发送消息到Telegram
        
        Args:
            text: 要发送的消息文本
            
        Returns:
            是否发送成功
        """
        if not self.chat_id:
            self.logger.warning("未配置 Telegram chat_id，无法发送消息")
            return False
        
        try:
            session = await self.get_session()
            params = {
                "chat_id": self.chat_id,
                "text": text,
                "parse_mode": "HTML"
            }
            
            async with session.post(self.api_url, json=params) as response:
                if response.status == 200:
                    self.logger.info("Telegram 消息已发送")
                    return True
                else:
                    response_text = await response.text()
                    self.logger.error(f"发送 Telegram 消息失败: {response.status} - {response_text}")
                    return False
                
        except Exception as e:
            self.logger.error(f"发送 Telegram 消息时出错: {e}")
            return False
    
    async def send_trade_notification(self, action: str, symbol: str, side: str, 
                                    quantity: float, price: float, 
                                    profit_loss: Optional[float] = None, 
                                    reason: Optional[str] = None) -> bool:
        """发送交易通知
        
        Args:
            action: 交易动作（开仓/平仓）
            symbol: 交易对
            side: 交易方向（买入/卖出）
            quantity: 交易数量
            price: 交易价格
            profit_loss: 盈亏金额（如适用）
            reason: 交易原因（如适用）
            
        Returns:
            是否发送成功
        """
        # 格式化时间
        time_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # 构建消息
        message = f"<b>交易通知 - {action}</b>\n"
        message += f"<b>时间:</b> {time_str}\n"
        message += f"<b>交易对:</b> {symbol}\n"
        message += f"<b>方向:</b> {'做多' if side == 'BUY' else '做空'}\n"
        message += f"<b>数量:</b> {quantity}\n"
        message += f"<b>价格:</b> {price}\n"
        
        if profit_loss is not None:
            pl_emoji = "🟢" if profit_loss >= 0 else "🔴"
            message += f"<b>盈亏:</b> {pl_emoji} {profit_loss:.2f} USDC\n"
        
        if reason:
            message += f"<b>原因:</b> {reason}\n"
        
        return await self.send_message(message)
    
    async def send_balance_notification(self, balance: Dict[str, Any]) -> bool:
        """发送余额通知
        
        Args:
            balance: 余额信息字典
            
        Returns:
            是否发送成功
        """
        # 格式化时间
        time_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # 构建消息
        message = f"<b>账户余额通知</b>\n"
        message += f"<b>时间:</b> {time_str}\n"
        
        for asset, info in balance.items():
            message += f"<b>{asset}:</b> {info['available']} (可用) + {info['locked']} (锁定)\n"
        
        return await self.send_message(message)
    
    async def send_error_notification(self, error_message: str) -> bool:
        """发送错误通知
        
        Args:
            error_message: 错误信息
            
        Returns:
            是否发送成功
        """
        # 格式化时间
        time_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # 构建消息
        message = f"<b>⚠️ 错误通知</b>\n"
        message += f"<b>时间:</b> {time_str}\n"
        message += f"<b>错误:</b> {error_message}\n"
        
        return await self.send_message(message)
    
    async def send_start_notification(self) -> bool:
        """发送机器人启动通知
        
        Returns:
            是否发送成功
        """
        # 格式化时间
        time_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # 构建消息
        message = f"<b>🚀 交易机器人已启动</b>\n"
        message += f"<b>时间:</b> {time_str}\n"
        
        return await self.send_message(message)
    
    async def send_stop_notification(self) -> bool:
        """发送机器人停止通知
        
        Returns:
            是否发送成功
        """
        # 格式化时间
        time_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # 构建消息
        message = f"<b>🛑 交易机器人已停止</b>\n"
        message += f"<b>时间:</b> {time_str}\n"
        
        return await self.send_message(message) 