"""回测引擎模块
支持历史数据回测和策略评估功能
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
import json
import os

from ..utils.common_utils import Logger, DateTimeUtils
from ..market_data.market_data_provider import MarketDataProvider
from ..screening_strategies.screening_engine import ScreeningEngine
from ..trading_execution.trading_engine import TradingEngine
from ..product_types.product_factory import ProductFactory
from ..config.config_manager import ConfigManager, Market, ProductType


class BacktestEngine:
    """回测引擎类"""
    
    def __init__(self, config_manager: ConfigManager):
        self.config_manager = config_manager
        self.data_provider = MarketDataProvider(config_manager)
        self.screening_engine = ScreeningEngine()
        self.trading_engine = TradingEngine(config_manager)
        self.logger = Logger("backtest_engine")
        
        # 回测配置
        self.backtest_config = self.config_manager.get_backtest_config()
    
    def run_backtest(self, 
                    start_date: str, 
                    end_date: str,
                    markets: List[Market],
                    products: List[ProductType],
                    strategy_config: Dict[str, Any] = None) -> Dict[str, Any]:
        """运行回测"""
        self.logger.info(f"开始回测: {start_date} 到 {end_date}")
        
        # 验证参数
        if not self._validate_backtest_params(start_date, end_date, markets, products):
            return {"success": False, "error": "参数验证失败"}
        
        # 初始化回测结果
        backtest_results = {
            "start_date": start_date,
            "end_date": end_date,
            "markets": [market.value for market in markets],
            "products": [product.value for product in products],
            "total_trading_days": 0,
            "total_trades": 0,
            "winning_trades": 0,
            "losing_trades": 0,
            "total_return": 0.0,
            "max_drawdown": 0.0,
            "sharpe_ratio": 0.0,
            "daily_returns": [],
            "trades": [],
            "portfolio_value_history": []
        }
        
        # 获取交易日历
        trading_days = self._get_trading_days(start_date, end_date, markets)
        if not trading_days:
            return {"success": False, "error": "没有找到交易日数据"}
        
        backtest_results["total_trading_days"] = len(trading_days)
        
        # 初始化投资组合
        portfolio = self._initialize_portfolio()
        
        # 按交易日进行回测
        for i, current_date in enumerate(trading_days):
            day_results = self._run_daily_backtest(
                current_date, portfolio, markets, products, strategy_config
            )
            
            # 更新投资组合
            portfolio = self._update_portfolio(portfolio, day_results)
            
            # 记录每日结果
            self._record_daily_results(backtest_results, portfolio, day_results, current_date)
            
            # 进度显示
            if (i + 1) % 10 == 0 or i == len(trading_days) - 1:
                progress = (i + 1) / len(trading_days) * 100
                self.logger.info(f"回测进度: {progress:.1f}% ({i+1}/{len(trading_days)})")
        
        # 计算最终指标
        final_results = self._calculate_final_metrics(backtest_results)
        
        self.logger.info(f"回测完成: 总收益率 {final_results['total_return']:.2f}%")
        
        return final_results
    
    def _validate_backtest_params(self, start_date: str, end_date: str, 
                                 markets: List[Market], products: List[ProductType]) -> bool:
        """验证回测参数"""
        try:
            start_dt = datetime.strptime(start_date, "%Y-%m-%d")
            end_dt = datetime.strptime(end_date, "%Y-%m-%d")
            
            if start_dt >= end_dt:
                self.logger.error("开始日期必须早于结束日期")
                return False
            
            if (end_dt - start_dt).days > 365 * 5:  # 限制5年回测
                self.logger.error("回测时间范围不能超过5年")
                return False
            
            if not markets:
                self.logger.error("必须指定至少一个市场")
                return False
            
            if not products:
                self.logger.error("必须指定至少一个产品类型")
                return False
            
            return True
            
        except ValueError:
            self.logger.error("日期格式错误，请使用 YYYY-MM-DD 格式")
            return False
    
    def _get_trading_days(self, start_date: str, end_date: str, 
                         markets: List[Market]) -> List[str]:
        """获取交易日历"""
        trading_days = []
        
        try:
            # 获取所有市场的交易日并合并
            all_days = set()
            for market in markets:
                market_days = self.data_provider.get_trading_days(
                    market.value, start_date, end_date
                )
                if market_days:
                    all_days.update(market_days)
            
            # 排序并返回
            trading_days = sorted(list(all_days))
            return trading_days
            
        except Exception as e:
            self.logger.error(f"获取交易日历失败: {e}")
            return []
    
    def _initialize_portfolio(self) -> Dict[str, Any]:
        """初始化投资组合"""
        initial_cash = self.backtest_config.get('initial_cash', 1000000.0)
        
        return {
            "cash": initial_cash,
            "positions": {},
            "total_value": initial_cash,
            "daily_pnl": 0.0,
            "cumulative_pnl": 0.0
        }
    
    def _run_daily_backtest(self, current_date: str, portfolio: Dict[str, Any],
                           markets: List[Market], products: List[ProductType],
                           strategy_config: Dict[str, Any]) -> Dict[str, Any]:
        """运行每日回测"""
        day_results = {
            "date": current_date,
            "screened_symbols": [],
            "executed_trades": [],
            "daily_return": 0.0,
            "portfolio_value": portfolio["total_value"]
        }
        
        try:
            # 模拟筛选过程
            screened_symbols = self._simulate_screening(current_date, markets, products)
            day_results["screened_symbols"] = screened_symbols
            
            # 模拟交易执行
            if screened_symbols:
                trades = self._simulate_trading(current_date, screened_symbols, portfolio, strategy_config)
                day_results["executed_trades"] = trades
            
            return day_results
            
        except Exception as e:
            self.logger.error(f"每日回测执行失败 {current_date}: {e}")
            return day_results
    
    def _simulate_screening(self, current_date: str, markets: List[Market],
                           products: List[ProductType]) -> List[Dict[str, Any]]:
        """模拟筛选过程"""
        screened_results = []
        
        for market in markets:
            for product in products:
                try:
                    # 获取历史数据（模拟）
                    symbols = self._get_historical_symbols(market, product, current_date)
                    
                    for symbol in symbols[:50]:  # 限制数量提高效率
                        # 模拟技术指标计算
                        technical_data = self._simulate_technical_analysis(symbol, current_date)
                        
                        if technical_data:
                            # 应用筛选策略
                            screening_result = self.screening_engine.screen_symbol(
                                symbol, technical_data, ProductFactory.create_product(symbol, product)
                            )
                            
                            if screening_result and screening_result.get('final_score', 0) >= 6.0:
                                screened_results.append(screening_result)
                
                except Exception as e:
                    self.logger.warning(f"筛选 {market.value} {product.value} 失败: {e}")
                    continue
        
        return screened_results
    
    def _simulate_trading(self, current_date: str, screened_symbols: List[Dict[str, Any]],
                         portfolio: Dict[str, Any], strategy_config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """模拟交易执行"""
        executed_trades = []
        
        # 按评分排序，选择前10个
        top_symbols = sorted(screened_symbols, key=lambda x: x['final_score'], reverse=True)[:10]
        
        for symbol_data in top_symbols:
            try:
                trade_result = self._execute_simulated_trade(
                    current_date, symbol_data, portfolio, strategy_config
                )
                
                if trade_result.get('success'):
                    executed_trades.append(trade_result)
            
            except Exception as e:
                self.logger.warning(f"模拟交易执行失败 {symbol_data['symbol']}: {e}")
                continue
        
        return executed_trades
    
    def _execute_simulated_trade(self, current_date: str, symbol_data: Dict[str, Any],
                                portfolio: Dict[str, Any], strategy_config: Dict[str, Any]) -> Dict[str, Any]:
        """执行模拟交易"""
        symbol = symbol_data['symbol']
        product_type = ProductType(symbol_data['product_type'])
        
        try:
            # 模拟市场数据
            simulated_data = self._simulate_market_data(symbol, current_date)
            if not simulated_data:
                return {'success': False, 'reason': '无法获取模拟数据'}
            
            # 生成交易信号
            from ..trading_execution.trading_engine import MomentumTradingStrategy
            strategy = MomentumTradingStrategy()
            signal = strategy.generate_signal(symbol, simulated_data, 
                                            ProductFactory.create_product(symbol, product_type))
            
            # 风险管理
            risk_result = self.trading_engine.risk_manager.validate_trade(
                symbol, signal, 
                strategy.calculate_position_size(symbol, portfolio['cash'], simulated_data),
                {'total_cash': portfolio['cash']}
            )
            
            if not risk_result['approved']:
                return {'success': False, 'reason': '风险验证未通过'}
            
            # 执行模拟交易
            trade_result = {
                'success': True,
                'symbol': symbol,
                'signal': signal['signal'],
                'entry_price': simulated_data.get('last_done', 0),
                'quantity': risk_result['adjusted_size'],
                'commission': risk_result['adjusted_size'] * simulated_data.get('last_done', 0) * 0.001,
                'timestamp': current_date
            }
            
            return trade_result
            
        except Exception as e:
            return {'success': False, 'reason': str(e)}
    
    def _simulate_technical_analysis(self, symbol: str, date: str) -> Dict[str, Any]:
        """模拟技术分析数据"""
        # 这里应该调用真实的历史数据API
        # 目前使用模拟数据
        import random
        
        return {
            'last_done': random.uniform(10, 200),
            'rsi': random.uniform(20, 80),
            'ma5': random.uniform(10, 200),
            'ma20': random.uniform(10, 200),
            'volume': random.randint(100000, 10000000),
            'change_rate': random.uniform(-0.1, 0.1)
        }
    
    def _simulate_market_data(self, symbol: str, date: str) -> Dict[str, Any]:
        """模拟市场数据"""
        # 这里应该调用真实的历史数据API
        # 目前使用模拟数据
        import random
        
        return {
            'symbol': symbol,
            'last_done': random.uniform(10, 200),
            'open': random.uniform(10, 200),
            'high': random.uniform(10, 200),
            'low': random.uniform(10, 200),
            'volume': random.randint(100000, 10000000),
            'turnover': random.uniform(1000000, 100000000),
            'timestamp': date
        }
    
    def _get_historical_symbols(self, market: Market, product: ProductType, 
                               date: str) -> List[str]:
        """获取历史标的列表（模拟）"""
        # 这里应该调用真实的历史标的API
        # 目前使用模拟数据
        base_symbols = {
            Market.HK: ['00700', '00941', '01299', '02318'],
            Market.US: ['AAPL', 'GOOGL', 'TSLA', 'MSFT'],
            Market.CN: ['000001', '600036', '601318', '000858']
        }
        
        return base_symbols.get(market, [])
    
    def _update_portfolio(self, portfolio: Dict[str, Any], 
                         day_results: Dict[str, Any]) -> Dict[str, Any]:
        """更新投资组合"""
        # 简化实现：只更新现金和总价值
        new_portfolio = portfolio.copy()
        
        # 计算当日盈亏
        daily_pnl = 0.0
        for trade in day_results['executed_trades']:
            if trade['success']:
                # 简化计算：假设所有交易都是买入，盈亏为0
                pass
        
        new_portfolio['daily_pnl'] = daily_pnl
        new_portfolio['cumulative_pnl'] += daily_pnl
        
        # 更新总价值（简化）
        if day_results['portfolio_value'] > 0:
            new_portfolio['total_value'] = day_results['portfolio_value']
        
        return new_portfolio
    
    def _record_daily_results(self, backtest_results: Dict[str, Any],
                            portfolio: Dict[str, Any], day_results: Dict[str, Any],
                            current_date: str):
        """记录每日结果"""
        # 记录交易
        backtest_results['trades'].extend(day_results['executed_trades'])
        
        # 记录投资组合价值
        backtest_results['portfolio_value_history'].append({
            'date': current_date,
            'value': portfolio['total_value']
        })
        
        # 记录每日收益率
        if len(backtest_results['portfolio_value_history']) > 1:
            prev_value = backtest_results['portfolio_value_history'][-2]['value']
            curr_value = portfolio['total_value']
            daily_return = (curr_value - prev_value) / prev_value if prev_value > 0 else 0
            backtest_results['daily_returns'].append(daily_return)
        else:
            backtest_results['daily_returns'].append(0.0)
    
    def _calculate_final_metrics(self, backtest_results: Dict[str, Any]) -> Dict[str, Any]:
        """计算最终指标"""
        if not backtest_results['daily_returns']:
            return backtest_results
        
        returns = np.array(backtest_results['daily_returns'])
        
        # 总收益率
        total_return = (backtest_results['portfolio_value_history'][-1]['value'] / 
                       backtest_results['portfolio_value_history'][0]['value'] - 1) * 100
        
        # 最大回撤
        cumulative_returns = np.cumprod(1 + returns)
        peak = np.maximum.accumulate(cumulative_returns)
        drawdown = (cumulative_returns - peak) / peak
        max_drawdown = np.min(drawdown) * 100
        
        # 夏普比率（年化）
        avg_return = np.mean(returns) * 252  # 年化
        std_return = np.std(returns) * np.sqrt(252)  # 年化标准差
        sharpe_ratio = avg_return / std_return if std_return > 0 else 0
        
        # 交易统计
        successful_trades = [t for t in backtest_results['trades'] if t.get('success')]
        winning_trades = len([t for t in successful_trades if t.get('pnl', 0) > 0])
        
        backtest_results.update({
            'total_return': total_return,
            'max_drawdown': max_drawdown,
            'sharpe_ratio': sharpe_ratio,
            'total_trades': len(successful_trades),
            'winning_trades': winning_trades,
            'losing_trades': len(successful_trades) - winning_trades,
            'win_rate': winning_trades / len(successful_trades) if successful_trades else 0
        })
        
        return backtest_results
    
    def generate_backtest_report(self, results: Dict[str, Any]) -> str:
        """生成回测报告"""
        report = f"""
=== 回测报告 ===
回测期间: {results['start_date']} 到 {results['end_date']}
市场: {', '.join(results['markets'])}
产品: {', '.join(results['products'])}

绩效指标:
- 总收益率: {results.get('total_return', 0):.2f}%
- 最大回撤: {results.get('max_drawdown', 0):.2f}%
- 夏普比率: {results.get('sharpe_ratio', 0):.2f}
- 交易天数: {results.get('total_trading_days', 0)}

交易统计:
- 总交易次数: {results.get('total_trades', 0)}
- 盈利交易: {results.get('winning_trades', 0)}
- 亏损交易: {results.get('losing_trades', 0)}
- 胜率: {results.get('win_rate', 0)*100:.1f}%

投资组合:
- 期初价值: {results['portfolio_value_history'][0]['value']:,.2f}
- 期末价值: {results['portfolio_value_history'][-1]['value']:,.2f}
"""
        
        # 保存报告到文件
        report_file = f"backtest_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(report)
        
        self.logger.info(f"回测报告已保存: {report_file}")
        return report