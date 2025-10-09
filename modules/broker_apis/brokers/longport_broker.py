"""长桥券商API实现类"""

import time
from typing import Dict, Any, List, Optional
from decimal import Decimal
from longport.openapi import (
    TradeContext, QuoteContext, Config, Market, OrderSide as LBOrderSide,
    OrderType as LBOrderType, TimeInForceType, PushOrderChanged
)

from ..broker_interface import BrokerInterface, Market as CustomMarket, ProductType, OrderSide, OrderType


class LongPortBroker(BrokerInterface):
    """长桥券商API实现"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__("LongPort", config)
        self.trade_ctx: Optional[TradeContext] = None
        self.quote_ctx: Optional[QuoteContext] = None
    
    def connect(self) -> bool:
        """连接长桥API"""
        try:
            api_config = self.config
            
            # 创建配置
            config = Config(
                app_key=api_config.get("app_key"),
                app_secret=api_config.get("app_secret"),
                access_token=api_config.get("access_token"),
            )
            
            # 初始化交易和行情上下文
            self.trade_ctx = TradeContext(config)
            self.quote_ctx = QuoteContext(config)
            
            # 测试连接
            self.is_connected = True
            print("长桥API连接成功")
            return True
            
        except Exception as e:
            print(f"长桥API连接失败: {e}")
            self.is_connected = False
            return False
    
    def disconnect(self) -> bool:
        """断开长桥API连接"""
        try:
            if self.trade_ctx:
                self.trade_ctx = None
            if self.quote_ctx:
                self.quote_ctx = None
            
            self.is_connected = False
            print("长桥API连接已断开")
            return True
        except Exception as e:
            print(f"断开长桥API连接失败: {e}")
            return False
    
    def get_account_balance(self) -> Dict[str, Any]:
        """获取账户余额信息"""
        if not self.trade_ctx or not self.is_connected:
            return {}
        
        try:
            account_balance = self.trade_ctx.account_balance()
            return {
                "total_cash": float(account_balance.total_cash),
                "max_power_short": float(account_balance.max_power_short),
                "net_cash_power": float(account_balance.net_cash_power),
                "currency": "HKD",  # 长桥主要使用港币
                "timestamp": time.strftime('%Y-%m-%d %H:%M:%S')
            }
        except Exception as e:
            print(f"获取账户余额失败: {e}")
            return {}
    
    def get_positions(self) -> List[Dict[str, Any]]:
        """获取持仓信息"""
        if not self.trade_ctx or not self.is_connected:
            return []
        
        try:
            positions = self.trade_ctx.positions()
            result = []
            for pos in positions:
                result.append({
                    "symbol": pos.symbol,
                    "quantity": pos.quantity,
                    "available_quantity": pos.available_quantity,
                    "currency": pos.currency,
                    "cost_price": float(pos.cost_price),
                    "market": pos.market.value if pos.market else "UNKNOWN"
                })
            return result
        except Exception as e:
            print(f"获取持仓信息失败: {e}")
            return []
    
    def submit_order(self, symbol: str, side: OrderSide, order_type: OrderType,
                    quantity: int, price: Optional[float] = None) -> Dict[str, Any]:
        """提交订单"""
        if not self.trade_ctx or not self.is_connected:
            return {"success": False, "reason": "交易API未连接"}
        
        try:
            # 转换订单方向
            lb_side = LBOrderSide.Buy if side == OrderSide.BUY else LBOrderSide.Sell
            
            # 转换订单类型
            if order_type == OrderType.MARKET:
                lb_order_type = LBOrderType.MO
            elif order_type == OrderType.LIMIT:
                lb_order_type = LBOrderType.LO
            else:
                lb_order_type = LBOrderType.LO  # 默认限价单
            
            # 提交订单
            order_result = self.trade_ctx.submit_order(
                symbol=symbol,
                order_type=lb_order_type,
                side=lb_side,
                submitted_quantity=quantity,
                time_in_force=TimeInForceType.Day,
                submitted_price=Decimal(str(price)) if price else None
            )
            
            return {
                "success": True,
                "order_id": order_result.order_id,
                "symbol": symbol,
                "side": side.value,
                "order_type": order_type.value,
                "quantity": quantity,
                "price": price,
                "timestamp": time.strftime('%Y-%m-%d %H:%M:%S')
            }
            
        except Exception as e:
            return {"success": False, "reason": f"提交订单失败: {e}"}
    
    def cancel_order(self, order_id: str) -> bool:
        """取消订单"""
        if not self.trade_ctx or not self.is_connected:
            return False
        
        try:
            self.trade_ctx.withdraw_order(order_id)
            return True
        except Exception as e:
            print(f"取消订单失败: {e}")
            return False
    
    def get_order_status(self, order_id: str) -> Dict[str, Any]:
        """获取订单状态"""
        if not self.trade_ctx or not self.is_connected:
            return {}
        
        try:
            # 长桥API需要先获取所有订单，然后过滤
            orders = self.trade_ctx.today_orders()
            for order in orders:
                if order.order_id == order_id:
                    return {
                        "order_id": order.order_id,
                        "symbol": order.symbol,
                        "status": order.status.value,
                        "side": order.side.value,
                        "submitted_quantity": order.submitted_quantity,
                        "executed_quantity": order.executed_quantity,
                        "submitted_price": float(order.submitted_price),
                        "executed_price": float(order.executed_price) if order.executed_price else None,
                        "last_done": float(order.last_done) if order.last_done else None
                    }
            return {}
        except Exception as e:
            print(f"获取订单状态失败: {e}")
            return {}
    
    def get_market_data(self, symbol: str, data_type: str) -> Dict[str, Any]:
        """获取市场数据"""
        if not self.quote_ctx or not self.is_connected:
            return {}
        
        try:
            if data_type == "quote":
                # 获取实时报价
                quotes = self.quote_ctx.realtime_quote([symbol])
                if quotes:
                    quote = quotes[0]
                    return {
                        "symbol": symbol,
                        "last_done": float(quote.last_done) if quote.last_done else None,
                        "prev_close": float(quote.prev_close) if quote.prev_close else None,
                        "open": float(quote.open) if quote.open else None,
                        "high": float(quote.high) if quote.high else None,
                        "low": float(quote.low) if quote.low else None,
                        "volume": quote.volume,
                        "turnover": float(quote.turnover) if quote.turnover else None,
                        "timestamp": quote.timestamp.isoformat() if quote.timestamp else None
                    }
            
            elif data_type == "depth":
                # 获取深度数据
                depths = self.quote_ctx.depth(symbol)
                if depths:
                    return {
                        "symbol": symbol,
                        "bids": [(float(bid.price), bid.volume) for bid in depths.bids],
                        "asks": [(float(ask.price), ask.volume) for ask in depths.asks]
                    }
            
            return {}
            
        except Exception as e:
            print(f"获取市场数据失败: {e}")
            return {}
    
    def get_historical_data(self, symbol: str, period: str, 
                           start_date: str, end_date: str) -> List[Dict[str, Any]]:
        """获取历史数据"""
        if not self.quote_ctx or not self.is_connected:
            return []
        
        try:
            # 转换周期
            from longport.openapi import Period, AdjustType
            period_mapping = {
                "1min": Period.Min1,
                "5min": Period.Min5,
                "15min": Period.Min15,
                "30min": Period.Min30,
                "60min": Period.Min60,
                "day": Period.Day,
                "week": Period.Week,
                "month": Period.Month
            }
            
            lb_period = period_mapping.get(period, Period.Day)
            
            # 获取K线数据
            candles = self.quote_ctx.candlesticks(symbol, lb_period, AdjustType.NoAdjust)
            
            result = []
            for candle in candles:
                result.append({
                    "timestamp": candle.timestamp.isoformat(),
                    "open": float(candle.open),
                    "high": float(candle.high),
                    "low": float(candle.low),
                    "close": float(candle.close),
                    "volume": candle.volume
                })
            
            return result
            
        except Exception as e:
            print(f"获取历史数据失败: {e}")
            return []
    
    def get_supported_markets(self) -> List[CustomMarket]:
        """获取支持的交易市场"""
        return [CustomMarket.HK, CustomMarket.US]
    
    def get_supported_products(self) -> List[ProductType]:
        """获取支持的产品类型"""
        return [
            ProductType.STOCK,
            ProductType.ETF,
            ProductType.WARRANT,
            ProductType.CBBC
        ]
    
    def get_trading_hours(self, market: CustomMarket) -> Dict[str, str]:
        """获取交易时间"""
        trading_hours = {
            CustomMarket.HK: {"open": "09:30", "close": "16:00"},
            CustomMarket.US: {"open": "21:30", "close": "04:00"}
        }
        return trading_hours.get(market, {})