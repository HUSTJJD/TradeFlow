"""
主窗口类
集成所有GUI组件，提供完整的交易系统界面
"""

import sys
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                            QHBoxLayout, QTabWidget, QMenuBar, QMenu, 
                            QStatusBar, QLabel, QMessageBox, QFrame)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QThread
from PyQt6.QtGui import QFont, QIcon, QAction
from typing import Dict, Any

from ..broker_apis.broker_manager import BrokerManager
from ..main_system import TradingSystem

# 导入新创建的面板类
from .dashboard import Dashboard
from .trading_panel import TradingPanel
from .screening_panel import ScreeningPanel
from .backtest_panel import BacktestPanel
from .broker_panel import BrokerPanel
from .system_status_panel import SystemStatusPanel


class StatusUpdaterThread(QThread):
    """状态更新线程"""
    status_updated = pyqtSignal(dict)
    time_updated = pyqtSignal(str)
    
    def __init__(self, trading_system):
        super().__init__()
        self.trading_system = trading_system
        self.running = True
        
    def run(self):
        from datetime import datetime
        import time
        
        while self.running:
            try:
                # 更新时间
                current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                self.time_updated.emit(current_time)
                
                # 更新系统状态
                system_status = self.trading_system.get_system_status()
                self.status_updated.emit(system_status)
                
                time.sleep(1)
            except Exception as e:
                print(f"状态更新错误: {e}")
                time.sleep(5)
    
    def stop(self):
        self.running = False


class MainWindow(QMainWindow):
    """交易系统主窗口"""
    
    def __init__(self, trading_system: TradingSystem, broker_manager: BrokerManager):
        super().__init__()
        self.trading_system = trading_system
        self.broker_manager = broker_manager
        
        # 系统状态
        self.is_running = False
        self.auto_mode = False
        
        # 初始化界面
        self._init_ui()
        
        # 启动状态更新器
        self._start_status_updater()
    
    def _init_ui(self):
        """初始化用户界面"""
        self.setWindowTitle("智能交易系统 - 多券商支持")
        self.setGeometry(100, 100, 1400, 900)
        
        # 设置中心窗口
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 创建主布局
        main_layout = QVBoxLayout(central_widget)
        
        # 创建菜单栏
        self._create_menu_bar()
        
        # 创建标签页
        self._create_tabs(main_layout)
        
        # 创建状态栏
        self._create_status_bar()
    
    def _create_menu_bar(self):
        """创建菜单栏"""
        menubar = self.menuBar()
        
        # 文件菜单
        file_menu = menubar.addMenu('文件')
        
        settings_action = QAction('系统设置', self)
        settings_action.triggered.connect(self._show_settings)
        file_menu.addAction(settings_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction('退出', self)
        exit_action.triggered.connect(self._exit_system)
        file_menu.addAction(exit_action)
        
        # 交易菜单
        trade_menu = menubar.addMenu('交易')
        
        manual_trade_action = QAction('手动交易', self)
        manual_trade_action.triggered.connect(self._show_trading_panel)
        trade_menu.addAction(manual_trade_action)
        
        auto_trade_action = QAction('自动交易', self)
        auto_trade_action.triggered.connect(self._toggle_auto_trading)
        trade_menu.addAction(auto_trade_action)
        
        # 筛选菜单
        screen_menu = menubar.addMenu('标的筛选')
        
        run_screen_action = QAction('运行筛选', self)
        run_screen_action.triggered.connect(self._run_screening)
        screen_menu.addAction(run_screen_action)
        
        screen_results_action = QAction('筛选结果', self)
        screen_results_action.triggered.connect(self._show_screening_results)
        screen_menu.addAction(screen_results_action)
        
        # 回测菜单
        backtest_menu = menubar.addMenu('回测分析')
        
        backtest_config_action = QAction('回测配置', self)
        backtest_config_action.triggered.connect(self._show_backtest_panel)
        backtest_menu.addAction(backtest_config_action)
        
        strategy_opt_action = QAction('策略优化', self)
        strategy_opt_action.triggered.connect(self._run_strategy_optimization)
        backtest_menu.addAction(strategy_opt_action)
        
        # 券商菜单
        broker_menu = menubar.addMenu('券商账户')
        
        broker_manage_action = QAction('券商管理', self)
        broker_manage_action.triggered.connect(self._show_broker_panel)
        broker_menu.addAction(broker_manage_action)
        
        account_info_action = QAction('账户信息', self)
        account_info_action.triggered.connect(self._show_account_info)
        broker_menu.addAction(account_info_action)
        
        # 帮助菜单
        help_menu = menubar.addMenu('帮助')
        
        help_action = QAction('使用说明', self)
        help_action.triggered.connect(self._show_help)
        help_menu.addAction(help_action)
        
        about_action = QAction('关于', self)
        about_action.triggered.connect(self._show_about)
        help_menu.addAction(about_action)
    
    def _create_tabs(self, main_layout):
        """创建标签页"""
        self.tab_widget = QTabWidget()
        main_layout.addWidget(self.tab_widget)
        
        # 创建各个标签页
        self._create_dashboard_tab()
        self._create_trading_tab()
        self._create_screening_tab()
        self._create_backtest_tab()
        self._create_broker_tab()
        self._create_status_tab()
    
    def _create_dashboard_tab(self):
        """创建仪表盘标签页"""
        self.dashboard_widget = QWidget()
        self.dashboard_layout = QVBoxLayout(self.dashboard_widget)
        
        # 创建仪表盘面板
        self.dashboard = Dashboard(self.dashboard_widget, self.trading_system, self.broker_manager)
        self.dashboard_layout.addWidget(self.dashboard)
        
        self.tab_widget.addTab(self.dashboard_widget, "仪表盘")
    
    def _create_trading_tab(self):
        """创建交易标签页"""
        self.trading_widget = QWidget()
        self.trading_layout = QVBoxLayout(self.trading_widget)
        
        # 创建交易面板
        self.trading_panel = TradingPanel(self.trading_widget, self.trading_system, self.broker_manager)
        self.trading_layout.addWidget(self.trading_panel)
        
        self.tab_widget.addTab(self.trading_widget, "交易执行")
    
    def _create_screening_tab(self):
        """创建筛选标签页"""
        self.screening_widget = QWidget()
        self.screening_layout = QVBoxLayout(self.screening_widget)
        
        # 创建筛选面板
        self.screening_panel = ScreeningPanel(self.screening_widget, self.trading_system)
        self.screening_layout.addWidget(self.screening_panel)
        
        self.tab_widget.addTab(self.screening_widget, "标的筛选")
    
    def _create_backtest_tab(self):
        """创建回测标签页"""
        self.backtest_widget = QWidget()
        self.backtest_layout = QVBoxLayout(self.backtest_widget)
        
        # 创建回测面板
        self.backtest_panel = BacktestPanel(self.backtest_widget, self.trading_system)
        self.backtest_layout.addWidget(self.backtest_panel)
        
        self.tab_widget.addTab(self.backtest_widget, "回测分析")
    
    def _create_broker_tab(self):
        """创建券商标签页"""
        self.broker_widget = QWidget()
        self.broker_layout = QVBoxLayout(self.broker_widget)
        
        # 创建券商面板
        self.broker_panel = BrokerPanel(self.broker_widget, self.broker_manager)
        self.broker_layout.addWidget(self.broker_panel)
        
        self.tab_widget.addTab(self.broker_widget, "券商管理")
    
    def _create_status_tab(self):
        """创建状态标签页"""
        self.status_widget = QWidget()
        self.status_layout = QVBoxLayout(self.status_widget)
        
        # 创建系统状态面板
        self.status_panel = SystemStatusPanel(self.status_widget, self.trading_system, self.broker_manager)
        self.status_layout.addWidget(self.status_panel)
        
        self.tab_widget.addTab(self.status_widget, "系统状态")
    
    def _create_status_bar(self):
        """创建状态栏"""
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        
        # 状态文本
        self.status_label = QLabel("系统就绪")
        self.status_bar.addWidget(self.status_label)
        
        # 时间显示
        self.time_label = QLabel()
        self.status_bar.addPermanentWidget(self.time_label)
    
    def _start_status_updater(self):
        """启动状态更新器"""
        self.status_updater = StatusUpdaterThread(self.trading_system)
        self.status_updater.time_updated.connect(self._update_time_display)
        self.status_updater.status_updated.connect(self._update_status_display)
        self.status_updater.start()
    
    def _update_time_display(self, time_str):
        """更新时间显示"""
        self.time_label.setText(time_str)
    
    def _update_status_display(self, system_status: Dict[str, Any]):
        """更新状态显示"""
        try:
            # 更新状态栏
            if self.is_running:
                status_text = f"系统运行中 - 连接券商: {len(system_status.get('connected_brokers', []))}"
                self.status_label.setText(status_text)
            
            # 更新各个面板的状态
            if hasattr(self, 'dashboard'):
                # 仪表盘有自己的状态更新机制
                pass
            
            if hasattr(self, 'status_panel'):
                # 系统状态面板有自己的状态更新机制
                pass
                
        except Exception as e:
            print(f"更新状态显示失败: {e}")
    
    def _start_system(self):
        """启动系统"""
        try:
            self.is_running = True
            self.status_label.setText("系统已启动")
            QMessageBox.information(self, "系统", "交易系统已启动")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"启动系统失败: {e}")
    
    def _stop_system(self):
        """停止系统"""
        try:
            self.is_running = False
            self.auto_mode = False
            self.status_label.setText("系统已停止")
            QMessageBox.information(self, "系统", "交易系统已停止")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"停止系统失败: {e}")
    
    def _toggle_auto_trading(self):
        """切换自动交易模式"""
        self.auto_mode = not self.auto_mode
        status = "开启" if self.auto_mode else "关闭"
        self.status_label.setText(f"自动交易模式已{status}")
        QMessageBox.information(self, "自动交易", f"自动交易模式已{status}")
    
    def _run_screening(self):
        """运行筛选"""
        if not self.is_running:
            QMessageBox.warning(self, "警告", "请先启动系统")
            return
        
        # 在后台线程中运行筛选
        from threading import Thread
        
        def run_in_thread():
            try:
                self.status_label.setText("正在运行标的筛选...")
                results = self.trading_system.run_screening_mode()
                self.status_label.setText(f"筛选完成，找到 {len(results)} 个标的")
                QMessageBox.information(self, "筛选完成", f"找到 {len(results)} 个符合条件的标的")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"筛选失败: {e}")
        
        Thread(target=run_in_thread, daemon=True).start()
    
    def _run_trading(self):
        """执行交易"""
        if not self.is_running:
            QMessageBox.warning(self, "警告", "请先启动系统")
            return
        
        # 在后台线程中执行交易
        from threading import Thread
        
        def run_in_thread():
            try:
                self.status_label.setText("正在执行交易...")
                results = self.trading_system.run_trading_mode()
                self.status_label.setText(f"交易完成，执行 {len(results)} 笔交易")
                QMessageBox.information(self, "交易完成", f"执行 {len(results)} 笔交易")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"交易失败: {e}")
        
        Thread(target=run_in_thread, daemon=True).start()
    
    # 菜单功能实现
    def _show_settings(self):
        """显示系统设置"""
        QMessageBox.information(self, "设置", "系统设置功能开发中")
    
    def _exit_system(self):
        """退出系统"""
        reply = QMessageBox.question(self, "退出", "确定要退出系统吗？",
                                   QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            self.close()
    
    def _show_trading_panel(self):
        """显示交易面板"""
        self.tab_widget.setCurrentIndex(1)  # 交易标签页索引为1
    
    def _show_screening_results(self):
        """显示筛选结果"""
        self.tab_widget.setCurrentIndex(2)  # 筛选标签页索引为2
    
    def _show_backtest_panel(self):
        """显示回测面板"""
        self.tab_widget.setCurrentIndex(3)  # 回测标签页索引为3
    
    def _run_strategy_optimization(self):
        """运行策略优化"""
        QMessageBox.information(self, "策略优化", "策略优化功能开发中")
    
    def _show_broker_panel(self):
        """显示券商面板"""
        self.tab_widget.setCurrentIndex(4)  # 券商标签页索引为4
    
    def _show_account_info(self):
        """显示账户信息"""
        QMessageBox.information(self, "账户信息", "账户信息查看功能开发中")
    
    def _show_help(self):
        """显示帮助"""
        QMessageBox.information(self, "帮助", "使用说明文档开发中")
    
    def _show_about(self):
        """显示关于信息"""
        QMessageBox.information(self, "关于", 
                               "智能交易系统 v2.0\n支持多券商API\n作者: AI助手")
    
    def closeEvent(self, event):
        """关闭事件处理"""
        # 停止状态更新线程
        if hasattr(self, 'status_updater'):
            self.status_updater.stop()
            self.status_updater.wait(2000)  # 等待2秒
        
        event.accept()
    
    def run(self):
        """运行GUI主循环"""
        self.show()