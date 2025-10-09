#!/usr/bin/env python3
"""
智能交易系统主程序
支持多券商API和GUI界面
"""

import argparse
import sys
import os
from typing import Dict, Any

# 添加模块路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from modules.main_system import TradingSystem
from modules.gui.main_window import MainWindow
from modules.broker_apis.broker_manager import BrokerManager
from modules.config.config_manager import ConfigManager


def setup_environment():
    """设置运行环境"""
    print("正在设置交易系统环境...")
    
    # 检查必要的依赖
    try:
        import pandas
        import numpy
        import yaml
        print("✓ 核心依赖检查通过")
    except ImportError as e:
        print(f"✗ 缺少必要依赖: {e}")
        print("请运行: pip install -r requirements.txt")
        return False
    # 检查券商特定依赖
    try:
        import longport
        print("✓ 长桥SDK可用")
    except ImportError:
        print("⚠ 长桥SDK未安装，相关功能将受限")
    try:
        import ib_async
        print("✓ IBKR SDK可用")
    except ImportError:
        print("⚠ IBKR SDK未安装，相关功能将受限")
    
    return True


def parse_arguments():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description="智能交易系统")
    
    parser.add_argument(
        "--mode", 
        choices=["gui", "cli", "daemon"], 
        default="gui",
        help="运行模式: gui(图形界面), cli(命令行), daemon(后台服务)"
    )
    
    parser.add_argument(
        "--config", 
        default="config.yaml",
        help="配置文件路径"
    )
    
    parser.add_argument(
        "--screening", 
        action="store_true",
        help="运行标的筛选模式"
    )
    
    parser.add_argument(
        "--trading", 
        action="store_true", 
        help="运行交易模式"
    )
    
    parser.add_argument(
        "--backtest", 
        action="store_true",
        help="运行回测模式"
    )
    
    parser.add_argument(
        "--development", 
        action="store_true",
        help="运行开发模式"
    )
    
    parser.add_argument(
        "--broker-status", 
        action="store_true",
        help="显示券商状态"
    )
    
    parser.add_argument(
        "--validate-config", 
        action="store_true",
        help="验证配置文件"
    )
    
    return parser.parse_args()


def run_gui_mode(config_path: str):
    """运行GUI模式"""
    print("启动图形界面模式...")
    
    try:
        # 创建交易系统和券商管理器
        trading_system = TradingSystem(config_path)
        broker_manager = BrokerManager(trading_system.config_manager.get_all_broker_configs())
        
        # 创建主窗口
        app = MainWindow(trading_system, broker_manager)
        
        print("✓ 图形界面初始化完成")
        print("系统信息:")
        print(f"  - 活跃券商: {len(broker_manager.active_brokers)} 个")
        print(f"  - 启用市场: {trading_system._get_enabled_markets()}")
        print(f"  - 启用产品: {trading_system._get_enabled_products()}")
        
        # 运行GUI主循环
        app.run()
        
    except Exception as e:
        print(f"✗ GUI模式启动失败: {e}")
        return False
    
    return True


def run_cli_mode(args, config_path: str):
    """运行命令行模式"""
    print("启动命令行模式...")
    
    try:
        trading_system = TradingSystem(config_path)
        broker_manager = BrokerManager(trading_system.config_manager.get_all_broker_configs())
        
        # 显示系统信息
        system_status = trading_system.get_system_status()
        broker_status = broker_manager.get_system_status()
        
        print("\n=== 系统状态 ===")
        print(f"当前时间: {system_status['current_time']}")
        print(f"筛选时间: {'是' if system_status['is_screening_time'] else '否'}")
        print(f"交易时间: {'是' if system_status['is_trading_time'] else '否'}")
        print(f"启用市场: {', '.join(system_status['enabled_markets'])}")
        print(f"启用产品: {', '.join(system_status['enabled_products'])}")
        print(f"活跃券商: {broker_status['total_brokers']} 个")
        
        # 显示券商状态
        if args.broker_status:
            print("\n=== 券商状态 ===")
            for broker_type, status in broker_status['broker_status'].items():
                print(f"{broker_type}: {'连接' if status['is_connected'] else '断开'}")
        
        # 执行指定操作
        if args.screening:
            print("\n=== 运行标的筛选 ===")
            results = trading_system.run_screening_mode()
            print(f"筛选完成，找到 {len(results)} 个标的")
            
        if args.trading:
            print("\n=== 运行交易模式 ===")
            results = trading_system.run_trading_mode()
            print(f"交易完成，执行 {len(results)} 笔交易")
            
        if args.backtest:
            print("\n=== 运行回测模式 ===")
            results = trading_system.run_development_mode()
            if results.get('success'):
                print("回测完成")
                report = results.get('report', {})
                if report:
                    print(f"总收益: {report.get('total_return', 0):.2%}")
                    print(f"夏普比率: {report.get('sharpe_ratio', 0):.2f}")
            else:
                print(f"回测失败: {results.get('error')}")
                
        if args.development:
            print("\n=== 运行开发模式 ===")
            # 这里可以添加更复杂的开发模式操作
            
        # 如果没有指定具体操作，显示帮助信息
        if not any([args.screening, args.trading, args.backtest, args.development, args.broker_status]):
            print("\n可用操作:")
            print("  --screening     运行标的筛选")
            print("  --trading       运行交易模式") 
            print("  --backtest      运行回测模式")
            print("  --development   运行开发模式")
            print("  --broker-status 显示券商状态")
            
    except Exception as e:
        print(f"✗ 命令行模式执行失败: {e}")
        return False
    
    return True


def run_daemon_mode(config_path: str):
    """运行后台服务模式"""
    print("启动后台服务模式...")
    
    try:
        trading_system = TradingSystem(config_path)
        
        print("✓ 交易系统初始化完成")
        print("开始运行定时任务...")
        
        # 启动定时任务
        trading_system.start_scheduled_tasks()
        
    except KeyboardInterrupt:
        print("\n后台服务被用户中断")
    except Exception as e:
        print(f"✗ 后台服务模式启动失败: {e}")
        return False
    
    return True


def validate_configuration(config_path: str):
    """验证配置文件"""
    print("验证配置文件...")
    
    try:
        config_manager = ConfigManager(config_path)
        validation_result = config_manager.validate_config()
        
        if validation_result['valid']:
            print("✓ 配置文件验证通过")
        else:
            print("✗ 配置文件验证失败:")
            for error in validation_result['errors']:
                print(f"  - {error}")
        
        if validation_result['warnings']:
            print("⚠ 配置文件警告:")
            for warning in validation_result['warnings']:
                print(f"  - {warning}")
                
        return validation_result['valid']
        
    except Exception as e:
        print(f"✗ 配置文件验证失败: {e}")
        return False


def main():
    """主函数"""
    print("=" * 50)
    print("             智能交易系统            ")
    print("=" * 50)
    
    # 设置环境
    if not setup_environment():
        return 1
    
    # 解析参数
    args = parse_arguments()
    
    # 验证配置文件
    if args.validate_config:
        if validate_configuration(args.config):
            return 0
        else:
            return 1
    
    # 根据模式运行
    success = False
    
    if args.mode == "gui":
        success = run_gui_mode(args.config)
    elif args.mode == "cli":
        success = run_cli_mode(args, args.config)
    elif args.mode == "daemon":
        success = run_daemon_mode(args.config)
    
    if success:
        print("✓ 程序执行完成")
        return 0
    else:
        print("✗ 程序执行失败")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
