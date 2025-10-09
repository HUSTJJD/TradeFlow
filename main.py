#!/usr/bin/env python3
"""
智能交易系统主入口
支持多券商API，提供完整的交易、筛选、回测功能
"""

import sys
import os

# 添加项目路径到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QCoreApplication

from modules.config.config_manager import ConfigManager
from modules.broker_apis.broker_manager import BrokerManager
from modules.market_data.market_data_provider import MarketDataProvider
from modules.main_system import TradingSystem
from modules.gui.main_window import MainWindow


def main():
    """主函数"""
    try:
        # 创建QApplication实例
        app = QApplication(sys.argv)
        
        # 设置应用程序属性
        QCoreApplication.setApplicationName("智能交易系统")
        QCoreApplication.setApplicationVersion("2.0")
        
        print("正在初始化智能交易系统...")
        
        # 初始化配置管理器
        config_manager = ConfigManager()
        print("✓ 配置管理器初始化完成")
        
        # 初始化市场数据提供者
        market_data_provider = MarketDataProvider(config_manager)
        print("✓ 市场数据提供者初始化完成")
        
        # 初始化券商管理器
        broker_manager = BrokerManager(config_manager)
        print("✓ 券商管理器初始化完成")
        
        # 初始化交易系统
        trading_system = TradingSystem()
        print("✓ 交易系统初始化完成")
        
        # 创建主窗口
        main_window = MainWindow(trading_system, broker_manager)
        print("✓ 主窗口创建完成")
        main_window.show()
        print("系统启动成功！")
        print("=" * 50)
        print("系统功能:")
        print("- 多券商账户管理")
        print("- 实时市场数据")
        print("- 智能标的筛选")
        print("- 策略回测分析")
        print("- 自动/手动交易")
        print("=" * 50)
        
        # 运行应用程序
        sys.exit(app.exec())
        
    except Exception as e:
        print(f"系统启动失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
