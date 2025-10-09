"""
回测面板模块
提供策略回测和参数优化功能
"""

import sys
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, 
                            QLabel, QPushButton, QGroupBox, QTreeWidget, 
                            QTreeWidgetItem, QMessageBox, QComboBox, QLineEdit,
                            QSpinBox, QDoubleSpinBox, QTabWidget, QCheckBox,
                            QDateEdit, QScrollArea)
from PyQt6.QtCore import Qt, QDate
from PyQt6.QtGui import QFont
import threading
from datetime import datetime, timedelta
from typing import Dict, Any, List

from ..main_system import TradingSystem


class BacktestPanel(QWidget):
    """回测分析面板"""
    
    def __init__(self, parent, trading_system: TradingSystem):
        super().__init__(parent)
        self.trading_system = trading_system
        self.backtest_results = {}
        
        self.key_metrics_labels = {}
        self.equity_stats_labels = {}
        
        self._create_widgets()
        self._setup_connections()
    
    def _create_widgets(self):
        """创建界面组件"""
        # 主布局
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(10, 10, 10, 10)
        
        # 回测配置面板
        config_frame = self._create_config_panel()
        main_layout.addWidget(config_frame)
        
        # 回测结果面板
        result_frame = self._create_results_panel()
        main_layout.addWidget(result_frame)
    
    def _create_config_panel(self):
        """创建回测配置面板"""
        group_box = QGroupBox("回测配置")
        group_box.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        
        main_layout = QVBoxLayout()
        
        # 时间范围设置
        time_frame = self._create_time_section()
        main_layout.addWidget(time_frame)
        
        # 市场选择
        market_frame = self._create_market_section()
        main_layout.addWidget(market_frame)
        
        # 初始资金设置
        capital_frame = self._create_capital_section()
        main_layout.addWidget(capital_frame)
        
        # 策略参数设置
        strategy_frame = self._create_strategy_section()
        main_layout.addWidget(strategy_frame)
        
        # 操作按钮
        button_frame = self._create_button_section()
        main_layout.addWidget(button_frame)
        
        group_box.setLayout(main_layout)
        return group_box
    
    def _create_time_section(self):
        """创建时间范围设置区域"""
        frame = QWidget()
        layout = QHBoxLayout(frame)
        layout.setSpacing(10)
        
        layout.addWidget(QLabel("开始日期:"))
        self.start_date_edit = QDateEdit()
        self.start_date_edit.setDate(QDate(2024, 1, 1))
        self.start_date_edit.setCalendarPopup(True)
        self.start_date_edit.setMaximumWidth(120)
        layout.addWidget(self.start_date_edit)
        
        layout.addWidget(QLabel("结束日期:"))
        self.end_date_edit = QDateEdit()
        self.end_date_edit.setDate(QDate(2024, 12, 31))
        self.end_date_edit.setCalendarPopup(True)
        self.end_date_edit.setMaximumWidth(120)
        layout.addWidget(self.end_date_edit)
        
        layout.addStretch()
        
        return frame
    
    def _create_market_section(self):
        """创建市场选择区域"""
        frame = QWidget()
        layout = QHBoxLayout(frame)
        layout.setSpacing(10)
        
        layout.addWidget(QLabel("目标市场:"))
        
        self.market_checks = {}
        markets = ["HK", "US", "CN"]
        
        for market in markets:
            check = QCheckBox(market)
            check.setChecked(True)
            layout.addWidget(check)
            self.market_checks[market] = check
        
        layout.addStretch()
        
        return frame
    
    def _create_capital_section(self):
        """创建资金设置区域"""
        frame = QWidget()
        layout = QHBoxLayout(frame)
        layout.setSpacing(10)
        
        layout.addWidget(QLabel("初始资金:"))
        self.initial_cash_spin = QDoubleSpinBox()
        self.initial_cash_spin.setRange(1000, 10000000)
        self.initial_cash_spin.setValue(1000000.0)
        self.initial_cash_spin.setSingleStep(10000)
        self.initial_cash_spin.setMaximumWidth(120)
        layout.addWidget(self.initial_cash_spin)
        
        layout.addWidget(QLabel("手续费率:"))
        self.commission_spin = QDoubleSpinBox()
        self.commission_spin.setRange(0.0001, 0.1)
        self.commission_spin.setValue(0.001)
        self.commission_spin.setSingleStep(0.0005)
        self.commission_spin.setMaximumWidth(80)
        layout.addWidget(self.commission_spin)
        
        layout.addStretch()
        
        return frame
    
    def _create_strategy_section(self):
        """创建策略参数区域"""
        group_box = QGroupBox("策略参数")
        group_box.setFont(QFont("Arial", 9))
        
        layout = QGridLayout()
        layout.setSpacing(10)
        
        # 风险控制参数
        row = 0
        
        layout.addWidget(QLabel("最大仓位:"), row, 0)
        self.position_size_spin = QDoubleSpinBox()
        self.position_size_spin.setRange(0.01, 1.0)
        self.position_size_spin.setValue(0.1)
        self.position_size_spin.setSingleStep(0.05)
        layout.addWidget(self.position_size_spin, row, 1)
        
        layout.addWidget(QLabel("止损比例:"), row, 2)
        self.stop_loss_spin = QDoubleSpinBox()
        self.stop_loss_spin.setRange(0.01, 0.5)
        self.stop_loss_spin.setValue(0.05)
        self.stop_loss_spin.setSingleStep(0.01)
        layout.addWidget(self.stop_loss_spin, row, 3)
        
        layout.addWidget(QLabel("止盈比例:"), row, 4)
        self.take_profit_spin = QDoubleSpinBox()
        self.take_profit_spin.setRange(0.01, 1.0)
        self.take_profit_spin.setValue(0.15)
        self.take_profit_spin.setSingleStep(0.05)
        layout.addWidget(self.take_profit_spin, row, 5)
        
        row += 1
        
        # 技术指标参数
        layout.addWidget(QLabel("RSI阈值:"), row, 0)
        self.rsi_spin = QSpinBox()
        self.rsi_spin.setRange(0, 100)
        self.rsi_spin.setValue(30)
        layout.addWidget(self.rsi_spin, row, 1)
        
        layout.addWidget(QLabel("MA周期:"), row, 2)
        self.ma_spin = QSpinBox()
        self.ma_spin.setRange(5, 200)
        self.ma_spin.setValue(20)
        layout.addWidget(self.ma_spin, row, 3)
        
        group_box.setLayout(layout)
        return group_box
    
    def _create_button_section(self):
        """创建操作按钮区域"""
        frame = QWidget()
        layout = QHBoxLayout(frame)
        
        # 运行回测按钮
        backtest_button = QPushButton("运行回测")
        backtest_button.setStyleSheet("QPushButton { background-color: #007bff; color: white; }")
        backtest_button.setMinimumHeight(35)
        layout.addWidget(backtest_button)
        
        # 参数优化按钮
        optimize_button = QPushButton("参数优化")
        optimize_button.setStyleSheet("QPushButton { background-color: #28a745; color: white; }")
        optimize_button.setMinimumHeight(35)
        layout.addWidget(optimize_button)
        
        # 生成报告按钮
        report_button = QPushButton("生成报告")
        report_button.setStyleSheet("QPushButton { background-color: #6c757d; color: white; }")
        report_button.setMinimumHeight(35)
        layout.addWidget(report_button)
        
        layout.addStretch()
        
        return frame
    
    def _create_results_panel(self):
        """创建回测结果面板"""
        group_box = QGroupBox("回测结果")
        group_box.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        
        layout = QVBoxLayout()
        
        # 创建标签页组件
        self.result_tabs = QTabWidget()
        
        # 性能指标标签页
        metrics_tab = self._create_metrics_tab()
        self.result_tabs.addTab(metrics_tab, "性能指标")
        
        # 交易记录标签页
        trades_tab = self._create_trades_tab()
        self.result_tabs.addTab(trades_tab, "交易记录")
        
        # 资金曲线标签页
        equity_tab = self._create_equity_tab()
        self.result_tabs.addTab(equity_tab, "资金曲线")
        
        layout.addWidget(self.result_tabs)
        group_box.setLayout(layout)
        return group_box
    
    def _create_metrics_tab(self):
        """创建性能指标标签页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # 关键指标显示
        key_group = QGroupBox("关键指标")
        key_group.setFont(QFont("Arial", 9))
        key_layout = QGridLayout(key_group)
        
        key_metrics = [
            ("总收益率", "total_return"),
            ("年化收益率", "annual_return"),
            ("夏普比率", "sharpe_ratio"),
            ("最大回撤", "max_drawdown"),
            ("胜率", "win_rate"),
            ("盈亏比", "profit_factor")
        ]
        
        for i, (label, key) in enumerate(key_metrics):
            row = i // 3
            col = i % 3
            
            key_layout.addWidget(QLabel(f"{label}:"), row, col*2)
            value_label = QLabel("0.00%")
            value_label.setFont(QFont("Arial", 10, QFont.Weight.Bold))
            value_label.setStyleSheet("color: #2E86AB;")
            key_layout.addWidget(value_label, row, col*2+1)
            
            self.key_metrics_labels[key] = value_label
        
        layout.addWidget(key_group)
        
        # 详细指标表格
        detail_group = QGroupBox("详细指标")
        detail_group.setFont(QFont("Arial", 9))
        detail_layout = QVBoxLayout(detail_group)
        
        self.metrics_tree = QTreeWidget()
        self.metrics_tree.setHeaderLabels(["指标", "数值", "说明"])
        self.metrics_tree.setColumnWidth(0, 120)
        self.metrics_tree.setColumnWidth(1, 100)
        self.metrics_tree.setColumnWidth(2, 150)
        
        detail_layout.addWidget(self.metrics_tree)
        layout.addWidget(detail_group)
        
        return widget
    
    def _create_trades_tab(self):
        """创建交易记录标签页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        self.trades_tree = QTreeWidget()
        self.trades_tree.setHeaderLabels(["时间", "标的", "方向", "数量", "价格", "金额", "盈亏", "状态"])
        
        # 设置列宽
        for i, width in enumerate([150, 100, 60, 60, 80, 100, 80, 80]):
            self.trades_tree.setColumnWidth(i, width)
        
        layout.addWidget(self.trades_tree)
        return widget
    
    def _create_equity_tab(self):
        """创建资金曲线标签页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # 资金曲线图区域
        chart_group = QGroupBox("资金曲线")
        chart_group.setFont(QFont("Arial", 9))
        chart_layout = QVBoxLayout(chart_group)
        
        # 简化实现：显示文本说明
        chart_label = QLabel("资金曲线图将在这里显示")
        chart_label.setFont(QFont("Arial", 12))
        chart_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        chart_layout.addWidget(chart_label)
        
        layout.addWidget(chart_group)
        
        # 资金统计
        stats_group = QGroupBox("资金统计")
        stats_group.setFont(QFont("Arial", 9))
        stats_layout = QGridLayout(stats_group)
        
        stats_info = [
            ("初始资金", "initial_capital"),
            ("最终资金", "final_capital"),
            ("总盈亏", "total_pnl"),
            ("日均盈亏", "daily_pnl"),
            ("最大资金", "max_equity"),
            ("最小资金", "min_equity")
        ]
        
        for i, (label, key) in enumerate(stats_info):
            row = i // 3
            col = i % 3
            
            stats_layout.addWidget(QLabel(f"{label}:"), row, col*2)
            value_label = QLabel("0")
            value_label.setFont(QFont("Arial", 10, QFont.Weight.Bold))
            value_label.setStyleSheet("color: #2E86AB;")
            stats_layout.addWidget(value_label, row, col*2+1)
            
            self.equity_stats_labels[key] = value_label
        
        layout.addWidget(stats_group)
        
        return widget
    
    def _setup_connections(self):
        """设置信号连接"""
        # 按钮连接
        for widget in self.findChildren(QPushButton):
            if widget.text() == "运行回测":
                widget.clicked.connect(self._run_backtest)
            elif widget.text() == "参数优化":
                widget.clicked.connect(self._optimize_parameters)
            elif widget.text() == "生成报告":
                widget.clicked.connect(self._generate_report)
    
    def _run_backtest(self):
        """运行回测"""
        def run_in_thread():
            try:
                # 准备回测配置
                backtest_config = self._prepare_backtest_config()
                
                # 运行回测
                results = self.trading_system.run_backtest_mode(backtest_config)
                
                if results.get("success"):
                    self.backtest_results = results
                    self._update_results_display(results)
                    QMessageBox.information(self, "回测完成", "回测执行成功")
                else:
                    error_msg = results.get('error', '未知错误')
                    QMessageBox.critical(self, "回测失败", f"回测执行失败: {error_msg}")
                    
            except Exception as e:
                QMessageBox.critical(self, "回测错误", f"回测执行失败: {e}")
        
        threading.Thread(target=run_in_thread, daemon=True).start()
    
    def _prepare_backtest_config(self):
        """准备回测配置"""
        # 获取选中的市场
        selected_markets = [market for market, check in self.market_checks.items() if check.isChecked()]
        
        return {
            "start_date": self.start_date_edit.date().toString("yyyy-MM-dd"),
            "end_date": self.end_date_edit.date().toString("yyyy-MM-dd"),
            "markets": selected_markets,
            "products": ["stock", "etf"],  # 默认产品类型
            "strategy_config": {
                "max_position_size": self.position_size_spin.value(),
                "stop_loss": self.stop_loss_spin.value(),
                "take_profit": self.take_profit_spin.value(),
                "rsi_threshold": self.rsi_spin.value(),
                "ma_period": self.ma_spin.value()
            }
        }
    
    def _update_results_display(self, results: Dict[str, Any]):
        """更新结果显示"""
        report = results.get("report", {})
        backtest_results = results.get("backtest_results", {})
        
        # 更新关键指标
        self._update_key_metrics(report)
        
        # 更新详细指标
        self._update_detail_metrics(report)
        
        # 更新交易记录
        self._update_trades_display(backtest_results.get("trades", []))
        
        # 更新资金统计
        self._update_equity_stats(backtest_results)
    
    def _update_key_metrics(self, report: Dict[str, Any]):
        """更新关键指标显示"""
        metrics_mapping = {
            "total_return": report.get("total_return", 0),
            "annual_return": report.get("annual_return", 0),
            "sharpe_ratio": report.get("sharpe_ratio", 0),
            "max_drawdown": report.get("max_drawdown", 0),
            "win_rate": report.get("win_rate", 0),
            "profit_factor": report.get("profit_factor", 0)
        }
        
        for key, value in metrics_mapping.items():
            if key in ["total_return", "annual_return", "max_drawdown"]:
                display_text = f"{value:.2%}"
            elif key == "sharpe_ratio":
                display_text = f"{value:.2f}"
            elif key == "win_rate":
                display_text = f"{value:.1%}"
            elif key == "profit_factor":
                display_text = f"{value:.2f}"
            else:
                display_text = str(value)
            
            if key in self.key_metrics_labels:
                self.key_metrics_labels[key].setText(display_text)
    
    def _update_detail_metrics(self, report: Dict[str, Any]):
        """更新详细指标显示"""
        # 清空现有数据
        self.metrics_tree.clear()
        
        # 添加详细指标
        detail_metrics = [
            ("交易次数", report.get("total_trades", 0), "总交易笔数"),
            ("盈利交易", report.get("winning_trades", 0), "盈利交易数量"),
            ("亏损交易", report.get("losing_trades", 0), "亏损交易数量"),
            ("平均盈利", f"{report.get('avg_win', 0):.2%}", "平均盈利比例"),
            ("平均亏损", f"{report.get('avg_loss', 0):.2%}", "平均亏损比例"),
            ("最大单笔盈利", f"{report.get('max_win', 0):.2%}", "最大单笔盈利比例"),
            ("最大单笔亏损", f"{report.get('max_loss', 0):.2%}", "最大单笔亏损比例"),
            ("持仓天数", report.get("holding_days", 0), "平均持仓天数"),
            ("年化波动率", f"{report.get('annual_volatility', 0):.2%}", "年化波动率")
        ]
        
        for metric in detail_metrics:
            item = QTreeWidgetItem(self.metrics_tree, [str(x) for x in metric])
            self.metrics_tree.addTopLevelItem(item)
    
    def _update_trades_display(self, trades: List[Dict[str, Any]]):
        """更新交易记录显示"""
        # 清空现有数据
        self.trades_tree.clear()
        
        # 添加交易记录
        for trade in trades[:100]:  # 限制显示数量
            values = (
                trade.get("timestamp", "未知"),
                trade.get("symbol", "未知"),
                trade.get("side", "未知"),
                str(trade.get("quantity", 0)),
                f"{trade.get('price', 0):.2f}",
                f"{trade.get('amount', 0):.0f}",
                f"{trade.get('pnl', 0):.2f}",
                trade.get("status", "未知")
            )
            item = QTreeWidgetItem(self.trades_tree, values)
            self.trades_tree.addTopLevelItem(item)
    
    def _update_equity_stats(self, backtest_results: Dict[str, Any]):
        """更新资金统计"""
        equity_data = backtest_results.get("equity_curve", [])
        if not equity_data:
            return
        
        initial_capital = backtest_results.get("initial_capital", 1000000)
        final_capital = equity_data[-1].get("equity", initial_capital) if equity_data else initial_capital
        total_pnl = final_capital - initial_capital
        
        max_equity = max(item.get("equity", 0) for item in equity_data) if equity_data else final_capital
        min_equity = min(item.get("equity", 0) for item in equity_data) if equity_data else final_capital
        
        stats = {
            "initial_capital": f"{initial_capital:,.0f}",
            "final_capital": f"{final_capital:,.0f}",
            "total_pnl": f"{total_pnl:,.0f} ({total_pnl/initial_capital:.2%})",
            "daily_pnl": f"{total_pnl/len(equity_data):.0f}" if equity_data else "0",
            "max_equity": f"{max_equity:,.0f}",
            "min_equity": f"{min_equity:,.0f}"
        }
        
        for key, value in stats.items():
            if key in self.equity_stats_labels:
                self.equity_stats_labels[key].setText(value)
    
    def _optimize_parameters(self):
        """参数优化"""
        QMessageBox.information(self, "参数优化", "参数优化功能开发中")
    
    def _generate_report(self):
        """生成报告"""
        if not self.backtest_results:
            QMessageBox.warning(self, "生成报告", "请先运行回测")
            return
        
        QMessageBox.information(self, "生成报告", "回测报告生成功能开发中")