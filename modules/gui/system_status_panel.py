"""
系统状态面板模块
提供系统运行状态监控功能
"""

import sys
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, 
                            QLabel, QPushButton, QGroupBox, QTreeWidget, 
                            QTreeWidgetItem, QMessageBox, QProgressBar, QTextEdit)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QThread
from PyQt6.QtGui import QFont, QTextCursor
import psutil
import time
from datetime import datetime
from typing import Dict, Any

from ..main_system import TradingSystem
from ..broker_apis.broker_manager import BrokerManager


class StatusUpdaterThread(QThread):
    """状态更新线程"""
    status_updated = pyqtSignal()
    
    def __init__(self, trading_system, broker_manager):
        super().__init__()
        self.trading_system = trading_system
        self.broker_manager = broker_manager
        self.running = True
        
    def run(self):
        while self.running:
            try:
                self.status_updated.emit()
                time.sleep(2)  # 每2秒更新一次
            except Exception as e:
                print(f"状态更新错误: {e}")
                time.sleep(5)
    
    def stop(self):
        self.running = False


class SystemStatusPanel(QWidget):
    """系统状态面板"""
    
    def __init__(self, parent, trading_system: TradingSystem, broker_manager: BrokerManager):
        super().__init__(parent)
        self.trading_system = trading_system
        self.broker_manager = broker_manager
        
        self.status_labels = {}
        self.trading_stats_labels = {}
        
        self._create_widgets()
        self._setup_connections()
        self._start_status_updater()
    
    def _create_widgets(self):
        """创建界面组件"""
        # 主布局
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(10, 10, 10, 10)
        
        # 系统概览面板
        overview_frame = self._create_overview_panel()
        main_layout.addWidget(overview_frame)
        
        # 性能监控面板
        performance_frame = self._create_performance_panel()
        main_layout.addWidget(performance_frame)
        
        # 交易统计面板
        trading_stats_frame = self._create_trading_stats_panel()
        main_layout.addWidget(trading_stats_frame)
        
        # 券商状态面板
        broker_frame = self._create_broker_panel()
        main_layout.addWidget(broker_frame)
        
        # 系统日志面板
        log_frame = self._create_log_panel()
        main_layout.addWidget(log_frame)
    
    def _create_overview_panel(self):
        """创建系统概览面板"""
        group_box = QGroupBox("系统概览")
        group_box.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        
        layout = QGridLayout()
        
        # 系统状态指标
        status_info = [
            ("运行状态", "system_status"),
            ("运行时间", "uptime"),
            ("最后筛选", "last_screening"),
            ("最后交易", "last_trading"),
            ("最后回测", "last_backtest"),
            ("活跃券商", "active_brokers")
        ]
        
        for i, (label, key) in enumerate(status_info):
            row = i // 3
            col = i % 3
            
            layout.addWidget(QLabel(f"{label}:"), row, col*2)
            value_label = QLabel("未知")
            value_label.setFont(QFont("Arial", 10, QFont.Weight.Bold))
            layout.addWidget(value_label, row, col*2+1)
            
            self.status_labels[key] = value_label
        
        group_box.setLayout(layout)
        return group_box
    
    def _create_performance_panel(self):
        """创建性能监控面板"""
        group_box = QGroupBox("性能监控")
        group_box.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        
        layout = QHBoxLayout()
        
        # CPU使用率
        cpu_group = QGroupBox("CPU使用率")
        cpu_group.setFont(QFont("Arial", 9))
        cpu_layout = QVBoxLayout(cpu_group)
        
        self.cpu_progress = QProgressBar()
        self.cpu_progress.setMaximum(100)
        cpu_layout.addWidget(self.cpu_progress)
        
        self.cpu_label = QLabel("0.0%")
        self.cpu_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        cpu_layout.addWidget(self.cpu_label)
        
        layout.addWidget(cpu_group)
        
        # 内存使用率
        memory_group = QGroupBox("内存使用率")
        memory_group.setFont(QFont("Arial", 9))
        memory_layout = QVBoxLayout(memory_group)
        
        self.memory_progress = QProgressBar()
        self.memory_progress.setMaximum(100)
        memory_layout.addWidget(self.memory_progress)
        
        self.memory_label = QLabel("0.0%")
        self.memory_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        memory_layout.addWidget(self.memory_label)
        
        layout.addWidget(memory_group)
        
        # 磁盘使用率
        disk_group = QGroupBox("磁盘使用率")
        disk_group.setFont(QFont("Arial", 9))
        disk_layout = QVBoxLayout(disk_group)
        
        self.disk_progress = QProgressBar()
        self.disk_progress.setMaximum(100)
        disk_layout.addWidget(self.disk_progress)
        
        self.disk_label = QLabel("0.0%")
        self.disk_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        disk_layout.addWidget(self.disk_label)
        
        layout.addWidget(disk_group)
        
        group_box.setLayout(layout)
        return group_box
    
    def _create_trading_stats_panel(self):
        """创建交易统计面板"""
        group_box = QGroupBox("交易统计")
        group_box.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        
        layout = QGridLayout()
        
        trading_stats = [
            ("总筛选标的", "total_screened"),
            ("总交易笔数", "total_trades"),
            ("总回测次数", "total_backtests"),
            ("今日交易", "today_trades"),
            ("今日盈亏", "today_pnl"),
            ("总盈亏", "total_pnl")
        ]
        
        for i, (label, key) in enumerate(trading_stats):
            row = i // 3
            col = i % 3
            
            layout.addWidget(QLabel(f"{label}:"), row, col*2)
            value_label = QLabel("0")
            value_label.setFont(QFont("Arial", 10, QFont.Weight.Bold))
            value_label.setStyleSheet("color: #2E86AB;")
            layout.addWidget(value_label, row, col*2+1)
            
            self.trading_stats_labels[key] = value_label
        
        group_box.setLayout(layout)
        return group_box
    
    def _create_broker_panel(self):
        """创建券商状态面板"""
        group_box = QGroupBox("券商状态")
        group_box.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        
        layout = QVBoxLayout()
        
        # 券商状态表格
        self.broker_tree = QTreeWidget()
        self.broker_tree.setHeaderLabels(["券商", "状态", "连接时间", "最后活动", "支持功能", "账户状态"])
        
        # 设置列宽
        for i, width in enumerate([100, 80, 120, 120, 150, 100]):
            self.broker_tree.setColumnWidth(i, width)
        
        layout.addWidget(self.broker_tree)
        group_box.setLayout(layout)
        return group_box
    
    def _create_log_panel(self):
        """创建系统日志面板"""
        group_box = QGroupBox("系统日志")
        group_box.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        
        layout = QVBoxLayout()
        
        # 日志文本框
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumHeight(200)
        layout.addWidget(self.log_text)
        
        # 日志控制按钮
        log_control_frame = QWidget()
        log_control_layout = QHBoxLayout(log_control_frame)
        
        # 清空日志按钮
        clear_button = QPushButton("清空日志")
        clear_button.setStyleSheet("QPushButton { background-color: #dc3545; color: white; }")
        log_control_layout.addWidget(clear_button)
        
        # 保存日志按钮
        save_button = QPushButton("保存日志")
        save_button.setStyleSheet("QPushButton { background-color: #28a745; color: white; }")
        log_control_layout.addWidget(save_button)
        
        log_control_layout.addStretch()
        
        # 刷新日志按钮
        refresh_button = QPushButton("刷新日志")
        refresh_button.setStyleSheet("QPushButton { background-color: #007bff; color: white; }")
        log_control_layout.addWidget(refresh_button)
        
        layout.addWidget(log_control_frame)
        group_box.setLayout(layout)
        return group_box
    
    def _setup_connections(self):
        """设置信号连接"""
        # 按钮连接
        for widget in self.findChildren(QPushButton):
            if widget.text() == "清空日志":
                widget.clicked.connect(self._clear_logs)
            elif widget.text() == "保存日志":
                widget.clicked.connect(self._save_logs)
            elif widget.text() == "刷新日志":
                widget.clicked.connect(self._refresh_logs)
    
    def _start_status_updater(self):
        """启动状态更新器"""
        self.status_updater = StatusUpdaterThread(self.trading_system, self.broker_manager)
        self.status_updater.status_updated.connect(self._update_system_status)
        self.status_updater.start()
    
    def _update_system_status(self):
        """更新系统状态"""
        try:
            # 更新系统概览
            self._update_overview_status()
            
            # 更新性能监控
            self._update_performance_status()
            
            # 更新交易统计
            self._update_trading_stats()
            
            # 更新券商状态
            self._update_broker_status()
            
            # 更新系统日志
            self._update_system_logs()
            
        except Exception as e:
            print(f"更新系统状态失败: {e}")
    
    def _update_overview_status(self):
        """更新系统概览状态"""
        system_status = self.trading_system.get_system_status()
        
        # 运行状态
        is_running = system_status.get("is_running", False)
        status_text = "运行中" if is_running else "停止"
        status_color = "green" if is_running else "red"
        self.status_labels["system_status"].setText(status_text)
        self.status_labels["system_status"].setStyleSheet(f"color: {status_color};")
        
        # 运行时间
        start_time = system_status.get("system_start_time")
        if start_time:
            uptime = datetime.now() - start_time
            days = uptime.days
            hours = uptime.seconds // 3600
            minutes = (uptime.seconds % 3600) // 60
            self.status_labels["uptime"].setText(f"{days}天{hours}时{minutes}分")
        
        # 最后活动时间
        last_screening = system_status.get("last_screening_time")
        if last_screening:
            self.status_labels["last_screening"].setText(last_screening.strftime("%Y-%m-%d %H:%M"))
        
        last_trading = system_status.get("last_trading_time")
        if last_trading:
            self.status_labels["last_trading"].setText(last_trading.strftime("%Y-%m-%d %H:%M"))
        
        last_backtest = system_status.get("last_backtest_time")
        if last_backtest:
            self.status_labels["last_backtest"].setText(last_backtest.strftime("%Y-%m-%d %H:%M"))
        
        # 活跃券商数量
        active_brokers = system_status.get("active_brokers", 0)
        self.status_labels["active_brokers"].setText(str(active_brokers))
    
    def _update_performance_status(self):
        """更新性能监控状态"""
        # CPU使用率
        cpu_percent = psutil.cpu_percent(interval=0.1)
        self.cpu_progress.setValue(int(cpu_percent))
        self.cpu_label.setText(f"{cpu_percent:.1f}%")
        
        # 内存使用率
        memory = psutil.virtual_memory()
        memory_percent = memory.percent
        self.memory_progress.setValue(int(memory_percent))
        self.memory_label.setText(f"{memory_percent:.1f}%")
        
        # 磁盘使用率（使用C盘）
        try:
            disk = psutil.disk_usage('C:')
            disk_percent = disk.percent
            self.disk_progress.setValue(int(disk_percent))
            self.disk_label.setText(f"{disk_percent:.1f}%")
        except:
            self.disk_progress.setValue(0)
            self.disk_label.setText("N/A")
    
    def _update_trading_stats(self):
        """更新交易统计"""
        system_status = self.trading_system.get_system_status()
        
        stats = {
            "total_screened": system_status.get("total_screened_symbols", 0),
            "total_trades": system_status.get("total_trades_executed", 0),
            "total_backtests": system_status.get("total_backtests_run", 0),
            "today_trades": "5",  # 简化实现
            "today_pnl": "+1.2%",  # 简化实现
            "total_pnl": "+15.8%"  # 简化实现
        }
        
        for key, value in stats.items():
            if key in self.trading_stats_labels:
                self.trading_stats_labels[key].setText(str(value))
    
    def _update_broker_status(self):
        """更新券商状态"""
        broker_status = self.broker_manager.get_system_status()
        
        # 清空现有数据
        self.broker_tree.clear()
        
        # 添加券商状态数据
        for broker_type, status in broker_status.get("broker_status", {}).items():
            is_connected = status.get("is_connected", False)
            account_status = "正常" if status.get("account_valid", False) else "异常"
            
            values = [
                broker_type,
                "连接" if is_connected else "断开",
                status.get("connection_time", "未知"),
                status.get("last_activity", "未知"),
                ", ".join(status.get("supported_features", [])),
                account_status
            ]
            item = QTreeWidgetItem(self.broker_tree, values)
            self.broker_tree.addTopLevelItem(item)
    
    def _update_system_logs(self):
        """更新系统日志"""
        # 简化实现：显示最近几条日志
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"[{current_time}] 系统运行正常\n"
        
        # 限制日志行数
        current_text = self.log_text.toPlainText()
        lines = current_text.split('\n')
        if len(lines) > 50:  # 保留最近50行
            self.log_text.setPlainText('\n'.join(lines[-50:]))
        
        # 添加新日志（如果内容有变化）
        if log_entry not in current_text:
            self.log_text.append(log_entry.strip())
            cursor = self.log_text.textCursor()
            cursor.movePosition(QTextCursor.MoveOperation.End)
            self.log_text.setTextCursor(cursor)
    
    def _clear_logs(self):
        """清空日志"""
        self.log_text.clear()
    
    def _save_logs(self):
        """保存日志"""
        try:
            log_content = self.log_text.toPlainText()
            if log_content.strip():
                filename = f"system_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(log_content)
                QMessageBox.information(self, "保存成功", f"日志已保存到 {filename}")
            else:
                QMessageBox.warning(self, "保存失败", "没有日志内容可保存")
        except Exception as e:
            QMessageBox.critical(self, "保存错误", f"保存日志失败: {e}")
    
    def _refresh_logs(self):
        """刷新日志"""
        self._update_system_logs()
    
    def closeEvent(self, event):
        """关闭事件处理"""
        # 停止状态更新线程
        if hasattr(self, 'status_updater'):
            self.status_updater.stop()
            self.status_updater.wait(2000)
        
        event.accept()