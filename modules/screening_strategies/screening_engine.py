"""筛选策略模块
支持技术面、基本面、消息面等多种筛选策略
"""

import pandas as pd
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta

from ..config.config_manager import ProductType
from ..product_types.product_factory import ProductBase


class ScreeningStrategy(ABC):
    """筛选策略基类"""
    
    def __init__(self, name: str, weight: float = 1.0):
        self.name = name
        self.weight = weight
    
    @abstractmethod
    def calculate_score(self, symbol: str, market_data: Dict[str, Any], 
                       product: ProductBase) -> Dict[str, Any]:
        """计算筛选分数"""
        pass
    
    @abstractmethod
    def get_required_data(self) -> List[str]:
        """获取策略所需的数据字段"""
        pass


class TechnicalScreeningStrategy(ScreeningStrategy):
    """技术面筛选策略"""
    
    def __init__(self):
        super().__init__("技术面筛选", weight=0.4)
    
    def calculate_score(self, symbol: str, market_data: Dict[str, Any], 
                       product: ProductBase) -> Dict[str, Any]:
        """计算技术面分数"""
        score = 0
        reasons = []
        
        # RSI指标分析
        rsi = market_data.get('rsi', 0)
        if 30 <= rsi <= 70:
            score += 2
            reasons.append("RSI处于合理区间")
        elif rsi < 30:
            score += 3
            reasons.append("RSI显示超卖，反弹概率大")
        elif rsi > 70:
            score -= 1
            reasons.append("RSI显示超买，注意风险")
        
        # 移动平均线分析
        ma5 = market_data.get('ma5', 0)
        ma20 = market_data.get('ma20', 0)
        current_price = market_data.get('last_done', 0)
        
        if current_price > ma5 > ma20:
            score += 3
            reasons.append("价格在均线之上，趋势向上")
        elif current_price < ma5 < ma20:
            score -= 2
            reasons.append("价格在均线之下，趋势向下")
        
        # 成交量分析
        volume = market_data.get('volume', 0)
        avg_volume = market_data.get('avg_volume', volume)
        if volume > avg_volume * 1.5:
            score += 1
            reasons.append("成交量放大，关注度提升")
        
        # 波动率分析
        volatility = market_data.get('volatility', 0)
        if 0.01 <= volatility <= 0.05:
            score += 1
            reasons.append("波动率适中，风险可控")
        elif volatility > 0.1:
            score -= 1
            reasons.append("波动率过高，风险较大")
        
        return {
            'score': max(0, min(10, score)),
            'reasons': reasons,
            'weight': self.weight
        }
    
    def get_required_data(self) -> List[str]:
        return ['rsi', 'ma5', 'ma20', 'last_done', 'volume', 'avg_volume', 'volatility']


class FundamentalScreeningStrategy(ScreeningStrategy):
    """基本面筛选策略（适用于股票和ETF）"""
    
    def __init__(self):
        super().__init__("基本面筛选", weight=0.3)
    
    def calculate_score(self, symbol: str, market_data: Dict[str, Any], 
                       product: ProductBase) -> Dict[str, Any]:
        """计算基本面分数"""
        score = 0
        reasons = []
        
        # 仅对股票和ETF进行基本面分析
        if product.product_type not in [ProductType.STOCK, ProductType.ETF]:
            return {'score': 0, 'reasons': ['该产品类型不支持基本面分析'], 'weight': self.weight}
        
        # 市值分析
        market_cap = market_data.get('market_cap', 0)
        if market_cap > 10e9:  # 大于100亿
            score += 2
            reasons.append("大市值公司，稳定性较好")
        elif market_cap > 1e9:  # 10-100亿
            score += 1
            reasons.append("中等市值公司，成长性较好")
        
        # 估值指标（PE、PB）
        pe_ratio = market_data.get('pe_ratio', 0)
        pb_ratio = market_data.get('pb_ratio', 0)
        
        if 0 < pe_ratio < 15:
            score += 2
            reasons.append("市盈率较低，估值合理")
        elif pe_ratio > 50:
            score -= 1
            reasons.append("市盈率偏高，估值较贵")
        
        if 0 < pb_ratio < 2:
            score += 1
            reasons.append("市净率合理")
        
        # 股息率分析
        dividend_yield = market_data.get('dividend_yield', 0)
        if dividend_yield > 0.03:  # 3%以上
            score += 1
            reasons.append("股息率较高，具有防御性")
        
        return {
            'score': max(0, min(10, score)),
            'reasons': reasons,
            'weight': self.weight
        }
    
    def get_required_data(self) -> List[str]:
        return ['market_cap', 'pe_ratio', 'pb_ratio', 'dividend_yield']


class SentimentScreeningStrategy(ScreeningStrategy):
    """市场情绪筛选策略"""
    
    def __init__(self):
        super().__init__("市场情绪筛选", weight=0.2)
    
    def calculate_score(self, symbol: str, market_data: Dict[str, Any], 
                       product: ProductBase) -> Dict[str, Any]:
        """计算市场情绪分数"""
        score = 0
        reasons = []
        
        # 分析师评级数据
        analyst_data = market_data.get('analyst_data', {})
        if analyst_data:
            buy_percentage = analyst_data.get('buy_percentage', 0)
            if buy_percentage > 70:
                score += 3
                reasons.append(f"分析师强烈看好，买入评级占比{buy_percentage}%")
            elif buy_percentage > 50:
                score += 2
                reasons.append(f"分析师普遍看好，买入评级占比{buy_percentage}%")
            
            reports_count = analyst_data.get('reports_count', 0)
            if reports_count >= 3:
                score += 1
                reasons.append("近期研究报告较多，关注度高")
        
        # 新闻情绪分析
        news_sentiment = market_data.get('news_sentiment', 0)
        if news_sentiment > 0.7:
            score += 2
            reasons.append("新闻情绪积极")
        elif news_sentiment < 0.3:
            score -= 1
            reasons.append("新闻情绪偏负面")
        
        # 社交媒体热度
        social_heat = market_data.get('social_heat', 0)
        if 0.3 <= social_heat <= 0.7:
            score += 1
            reasons.append("社交媒体关注度适中")
        elif social_heat > 0.7:
            score -= 1
            reasons.append("社交媒体过热，注意风险")
        
        return {
            'score': max(0, min(10, score)),
            'reasons': reasons,
            'weight': self.weight
        }
    
    def get_required_data(self) -> List[str]:
        return ['analyst_data', 'news_sentiment', 'social_heat']


class DerivativeScreeningStrategy(ScreeningStrategy):
    """衍生品筛选策略（适用于窝轮、牛熊证、期权）"""
    
    def __init__(self):
        super().__init__("衍生品筛选", weight=0.5)
    
    def calculate_score(self, symbol: str, market_data: Dict[str, Any], 
                       product: ProductBase) -> Dict[str, Any]:
        """计算衍生品筛选分数"""
        score = 0
        reasons = []
        
        # 仅对衍生品进行特定分析
        if product.product_type not in [ProductType.WARRANT, ProductType.CBBC, ProductType.OPTION]:
            return {'score': 0, 'reasons': ['该产品类型不支持衍生品分析'], 'weight': self.weight}
        
        # 杠杆分析
        leverage = market_data.get('leverage', 1)
        if 3 <= leverage <= 8:
            score += 2
            reasons.append(f"杠杆倍数适中({leverage}x)")
        elif leverage > 10:
            score -= 2
            reasons.append(f"杠杆倍数过高({leverage}x)，风险较大")
        
        # 时间价值分析
        days_to_expiry = market_data.get('days_to_expiry', 0)
        if days_to_expiry > 30:
            score += 2
            reasons.append(f"剩余时间充足({days_to_expiry}天)")
        elif days_to_expiry < 7:
            score -= 3
            reasons.append(f"即将到期({days_to_expiry}天)，时间价值快速衰减")
        
        # 隐含波动率分析
        implied_vol = market_data.get('implied_volatility', 0)
        if 0.2 <= implied_vol <= 0.5:
            score += 1
            reasons.append("隐含波动率合理")
        elif implied_vol > 0.8:
            score -= 1
            reasons.append("隐含波动率过高，定价较贵")
        
        # 流动性分析
        volume = market_data.get('volume', 0)
        if volume > 1000000:  # 成交量大于100万
            score += 1
            reasons.append("流动性良好")
        
        return {
            'score': max(0, min(10, score)),
            'reasons': reasons,
            'weight': self.weight
        }
    
    def get_required_data(self) -> List[str]:
        return ['leverage', 'days_to_expiry', 'implied_volatility', 'volume']


class ScreeningEngine:
    """筛选引擎"""
    
    def __init__(self):
        self.strategies = self._initialize_strategies()
    
    def _initialize_strategies(self) -> Dict[str, ScreeningStrategy]:
        """初始化筛选策略"""
        return {
            'technical': TechnicalScreeningStrategy(),
            'fundamental': FundamentalScreeningStrategy(),
            'sentiment': SentimentScreeningStrategy(),
            'derivative': DerivativeScreeningStrategy()
        }
    
    def screen_symbol(self, symbol: str, market_data: Dict[str, Any], 
                     product: ProductBase, enabled_strategies: List[str] = None) -> Dict[str, Any]:
        """筛选单个标的"""
        if enabled_strategies is None:
            enabled_strategies = list(self.strategies.keys())
        
        total_score = 0
        total_weight = 0
        all_reasons = []
        strategy_results = {}
        
        for strategy_name in enabled_strategies:
            if strategy_name in self.strategies:
                strategy = self.strategies[strategy_name]
                
                # 检查是否有所需数据
                required_data = strategy.get_required_data()
                if all(field in market_data for field in required_data):
                    result = strategy.calculate_score(symbol, market_data, product)
                    
                    strategy_results[strategy_name] = {
                        'score': result['score'],
                        'reasons': result['reasons'],
                        'weight': result['weight']
                    }
                    
                    total_score += result['score'] * result['weight']
                    total_weight += result['weight']
                    all_reasons.extend(result['reasons'])
        
        # 计算加权平均分
        if total_weight > 0:
            final_score = total_score / total_weight
        else:
            final_score = 0
        
        return {
            'symbol': symbol,
            'product_type': product.product_type.value,
            'final_score': round(final_score, 2),
            'strategy_results': strategy_results,
            'reasons': all_reasons,
            'analysis_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
    
    def batch_screen(self, symbols: List[str], market_data_list: List[Dict[str, Any]], 
                    products: List[ProductBase], enabled_strategies: List[str] = None) -> List[Dict[str, Any]]:
        """批量筛选标的"""
        results = []
        
        for symbol, market_data, product in zip(symbols, market_data_list, products):
            result = self.screen_symbol(symbol, market_data, product, enabled_strategies)
            results.append(result)
        
        # 按分数排序
        results.sort(key=lambda x: x['final_score'], reverse=True)
        return results
    
    def get_strategy_info(self) -> Dict[str, Any]:
        """获取策略信息"""
        return {
            strategy_name: {
                'name': strategy.name,
                'weight': strategy.weight,
                'required_data': strategy.get_required_data()
            }
            for strategy_name, strategy in self.strategies.items()
        }


if __name__ == "__main__":
    # 测试筛选引擎
    engine = ScreeningEngine()
    
    # 测试策略信息
    strategy_info = engine.get_strategy_info()
    print("可用筛选策略:")
    for name, info in strategy_info.items():
        print(f"- {name}: {info['name']} (权重: {info['weight']})")
    
    # 测试筛选功能
    test_data = {
        'rsi': 45,
        'ma5': 150.5,
        'ma20': 148.2,
        'last_done': 152.3,
        'volume': 5000000,
        'avg_volume': 3000000,
        'volatility': 0.03
    }
    
    from ..product_types.product_factory import ProductFactory
    product = ProductFactory.create_product("00700", ProductType.STOCK)
    
    result = engine.screen_symbol("00700", test_data, product)
    print(f"\n筛选结果: {result}")