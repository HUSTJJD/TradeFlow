#!/usr/bin/env python3
"""
智能交易系统演示脚本
展示多券商API和GUI功能
"""

import sys
import os
import time
from datetime import datetime

# 添加模块路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))


def demo_broker_management():
    """演示券商管理功能"""
    print("=" * 60)
    print("券商管理功能演示")
    print("=" * 60)
    
    try:
        # 尝试导入相关模块
        from modules.config.config_manager import ConfigManager
        from modules.broker_apis.broker_manager import BrokerManager
        
        # 创建配置管理器和券商管理器
        config_manager = ConfigManager("config.yaml")
        broker_manager = BrokerManager(config_manager.get_all_broker_configs())
        
        # 显示券商状态
        broker_status = broker_manager.get_system_status()
        print(f"活跃券商数量: {broker_status['total_brokers']}")
        print("券商状态详情:")
        
        for broker_type, status in broker_status['broker_status'].items():
            connection_status = "✅ 已连接" if status['is_connected'] else "❌ 未连接"
            markets = ", ".join(status.get('supported_markets', []))
            print(f"  {broker_type}: {connection_status} | 支持市场: {markets}")
        
        # 显示市场映射
        print("\n市场与券商映射:")
        market_mapping = broker_status.get('market_mapping', {})
        for market, broker in market_mapping.items():
            print(f"  {market}市场 → {broker}券商")
        
        # 演示账户余额查询
        print("\n账户余额查询:")
        balances = broker_manager.get_account_balance()
        for broker_type, balance in balances.items():
            if balance:
                cash = balance.get('total_cash', 0)
                currency = balance.get('currency', '未知')
                print(f"  {broker_type}: {cash:,.2f} {currency}")
        
        return True
        
    except ImportError as e:
        print(f"模块导入失败，请安装依赖: {e}")
        return False
    except Exception as e:
        print(f"券商管理演示失败: {e}")
        return False


def demo_trading_system():
    """演示交易系统功能"""
    print("\n" + "=" * 60)
    print("交易系统功能演示")
    print("=" * 60)
    
    try:
        from modules.main_system import TradingSystem
        
        trading_system = TradingSystem("config.yaml")
        
        # 显示系统状态
        system_status = trading_system.get_system_status()
        print("系统状态:")
        print(f"  当前时间: {system_status['current_time']}")
        print(f"  筛选时间: {'是' if system_status['is_screening_time'] else '否'}")
        print(f"  交易时间: {'是' if system_status['is_trading_time'] else '否'}")
        print(f"  启用市场: {', '.join(system_status['enabled_markets'])}")
        print(f"  启用产品: {', '.join(system_status['enabled_products'])}")
        
        # 显示券商状态
        broker_status = system_status.get('broker_status', {})
        print(f"  活跃券商: {broker_status.get('total_brokers', 0)}个")
        
        # 演示标的筛选（模拟）
        print("\n标的筛选演示:")
        enabled_markets = trading_system._get_enabled_markets()
        enabled_products = trading_system._get_enabled_products()
        
        print(f"  将筛选 {len(enabled_markets)} 个市场的 {len(enabled_products)} 种产品")
        print("  筛选条件: RSI < 30, 成交量 > 100万, 波动率 < 50%")
        
        # 模拟筛选结果
        simulated_results = [
            {
                'symbol': '00700.HK',
                'product_type': 'stock',
                'final_score': 8.5,
                'rsi': 28.5,
                'volume': 1500000,
                'volatility': 0.35
            },
            {
                'symbol': 'AAPL.US',
                'product_type': 'stock', 
                'final_score': 7.8,
                'rsi': 25.2,
                'volume': 2500000,
                'volatility': 0.28
            }
        ]
        
        print(f"  模拟筛选结果: {len(simulated_results)} 个标的")
        for result in simulated_results:
            print(f"    {result['symbol']}: 评分{result['final_score']}, RSI{result['rsi']}")
        
        return True
        
    except ImportError as e:
        print(f"模块导入失败，请安装依赖: {e}")
        return False
    except Exception as e:
        print(f"交易系统演示失败: {e}")
        return False


def demo_gui_functionality():
    """演示GUI功能"""
    print("\n" + "=" * 60)
    print("GUI功能演示")
    print("=" * 60)
    
    try:
        # 尝试导入GUI模块
        from modules.gui.main_window import MainWindow
        print("GUI模块导入成功!")
        
        print("GUI界面功能:")
        print("  ✅ 主仪表盘 - 系统状态概览")
        print("  ✅ 交易面板 - 手动/自动交易操作")
        print("  ✅ 筛选面板 - 标的筛选和结果查看")
        print("  ✅ 回测面板 - 策略回测和优化")
        print("  ✅ 券商面板 - 多券商管理和监控")
        print("  ✅ 状态面板 - 详细系统状态信息")
        
        print("\n界面特性:")
        print("  📊 实时数据图表显示")
        print("  🔔 交易通知和警报")
        print("  ⚙️ 可视化配置管理")
        print("  📈 性能指标监控")
        print("  🎯 一键式操作按钮")
        
        print("\n启动GUI命令:")
        print("  python main.py --mode gui")
        
        return True
        
    except ImportError as e:
        print(f"GUI模块导入失败，Tkinter可能未安装: {e}")
        print("GUI功能需要Tkinter支持，这是Python标准库的一部分")
        return False
    except Exception as e:
        print(f"GUI功能演示失败: {e}")
        return False


def demo_development_mode():
    """演示开发模式功能"""
    print("\n" + "=" * 60)
    print("开发模式功能演示")
    print("=" * 60)
    
    try:
        from modules.backtesting.backtest_engine import BacktestEngine
        print("回测模块导入成功!")
        
        print("回测分析功能:")
        print("  📅 历史数据回测")
        print("  ⚙️ 策略参数优化")
        print("  📊 绩效报告生成")
        print("  🔍 样本外验证")
        
        print("\n策略优化演示:")
        print("  优化参数: RSI阈值, 移动平均周期")
        print("  优化方法: 网格搜索")
        print("  评估指标: 夏普比率")
        
        # 模拟优化结果
        print("\n模拟优化结果:")
        print("  最佳参数: RSI阈值=30, MA周期=20")
        print("  夏普比率: 1.85")
        print("  最大回撤: -12.5%")
        print("  年化收益: 25.3%")
        
        print("\n开发工具:")
        print("  📝 策略代码编辑器")
        print("  🔧 参数调试工具")
        print("  📋 回测结果对比")
        print("  💾 策略模板库")
        
        return True
        
    except ImportError as e:
        print(f"回测模块导入失败: {e}")
        return False
    except Exception as e:
        print(f"开发模式演示失败: {e}")
        return False


def demo_advanced_features():
    """演示高级功能"""
    print("\n" + "=" * 60)
    print("高级功能演示")
    print("=" * 60)
    
    try:
        print("多市场支持:")
        print("  🇭🇰 港股市场 - 股票、ETF、窝轮、牛熊证")
        print("  🇺🇸 美股市场 - 股票、ETF、期权")
        print("  🇨🇳 A股市场 - 股票、ETF")
        
        print("\n多产品支持:")
        products = [
            ("股票", "STOCK", "📈"),
            ("ETF", "ETF", "📊"), 
            ("窝轮", "WARRANT", "⚡"),
            ("牛熊证", "CBBC", "🐂🐻"),
            ("期权", "OPTION", "⏰")
        ]
        
        for name, code, icon in products:
            print(f"  {icon} {name} ({code})")
        
        print("\n风险管理特性:")
        print("  🛡️ 仓位大小控制")
        print("  ⚠️ 止损止盈设置")
        print("  📉 波动率限制")
        print("  🔒 最大回撤控制")
        print("  📊 风险暴露监控")
        
        print("\n系统监控:")
        print("  💻 性能指标实时监控")
        print("  🔗 API连接状态检查")
        print("  📝 操作日志记录")
        print("  ⚡ 系统资源使用情况")
        
        # 显示系统架构信息
        print("\n系统架构:")
        modules = [
            "broker_apis/ - 多券商API抽象层",
            "config/ - 配置管理",
            "gui/ - GUI界面",
            "market_data/ - 市场数据",
            "product_types/ - 产品类型", 
            "screening_strategies/ - 筛选策略",
            "trading_execution/ - 交易执行",
            "backtesting/ - 回测分析",
            "utils/ - 工具函数"
        ]
        
        for module in modules:
            print(f"  {module}")
        
        return True
        
    except Exception as e:
        print(f"高级功能演示失败: {e}")
        return False


def check_dependencies():
    """检查系统依赖"""
    print("=" * 60)
    print("依赖检查")
    print("=" * 60)
    
    dependencies = [
        ("pandas", "数据分析"),
        ("numpy", "数值计算"),
        ("yaml", "配置解析"),
        ("datetime", "时间处理"),
        ("tkinter", "GUI界面")
    ]
    
    missing_deps = []
    for dep, desc in dependencies:
        try:
            if dep == "tkinter":
                import tkinter
            elif dep == "yaml":
                import yaml
            else:
                __import__(dep)
            print(f"✅ {dep} - {desc}")
        except ImportError:
            print(f"❌ {dep} - {desc} (缺失)")
            missing_deps.append(dep)
    
    if missing_deps:
        print(f"\n缺失依赖: {', '.join(missing_deps)}")
        print("请运行: pip install " + " ".join(missing_deps))
        return False
    else:
        print("\n所有核心依赖已安装!")
        return True


def main():
    """主演示函数"""
    print("🚀 智能交易系统 v2.0 功能演示")
    print("=" * 60)
    print("演示开始时间:", datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    print()
    
    # 先检查依赖
    if not check_dependencies():
        print("\n⚠️  部分依赖缺失，演示功能可能受限")
    
    # 执行各个演示模块
    demos = [
        ("券商管理", demo_broker_management),
        ("交易系统", demo_trading_system),
        ("GUI功能", demo_gui_functionality),
        ("开发模式", demo_development_mode),
        ("高级功能", demo_advanced_features)
    ]
    
    results = []
    for demo_name, demo_func in demos:
        try:
            success = demo_func()
            results.append((demo_name, success))
            time.sleep(1)  # 演示间隔
        except Exception as e:
            print(f"{demo_name}演示异常: {e}")
            results.append((demo_name, False))
    
    # 显示演示结果
    print("\n" + "=" * 60)
    print("演示结果汇总")
    print("=" * 60)
    
    successful_demos = 0
    for demo_name, success in results:
        status = "✅ 成功" if success else "❌ 失败"
        print(f"{demo_name}: {status}")
        if success:
            successful_demos += 1
    
    print(f"\n总演示模块: {len(demos)}")
    print(f"成功演示: {successful_demos}")
    print(f"成功率: {successful_demos/len(demos)*100:.1f}%")
    
    # 下一步建议
    print("\n🎯 下一步建议:")
    if successful_demos == len(demos):
        print("1. 配置真实的券商API参数")
        print("2. 运行 'python main.py --mode gui' 启动图形界面")
        print("3. 在GUI中测试实际交易功能")
    else:
        print("1. 安装缺失依赖: pip install -r requirements.txt")
        print("2. 验证配置文件: python main.py --validate-config")
        print("3. 查看详细错误信息进行调试")
    
    print("\n演示结束时间:", datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    print("感谢使用智能交易系统! 🎉")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n演示被用户中断")
    except Exception as e:
        print(f"演示执行失败: {e}")