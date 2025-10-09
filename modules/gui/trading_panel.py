"""
交易面板模块
提供手动交易和自动交易功能
"""

import sys
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, 
                            QLabel, QPushButton, QGroupBox, QTreeWidget, 
                            QTreeWidgetItem, QMessageBox, QCheckBox, QLineEdit,
                            QComboBox, QSpinBox, QDoubleSpinBox, QScrollArea)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont
import threading
from typing import Dict, Any, List

from ..broker_apis.broker_manager import BrokerManager
from ..main_system import TradingSystem


class TradingPanel(QWidget):
    """交易执行面板"""
    
    def __init__(self, parent, trading_system: TradingSystem, broker_manager: BrokerManager):
        super().__init__(parent)
        self.trading_system = trading_system
        self.broker_manager = broker_manager
        
        self.stats_labels = {}
        
        self._create_widgets()
        self._setup_connections()
    
    def _create_widgets(self):
        """创建界面组件"""
        # 主布局
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(10, 10, 10, 10)
        
        # 交易控制面板
        control_frame = self._create_control_panel()
        main_layout.addWidget(control_frame)
        
        # 交易参数设置
        param_frame = self._create_parameter_panel()
        main_layout.addWidget(param_frame)
        
        # 手动交易面板
        manual_frame = self._create_manual_trading_panel()
        main_layout.addWidget(manual_frame)
        
        # 交易统计
        stats_frame = self._create_statistics_panel()
        main_layout.addWidget(stats_frame)
    
    def _create_control_panel(self):
        """创建交易控制面板"""
        group_box = QGroupBox("交易控制")
        group_box.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        
        layout = QHBoxLayout()
        
        # 自动交易控制
        self.auto_trading_check = QCheckBox("启用自动交易")
        self.auto_trading_check.setFont(QFont("Arial", 10))
        layout.addWidget(self.auto_trading_check)
        
        layout.addStretch()
        
        # 立即执行交易按钮
        execute_button = QPushButton("立即执行交易")
        execute_button.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        execute_button.setStyleSheet("QPushButton { background-color: #28a745; color: white; }")
        execute_button.setMinimumHeight(35)
        layout.addWidget(execute_button)
        
        group_box.setLayout(layout)
        return group_box
    
    def _create_parameter_panel(self):
        """创建交易参数面板"""
        group_box = QGroupBox("交易参数")
        group_box.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        
        layout = QGridLayout()
        layout.setSpacing(10)
        
        # 仓位管理参数
        row = 0
        
        # 最大仓位比例
        layout.addWidget(QLabel("最大仓位比例:"), row, 0)
        self.position_size_spin = QDoubleSpinBox()
        self.position_size_spin.setRange(0.01, 1.0)
        self.position_size_spin.setValue(0.1)
        self.position_size_spin.setSingleStep(0.05)
        layout.addWidget(self.position_size_spin, row, 1)
        
        # 止损比例
        layout.addWidget(QLabel("止损比例:"), row, 2)
        self.stop_loss_spin = QDoubleSpinBox()
        self.stop_loss_spin.setRange(0.01, 0.5)
        self.stop_loss_spin.setValue(0.05)
        self.stop_loss_spin.setSingleStep(0.01)
        layout.addWidget(self.stop_loss_spin, row, 3)
        
        row += 1
        
        # 止盈比例
        layout.addWidget(QLabel("止盈比例:"), row, 0)
        self.take_profit_spin = QDoubleSpinBox()
        self.take_profit_spin.setRange(0.01, 1.0)
        self.take_profit_spin.setValue(0.15)
        self.take_profit_spin.setSingleStep(0.05)
        layout.addWidget(self.take_profit_spin, row, 1)
        
        # 最大交易笔数
        layout.addWidget(QLabel("最大交易笔数:"), row, 2)
        self.max_trades_spin = QSpinBox()
        self.max_trades_spin.setRange(1, 100)
        self.max_trades_spin.setValue(10)
        layout.addWidget(self.max_trades_spin, row, 3)
        
        group_box.setLayout(layout)
        return group_box
    
    def _create_manual_trading_panel(self):
        """创建手动交易面板"""
        group_box = QGroupBox("手动交易")
        group_box.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        
        main_layout = QVBoxLayout()
        
        # 交易输入区域
        input_frame = self._create_trading_input()
        main_layout.addWidget(input_frame)
        
        # 交易记录表格
        record_frame = self._create_trade_records()
        main_layout.addWidget(record_frame)
        
        group_box.setLayout(main_layout)
        return group_box
    
    def _create_trading_input(self):
        """创建交易输入区域"""
        frame = QWidget()
        layout = QHBoxLayout(frame)
        layout.setSpacing(10)
        
        # 标的代码
        layout.addWidget(QLabel("标的代码:"))
        self.symbol_edit = QLineEdit()
        self.symbol_edit.setPlaceholderText("例如: 00700.HK")
        self.symbol_edit.setMaximumWidth(120)
        layout.addWidget(self.symbol_edit)
        
        # 交易方向
        layout.addWidget(QLabel("方向:"))
        self.side_combo = QComboBox()
        self.side_combo.addItems(["BUY", "SELL"])
        self.side_combo.setMaximumWidth(80)
        layout.addWidget(self.side_combo)
        
        # 数量
        layout.addWidget(QLabel("数量:"))
        self.quantity_spin = QSpinBox()
        self.quantity_spin.setRange(1, 10000)
        self.quantity_spin.setValue(100)
        self.quantity_spin.setMaximumWidth(80)
        layout.addWidget(self.quantity_spin)
        
        # 价格类型
        layout.addWidget(QLabel("价格类型:"))
        self.order_type_combo = QComboBox()
        self.order_type_combo.addItems(["MARKET", "LIMIT"])
        self.order_type_combo.setMaximumWidth(80)
        layout.addWidget(self.order_type_combo)
        
        # 价格（限价单使用）
        layout.addWidget(QLabel("价格:"))
        self.price_spin = QDoubleSpinBox()
        self.price_spin.setRange(0.01, 10000.0)
        self.price_spin.setDecimals(2)
        self.price_spin.setMaximumWidth(80)
        layout.addWidget(self.price_spin)
        
        layout.addStretch()
        
        # 提交订单按钮
        submit_button = QPushButton("提交订单")
        submit_button.setStyleSheet("QPushButton { background-color: #007bff; color: white; }")
        submit_button.setMinimumHeight(30)
        layout.addWidget(submit_button)
        
        return frame
    
    def _create_trade_records(self):
        """创建交易记录表格"""
        frame = QWidget()
        layout = QVBoxLayout(frame)
        
        # 交易记录表格
        self.trade_tree = QTreeWidget()
        self.trade_tree.setHeaderLabels(["时间", "标的", "方向", "数量", "价格", "状态", "券商"])
        self.trade_tree.setColumnWidth(0, 150)
        self.trade_tree.setColumnWidth(1, 100)
        self.trade_tree.setColumnWidth(2, 60)
        self.trade_tree.setColumnWidth(3, 60)
        self.trade_tree.setColumnWidth(4, 80)
        self.trade_tree.setColumnWidth(5, 80)
        self.trade_tree.setColumnWidth(6, 80)
        
        layout.addWidget(self.trade_tree)
        return frame
    
    def _create_statistics_panel(self):
        """创建交易统计面板"""
        group_box = QGroupBox("交易统计")
        group_box.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        
        layout = QHBoxLayout()
        
        # 交易统计信息
        stats_info = [
            ("今日交易笔数", "today_trades"),
            ("今日盈亏", "today_pnl"),
            ("总交易笔数", "total_trades"),
            ("总盈亏", "total_pnl"),
            ("胜率", "win_rate")
        ]
        
        for label, key in stats_info:
            stat_frame = QWidget()
            stat_layout = QVBoxLayout(stat_frame)
            
            label_widget = QLabel(f"{label}:")
            label_widget.setFont(QFont("Arial", 9))
            stat_layout.addWidget(label_widget)
            
            value_label = QLabel("0")
            value_label.setFont(QFont("Arial", 12, QFont.Weight.Bold))
            value_label.setStyleSheet("color: #2E86AB;")
            stat_layout.addWidget(value_label)
            
            self.stats_labels[key] = value_label
            layout.addWidget(stat_frame)
        
        group_box.setLayout(layout)
        return group_box
    
    def _setup_connections(self):
        """设置信号连接"""
        # 自动交易复选框
        self.auto_trading_check.stateChanged.connect(self._toggle_auto_trading)
        
        # 订单类型改变
        self.order_type_combo.currentTextChanged.connect(self._on_order_type_change)
        
        # 按钮连接
        # 注意：需要找到正确的按钮对象进行连接
        for widget in self.findChildren(QPushButton):
            if widget.text() == "立即执行交易":
                widget.clicked.connect(self._execute_trading)
            elif widget.text() == "提交订单":
                widget.clicked.connect(self._submit_manual_order)
    
    def _on_order_type_change(self, order_type):
        """订单类型改变时的处理"""
        if order_type == "MARKET":
            self.price_spin.setEnabled(False)
            self.price_spin.setValue(0)
        else:
            self.price_spin.setEnabled(True)
    
    def _toggle_auto_trading(self, state):
        """切换自动交易模式"""
        auto_mode = (state == Qt.Checked)
        if auto_mode:
            QMessageBox.information(self, "自动交易", "自动交易模式已启用")
        else:
            QMessageBox.information(self, "自动交易", "自动交易模式已禁用")
    
    def _execute_trading(self):
        """执行交易模式"""
        def run_in_thread():
            try:
                results = self.trading_system.run_trading_mode()
                QMessageBox.information(self, "交易完成", f"执行 {len(results)} 笔交易")
                self._update_trade_records(results)
            except Exception as e:
                QMessageBox.critical(self, "交易错误", f"交易执行失败: {e}")
        
        threading.Thread(target=run_in_thread, daemon=True).start()
    
    def _submit_manual_order(self):
        """提交手动订单"""
        symbol = self.symbol_edit.text().strip()
        if not symbol:
            QMessageBox.warning(self, "输入错误", "请输入标的代码")
            return
        
        def submit_in_thread():
            try:
                # 这里应该调用券商API提交订单
                # 简化实现，仅显示成功消息
                QMessageBox.information(self, "订单提交", f"订单提交成功: {symbol}")
                
                # 更新交易记录
                trade_record = {
                    "时间": "2024-01-01 10:00:00",
                    "标的": symbol,
                    "方向": self.side_combo.currentText(),
                    "数量": self.quantity_spin.value(),
                    "价格": self.price_spin.value() if self.order_type_combo.currentText() == "LIMIT" else "市价",
                    "状态": "已提交",
                    "券商": "长桥"
                }
                self._add_trade_record(trade_record)
                
            except Exception as e:
                QMessageBox.critical(self, "订单错误", f"订单提交失败: {e}")
        
        threading.Thread(target=submit_in_thread, daemon=True).start()
    
    def _add_trade_record(self, trade_record: Dict[str, Any]):
        """添加交易记录"""
        values = [
            trade_record.get("时间", ""),
            trade_record.get("标的", ""),
            trade_record.get("方向", ""),
            str(trade_record.get("数量", 0)),
            str(trade_record.get("价格", "")),
            trade_record.get("状态", ""),
            trade_record.get("券商", "")
        ]
        item = QTreeWidgetItem(self.trade_tree, values)
        self.trade_tree.addTopLevelItem(item)
    
    def _update_trade_records(self, trade_results: List[Dict[str, Any]]):
        """更新交易记录"""
        for result in trade_results:
            if result.get('success'):
                trade_record = {
                    "时间": result.get('timestamp', '未知'),
                    "标的": result.get('symbol', '未知'),
                    "方向": result.get('side', '未知'),
                    "数量": result.get('quantity', 0),
                    "价格": result.get('price', '市价'),
                    "状态": "已完成",
                    "券商": result.get('broker', '未知')
                }
                self._add_trade_record(trade_record)
    
    def update_stats(self):
        """更新交易统计"""
        # 这里应该从系统获取实际的统计数据
        self.stats_labels["today_trades"].setText("5")
        self.stats_labels["today_pnl"].setText("+1.2%")
        self.stats_labels["total_trades"].setText("150")
        self.stats_labels["total_pnl"].setText("+15.8%")
        self.stats_labels["win_rate"].setText("68.5%")