"""交易执行模块
支持不同产品的交易逻辑和风险管理
"""

import time
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from decimal import Decimal

from longport.openapi import (
    TradeContext, OrderType, OrderSide, TimeInForceType,
    PushOrderChanged, Market,Config
)

from ..config.config_manager import ProductType, ConfigManager
from ..product_types.product_factory import ProductBase


class TradingStrategy(ABC):
    """交易策略基类"""
    
    def __init__(self, name: str, risk_level: str = "medium"):
        self.name = name
        self.risk_level = risk_level
    
    @abstractmethod
    def generate_signal(self, symbol: str, market_data: Dict[str, Any], 
                       product: ProductBase) -> Dict[str, Any]:
        """生成交易信号"""
        pass
    
    @abstractmethod
    def calculate_position_size(self, symbol: str, account_balance: float,
                              market_data: Dict[str, Any]) -> float:
        """计算仓位大小"""
        pass


class MomentumTradingStrategy(TradingStrategy):
    """动量交易策略"""
    
    def __init__(self):
        super().__init__("动量交易", risk_level="high")
    
    def generate_signal(self, symbol: str, market_data: Dict[str, Any], 
                       product: ProductBase) -> Dict[str, Any]:
        """生成动量交易信号"""
        signal = {
            'symbol': symbol,
            'strategy': self.name,
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'signal': 'HOLD',  # 默认持有
            'confidence': 0,
            'reason': []
        }
        
        # 动量指标分析
        price_change = market_data.get('change_percent', 0)
        volume_ratio = market_data.get('volume', 0) / market_data.get('avg_volume', 1)
        rsi = market_data.get('rsi', 50)
        
        # 强势突破信号
        if (price_change > 0.03 and volume_ratio > 1.5 and rsi < 70):
            signal['signal'] = 'BUY'
            signal['confidence'] = 0.7
            signal['reason'].append("强势突破，量价齐升")
        
        # 超卖反弹信号
        elif (price_change < -0.02 and rsi < 30 and volume_ratio > 1.2):
            signal['signal'] = 'BUY'
            signal['confidence'] = 0.6
            signal['reason'].append("超卖反弹，技术修复")
        
        # 趋势反转信号
        elif (price_change < -0.05 and rsi > 70):
            signal['signal'] = 'SELL'
            signal['confidence'] = 0.65
            signal['reason'].append("趋势反转，获利了结")
        
        return signal
    
    def calculate_position_size(self, symbol: str, account_balance: float,
                              market_data: Dict[str, Any]) -> float:
        """计算动量策略仓位"""
        volatility = market_data.get('volatility', 0.02)
        confidence = market_data.get('signal_confidence', 0.5)
        
        # 基于波动率和置信度计算仓位
        base_size = account_balance * 0.1  # 基础仓位10%
        risk_adjusted = base_size * (1 - volatility * 10)  # 波动率调整
        confidence_adjusted = risk_adjusted * confidence  # 置信度调整
        
        return max(confidence_adjusted, account_balance * 0.01)  # 最小仓位1%


class MeanReversionStrategy(TradingStrategy):
    """均值回归策略"""
    
    def __init__(self):
        super().__init__("均值回归", risk_level="medium")
    
    def generate_signal(self, symbol: str, market_data: Dict[str, Any], 
                       product: ProductBase) -> Dict[str, Any]:
        """生成均值回归信号"""
        signal = {
            'symbol': symbol,
            'strategy': self.name,
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'signal': 'HOLD',
            'confidence': 0,
            'reason': []
        }
        
        current_price = market_data.get('last_done', 0)
        ma20 = market_data.get('ma20', current_price)
        rsi = market_data.get('rsi', 50)
        
        # 计算价格偏离度
        deviation = (current_price - ma20) / ma20
        
        # 超卖回归信号
        if deviation < -0.1 and rsi < 35:
            signal['signal'] = 'BUY'
            signal['confidence'] = 0.75
            signal['reason'].append(f"价格偏离均值{deviation:.1%}，超卖回归")
        
        # 超买回归信号
        elif deviation > 0.1 and rsi > 65:
            signal['signal'] = 'SELL'
            signal['confidence'] = 0.7
            signal['reason'].append(f"价格偏离均值{deviation:.1%}，超买回归")
        
        return signal
    
    def calculate_position_size(self, symbol: str, account_balance: float,
                              market_data: Dict[str, Any]) -> float:
        """计算均值回归策略仓位"""
        deviation = abs((market_data.get('last_done', 0) - market_data.get('ma20', 1)) / 
                       market_data.get('ma20', 1))
        
        # 偏离度越大，仓位越大
        position_size = account_balance * 0.08 * min(deviation * 10, 1)
        return max(position_size, account_balance * 0.02)  # 最小仓位2%


class RiskManager:
    """风险管理器"""
    
    def __init__(self, config_manager: ConfigManager):
        self.config_manager = config_manager
        self.trading_config = config_manager.get_trading_config()
    
    def validate_trade(self, symbol: str, signal: Dict[str, Any], 
                      proposed_size: float, current_positions: Dict[str, Any]) -> Dict[str, Any]:
        """验证交易是否满足风险要求"""
        validation = {
            'approved': True,
            'adjusted_size': proposed_size,
            'reasons': [],
            'risk_level': 'LOW'
        }
        
        # 单只股票最大仓位限制
        max_position_size = self.trading_config.get('max_position_size', 0.1)
        if proposed_size > current_positions.get('total_equity', 1) * max_position_size:
            validation['adjusted_size'] = current_positions['total_equity'] * max_position_size
            validation['reasons'].append(f"超过单只股票最大仓位限制({max_position_size:.1%})")
        
        # 信号置信度检查
        if signal.get('confidence', 0) < 0.5:
            validation['approved'] = False
            validation['reasons'].append("信号置信度过低")
            validation['risk_level'] = 'HIGH'
        
        # 波动率风险检查
        volatility = signal.get('market_data', {}).get('volatility', 0)
        if volatility > 0.1:
            validation['risk_level'] = 'HIGH'
            validation['reasons'].append("波动率过高")
        
        return validation
    
    def calculate_stop_loss(self, entry_price: float, signal: Dict[str, Any]) -> float:
        """计算止损价格"""
        stop_loss_ratio = self.trading_config.get('stop_loss', 0.05)
        
        if signal['signal'] == 'BUY':
            return entry_price * (1 - stop_loss_ratio)
        else:  # SELL信号（做空）
            return entry_price * (1 + stop_loss_ratio)
    
    def calculate_take_profit(self, entry_price: float, signal: Dict[str, Any]) -> float:
        """计算止盈价格"""
        take_profit_ratio = self.trading_config.get('take_profit', 0.15)
        
        if signal['signal'] == 'BUY':
            return entry_price * (1 + take_profit_ratio)
        else:  # SELL信号（做空）
            return entry_price * (1 - take_profit_ratio)


class TradingEngine:
    """交易执行引擎"""
    
    def __init__(self, config_manager: ConfigManager):
        self.config_manager = config_manager
        self.trade_ctx: Optional[TradeContext] = None
        self.risk_manager = RiskManager(config_manager)
        self.strategies = self._initialize_strategies()
        self._connect_trading_api()
    
    def _initialize_strategies(self) -> Dict[str, TradingStrategy]:
        """初始化交易策略"""
        return {
            'momentum': MomentumTradingStrategy(),
            'mean_reversion': MeanReversionStrategy()
        }
    
    def _connect_trading_api(self):
        """连接交易API"""
        try:
            api_config = self.config_manager.get_api_config()
            if not all([api_config.get('app_key'), api_config.get('app_secret'), api_config.get('access_token')]):
                print("交易API配置不完整")
                return
            
            config = Config.from_env()
            self.trade_ctx = TradeContext(config)
            print("交易API连接成功")
        except Exception as e:
            print(f"交易API连接失败: {e}")
    
    def execute_trade(self, symbol: str, signal: Dict[str, Any], 
                     product: ProductBase, account_info: Dict[str, Any]) -> Dict[str, Any]:
        """执行交易"""
        if not self.trade_ctx or not signal.get('approved', False):
            return {'success': False, 'reason': '交易未获批准或API未连接'}
        
        try:
            # 获取交易参数
            trading_params = product.get_trading_parameters()
            order_side = OrderSide.Buy if signal['signal'] == 'BUY' else OrderSide.Sell
            
            # 计算订单数量
            quantity = self._calculate_order_quantity(signal, trading_params, account_info)
            if quantity <= 0:
                return {'success': False, 'reason': '计算订单数量失败'}
            
            # 提交订单
            order_result = self.trade_ctx.submit_order(
                symbol=symbol,
                order_type=OrderType.LO,
                side=order_side,
                submitted_quantity=quantity,
                time_in_force=TimeInForceType.Day,
                submitted_price=Decimal(str(signal.get('entry_price', 0)))
            )
            
            return {
                'success': True,
                'order_id': order_result.order_id,
                'symbol': symbol,
                'side': signal['signal'],
                'quantity': quantity,
                'price': float(signal.get('entry_price', 0)),
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            
        except Exception as e:
            return {'success': False, 'reason': f'交易执行失败: {e}'}
    
    def _calculate_order_quantity(self, signal: Dict[str, Any], 
                                trading_params: Dict[str, Any], 
                                account_info: Dict[str, Any]) -> int:
        """计算订单数量"""
        position_size = signal.get('adjusted_size', 0)
        current_price = signal.get('entry_price', 1)
        
        if position_size <= 0 or current_price <= 0:
            return 0
        
        # 计算理论数量
        theoretical_quantity = position_size / current_price
        
        # 考虑最小交易单位
        min_trade_size = trading_params.get('min_trade_size', 100)
        quantity = max(theoretical_quantity, min_trade_size)
        
        # 考虑数量精度
        quantity_precision = trading_params.get('quantity_precision', 0)
        quantity = round(quantity, quantity_precision)
        
        return int(quantity)
    
    def get_account_balance(self) -> Dict[str, Any]:
        """获取账户余额信息"""
        if not self.trade_ctx:
            return {}
        
        try:
            # 获取账户信息
            account_balance = self.trade_ctx.account_balance()
            return {
                'total_cash': float(account_balance.total_cash),
                'max_power_short': float(account_balance.max_power_short),
                'net_cash_power': float(account_balance.net_cash_power),
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
        except Exception as e:
            print(f"获取账户余额失败: {e}")
            return {}
    
    def get_positions(self) -> List[Dict[str, Any]]:
        """获取持仓信息"""
        if not self.trade_ctx:
            return []
        
        try:
            positions = self.trade_ctx.positions()
            result = []
            for pos in positions:
                result.append({
                    'symbol': pos.symbol,
                    'quantity': pos.quantity,
                    'available_quantity': pos.available_quantity,
                    'currency': pos.currency,
                    'cost_price': float(pos.cost_price),
                    'market': pos.market
                })
            return result
        except Exception as e:
            print(f"获取持仓信息失败: {e}")
            return []
    
    def cancel_order(self, order_id: str) -> bool:
        """取消订单"""
        if not self.trade_ctx:
            return False
        
        try:
            self.trade_ctx.withdraw_order(order_id)
            return True
        except Exception as e:
            print(f"取消订单失败: {e}")
            return False


if __name__ == "__main__":
    # 测试交易引擎
    config_mgr = ConfigManager()
    trading_engine = TradingEngine(config_mgr)
    
    # 测试获取账户信息
    account_info = trading_engine.get_account_balance()
    print("账户信息:", account_info)
    
    # 测试获取持仓
    positions = trading_engine.get_positions()
    print("持仓信息:", positions)