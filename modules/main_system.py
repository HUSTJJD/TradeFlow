"""主系统模块
整合所有模块功能，实现完整的交易系统（支持多券商API）
"""

import time
import schedule
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional

from .config.config_manager import ConfigManager, Market, ProductType
from .market_data.market_data_provider import MarketDataProvider
from .product_types.product_factory import ProductFactory
from .screening_strategies.screening_engine import ScreeningEngine
from .trading_execution.trading_engine import TradingEngine
from .utils.common_utils import DateTimeUtils, Logger
from .backtesting.backtest_engine import BacktestEngine
from .broker_apis.broker_manager import BrokerManager


class TradingSystem:
    """交易系统主类（支持多券商API）"""
    
    def __init__(self, config_path: str = "config.yaml"):
        self.config_manager = ConfigManager(config_path)
        self.broker_manager = BrokerManager(self.config_manager.get_all_broker_configs())
        self.data_provider = MarketDataProvider(self.config_manager)
        self.screening_engine = ScreeningEngine()
        self.trading_engine = TradingEngine(self.config_manager)
        self.backtest_engine = BacktestEngine(self.config_manager)
        self.logger = Logger("trading_system")
        
        # 系统状态
        self.system_status = {
            "last_screening_time": None,
            "last_trading_time": None,
            "last_backtest_time": None,
            "total_screened_symbols": 0,
            "total_trades_executed": 0,
            "total_backtests_run": 0,
            "system_start_time": datetime.now(),
            "active_brokers": len(self.broker_manager.active_brokers),
            "broker_status": self.broker_manager.get_system_status()
        }
    
    def run_screening_mode(self):
        """运行筛选模式（非交易时段）"""
        if not self._is_screening_time():
            self.logger.info("当前不是筛选模式运行时间")
            return []
        
        self.logger.info("开始运行筛选模式...")
        
        # 获取所有启用的市场和产品
        enabled_markets = self._get_enabled_markets()
        enabled_products = self._get_enabled_products()
        
        screened_results = []
        
        for market in enabled_markets:
            for product_type in enabled_products:
                if self.config_manager.is_product_enabled(product_type):
                    results = self._screen_market_products(market, product_type)
                    screened_results.extend(results)
        
        # 保存筛选结果
        self._save_screening_results(screened_results)
        self.system_status["last_screening_time"] = datetime.now()
        self.system_status["total_screened_symbols"] += len(screened_results)
        
        self.logger.info(f"筛选模式完成，共筛选 {len(screened_results)} 个标的")
        return screened_results
    
    def run_trading_mode(self):
        """运行交易模式（交易时段）"""
        if not self._is_trading_time():
            self.logger.info("当前不是交易模式运行时间")
            return []

        self.logger.info("开始运行交易模式...")
        
        # 检查券商连接状态
        broker_status = self.broker_manager.get_system_status()
        if broker_status["total_brokers"] == 0:
            self.logger.warning("没有可用的券商连接，无法执行交易")
            return []
        
        # 加载之前的筛选结果
        screening_results = self._load_screening_results()
        if not screening_results:
            self.logger.warning("没有找到筛选结果，无法执行交易")
            return []
        
        # 获取高评分标的
        high_score_symbols = [result for result in screening_results 
                             if result['final_score'] >= 7.0]
        
        executed_trades = []
        
        for symbol_data in high_score_symbols[:10]:  # 限制交易数量
            trade_result = self._execute_trade(symbol_data)
            if trade_result.get('success'):
                executed_trades.append(trade_result)
        
        self.system_status["last_trading_time"] = datetime.now()
        self.system_status["total_trades_executed"] += len(executed_trades)
        
        self.logger.info(f"交易模式完成，共执行 {len(executed_trades)} 笔交易")
        return executed_trades
    
    def run_backtest_mode(self, backtest_config: Dict[str, Any] = None):
        """运行回测模式"""
        self.logger.info("开始运行回测模式...")
        
        # 默认回测配置
        if backtest_config is None:
            backtest_config = {
                "start_date": "2024-01-01",
                "end_date": "2024-12-31",
                "markets": self._get_enabled_markets(),
                "products": self._get_enabled_products(),
                "strategy_config": {
                    "max_position_size": 0.1,
                    "stop_loss": 0.05,
                    "take_profit": 0.15
                }
            }
        
        try:
            # 运行回测
            backtest_results = self.backtest_engine.run_backtest(
                start_date=backtest_config["start_date"],
                end_date=backtest_config["end_date"],
                markets=backtest_config["markets"],
                products=backtest_config["products"],
                strategy_config=backtest_config.get("strategy_config")
            )
            
            if backtest_results.get("success", True):
                # 生成回测报告
                report = self.backtest_engine.generate_backtest_report(backtest_results)
                
                # 更新系统状态
                self.system_status["last_backtest_time"] = datetime.now()
                self.system_status["total_backtests_run"] += 1
                
                self.logger.info("回测模式完成")
                return {
                    "success": True,
                    "backtest_results": backtest_results,
                    "report": report
                }
            else:
                self.logger.error(f"回测失败: {backtest_results.get('error', '未知错误')}")
                return {"success": False, "error": backtest_results.get('error')}
                
        except Exception as e:
            self.logger.error(f"回测模式执行失败: {e}")
            return {"success": False, "error": str(e)}
    
    def get_broker_status(self) -> Dict[str, Any]:
        """获取券商状态信息"""
        return self.broker_manager.get_system_status()
    
    def reconnect_broker(self, broker_type: str) -> bool:
        """重新连接指定券商"""
        return self.broker_manager.reconnect_broker(broker_type)
    
    def get_account_balances(self) -> Dict[str, Any]:
        """获取所有券商的账户余额"""
        return self.broker_manager.get_account_balance()
    
    def get_all_positions(self) -> List[Dict[str, Any]]:
        """获取所有券商的持仓信息"""
        return self.broker_manager.get_positions()
    
    def _screen_market_products(self, market: Market, product_type: ProductType) -> List[Dict[str, Any]]:
        """筛选指定市场和产品类型的标的"""
        self.logger.info(f"开始筛选 {market.value} 市场 {product_type.value} 产品...")
        
        try:
            # 获取标的列表
            symbols = self.data_provider.get_market_symbols(market, product_type)
            if not symbols:
                self.logger.warning(f"未找到 {market.value} 市场 {product_type.value} 产品的标的")
                return []
            
            # 分批处理，避免API限制
            batch_size = self.config_manager.get_screening_config().get('batch_size', 100)
            all_results = []
            
            for i in range(0, len(symbols), batch_size):
                batch_symbols = symbols[i:i + batch_size]
                batch_results = self._process_symbol_batch(batch_symbols, product_type)
                all_results.extend(batch_results)
                
                # 添加延迟，避免API限制
                time.sleep(1)
            
            # 过滤有效结果
            valid_results = [result for result in all_results if result]
            self.logger.info(f"{market.value} 市场 {product_type.value} 产品筛选完成: {len(valid_results)} 个有效结果")
            
            return valid_results
            
        except Exception as e:
            self.logger.error(f"筛选 {market.value} 市场 {product_type.value} 产品失败: {e}")
            return []
    
    def _process_symbol_batch(self, symbols: List[str], product_type: ProductType) -> List[Dict[str, Any]]:
        """处理符号批次"""
        results = []
        
        for symbol in symbols:
            try:
                # 创建产品实例
                product = ProductFactory.create_product(symbol, product_type)
                
                # 获取市场数据
                market_data = self._get_comprehensive_market_data(symbol, product)
                if not market_data:
                    continue
                
                # 筛选标的
                screening_result = self.screening_engine.screen_symbol(
                    symbol, market_data, product
                )
                
                if screening_result:
                    results.append(screening_result)
                    
            except Exception as e:
                self.logger.error(f"处理标的 {symbol} 失败: {e}")
                continue
        
        return results
    
    def _get_comprehensive_market_data(self, symbol: str, product: Any) -> Dict[str, Any]:
        """获取综合市场数据"""
        market_data = {}
        
        try:
            # 获取实时报价
            quotes = self.data_provider.get_real_time_quotes([symbol])
            if quotes:
                market_data.update(quotes[0])
            
            # 获取K线数据
            candlesticks = self.data_provider.get_candlestick_data(symbol, days=30)
            if candlesticks:
                # 计算技术指标
                technical_indicators = self._calculate_technical_indicators(candlesticks)
                market_data.update(technical_indicators)
            
            # 获取产品特定数据
            product_data = self.data_provider.get_product_specific_data(
                symbol, product.product_type
            )
            market_data.update(product_data)
            
            # 获取分析师数据（模拟）
            market_data['analyst_data'] = self._get_simulated_analyst_data(symbol)
            
        except Exception as e:
            self.logger.error(f"获取 {symbol} 市场数据失败: {e}")
            return {}
        
        return market_data
    
    def _calculate_technical_indicators(self, candlesticks: List[Dict[str, Any]]) -> Dict[str, Any]:
        """计算技术指标"""
        if len(candlesticks) < 14:
            return {}
        
        try:
            import pandas as pd
            df = pd.DataFrame(candlesticks)
            
            # 计算RSI
            delta = df['close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rs = gain / loss
            rsi = 100 - (100 / (1 + rs))
            
            # 计算移动平均线
            ma5 = df['close'].rolling(window=5).mean()
            ma20 = df['close'].rolling(window=20).mean()
            
            # 计算波动率
            volatility = df['close'].pct_change().std() * 100
            
            return {
                'rsi': float(rsi.iloc[-1]) if not rsi.empty else 0,
                'ma5': float(ma5.iloc[-1]) if not ma5.empty else 0,
                'ma20': float(ma20.iloc[-1]) if not ma20.empty else 0,
                'volatility': float(volatility) if not pd.isna(volatility) else 0,
                'avg_volume': df['volume'].mean()
            }
        except Exception as e:
            self.logger.error(f"计算技术指标失败: {e}")
            return {}
    
    def _get_simulated_analyst_data(self, symbol: str) -> Dict[str, Any]:
        """获取模拟的分析师数据"""
        import random
        return {
            'buy_percentage': random.randint(40, 80),
            'reports_count': random.randint(1, 10),
            'consensus_rating': random.choice(['买入', '增持', '中性', '减持']),
            'average_target_price': random.uniform(50, 200)
        }
    
    def _execute_trade(self, symbol_data: Dict[str, Any]) -> Dict[str, Any]:
        """执行交易（使用多券商API）"""
        symbol = symbol_data['symbol']
        product_type = ProductType(symbol_data['product_type'])
        
        try:
            # 创建产品实例
            product = ProductFactory.create_product(symbol, product_type)
            
            # 获取最新市场数据
            market_data = self._get_comprehensive_market_data(symbol, product)
            if not market_data:
                return {'success': False, 'reason': '无法获取市场数据'}
            
            # 获取账户信息（从对应券商）
            account_info = self.trading_engine.get_account_balance(symbol)
            if not account_info:
                return {'success': False, 'reason': '无法获取账户信息'}
            
            # 生成交易信号
            from .trading_execution.trading_engine import MomentumTradingStrategy
            strategy = MomentumTradingStrategy()
            signal = strategy.generate_signal(symbol, market_data, product)
            
            # 风险管理验证
            risk_validation = self.trading_engine.risk_manager.validate_trade(
                symbol, signal, 
                strategy.calculate_position_size(symbol, account_info['total_cash'], market_data),
                account_info
            )
            
            if not risk_validation['approved']:
                return {'success': False, 'reason': '风险验证未通过'}
            
            # 执行交易（通过券商管理器自动选择券商）
            signal.update({
                'approved': True,
                'adjusted_size': risk_validation['adjusted_size'],
                'entry_price': market_data.get('last_done', 0)
            })
            
            trade_result = self.trading_engine.execute_trade(
                symbol, signal, product, account_info
            )
            
            if trade_result['success']:
                self.logger.info(f"交易执行成功: {symbol} - {signal['signal']}")
            else:
                self.logger.warning(f"交易执行失败: {symbol} - {trade_result['reason']}")
            
            return trade_result
            
        except Exception as e:
            self.logger.error(f"执行交易 {symbol} 失败: {e}")
            return {'success': False, 'reason': str(e)}
    
    def _is_screening_time(self) -> bool:
        """判断是否为筛选时间"""
        current_time = datetime.now()
        
        # 非交易时段进行筛选
        enabled_markets = self._get_enabled_markets()
        for market in enabled_markets:
            if DateTimeUtils.is_trading_time(market.value, current_time):
                return False
        
        # 避免在周末运行
        if DateTimeUtils.is_weekend(current_time):
            return False
        
        return True
    
    def _is_trading_time(self) -> bool:
        """判断是否为交易时间"""
        current_time = datetime.now()
        
        # 在任一启用市场的交易时段运行
        enabled_markets = self._get_enabled_markets()
        for market in enabled_markets:
            if DateTimeUtils.is_trading_time(market.value, current_time):
                return True
        
        return False
    
    def _get_enabled_markets(self) -> List[Market]:
        """获取启用的市场列表"""
        return [market for market in Market if self.config_manager.is_market_enabled(market)]
    
    def _get_enabled_products(self) -> List[ProductType]:
        """获取启用的产品列表"""
        return [product for product in ProductType if self.config_manager.is_product_enabled(product)]
    
    def _save_screening_results(self, results: List[Dict[str, Any]]):
        """保存筛选结果"""
        try:
            import json
            with open('screening_results.json', 'w', encoding='utf-8') as f:
                json.dump(results, f, ensure_ascii=False, indent=2)
        except Exception as e:
            self.logger.error(f"保存筛选结果失败: {e}")
    
    def _load_screening_results(self) -> List[Dict[str, Any]]:
        """加载筛选结果"""
        try:
            import json
            with open('screening_results.json', 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            return []
        except Exception as e:
            self.logger.error(f"加载筛选结果失败: {e}")
            return []
    
    def get_system_status(self) -> Dict[str, Any]:
        """获取系统状态"""
        status = self.system_status.copy()
        status.update({
            "current_time": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            "is_screening_time": self._is_screening_time(),
            "is_trading_time": self._is_trading_time(),
            "enabled_markets": [market.value for market in self._get_enabled_markets()],
            "enabled_products": [product.value for product in self._get_enabled_products()],
            "broker_status": self.broker_manager.get_system_status()
        })
        return status
    
    def start_scheduled_tasks(self):
        """启动定时任务"""
        # 非交易时段每小时运行一次筛选
        schedule.every().hour.do(self.run_screening_mode)
        
        # 交易时段每30分钟运行一次交易
        schedule.every(30).minutes.do(self.run_trading_mode)
        
        # 回测模式：每周运行一次回测（可选）
        if self.config_manager.get_backtest_config().get('auto_backtest', False):
            schedule.every().week.do(self.run_backtest_mode)
        
        self.logger.info("定时任务已启动")
        
        while True:
            try:
                schedule.run_pending()
                time.sleep(60)  # 每分钟检查一次
            except KeyboardInterrupt:
                self.logger.info("系统被用户中断")
                break
            except Exception as e:
                self.logger.error(f"定时任务执行错误: {e}")
                time.sleep(300)  # 错误后等待5分钟


def main():
    """主函数"""
    print("=== 多市场多产品交易系统 ===")
    
    # 创建交易系统实例
    system = TradingSystem()
    
    # 显示系统状态
    status = system.get_system_status()
    print(f"系统启动时间: {status['system_start_time']}")
    print(f"启用市场: {', '.join(status['enabled_markets'])}")
    print(f"启用产品: {', '.join(status['enabled_products'])}")
    print(f"当前模式: {'筛选模式' if status['is_screening_time'] else '交易模式' if status['is_trading_time'] else '等待模式'}")
    
    # 根据当前时间选择运行模式
    if status['is_screening_time']:
        print("\n运行筛选模式...")
        results = system.run_screening_mode()
        if results:
            print(f"筛选完成，共找到 {len(results)} 个标的")
            top_results = sorted(results, key=lambda x: x['final_score'], reverse=True)[:5]
            for i, result in enumerate(top_results, 1):
                print(f"{i}. {result['symbol']} - 评分: {result['final_score']}")
    
    elif status['is_trading_time']:
        print("\n运行交易模式...")
        trades = system.run_trading_mode()
        if trades:
            print(f"交易完成，共执行 {len(trades)} 笔交易")
        else:
            print("暂无符合条件的交易机会")
    
    else:
        print("\n当前不是运行时间，系统进入等待状态")
    
    print("\n系统运行完成")


if __name__ == "__main__":
    main()