"""市场数据提供模块
负责获取不同市场、不同产品的实时数据
"""

import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from decimal import Decimal

from longport.openapi import (
    Config, QuoteContext, TradeContext, SubType, Market,
    SecurityListCategory, PushQuote, PushDepth, PushBrokers, PushTrades
)

from ..config.config_manager import Market, ProductType, ConfigManager


class MarketDataProvider:
    """市场数据提供器"""
    
    def __init__(self, config_manager: ConfigManager):
        self.config_manager = config_manager
        self.quote_ctx: Optional[QuoteContext] = None
        self.trade_ctx: Optional[TradeContext] = None
        self._connect_api()
    
    def _connect_api(self):
        """连接API"""
        try:
            api_config = self.config_manager.get_api_config()
            if not all([api_config.get('app_key'), api_config.get('app_secret'), api_config.get('access_token')]):
                print("API配置不完整，请检查config.yaml文件")
                return
            
            config = Config.from_env()
            self.quote_ctx = QuoteContext(config)
            self.trade_ctx = TradeContext(config)
            print("市场数据API连接成功")
        except Exception as e:
            print(f"API连接失败: {e}")
    
    def get_real_time_quotes(self, symbols: List[str]) -> List[Dict[str, Any]]:
        """获取实时报价数据"""
        if not self.quote_ctx or not symbols:
            return []
        
        try:
            quotes = self.quote_ctx.quote(symbols)
            result = []
            for quote in quotes:
                result.append({
                    'symbol': quote.symbol,
                    'market': self._parse_market_from_symbol(quote.symbol),
                    'last_done': float(quote.last_done) if quote.last_done else 0,
                    'prev_close': float(quote.prev_close) if quote.prev_close else 0,
                    'open': float(quote.open) if quote.open else 0,
                    'high': float(quote.high) if quote.high else 0,
                    'low': float(quote.low) if quote.low else 0,
                    'volume': quote.volume,
                    'turnover': float(quote.turnover) if quote.turnover else 0,
                    'change': float(quote.change) if quote.change else 0,
                    'change_percent': float(quote.change_percent) if quote.change_percent else 0,
                    'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                })
            return result
        except Exception as e:
            print(f"获取实时报价失败: {e}")
            return []
    
    def get_candlestick_data(self, symbol: str, days: int = 30, period: int = 1440) -> List[Dict[str, Any]]:
        """获取K线数据"""
        if not self.quote_ctx:
            return []
        
        try:
            candlesticks = self.quote_ctx.candlesticks(symbol, period=period)
            result = []
            for candle in candlesticks:
                result.append({
                    'symbol': symbol,
                    'timestamp': candle.timestamp,
                    'open': float(candle.open),
                    'high': float(candle.high),
                    'low': float(candle.low),
                    'close': float(candle.close),
                    'volume': candle.volume,
                    'period': period
                })
            return result
        except Exception as e:
            print(f"获取K线数据失败 {symbol}: {e}")
            return []
    
    def get_depth_data(self, symbol: str) -> Dict[str, Any]:
        """获取深度数据（买卖盘）"""
        if not self.quote_ctx:
            return {}
        
        try:
            depth = self.quote_ctx.depth(symbol)
            return {
                'symbol': symbol,
                'asks': [{'price': float(ask.price), 'volume': ask.volume} for ask in depth.asks],
                'bids': [{'price': float(bid.price), 'volume': bid.volume} for bid in depth.bids],
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
        except Exception as e:
            print(f"获取深度数据失败 {symbol}: {e}")
            return {}
    
    def get_broker_data(self, symbol: str) -> Dict[str, Any]:
        """获取经纪商数据"""
        if not self.quote_ctx:
            return {}
        
        try:
            brokers = self.quote_ctx.brokers(symbol)
            return {
                'symbol': symbol,
                'broker_ids': brokers.broker_ids,
                'positions': [{'broker_id': pos.broker_id, 'position': pos.position} for pos in brokers.positions],
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
        except Exception as e:
            print(f"获取经纪商数据失败 {symbol}: {e}")
            return {}
    
    def get_market_symbols(self, market: Market, product_type: ProductType) -> List[str]:
        """获取指定市场、产品类型的股票列表"""
        if not self.quote_ctx:
            return []
        
        try:
            # 根据市场选择对应的SecurityListCategory
            category_map = {
                Market.HK: SecurityListCategory.HK,
                Market.US: SecurityListCategory.US,
                Market.CN: SecurityListCategory.CN
            }
            
            category = category_map.get(market)
            if not category:
                return []
            
            securities = self.quote_ctx.securities(category)
            
            # 根据产品类型过滤
            if product_type == ProductType.STOCK:
                return [sec.symbol for sec in securities if sec.security_type == "stock"]
            elif product_type == ProductType.ETF:
                return [sec.symbol for sec in securities if sec.security_type == "etf"]
            elif product_type == ProductType.WARRANT:
                return [sec.symbol for sec in securities if sec.security_type == "warrant"]
            elif product_type == ProductType.CBBC:
                return [sec.symbol for sec in securities if sec.security_type == "cbbc"]
            elif product_type == ProductType.OPTION:
                return [sec.symbol for sec in securities if sec.security_type == "option"]
            else:
                return [sec.symbol for sec in securities]
                
        except Exception as e:
            print(f"获取{symbol}列表失败: {e}")
            return []
    
    def _parse_market_from_symbol(self, symbol: str) -> str:
        """从股票代码解析市场"""
        if symbol.startswith(('0', '3', '6')) and len(symbol) == 6:
            return Market.CN.value
        elif symbol.startswith(('0', '1', '2', '3', '4', '5', '6', '7', '8', '9')) and len(symbol) == 5:
            return Market.HK.value
        elif symbol.endswith('.US') or symbol.endswith('.OTC'):
            return Market.US.value
        else:
            return "UNKNOWN"
    
    def get_product_specific_data(self, symbol: str, product_type: ProductType) -> Dict[str, Any]:
        """获取产品特定数据"""
        base_data = {
            'symbol': symbol,
            'product_type': product_type.value,
            'market': self._parse_market_from_symbol(symbol)
        }
        
        if product_type == ProductType.WARRANT:
            # 窝轮特定数据
            base_data.update({
                'underlying': self._get_warrant_underlying(symbol),
                'strike_price': self._get_warrant_strike_price(symbol),
                'expiry_date': self._get_warrant_expiry(symbol)
            })
        elif product_type == ProductType.OPTION:
            # 期权特定数据
            base_data.update({
                'strike_price': self._get_option_strike_price(symbol),
                'expiry_date': self._get_option_expiry(symbol),
                'option_type': self._get_option_type(symbol)
            })
        
        return base_data
    
    def _get_warrant_underlying(self, symbol: str) -> str:
        """获取窝轮标的（模拟实现）"""
        # 实际应用中需要调用API获取窝轮信息
        return "UNKNOWN"
    
    def _get_warrant_strike_price(self, symbol: str) -> float:
        """获取窝轮行使价（模拟实现）"""
        return 0.0
    
    def _get_warrant_expiry(self, symbol: str) -> str:
        """获取窝轮到期日（模拟实现）"""
        return "UNKNOWN"
    
    def _get_option_strike_price(self, symbol: str) -> float:
        """获取期权行使价（模拟实现）"""
        return 0.0
    
    def _get_option_expiry(self, symbol: str) -> str:
        """获取期权到期日（模拟实现）"""
        return "UNKNOWN"
    
    def _get_option_type(self, symbol: str) -> str:
        """获取期权类型（模拟实现）"""
        return "UNKNOWN"


if __name__ == "__main__":
    # 测试市场数据提供器
    config_mgr = ConfigManager()
    data_provider = MarketDataProvider(config_mgr)
    
    # 测试获取港股股票列表
    hk_stocks = data_provider.get_market_symbols(Market.HK, ProductType.STOCK)
    print(f"港股股票数量: {len(hk_stocks)}")
    
    if hk_stocks:
        # 测试获取实时报价
        quotes = data_provider.get_real_time_quotes(hk_stocks[:5])
        print(f"获取到 {len(quotes)} 只股票的实时报价")