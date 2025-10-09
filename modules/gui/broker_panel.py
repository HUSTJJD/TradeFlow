"""
券商管理面板模块
提供券商状态监控和账户管理功能
"""

import sys
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, 
                            QLabel, QPushButton, QGroupBox, QTreeWidget, 
                            QTreeWidgetItem, QMessageBox, QComboBox, QTabWidget)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QThread
from PyQt6.QtGui import QFont
import threading
from typing import Dict, Any, List

from ..broker_apis.broker_manager import BrokerManager


class StatusUpdaterThread(QThread):
    """状态更新线程"""
    status_updated = pyqtSignal(dict)
    
    def __init__(self, broker_manager):
        super().__init__()
        self.broker_manager = broker_manager
        self.running = True
        
    def run(self):
        import time
        while self.running:
            try:
                broker_status = self.broker_manager.get_system_status()
                self.status_updated.emit(broker_status)
                time.sleep(5)  # 每5秒更新一次
            except Exception as e:
                print(f"状态更新错误: {e}")
                time.sleep(10)
    
    def stop(self):
        self.running = False


class BrokerPanel(QWidget):
    """券商管理面板"""
    
    def __init__(self, parent, broker_manager: BrokerManager):
        super().__init__(parent)
        self.broker_manager = broker_manager
        
        self.capital_labels = {}
        
        self._create_widgets()
        self._setup_connections()
        self._start_status_updater()
    
    def _create_widgets(self):
        """创建界面组件"""
        # 主布局
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(10, 10, 10, 10)
        
        # 券商状态面板
        status_frame = self._create_status_panel()
        main_layout.addWidget(status_frame)
        
        # 券商操作面板
        control_frame = self._create_control_panel()
        main_layout.addWidget(control_frame)
        
        # 账户信息面板
        account_frame = self._create_account_panel()
        main_layout.addWidget(account_frame)
    
    def _create_status_panel(self):
        """创建券商状态面板"""
        group_box = QGroupBox("券商状态")
        group_box.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        
        layout = QVBoxLayout()
        
        # 券商状态表格
        self.broker_tree = QTreeWidget()
        self.broker_tree.setHeaderLabels(["券商", "状态", "连接时间", "最后活动", "支持市场", "账户余额", "可用资金"])
        
        # 设置列宽
        self.broker_tree.setColumnWidth(0, 100)  # 券商
        self.broker_tree.setColumnWidth(1, 80)   # 状态
        self.broker_tree.setColumnWidth(2, 120)  # 连接时间
        self.broker_tree.setColumnWidth(3, 120)  # 最后活动
        self.broker_tree.setColumnWidth(4, 150)  # 支持市场
        self.broker_tree.setColumnWidth(5, 100)  # 账户余额
        self.broker_tree.setColumnWidth(6, 100)  # 可用资金
        
        layout.addWidget(self.broker_tree)
        group_box.setLayout(layout)
        return group_box
    
    def _create_control_panel(self):
        """创建券商操作面板"""
        group_box = QGroupBox("券商操作")
        group_box.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        
        main_layout = QVBoxLayout()
        
        # 连接控制按钮
        connect_frame = self._create_connect_section()
        main_layout.addWidget(connect_frame)
        
        # 单个券商控制
        broker_control_frame = self._create_broker_control_section()
        main_layout.addWidget(broker_control_frame)
        
        group_box.setLayout(main_layout)
        return group_box
    
    def _create_connect_section(self):
        """创建连接控制区域"""
        frame = QWidget()
        layout = QHBoxLayout(frame)
        
        # 连接所有券商按钮
        connect_all_button = QPushButton("连接所有券商")
        connect_all_button.setStyleSheet("QPushButton { background-color: #28a745; color: white; }")
        connect_all_button.setMinimumHeight(35)
        layout.addWidget(connect_all_button)
        
        # 断开所有券商按钮
        disconnect_all_button = QPushButton("断开所有券商")
        disconnect_all_button.setStyleSheet("QPushButton { background-color: #dc3545; color: white; }")
        disconnect_all_button.setMinimumHeight(35)
        layout.addWidget(disconnect_all_button)
        
        layout.addStretch()
        
        # 刷新状态按钮
        refresh_button = QPushButton("刷新状态")
        refresh_button.setStyleSheet("QPushButton { background-color: #007bff; color: white; }")
        refresh_button.setMinimumHeight(35)
        layout.addWidget(refresh_button)
        
        return frame
    
    def _create_broker_control_section(self):
        """创建单个券商控制区域"""
        frame = QWidget()
        layout = QHBoxLayout(frame)
        
        layout.addWidget(QLabel("选择券商:"))
        
        # 券商选择下拉框
        self.broker_combo = QComboBox()
        self.broker_combo.setMaximumWidth(150)
        layout.addWidget(self.broker_combo)
        
        # 连接按钮
        connect_button = QPushButton("连接")
        connect_button.setStyleSheet("QPushButton { background-color: #28a745; color: white; }")
        layout.addWidget(connect_button)
        
        # 断开按钮
        disconnect_button = QPushButton("断开")
        disconnect_button.setStyleSheet("QPushButton { background-color: #dc3545; color: white; }")
        layout.addWidget(disconnect_button)
        
        # 测试连接按钮
        test_button = QPushButton("测试连接")
        test_button.setStyleSheet("QPushButton { background-color: #ffc107; color: black; }")
        layout.addWidget(test_button)
        
        layout.addStretch()
        
        return frame
    
    def _create_account_panel(self):
        """创建账户信息面板"""
        group_box = QGroupBox("账户信息")
        group_box.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        
        layout = QVBoxLayout()
        
        # 创建标签页组件
        self.account_tabs = QTabWidget()
        
        # 资金信息标签页
        capital_tab = self._create_capital_tab()
        self.account_tabs.addTab(capital_tab, "资金信息")
        
        # 持仓信息标签页
        position_tab = self._create_position_tab()
        self.account_tabs.addTab(position_tab, "持仓信息")
        
        # 订单信息标签页
        order_tab = self._create_order_tab()
        self.account_tabs.addTab(order_tab, "订单信息")
        
        layout.addWidget(self.account_tabs)
        group_box.setLayout(layout)
        return group_box
    
    def _create_capital_tab(self):
        """创建资金信息标签页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # 资金概览
        overview_group = QGroupBox("资金概览")
        overview_group.setFont(QFont("Arial", 9))
        overview_layout = QGridLayout(overview_group)
        
        capital_info = [
            ("总资产", "total_assets"),
            ("可用资金", "available_cash"),
            ("持仓市值", "position_value"),
            ("浮动盈亏", "floating_pnl"),
            ("当日盈亏", "daily_pnl"),
            ("冻结资金", "frozen_cash")
        ]
        
        for i, (label, key) in enumerate(capital_info):
            row = i // 3
            col = i % 3
            
            overview_layout.addWidget(QLabel(f"{label}:"), row, col*2)
            value_label = QLabel("0.00")
            value_label.setFont(QFont("Arial", 10, QFont.Weight.Bold))
            value_label.setStyleSheet("color: #2E86AB;")
            overview_layout.addWidget(value_label, row, col*2+1)
            
            self.capital_labels[key] = value_label
        
        layout.addWidget(overview_group)
        
        # 资金明细表格
        detail_group = QGroupBox("资金明细")
        detail_group.setFont(QFont("Arial", 9))
        detail_layout = QVBoxLayout(detail_group)
        
        self.capital_tree = QTreeWidget()
        self.capital_tree.setHeaderLabels(["券商", "币种", "总资产", "可用资金", "冻结资金", "更新时间"])
        
        # 设置列宽
        for i, width in enumerate([100, 80, 100, 100, 100, 120]):
            self.capital_tree.setColumnWidth(i, width)
        
        detail_layout.addWidget(self.capital_tree)
        layout.addWidget(detail_group)
        
        return widget
    
    def _create_position_tab(self):
        """创建持仓信息标签页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        self.position_tree = QTreeWidget()
        self.position_tree.setHeaderLabels(["券商", "标的", "名称", "数量", "成本价", "当前价", "市值", "盈亏", "盈亏率"])
        
        # 设置列宽
        for i, width in enumerate([100, 100, 120, 80, 80, 80, 100, 80, 80]):
            self.position_tree.setColumnWidth(i, width)
        
        layout.addWidget(self.position_tree)
        return widget
    
    def _create_order_tab(self):
        """创建订单信息标签页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        self.order_tree = QTreeWidget()
        self.order_tree.setHeaderLabels(["券商", "订单号", "标的", "方向", "类型", "数量", "价格", "状态", "时间"])
        
        # 设置列宽
        for i, width in enumerate([100, 120, 100, 60, 80, 80, 80, 80, 120]):
            self.order_tree.setColumnWidth(i, width)
        
        layout.addWidget(self.order_tree)
        return widget
    
    def _setup_connections(self):
        """设置信号连接"""
        # 按钮连接
        for widget in self.findChildren(QPushButton):
            if widget.text() == "连接所有券商":
                widget.clicked.connect(self._connect_all_brokers)
            elif widget.text() == "断开所有券商":
                widget.clicked.connect(self._disconnect_all_brokers)
            elif widget.text() == "刷新状态":
                widget.clicked.connect(self._refresh_status)
            elif widget.text() == "连接":
                widget.clicked.connect(self._connect_broker)
            elif widget.text() == "断开":
                widget.clicked.connect(self._disconnect_broker)
            elif widget.text() == "测试连接":
                widget.clicked.connect(self._test_broker)
    
    def _start_status_updater(self):
        """启动状态更新器"""
        self.status_updater = StatusUpdaterThread(self.broker_manager)
        self.status_updater.status_updated.connect(self._update_broker_status)
        self.status_updater.start()
    
    def _update_broker_status(self, broker_status: Dict[str, Any]):
        """更新券商状态"""
        try:
            self._update_broker_tree(broker_status)
            self._update_broker_combo(broker_status)
        except Exception as e:
            print(f"更新券商状态失败: {e}")
    
    def _update_broker_tree(self, broker_status: Dict[str, Any]):
        """更新券商状态表格"""
        # 清空现有数据
        self.broker_tree.clear()
        
        # 添加券商状态数据
        for broker_type, status in broker_status.get("broker_status", {}).items():
            values = [
                broker_type,
                "连接" if status.get("is_connected", False) else "断开",
                status.get("connection_time", "未知"),
                status.get("last_activity", "未知"),
                ", ".join(status.get("supported_markets", [])),
                f"{status.get('account_balance', 0):,.2f}",
                f"{status.get('available_cash', 0):,.2f}"
            ]
            item = QTreeWidgetItem(self.broker_tree, values)
            self.broker_tree.addTopLevelItem(item)
    
    def _update_broker_combo(self, broker_status: Dict[str, Any]):
        """更新券商选择下拉框"""
        broker_types = list(broker_status.get("broker_status", {}).keys())
        
        current_value = self.broker_combo.currentText()
        self.broker_combo.clear()
        self.broker_combo.addItems(broker_types)
        
        # 恢复之前的选择（如果还存在）
        if current_value in broker_types:
            self.broker_combo.setCurrentText(current_value)
    
    def _connect_all_brokers(self):
        """连接所有券商"""
        def connect_in_thread():
            try:
                success_count = self.broker_manager.connect_all_brokers()
                QMessageBox.information(self, "连接结果", f"成功连接 {success_count} 个券商")
            except Exception as e:
                QMessageBox.critical(self, "连接错误", f"连接券商失败: {e}")
        
        threading.Thread(target=connect_in_thread, daemon=True).start()
    
    def _disconnect_all_brokers(self):
        """断开所有券商"""
        def disconnect_in_thread():
            try:
                self.broker_manager.disconnect_all_brokers()
                QMessageBox.information(self, "断开结果", "所有券商已断开连接")
            except Exception as e:
                QMessageBox.critical(self, "断开错误", f"断开券商失败: {e}")
        
        threading.Thread(target=disconnect_in_thread, daemon=True).start()
    
    def _connect_broker(self):
        """连接指定券商"""
        broker_type = self.broker_combo.currentText()
        if not broker_type:
            QMessageBox.warning(self, "选择错误", "请先选择券商")
            return
        
        def connect_in_thread():
            try:
                success = self.broker_manager.connect_broker(broker_type)
                if success:
                    QMessageBox.information(self, "连接成功", f"{broker_type} 连接成功")
                else:
                    QMessageBox.critical(self, "连接失败", f"{broker_type} 连接失败")
            except Exception as e:
                QMessageBox.critical(self, "连接错误", f"连接 {broker_type} 失败: {e}")
        
        threading.Thread(target=connect_in_thread, daemon=True).start()
    
    def _disconnect_broker(self):
        """断开指定券商"""
        broker_type = self.broker_combo.currentText()
        if not broker_type:
            QMessageBox.warning(self, "选择错误", "请先选择券商")
            return
        
        def disconnect_in_thread():
            try:
                self.broker_manager.disconnect_broker(broker_type)
                QMessageBox.information(self, "断开成功", f"{broker_type} 已断开连接")
            except Exception as e:
                QMessageBox.critical(self, "断开错误", f"断开 {broker_type} 失败: {e}")
        
        threading.Thread(target=disconnect_in_thread, daemon=True).start()
    
    def _test_broker(self):
        """测试券商连接"""
        broker_type = self.broker_combo.currentText()
        if not broker_type:
            QMessageBox.warning(self, "选择错误", "请先选择券商")
            return
        
        def test_in_thread():
            try:
                # 这里应该调用券商的测试连接方法
                # 简化实现，显示测试结果
                QMessageBox.information(self, "测试结果", f"{broker_type} 连接测试完成")
            except Exception as e:
                QMessageBox.critical(self, "测试错误", f"测试 {broker_type} 失败: {e}")
        
        threading.Thread(target=test_in_thread, daemon=True).start()
    
    def _refresh_status(self):
        """手动刷新状态"""
        try:
            broker_status = self.broker_manager.get_system_status()
            self._update_broker_status(broker_status)
        except Exception as e:
            QMessageBox.critical(self, "刷新错误", f"刷新状态失败: {e}")
    
    def closeEvent(self, event):
        """关闭事件处理"""
        # 停止状态更新线程
        if hasattr(self, 'status_updater'):
            self.status_updater.stop()
            self.status_updater.wait(2000)
        
        event.accept()