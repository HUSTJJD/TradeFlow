"""产品类型模块
定义不同产品（股票、ETF、窝轮、牛熊证、期权）的特性和行为
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List
from enum import Enum
from datetime import datetime

from ..config.config_manager import ProductType


class ProductBase(ABC):
    """产品基类"""
    
    def __init__(self, symbol: str, product_type: ProductType):
        self.symbol = symbol
        self.product_type = product_type
        self.analysis_factors = []
    
    @abstractmethod
    def get_screening_factors(self) -> List[str]:
        """获取筛选因子"""
        pass
    
    @abstractmethod
    def get_trading_parameters(self) -> Dict[str, Any]:
        """获取交易参数"""
        pass
    
    @abstractmethod
    def validate_trading_conditions(self, market_data: Dict[str, Any]) -> bool:
        """验证交易条件"""
        pass


class StockProduct(ProductBase):
    """股票产品"""
    
    def __init__(self, symbol: str):
        super().__init__(symbol, ProductType.STOCK)
        self.analysis_factors = [
            "technical_indicators",  # 技术指标
            "fundamental_analysis",  # 基本面分析
            "analyst_ratings",       # 分析师评级
            "market_sentiment",      # 市场情绪
            "volume_analysis"        # 成交量分析
        ]
    
    def get_screening_factors(self) -> List[str]:
        return [
            "price_momentum",        # 价格动量
            "volatility",            # 波动率
            "liquidity",             # 流动性
            "valuation_metrics",     # 估值指标
            "growth_potential"       # 成长潜力
        ]
    
    def get_trading_parameters(self) -> Dict[str, Any]:
        return {
            "min_trade_size": 100,           # 最小交易数量
            "price_precision": 2,            # 价格精度
            "quantity_precision": 0,         # 数量精度
            "allow_fractional": False,       # 是否允许碎股
            "trading_hours": "market_hours"  # 交易时间
        }
    
    def validate_trading_conditions(self, market_data: Dict[str, Any]) -> bool:
        # 检查基本交易条件
        required_fields = ['last_done', 'volume', 'prev_close']
        if not all(field in market_data for field in required_fields):
            return False
        
        # 检查价格有效性
        if market_data['last_done'] <= 0:
            return False
        
        # 检查成交量有效性
        if market_data['volume'] <= 0:
            return False
        
        return True


class ETFProduct(ProductBase):
    """ETF产品"""
    
    def __init__(self, symbol: str):
        super().__init__(symbol, ProductType.ETF)
        self.analysis_factors = [
            "nav_premium_discount",  # 净值溢价折价
            "tracking_error",        # 跟踪误差
            "liquidity_analysis",    # 流动性分析
            "expense_ratio",         # 费用比率
            "underlying_assets"      # 底层资产
        ]
    
    def get_screening_factors(self) -> List[str]:
        return [
            "premium_discount_rate", # 溢价折价率
            "daily_volume",          # 日成交量
            "tracking_performance",  # 跟踪表现
            "expense_efficiency",    # 费用效率
            "diversification"        # 分散度
        ]
    
    def get_trading_parameters(self) -> Dict[str, Any]:
        return {
            "min_trade_size": 1,             # 最小交易数量
            "price_precision": 3,            # 价格精度
            "quantity_precision": 0,         # 数量精度
            "allow_fractional": True,        # 允许碎股
            "trading_hours": "market_hours"  # 交易时间
        }
    
    def validate_trading_conditions(self, market_data: Dict[str, Any]) -> bool:
        return StockProduct.validate_trading_conditions(self, market_data)


class WarrantProduct(ProductBase):
    """窝轮产品"""
    
    def __init__(self, symbol: str):
        super().__init__(symbol, ProductType.WARRANT)
        self.analysis_factors = [
            "implied_volatility",    # 隐含波动率
            "time_decay",            # 时间衰减
            "leverage_ratio",        # 杠杆比率
            "underlying_performance", # 标的资产表现
            "moneyness"              # 价内价外程度
        ]
    
    def get_screening_factors(self) -> List[str]:
        return [
            "leverage_multiplier",   # 杠杆倍数
            "time_to_expiry",        # 剩余时间
            "implied_volatility",    # 隐含波动率
            "delta_value",           # Delta值
            "liquidity_score"        # 流动性评分
        ]
    
    def get_trading_parameters(self) -> Dict[str, Any]:
        return {
            "min_trade_size": 1000,          # 最小交易数量
            "price_precision": 4,            # 价格精度
            "quantity_precision": 0,         # 数量精度
            "allow_fractional": False,       # 不允许碎股
            "trading_hours": "extended_hours" # 延长交易时间
        }
    
    def validate_trading_conditions(self, market_data: Dict[str, Any]) -> bool:
        # 窝轮特有的验证条件
        if not StockProduct.validate_trading_conditions(self, market_data):
            return False
        
        # 检查是否接近到期日
        expiry_date = market_data.get('expiry_date')
        if expiry_date:
            days_to_expiry = (datetime.strptime(expiry_date, '%Y-%m-%d') - datetime.now()).days
            if days_to_expiry < 7:  # 距离到期日不足7天
                return False
        
        return True


class CBBCProduct(ProductBase):
    """牛熊证产品"""
    
    def __init__(self, symbol: str):
        super().__init__(symbol, ProductType.CBBC)
        self.analysis_factors = [
            "knock_out_level",       # 收回价
            "funding_cost",          # 财务费用
            "leverage_effect",       # 杠杆效应
            "underlying_trend",      # 标的趋势
            "risk_management"        # 风险管理
        ]
    
    def get_screening_factors(self) -> List[str]:
        return [
            "distance_to_knock_out", # 距离收回价
            "effective_leverage",    # 有效杠杆
            "funding_rate",          # 财务费率
            "liquidity_indicator",   # 流动性指标
            "risk_reward_ratio"      # 风险收益比
        ]
    
    def get_trading_parameters(self) -> Dict[str, Any]:
        return {
            "min_trade_size": 1000,          # 最小交易数量
            "price_precision": 4,            # 价格精度
            "quantity_precision": 0,         # 数量精度
            "allow_fractional": False,       # 不允许碎股
            "trading_hours": "extended_hours" # 延长交易时间
        }
    
    def validate_trading_conditions(self, market_data: Dict[str, Any]) -> bool:
        if not StockProduct.validate_trading_conditions(self, market_data):
            return False
        
        # 检查是否接近收回价
        knock_out_level = market_data.get('knock_out_level')
        current_price = market_data.get('last_done', 0)
        if knock_out_level and current_price:
            distance_ratio = abs(current_price - knock_out_level) / knock_out_level
            if distance_ratio < 0.05:  # 距离收回价不足5%
                return False
        
        return True


class OptionProduct(ProductBase):
    """期权产品"""
    
    def __init__(self, symbol: str):
        super().__init__(symbol, ProductType.OPTION)
        self.analysis_factors = [
            "greeks_analysis",       # 希腊字母分析
            "volatility_smile",      # 波动率微笑
            "open_interest",         # 未平仓合约
            "volume_analysis",       # 成交量分析
            "time_value_decay"       # 时间价值衰减
        ]
    
    def get_screening_factors(self) -> List[str]:
        return [
            "implied_volatility",    # 隐含波动率
            "delta_exposure",        # Delta暴露
            "theta_decay",           # Theta衰减
            "volume_open_interest",  # 成交量/未平仓比
            "moneyness_ratio"        # 价内价外比率
        ]
    
    def get_trading_parameters(self) -> Dict[str, Any]:
        return {
            "min_trade_size": 1,             # 最小交易数量（合约）
            "price_precision": 3,            # 价格精度
            "quantity_precision": 0,         # 数量精度
            "allow_fractional": False,       # 不允许碎股
            "trading_hours": "extended_hours" # 延长交易时间
        }
    
    def validate_trading_conditions(self, market_data: Dict[str, Any]) -> bool:
        if not StockProduct.validate_trading_conditions(self, market_data):
            return False
        
        # 期权特有的验证条件
        expiry_date = market_data.get('expiry_date')
        if expiry_date:
            days_to_expiry = (datetime.strptime(expiry_date, '%Y-%m-%d') - datetime.now()).days
            if days_to_expiry < 3:  # 距离到期日不足3天
                return False
        
        return True


class ProductFactory:
    """产品工厂"""
    
    @staticmethod
    def create_product(symbol: str, product_type: ProductType) -> ProductBase:
        """创建产品实例"""
        product_map = {
            ProductType.STOCK: StockProduct,
            ProductType.ETF: ETFProduct,
            ProductType.WARRANT: WarrantProduct,
            ProductType.CBBC: CBBCProduct,
            ProductType.OPTION: OptionProduct
        }
        
        product_class = product_map.get(product_type)
        if not product_class:
            raise ValueError(f"不支持的产品类型: {product_type}")
        
        return product_class(symbol)
    
    @staticmethod
    def detect_product_type(symbol: str) -> ProductType:
        """根据股票代码检测产品类型"""
        # 实际应用中需要调用API获取准确的证券类型
        # 这里使用简单的规则进行判断
        
        if symbol.endswith('.US') or symbol.endswith('.OTC'):
            # 美股市场
            if symbol.endswith('W') or 'WARRANT' in symbol.upper():
                return ProductType.WARRANT
            elif 'OPTION' in symbol.upper() or 'CALL' in symbol.upper() or 'PUT' in symbol.upper():
                return ProductType.OPTION
            else:
                return ProductType.STOCK
        elif len(symbol) == 5 and symbol.startswith(('0', '1', '2', '3', '4', '5', '6', '7', '8', '9')):
            # 港股市场
            if symbol.endswith(('C', 'P')):  # 窝轮代码特征
                return ProductType.WARRANT
            elif symbol.endswith(('A', 'B')):  # 牛熊证代码特征
                return ProductType.CBBC
            elif '2800' in symbol or '2828' in symbol:  # ETF代码特征
                return ProductType.ETF
            else:
                return ProductType.STOCK
        elif len(symbol) == 6 and symbol.startswith(('0', '3', '6')):
            # A股市场
            if symbol.startswith('51'):  # ETF代码特征
                return ProductType.ETF
            else:
                return ProductType.STOCK
        else:
            return ProductType.STOCK  # 默认返回股票


if __name__ == "__main__":
    # 测试产品工厂
    factory = ProductFactory()
    
    # 测试创建不同产品
    stock = factory.create_product("00700", ProductType.STOCK)
    print(f"股票产品分析因子: {stock.analysis_factors}")
    
    etf = factory.create_product("02800", ProductType.ETF)
    print(f"ETF产品交易参数: {etf.get_trading_parameters()}")
    
    # 测试产品类型检测
    symbol = "00700"
    detected_type = factory.detect_product_type(symbol)
    print(f"股票代码 {symbol} 的产品类型: {detected_type}")