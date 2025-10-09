"""主窗口类
集成所有GUI组件，提供完整的交易系统界面
"""

import tkinter as tk
from tkinter import ttk, messagebox
import threading
from typing import Dict, Any

from ..broker_apis.broker_manager import BrokerManager
from ..main_system import TradingSystem


class MainWindow:
    """交易系统主窗口"""
    
    def __init__(self, trading_system: TradingSystem, broker_manager: BrokerManager):
        self.trading_system = trading_system
        self.broker_manager = broker_manager
        
        # 创建主窗口
        self.root = tk.Tk()
        self.root.title("智能交易系统 - 多券商支持")
        self.root.geometry("1400x900")
        self.root.configure(bg='#f0f0f0')
        
        # 系统状态
        self.is_running = False
        self.auto_mode = False
        
        # 创建界面组件
        self._create_menu()
        self._create_main_frame()
        self._create_status_bar()
        
        # 启动状态更新
        self._start_status_updater()
    
    def _create_menu(self):
        """创建菜单栏"""
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        
        # 文件菜单
        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="系统设置", command=self._show_settings)
        file_menu.add_separator()
        file_menu.add_command(label="退出", command=self._exit_system)
        menubar.add_cascade(label="文件", menu=file_menu)
        
        # 交易菜单
        trade_menu = tk.Menu(menubar, tearoff=0)
        trade_menu.add_command(label="手动交易", command=self._show_trading_panel)
        trade_menu.add_command(label="自动交易", command=self._toggle_auto_trading)
        menubar.add_cascade(label="交易", menu=trade_menu)
        
        # 筛选菜单
        screen_menu = tk.Menu(menubar, tearoff=0)
        screen_menu.add_command(label="运行筛选", command=self._run_screening)
        screen_menu.add_command(label="筛选结果", command=self._show_screening_results)
        menubar.add_cascade(label="标的筛选", menu=screen_menu)
        
        # 回测菜单
        backtest_menu = tk.Menu(menubar, tearoff=0)
        backtest_menu.add_command(label="回测配置", command=self._show_backtest_panel)
        backtest_menu.add_command(label="策略优化", command=self._run_strategy_optimization)
        menubar.add_cascade(label="回测分析", menu=backtest_menu)
        
        # 券商菜单
        broker_menu = tk.Menu(menubar, tearoff=0)
        broker_menu.add_command(label="券商管理", command=self._show_broker_panel)
        broker_menu.add_command(label="账户信息", command=self._show_account_info)
        menubar.add_cascade(label="券商账户", menu=broker_menu)
        
        # 帮助菜单
        help_menu = tk.Menu(menubar, tearoff=0)
        help_menu.add_command(label="使用说明", command=self._show_help)
        help_menu.add_command(label="关于", command=self._show_about)
        menubar.add_cascade(label="帮助", menu=help_menu)
    
    def _create_main_frame(self):
        """创建主框架"""
        # 创建笔记本组件（标签页）
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # 创建各个标签页
        self._create_dashboard_tab()
        self._create_trading_tab()
        self._create_screening_tab()
        self._create_backtest_tab()
        self._create_broker_tab()
        self._create_status_tab()
    
    def _create_dashboard_tab(self):
        """创建仪表盘标签页"""
        dashboard_frame = ttk.Frame(self.notebook)
        self.notebook.add(dashboard_frame, text="仪表盘")
        
        # 系统概览
        overview_frame = ttk.LabelFrame(dashboard_frame, text="系统概览", padding=10)
        overview_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # 系统状态显示
        self.status_labels = {}
        status_info = [
            ("运行状态", "status"),
            ("自动模式", "auto_mode"), 
            ("最后筛选", "last_screening"),
            ("最后交易", "last_trading"),
            ("活跃券商", "active_brokers")
        ]
        
        for i, (label, key) in enumerate(status_info):
            row = i // 3
            col = i % 3
            
            ttk.Label(overview_frame, text=f"{label}:").grid(
                row=row, column=col*2, sticky=tk.W, padx=5, pady=2
            )
            self.status_labels[key] = ttk.Label(overview_frame, text="未知")
            self.status_labels[key].grid(
                row=row, column=col*2+1, sticky=tk.W, padx=5, pady=2
            )
        
        # 快速操作按钮
        button_frame = ttk.Frame(dashboard_frame)
        button_frame.pack(fill=tk.X, padx=5, pady=10)
        
        ttk.Button(button_frame, text="启动系统", command=self._start_system).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="停止系统", command=self._stop_system).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="运行筛选", command=self._run_screening).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="执行交易", command=self._run_trading).pack(side=tk.LEFT, padx=5)
    
    def _create_trading_tab(self):
        """创建交易标签页"""
        trading_frame = ttk.Frame(self.notebook)
        self.notebook.add(trading_frame, text="交易执行")
        
        # 交易面板内容将在TradingPanel类中实现
        ttk.Label(trading_frame, text="交易执行面板 - 开发中").pack(pady=20)
    
    def _create_screening_tab(self):
        """创建筛选标签页"""
        screening_frame = ttk.Frame(self.notebook)
        self.notebook.add(screening_frame, text="标的筛选")
        
        # 筛选面板内容将在ScreeningPanel类中实现
        ttk.Label(screening_frame, text="标的筛选面板 - 开发中").pack(pady=20)
    
    def _create_backtest_tab(self):
        """创建回测标签页"""
        backtest_frame = ttk.Frame(self.notebook)
        self.notebook.add(backtest_frame, text="回测分析")
        
        # 回测面板内容将在BacktestPanel类中实现
        ttk.Label(backtest_frame, text="回测分析面板 - 开发中").pack(pady=20)
    
    def _create_broker_tab(self):
        """创建券商标签页"""
        broker_frame = ttk.Frame(self.notebook)
        self.notebook.add(broker_frame, text="券商管理")
        
        # 券商面板内容将在BrokerPanel类中实现
        ttk.Label(broker_frame, text="券商管理面板 - 开发中").pack(pady=20)
    
    def _create_status_tab(self):
        """创建状态标签页"""
        status_frame = ttk.Frame(self.notebook)
        self.notebook.add(status_frame, text="系统状态")
        
        # 状态面板内容将在SystemStatusPanel类中实现
        ttk.Label(status_frame, text="系统状态面板 - 开发中").pack(pady=20)
    
    def _create_status_bar(self):
        """创建状态栏"""
        self.status_bar = ttk.Frame(self.root, relief=tk.SUNKEN)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)
        
        self.status_text = tk.StringVar()
        self.status_text.set("系统就绪")
        
        ttk.Label(self.status_bar, textvariable=self.status_text).pack(side=tk.LEFT, padx=5)
        
        # 时间显示
        self.time_text = tk.StringVar()
        ttk.Label(self.status_bar, textvariable=self.time_text).pack(side=tk.RIGHT, padx=5)
    
    def _start_status_updater(self):
        """启动状态更新器"""
        def update_status():
            import time
            from datetime import datetime
            
            while True:
                try:
                    # 更新时间
                    self.time_text.set(datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
                    
                    # 更新系统状态
                    if self.is_running:
                        system_status = self.trading_system.get_system_status()
                        self._update_status_display(system_status)
                    
                    time.sleep(1)
                except Exception as e:
                    print(f"状态更新错误: {e}")
                    time.sleep(5)
        
        status_thread = threading.Thread(target=update_status, daemon=True)
        status_thread.start()
    
    def _update_status_display(self, system_status: Dict[str, Any]):
        """更新状态显示"""
        try:
            self.status_labels["status"].config(text="运行中" if self.is_running else "停止")
            self.status_labels["auto_mode"].config(text="开启" if self.auto_mode else "关闭")
            
            last_screening = system_status.get("last_screening_time")
            if last_screening:
                self.status_labels["last_screening"].config(text=last_screening)
            
            last_trading = system_status.get("last_trading_time") 
            if last_trading:
                self.status_labels["last_trading"].config(text=last_trading)
            
            active_brokers = len(self.broker_manager.active_brokers)
            self.status_labels["active_brokers"].config(text=str(active_brokers))
            
        except Exception as e:
            print(f"更新状态显示失败: {e}")
    
    def _start_system(self):
        """启动系统"""
        try:
            self.is_running = True
            self.status_text.set("系统已启动")
            messagebox.showinfo("系统", "交易系统已启动")
        except Exception as e:
            messagebox.showerror("错误", f"启动系统失败: {e}")
    
    def _stop_system(self):
        """停止系统"""
        try:
            self.is_running = False
            self.auto_mode = False
            self.status_text.set("系统已停止")
            messagebox.showinfo("系统", "交易系统已停止")
        except Exception as e:
            messagebox.showerror("错误", f"停止系统失败: {e}")
    
    def _toggle_auto_trading(self):
        """切换自动交易模式"""
        self.auto_mode = not self.auto_mode
        status = "开启" if self.auto_mode else "关闭"
        self.status_text.set(f"自动交易模式已{status}")
        messagebox.showinfo("自动交易", f"自动交易模式已{status}")
    
    def _run_screening(self):
        """运行筛选"""
        if not self.is_running:
            messagebox.showwarning("警告", "请先启动系统")
            return
        
        def run_in_thread():
            try:
                self.status_text.set("正在运行标的筛选...")
                results = self.trading_system.run_screening_mode()
                self.status_text.set(f"筛选完成，找到 {len(results)} 个标的")
                messagebox.showinfo("筛选完成", f"找到 {len(results)} 个符合条件的标的")
            except Exception as e:
                messagebox.showerror("错误", f"筛选失败: {e}")
        
        threading.Thread(target=run_in_thread, daemon=True).start()
    
    def _run_trading(self):
        """执行交易"""
        if not self.is_running:
            messagebox.showwarning("警告", "请先启动系统")
            return
        
        def run_in_thread():
            try:
                self.status_text.set("正在执行交易...")
                results = self.trading_system.run_trading_mode()
                self.status_text.set(f"交易完成，执行 {len(results)} 笔交易")
                messagebox.showinfo("交易完成", f"执行 {len(results)} 笔交易")
            except Exception as e:
                messagebox.showerror("错误", f"交易失败: {e}")
        
        threading.Thread(target=run_in_thread, daemon=True).start()
    
    # 其他菜单功能占位实现
    def _show_settings(self):
        messagebox.showinfo("设置", "系统设置功能开发中")
    
    def _exit_system(self):
        if messagebox.askokcancel("退出", "确定要退出系统吗？"):
            self.root.quit()
    
    def _show_trading_panel(self):
        messagebox.showinfo("交易", "手动交易面板开发中")
    
    def _show_screening_results(self):
        messagebox.showinfo("筛选结果", "筛选结果查看功能开发中")
    
    def _show_backtest_panel(self):
        messagebox.showinfo("回测", "回测配置面板开发中")
    
    def _run_strategy_optimization(self):
        messagebox.showinfo("策略优化", "策略优化功能开发中")
    
    def _show_broker_panel(self):
        messagebox.showinfo("券商管理", "券商管理面板开发中")
    
    def _show_account_info(self):
        messagebox.showinfo("账户信息", "账户信息查看功能开发中")
    
    def _show_help(self):
        messagebox.showinfo("帮助", "使用说明文档开发中")
    
    def _show_about(self):
        messagebox.showinfo("关于", "智能交易系统 v2.0\n支持多券商API\n作者: AI助手")
    
    def run(self):
        """运行GUI主循环"""
        self.root.mainloop()