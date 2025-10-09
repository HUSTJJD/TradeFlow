"""IBKR券商API实现类"""

import time
from typing import Dict, Any, List, Optional
from ib_async import IB, Stock, Option, Future, Forex, MarketOrder, LimitOrder

from ..broker_interface import BrokerInterface, Market, ProductType, OrderSide, OrderType


class IBKRBroker(BrokerInterface):
    """IBKR券商API实现"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__("ibkr", config)
        self.ib: Optional[IB] = None
    
    def connect(self) -> bool:
        """连接IBKR API"""
        try:
            api_config = self.config
            
            # 创建IB实例
            self.ib = IB()
            
            # 连接TWS/Gateway
            host = api_config.get("host", "127.0.0.1")
            port = api_config.get("port", 7497)
            client_id = api_config.get("client_id", 1)
            
            self.ib.connect(host, port, clientId=client_id)
            
            # 等待连接建立
            self.ib.reqCurrentTime()
            
            self.is_connected = True
            print("IBKR API连接成功")
            return True
            
        except Exception as e:
            print(f"IBKR API连接失败: {e}")
            self.is_connected = False
            return False
    
    def disconnect(self) -> bool:
        """断开IBKR API连接"""
        try:
            if self.ib:
                self.ib.disconnect()
                self.ib = None
            
            self.is_connected = False
            print("IBKR API连接已断开")
            return True
        except Exception as e:
            print(f"断开IBKR API连接失败: {e}")
            return False
    
    def get_account_balance(self) -> Dict[str, Any]:
        """获取账户余额信息"""
        if not self.ib or not self.is_connected:
            return {}
        
        try:
            # 获取账户摘要
            account = self.config.get("account", "")
            account_values = self.ib.accountValues(account)
            
            balance_info = {}
            for value in account_values:
                if value.currency == "USD":
                    if value.tag == "TotalCashValue":
                        balance_info["total_cash"] = float(value.value)
                    elif value.tag == "BuyingPower":
                        balance_info["buying_power"] = float(value.value)
                    elif value.tag == "NetLiquidation":
                        balance_info["net_liquidation"] = float(value.value)
            
            balance_info.update({
                "currency": "USD",
                "account": account,
                "timestamp": time.strftime('%Y-%m-%d %H:%M:%S')
            })
            
            return balance_info
            
        except Exception as e:
            print(f"获取账户余额失败: {e}")
            return {}
    
    def get_positions(self) -> List[Dict[str, Any]]:
        """获取持仓信息"""
        if not self.ib or not self.is_connected:
            return []
        
        try:
            positions = self.ib.positions()
            result = []
            
            for pos in positions:
                position_info = {
                    "symbol": pos.contract.symbol,
                    "quantity": pos.position,
                    "avg_cost": float(pos.avgCost) if pos.avgCost else 0,
                    "currency": pos.contract.currency,
                    "exchange": pos.contract.exchange,
                    "sec_type": pos.contract.secType
                }
                
                # 添加特定合约信息
                if hasattr(pos.contract, 'strike'):
                    position_info["strike"] = float(pos.contract.strike)
                if hasattr(pos.contract, 'lastTradeDateOrContractMonth'):
                    position_info["expiry"] = pos.contract.lastTradeDateOrContractMonth
                
                result.append(position_info)
            
            return result
            
        except Exception as e:
            print(f"获取持仓信息失败: {e}")
            return []
    
    def submit_order(self, symbol: str, side: OrderSide, order_type: OrderType,
                    quantity: int, price: Optional[float] = None) -> Dict[str, Any]:
        """提交订单"""
        if not self.ib or not self.is_connected:
            return {"success": False, "reason": "IBKR API未连接"}
        
        try:
            # 创建合约
            contract = self._create_contract(symbol)
            if not contract:
                return {"success": False, "reason": f"无法创建合约: {symbol}"}
            
            # 创建订单
            if order_type == OrderType.MARKET:
                order = MarketOrder(side.value, quantity)
            elif order_type == OrderType.LIMIT and price:
                order = LimitOrder(side.value, quantity, price)
            else:
                return {"success": False, "reason": "不支持的订单类型"}
            
            # 提交订单
            trade = self.ib.placeOrder(contract, order)
            
            # 等待订单确认
            while not trade.orderStatus.status:
                self.ib.sleep(0.1)
            
            return {
                "success": True,
                "order_id": str(trade.order.orderId),
                "symbol": symbol,
                "side": side.value,
                "order_type": order_type.value,
                "quantity": quantity,
                "price": price,
                "status": trade.orderStatus.status,
                "timestamp": time.strftime('%Y-%m-%d %H:%M:%S')
            }
            
        except Exception as e:
            return {"success": False, "reason": f"提交订单失败: {e}"}
    
    def _create_contract(self, symbol: str):
        """根据符号创建合约"""
        try:
            # 简单实现：根据符号特征判断合约类型
            if symbol.endswith('.HK'):
                return Stock(symbol.replace('.HK', ''), 'SEHK', 'HKD')
            elif symbol.endswith('.US') or (symbol.isalpha() and len(symbol) <= 5):
                return Stock(symbol.replace('.US', ''), 'SMART', 'USD')
            elif ' ' in symbol and 'CALL' in symbol.upper() or 'PUT' in symbol.upper():
                # 期权合约处理
                parts = symbol.split()
                if len(parts) >= 4:
                    underlying = parts[0]
                    expiry = parts[1]
                    strike = float(parts[2])
                    right = parts[3].upper()
                    return Option(underlying, expiry, strike, right, 'SMART')
            else:
                # 默认美股
                return Stock(symbol, 'SMART', 'USD')
                
        except Exception as e:
            print(f"创建合约失败: {e}")
            return None
    
    def cancel_order(self, order_id: str) -> bool:
        """取消订单"""
        if not self.ib or not self.is_connected:
            return False
        
        try:
            self.ib.cancelOrder(int(order_id))
            return True
        except Exception as e:
            print(f"取消订单失败: {e}")
            return False
    
    def get_order_status(self, order_id: str) -> Dict[str, Any]:
        """获取订单状态"""
        if not self.ib or not self.is_connected:
            return {}
        
        try:
            # 获取所有订单
            trades = self.ib.trades()
            for trade in trades:
                if str(trade.order.orderId) == order_id:
                    return {
                        "order_id": order_id,
                        "symbol": trade.contract.symbol,
                        "status": trade.orderStatus.status,
                        "side": trade.order.action,
                        "quantity": trade.order.totalQuantity,
                        "filled": trade.orderStatus.filled,
                        "remaining": trade.orderStatus.remaining,
                        "avg_fill_price": float(trade.orderStatus.avgFillPrice) if trade.orderStatus.avgFillPrice else None
                    }
            return {}
        except Exception as e:
            print(f"获取订单状态失败: {e}")
            return {}
    
    def get_market_data(self, symbol: str, data_type: str) -> Dict[str, Any]:
        """获取市场数据"""
        if not self.ib or not self.is_connected:
            return {}
        
        try:
            contract = self._create_contract(symbol)
            if not contract:
                return {}
            
            if data_type == "quote":
                # 获取实时报价
                ticker = self.ib.reqMktData(contract, '', False, False)
                self.ib.sleep(1)  # 等待数据
                
                return {
                    "symbol": symbol,
                    "bid": float(ticker.bid) if ticker.bid else None,
                    "ask": float(ticker.ask) if ticker.ask else None,
                    "last": float(ticker.last) if ticker.last else None,
                    "volume": ticker.volume,
                    "timestamp": time.strftime('%Y-%m-%d %H:%M:%S')
                }
            
            return {}
            
        except Exception as e:
            print(f"获取市场数据失败: {e}")
            return {}
    
    def get_historical_data(self, symbol: str, period: str, 
                           start_date: str, end_date: str) -> List[Dict[str, Any]]:
        """获取历史数据"""
        if not self.ib or not self.is_connected:
            return []
        
        try:
            contract = self._create_contract(symbol)
            if not contract:
                return []
            
            # 转换周期
            duration_str = "1 Y"  # 默认1年
            bar_size = "1 day"   # 默认日线
            
            period_mapping = {
                "1min": ("1 D", "1 min"),
                "5min": ("1 D", "5 mins"),
                "15min": ("1 D", "15 mins"),
                "30min": ("1 D", "30 mins"),
                "60min": ("1 D", "1 hour"),
                "day": ("1 Y", "1 day"),
                "week": ("2 Y", "1 week"),
                "month": ("5 Y", "1 month")
            }
            
            duration_str, bar_size = period_mapping.get(period, ("1 Y", "1 day"))
            
            # 获取历史数据
            bars = self.ib.reqHistoricalData(
                contract,
                endDateTime='',
                durationStr=duration_str,
                barSizeSetting=bar_size,
                whatToShow='TRADES',
                useRTH=True,
                formatDate=1
            )
            
            result = []
            for bar in bars:
                result.append({
                    "timestamp": bar.date.isoformat(),
                    "open": bar.open,
                    "high": bar.high,
                    "low": bar.low,
                    "close": bar.close,
                    "volume": bar.volume
                })
            
            return result
            
        except Exception as e:
            print(f"获取历史数据失败: {e}")
            return []
    
    def get_supported_markets(self) -> List[Market]:
        """获取支持的交易市场"""
        return [Market.US, Market.HK, Market.CN]
    
    def get_supported_products(self) -> List[ProductType]:
        """获取支持的产品类型"""
        return [
            ProductType.STOCK,
            ProductType.ETF,
            ProductType.OPTION
        ]
    
    def get_trading_hours(self, market: Market) -> Dict[str, str]:
        """获取交易时间"""
        trading_hours = {
            Market.US: {"open": "09:30", "close": "16:00"},  # 美东时间
            Market.HK: {"open": "09:30", "close": "16:00"},  # 香港时间
            Market.CN: {"open": "09:30", "close": "15:00"}   # 北京时间
        }
        return trading_hours.get(market, {})