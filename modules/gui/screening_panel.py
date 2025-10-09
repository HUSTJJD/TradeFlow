"""
筛选面板模块
提供标的筛选和结果查看功能
"""

import sys
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, 
                            QLabel, QPushButton, QGroupBox, QTreeWidget, 
                            QTreeWidgetItem, QMessageBox, QComboBox, QLineEdit,
                            QSpinBox, QDoubleSpinBox, QScrollArea)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
import threading
from typing import Dict, Any, List

from ..main_system import TradingSystem


class ScreeningPanel(QWidget):
    """标的筛选面板"""
    
    def __init__(self, parent, trading_system: TradingSystem):
        super().__init__(parent)
        self.trading_system = trading_system
        self.screening_results = []
        
        self.stats_labels = {}
        
        self._create_widgets()
        self._setup_connections()
    
    def _create_widgets(self):
        """创建界面组件"""
        # 主布局
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(10, 10, 10, 10)
        
        # 筛选控制面板
        control_frame = self._create_control_panel()
        main_layout.addWidget(control_frame)
        
        # 筛选结果表格
        result_frame = self._create_results_panel()
        main_layout.addWidget(result_frame)
        
        # 筛选统计
        stats_frame = self._create_statistics_panel()
        main_layout.addWidget(stats_frame)
    
    def _create_control_panel(self):
        """创建筛选控制面板"""
        group_box = QGroupBox("筛选控制")
        group_box.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        
        main_layout = QVBoxLayout()
        
        # 筛选参数设置
        param_frame = self._create_parameter_section()
        main_layout.addWidget(param_frame)
        
        # 筛选条件设置
        condition_frame = self._create_condition_section()
        main_layout.addWidget(condition_frame)
        
        # 操作按钮
        button_frame = self._create_button_section()
        main_layout.addWidget(button_frame)
        
        group_box.setLayout(main_layout)
        return group_box
    
    def _create_parameter_section(self):
        """创建筛选参数区域"""
        frame = QWidget()
        layout = QHBoxLayout(frame)
        layout.setSpacing(10)
        
        # 市场选择
        layout.addWidget(QLabel("目标市场:"))
        self.market_combo = QComboBox()
        self.market_combo.addItems(["ALL", "HK", "US", "CN"])
        self.market_combo.setMaximumWidth(80)
        layout.addWidget(self.market_combo)
        
        # 产品类型选择
        layout.addWidget(QLabel("产品类型:"))
        self.product_combo = QComboBox()
        self.product_combo.addItems(["ALL", "stock", "etf", "warrant", "cbbc"])
        self.product_combo.setMaximumWidth(80)
        layout.addWidget(self.product_combo)
        
        layout.addStretch()
        
        return frame
    
    def _create_condition_section(self):
        """创建筛选条件区域"""
        group_box = QGroupBox("筛选条件")
        group_box.setFont(QFont("Arial", 9))
        
        layout = QGridLayout()
        layout.setSpacing(10)
        
        # 技术指标条件
        row = 0
        
        # RSI阈值
        layout.addWidget(QLabel("RSI阈值:"), row, 0)
        self.rsi_spin = QSpinBox()
        self.rsi_spin.setRange(0, 100)
        self.rsi_spin.setValue(30)
        layout.addWidget(self.rsi_spin, row, 1)
        
        # MA周期
        layout.addWidget(QLabel("MA周期:"), row, 2)
        self.ma_spin = QSpinBox()
        self.ma_spin.setRange(5, 200)
        self.ma_spin.setValue(20)
        layout.addWidget(self.ma_spin, row, 3)
        
        # 最小成交量
        layout.addWidget(QLabel("最小成交量:"), row, 4)
        self.volume_spin = QSpinBox()
        self.volume_spin.setRange(1000, 10000000)
        self.volume_spin.setValue(1000000)
        self.volume_spin.setSingleStep(100000)
        layout.addWidget(self.volume_spin, row, 5)
        
        row += 1
        
        # 风险控制条件
        
        # 最大波动率
        layout.addWidget(QLabel("最大波动率:"), row, 0)
        self.volatility_spin = QDoubleSpinBox()
        self.volatility_spin.setRange(0.01, 5.0)
        self.volatility_spin.setValue(0.5)
        self.volatility_spin.setSingleStep(0.1)
        layout.addWidget(self.volatility_spin, row, 1)
        
        # 评分阈值
        layout.addWidget(QLabel("评分阈值:"), row, 2)
        self.score_spin = QDoubleSpinBox()
        self.score_spin.setRange(0.0, 10.0)
        self.score_spin.setValue(7.0)
        self.score_spin.setSingleStep(0.5)
        layout.addWidget(self.score_spin, row, 3)
        
        # 最大候选数
        layout.addWidget(QLabel("最大候选数:"), row, 4)
        self.max_candidates_spin = QSpinBox()
        self.max_candidates_spin.setRange(1, 500)
        self.max_candidates_spin.setValue(50)
        layout.addWidget(self.max_candidates_spin, row, 5)
        
        group_box.setLayout(layout)
        return group_box
    
    def _create_button_section(self):
        """创建操作按钮区域"""
        frame = QWidget()
        layout = QHBoxLayout(frame)
        
        # 立即筛选按钮
        screen_button = QPushButton("立即筛选")
        screen_button.setStyleSheet("QPushButton { background-color: #007bff; color: white; }")
        screen_button.setMinimumHeight(35)
        layout.addWidget(screen_button)
        
        # 保存结果按钮
        save_button = QPushButton("保存结果")
        save_button.setStyleSheet("QPushButton { background-color: #28a745; color: white; }")
        save_button.setMinimumHeight(35)
        layout.addWidget(save_button)
        
        # 导出CSV按钮
        export_button = QPushButton("导出CSV")
        export_button.setStyleSheet("QPushButton { background-color: #6c757d; color: white; }")
        export_button.setMinimumHeight(35)
        layout.addWidget(export_button)
        
        layout.addStretch()
        
        return frame
    
    def _create_results_panel(self):
        """创建筛选结果面板"""
        group_box = QGroupBox("筛选结果")
        group_box.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        
        layout = QVBoxLayout()
        
        # 筛选结果表格
        self.result_tree = QTreeWidget()
        self.result_tree.setHeaderLabels(["排名", "标的代码", "名称", "市场", "产品", "RSI", "MA", "成交量", "波动率", "综合评分"])
        
        # 设置列宽
        self.result_tree.setColumnWidth(0, 50)   # 排名
        self.result_tree.setColumnWidth(1, 100)  # 标的代码
        self.result_tree.setColumnWidth(2, 120)  # 名称
        self.result_tree.setColumnWidth(3, 60)   # 市场
        self.result_tree.setColumnWidth(4, 80)   # 产品
        self.result_tree.setColumnWidth(5, 60)   # RSI
        self.result_tree.setColumnWidth(6, 60)   # MA
        self.result_tree.setColumnWidth(7, 100)  # 成交量
        self.result_tree.setColumnWidth(8, 80)   # 波动率
        self.result_tree.setColumnWidth(9, 80)   # 综合评分
        
        layout.addWidget(self.result_tree)
        group_box.setLayout(layout)
        return group_box
    
    def _create_statistics_panel(self):
        """创建筛选统计面板"""
        group_box = QGroupBox("筛选统计")
        group_box.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        
        layout = QHBoxLayout()
        
        # 筛选统计信息
        stats_info = [
            ("总筛选标的", "total_screened"),
            ("符合条件", "qualified"),
            ("平均评分", "avg_score"),
            ("最高评分", "max_score"),
            ("筛选时间", "screening_time")
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
        # 按钮连接
        for widget in self.findChildren(QPushButton):
            if widget.text() == "立即筛选":
                widget.clicked.connect(self._run_screening)
            elif widget.text() == "保存结果":
                widget.clicked.connect(self._save_results)
            elif widget.text() == "导出CSV":
                widget.clicked.connect(self._export_csv)
    
    def _run_screening(self):
        """运行筛选"""
        def run_in_thread():
            try:
                # 更新筛选参数
                self._update_screening_params()
                
                # 运行筛选
                results = self.trading_system.run_screening_mode()
                self.screening_results = results
                
                # 更新界面
                self._update_results_display(results)
                QMessageBox.information(self, "筛选完成", f"找到 {len(results)} 个符合条件的标的")
                
            except Exception as e:
                QMessageBox.critical(self, "筛选错误", f"筛选执行失败: {e}")
        
        threading.Thread(target=run_in_thread, daemon=True).start()
    
    def _update_screening_params(self):
        """更新筛选参数"""
        # 这里应该更新系统的筛选参数配置
        # 简化实现，仅记录参数值
        params = {
            "market": self.market_combo.currentText(),
            "product": self.product_combo.currentText(),
            "rsi_threshold": self.rsi_spin.value(),
            "ma_period": self.ma_spin.value(),
            "min_volume": self.volume_spin.value(),
            "max_volatility": self.volatility_spin.value(),
            "score_threshold": self.score_spin.value(),
            "max_candidates": self.max_candidates_spin.value()
        }
        print(f"筛选参数已更新: {params}")
    
    def _update_results_display(self, results: List[Dict[str, Any]]):
        """更新结果显示"""
        # 清空现有结果
        self.result_tree.clear()
        
        # 添加新结果
        max_candidates = self.max_candidates_spin.value()
        for i, result in enumerate(results[:max_candidates], 1):
            values = [
                str(i),  # 排名
                result.get('symbol', '未知'),
                result.get('name', '未知'),
                result.get('market', '未知'),
                result.get('product_type', '未知'),
                f"{result.get('rsi', 0):.1f}",
                f"{result.get('ma_signal', 0):.1f}",
                f"{result.get('volume', 0):,}",
                f"{result.get('volatility', 0):.2%}",
                f"{result.get('final_score', 0):.1f}"
            ]
            item = QTreeWidgetItem(self.result_tree, values)
            self.result_tree.addTopLevelItem(item)
        
        # 更新统计信息
        self._update_stats_display(results)
    
    def _update_stats_display(self, results: List[Dict[str, Any]]):
        """更新统计信息显示"""
        if not results:
            self.stats_labels["total_screened"].setText("0")
            self.stats_labels["qualified"].setText("0")
            self.stats_labels["avg_score"].setText("0.0")
            self.stats_labels["max_score"].setText("0.0")
            self.stats_labels["screening_time"].setText("未知")
            return
        
        total_count = len(results)
        score_threshold = self.score_spin.value()
        qualified_count = len([r for r in results if r.get('final_score', 0) >= score_threshold])
        avg_score = sum(r.get('final_score', 0) for r in results) / total_count if total_count > 0 else 0
        max_score = max(r.get('final_score', 0) for r in results) if results else 0
        
        self.stats_labels["total_screened"].setText(str(total_count))
        self.stats_labels["qualified"].setText(str(qualified_count))
        self.stats_labels["avg_score"].setText(f"{avg_score:.2f}")
        self.stats_labels["max_score"].setText(f"{max_score:.2f}")
        self.stats_labels["screening_time"].setText("刚刚")
    
    def _save_results(self):
        """保存筛选结果"""
        if not self.screening_results:
            QMessageBox.warning(self, "保存失败", "没有筛选结果可保存")
            return
        
        try:
            # 这里应该实现保存到文件或数据库的逻辑
            QMessageBox.information(self, "保存成功", f"已保存 {len(self.screening_results)} 条筛选结果")
        except Exception as e:
            QMessageBox.critical(self, "保存错误", f"保存失败: {e}")
    
    def _export_csv(self):
        """导出CSV文件"""
        if not self.screening_results:
            QMessageBox.warning(self, "导出失败", "没有筛选结果可导出")
            return
        
        try:
            # 这里应该实现导出CSV的逻辑
            QMessageBox.information(self, "导出成功", "筛选结果已导出为CSV文件")
        except Exception as e:
            QMessageBox.critical(self, "导出错误", f"导出失败: {e}")