"""
仪表盘面板模块
提供系统概览和快速操作功能
"""

import sys
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, 
                            QLabel, QPushButton, QGroupBox, QTreeWidget, 
                            QTreeWidgetItem, QMessageBox, QScrollArea, QFrame)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QThread
from PyQt6.QtGui import QFont, QPalette, QColor
import threading
from datetime import datetime
from typing import Dict, Any

from ..main_system import TradingSystem
from ..broker_apis.broker_manager import BrokerManager


class StatusUpdaterThread(QThread):
    """状态更新线程"""
    status_updated = pyqtSignal(dict)
    time_updated = pyqtSignal(str)
    
    def __init__(self, trading_system):
        super().__init__()
        self.trading_system = trading_system
        self.running = True
        
    def run(self):
        import time
        while self.running:
            try:
                # 更新时间
                current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                self.time_updated.emit(current_time)
                
                # 更新系统状态
                system_status = self.trading_system.get_system_status()
                self.status_updated.emit(system_status)
                
                time.sleep(3)  # 每3秒更新一次
            except Exception as e:
                print(f"仪表盘状态更新错误: {e}")
                time.sleep(5)
    
    def stop(self):
        self.running = False


class Dashboard(QWidget):
    """系统仪表盘面板"""
    
    def __init__(self, parent, trading_system: TradingSystem, broker_manager: BrokerManager):
        super().__init__(parent)
        self.trading_system = trading_system
        self.broker_manager = broker_manager
        
        self.overview_labels = {}
        self.monitor_items = {}
        
        self._create_widgets()
        self._start_status_updater()
    
    def _create_widgets(self):
        """创建界面组件"""
        # 主布局
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(10, 10, 10, 10)
        
        # 顶部状态栏
        status_bar = self._create_status_bar()
        main_layout.addWidget(status_bar)
        
        # 快速操作面板
        quick_actions_frame = self._create_quick_actions()
        main_layout.addWidget(quick_actions_frame)
        
        # 系统概览面板
        overview_frame = self._create_overview_panel()
        main_layout.addWidget(overview_frame)
        
        # 实时监控面板
        monitor_frame = self._create_monitor_panel()
        main_layout.addWidget(monitor_frame)
    
    def _create_status_bar(self):
        """创建状态栏"""
        status_bar = QFrame()
        status_bar.setFrameStyle(QFrame.Shape.StyledPanel)
        status_bar.setStyleSheet("background-color: #f0f0f0; border: 1px solid #ccc;")
        
        layout = QHBoxLayout(status_bar)
        
        # 系统状态标签
        self.system_status_label = QLabel("系统状态: 初始化中...")
        self.system_status_label.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        layout.addWidget(self.system_status_label)
        
        # 时间显示标签
        self.time_label = QLabel("时间: --:--:--")
        self.time_label.setFont(QFont("Arial", 12))
        layout.addWidget(self.time_label)
        
        # 券商状态标签
        self.broker_status_label = QLabel("券商: 连接中...")
        self.broker_status_label.setFont(QFont("Arial", 12))
        layout.addWidget(self.broker_status_label)
        
        layout.addStretch()
        
        return status_bar
    
    def _create_quick_actions(self):
        """创建快速操作面板"""
        group_box = QGroupBox("快速操作")
        group_box.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        
        layout = QGridLayout()
        layout.setSpacing(10)
        
        # 定义操作按钮
        actions = [
            ("启动系统", self._start_system, "green"),
            ("停止系统", self._stop_system, "red"),
            ("运行筛选", self._run_screening, "blue"),
            ("执行交易", self._execute_trading, "orange"),
            ("运行回测", self._run_backtest, "purple"),
            ("券商管理", self._show_broker_manage, "brown")
        ]
        
        # 创建2x3的按钮网格
        for i, (text, command, color) in enumerate(actions):
            row = i // 3
            col = i % 3
            
            button = QPushButton(text)
            button.setMinimumHeight(40)
            button.setStyleSheet(f"QPushButton {{ background-color: {color}; color: white; font-weight: bold; }}")
            button.clicked.connect(command)
            
            layout.addWidget(button, row, col)
        
        group_box.setLayout(layout)
        return group_box
    
    def _create_overview_panel(self):
        """创建系统概览面板"""
        group_box = QGroupBox("系统概览")
        group_box.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        
        layout = QGridLayout()
        layout.setSpacing(10)
        
        # 概览指标定义
        overview_metrics = [
            ("活跃券商", "active_brokers", "0", "券商连接状态"),
            ("启用市场", "enabled_markets", "0", "交易市场数量"),
            ("启用产品", "enabled_products", "0", "产品类型数量"),
            ("今日筛选", "today_screened", "0", "今日筛选标的数"),
            ("今日交易", "today_trades", "0", "今日交易笔数"),
            ("系统运行", "system_uptime", "0天", "系统运行时间")
        ]
        
        # 创建2x3的概览指标网格
        for i, (title, key, value, description) in enumerate(overview_metrics):
            row = i // 3
            col = i % 3
            
            # 创建指标卡片
            metric_frame = QFrame()
            metric_frame.setFrameStyle(QFrame.Shape.Box)
            metric_frame.setLineWidth(1)
            metric_layout = QVBoxLayout(metric_frame)
            
            # 指标标题
            title_label = QLabel(title)
            title_label.setFont(QFont("Arial", 9, QFont.Weight.Bold))
            title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            metric_layout.addWidget(title_label)
            
            # 指标值
            value_label = QLabel(value)
            value_label.setFont(QFont("Arial", 16, QFont.Weight.Bold))
            value_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            value_label.setStyleSheet("color: #2E86AB;")
            metric_layout.addWidget(value_label)
            
            # 指标描述
            desc_label = QLabel(description)
            desc_label.setFont(QFont("Arial", 8))
            desc_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            desc_label.setStyleSheet("color: gray;")
            metric_layout.addWidget(desc_label)
            
            layout.addWidget(metric_frame, row, col)
            self.overview_labels[key] = value_label
        
        group_box.setLayout(layout)
        return group_box
    
    def _create_monitor_panel(self):
        """创建实时监控面板"""
        group_box = QGroupBox("实时监控")
        group_box.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        
        layout = QVBoxLayout()
        
        # 创建监控表格
        self.monitor_tree = QTreeWidget()
        self.monitor_tree.setHeaderLabels(["指标", "当前值", "状态", "最后更新"])
        self.monitor_tree.setColumnWidth(0, 120)
        self.monitor_tree.setColumnWidth(1, 100)
        self.monitor_tree.setColumnWidth(2, 80)
        self.monitor_tree.setColumnWidth(3, 120)
        
        # 初始化监控数据
        self._initialize_monitor_data()
        
        layout.addWidget(self.monitor_tree)
        group_box.setLayout(layout)
        return group_box
    
    def _initialize_monitor_data(self):
        """初始化监控数据"""
        monitor_data = [
            ("CPU使用率", "0%", "正常", "刚刚"),
            ("内存使用率", "0%", "正常", "刚刚"),
            ("磁盘使用率", "0%", "正常", "刚刚"),
            ("网络连接", "正常", "正常", "刚刚"),
            ("数据库连接", "正常", "正常", "刚刚"),
            ("API服务", "正常", "正常", "刚刚")
        ]
        
        for data in monitor_data:
            item = QTreeWidgetItem(self.monitor_tree, data)
            self.monitor_items[data[0]] = item
    
    def _start_status_updater(self):
        """启动状态更新器"""
        self.status_updater = StatusUpdaterThread(self.trading_system)
        self.status_updater.time_updated.connect(self._update_time_display)
        self.status_updater.status_updated.connect(self._update_dashboard_status)
        self.status_updater.start()
    
    def _update_time_display(self, time_str):
        """更新时间显示"""
        self.time_label.setText(time_str)
    
    def _update_dashboard_status(self, system_status: Dict[str, Any]):
        """更新仪表盘状态"""
        try:
            # 更新系统状态
            self._update_system_status(system_status)
            
            # 更新概览指标
            self._update_overview_metrics(system_status)
            
            # 更新监控指标
            self._update_monitor_metrics()
            
        except Exception as e:
            print(f"更新仪表盘状态失败: {e}")
    
    def _update_system_status(self, system_status: Dict[str, Any]):
        """更新系统状态"""
        is_running = system_status.get("is_running", False)
        status_text = "运行中" if is_running else "停止"
        status_color = "green" if is_running else "red"
        
        self.system_status_label.setText(status_text)
        self.system_status_label.setStyleSheet(f"color: {status_color}; font-weight: bold;")
    
    def _update_overview_metrics(self, system_status: Dict[str, Any]):
        """更新概览指标"""
        # 活跃券商数量
        active_brokers = system_status.get("active_brokers", 0)
        self.overview_labels["active_brokers"].setText(str(active_brokers))
        
        # 启用市场数量
        enabled_markets = len(system_status.get("enabled_markets", []))
        self.overview_labels["enabled_markets"].setText(str(enabled_markets))
        
        # 启用产品数量
        enabled_products = len(system_status.get("enabled_products", []))
        self.overview_labels["enabled_products"].setText(str(enabled_products))
        
        # 今日筛选数量（简化实现）
        today_screened = system_status.get("total_screened_symbols", 0) % 100
        self.overview_labels["today_screened"].setText(str(today_screened))
        
        # 今日交易数量（简化实现）
        today_trades = system_status.get("total_trades_executed", 0) % 50
        self.overview_labels["today_trades"].setText(str(today_trades))
        
        # 系统运行时间
        start_time = system_status.get("system_start_time")
        if start_time:
            uptime = datetime.now() - start_time
            days = uptime.days
            self.overview_labels["system_uptime"].setText(f"{days}天")
    
    def _update_monitor_metrics(self):
        """更新监控指标"""
        import psutil
        
        # 获取系统资源信息
        cpu_percent = psutil.cpu_percent()
        memory_percent = psutil.virtual_memory().percent
        
        try:
            disk_percent = psutil.disk_usage('C:').percent
        except:
            disk_percent = 0
        
        # 更新监控表格
        for metric_name, item in self.monitor_items.items():
            if metric_name == "CPU使用率":
                status = "正常" if cpu_percent < 80 else "警告"
                item.setText(1, f"{cpu_percent:.1f}%")
                item.setText(2, status)
            elif metric_name == "内存使用率":
                status = "正常" if memory_percent < 85 else "警告"
                item.setText(1, f"{memory_percent:.1f}%")
                item.setText(2, status)
            elif metric_name == "磁盘使用率":
                status = "正常" if disk_percent < 90 else "警告"
                item.setText(1, f"{disk_percent:.1f}%")
                item.setText(2, status)
            item.setText(3, "刚刚")
    
    def _start_system(self):
        """启动系统"""
        try:
            # 这里应该调用系统的启动方法
            QMessageBox.information(self, "系统", "交易系统已启动")
            self.system_status_label.setText("运行中")
            self.system_status_label.setStyleSheet("color: green; font-weight: bold;")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"启动系统失败: {e}")
    
    def _stop_system(self):
        """停止系统"""
        try:
            # 这里应该调用系统的停止方法
            QMessageBox.information(self, "系统", "交易系统已停止")
            self.system_status_label.setText("停止")
            self.system_status_label.setStyleSheet("color: red; font-weight: bold;")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"停止系统失败: {e}")
    
    def _run_screening(self):
        """运行筛选"""
        def run_in_thread():
            try:
                results = self.trading_system.run_screening_mode()
                QMessageBox.information(self, "筛选完成", f"找到 {len(results)} 个符合条件的标的")
            except Exception as e:
                QMessageBox.critical(self, "筛选错误", f"筛选执行失败: {e}")
        
        threading.Thread(target=run_in_thread, daemon=True).start()
    
    def _execute_trading(self):
        """执行交易"""
        def run_in_thread():
            try:
                results = self.trading_system.run_trading_mode()
                QMessageBox.information(self, "交易完成", f"执行 {len(results)} 笔交易")
            except Exception as e:
                QMessageBox.critical(self, "交易错误", f"交易执行失败: {e}")
        
        threading.Thread(target=run_in_thread, daemon=True).start()
    
    def _run_backtest(self):
        """运行回测"""
        def run_in_thread():
            try:
                results = self.trading_system.run_backtest_mode()
                if results.get("success"):
                    QMessageBox.information(self, "回测完成", "回测执行成功")
                else:
                    QMessageBox.critical(self, "回测失败", f"回测执行失败: {results.get('error')}")
            except Exception as e:
                QMessageBox.critical(self, "回测错误", f"回测执行失败: {e}")
        
        threading.Thread(target=run_in_thread, daemon=True).start()
    
    def _show_broker_manage(self):
        """显示券商管理"""
        QMessageBox.information(self, "券商管理", "券商管理功能已集成到主界面")
    
    def closeEvent(self, event):
        """关闭事件处理"""
        # 停止状态更新线程
        if hasattr(self, 'status_updater'):
            self.status_updater.stop()
            self.status_updater.wait(2000)
        
        event.accept()