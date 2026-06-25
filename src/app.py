# -*- coding: utf-8 -*-
"""光学参数计算工具 Tk 主窗口与回调编排。"""

import json
import os
import threading
import tkinter as tk
from tkinter import filedialog, ttk

from .constants import (
    THEME_COLORS,
    THEME_FONTS,
    DEFAULT_REFLECTANCE_CSV,
    DEFAULT_FWHM_MAP_CSV,
    FWHM_MODEL_FIXED,
    FWHM_MODELS,
    FWHM_FIELD_AVERAGE,
    FWHM_FIELD_OPTIONS,
)
from .io_utils import parse_positive_float, parse_float
from .optics import compute_object_height
from .colorimetry import (
    analyze_reflectance_mc_drift,
    analyze_fwhm_field_delta_e,
    build_fwhm_config,
)
from .widgets import RoundedButton

SETTINGS_PATH = os.path.join(
    os.path.expanduser("~"), ".color_measure_settings.json"
)

_COLORIMETRY_VAR_ATTRS = (
    "reflectance_csv_var",
    "sampling_start_var",
    "sampling_end_var",
    "sampling_step_var",
    "wavelength_drift_var",
    "illuminant_var",
    "fwhm_model_var",
    "fixed_fwhm_var",
    "fwhm_map_csv_var",
    "fwhm_field_var",
    "fwhm_manual_x_var",
    "fwhm_manual_y_var",
    "mc_samples_var",
    "mc_seed_var",
)


class OpticalParameterCalculator(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("光学参数计算工具 v1.3")
        self.geometry("1000x620")
        self.minsize(900, 540)
        self.configure(bg=THEME_COLORS["background"])

        self._setup_style()

        notebook = ttk.Notebook(self)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        self.object_height_tab = ttk.Frame(notebook, padding=15)
        notebook.add(self.object_height_tab, text="物高计算")

        self.colorimetry_tab = ttk.Frame(notebook, padding=15)
        notebook.add(self.colorimetry_tab, text="色度学计算")

        self._build_object_height_tab()
        self._build_colorimetry_tab()
        self._mc_busy = False
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self._apply_loaded_settings()

    def _setup_style(self):
        style = ttk.Style()
        style.theme_use("clam")

        colors = THEME_COLORS
        fonts = THEME_FONTS

        style.configure(
            ".",
            background=colors["background"],
            foreground=colors["text"],
            bordercolor=colors["border"],
            troughcolor=colors["fill"],
        )
        style.configure("TFrame", background=colors["background"])
        style.configure("Card.TFrame", background=colors["card_translucent"])
        style.configure(
            "TLabel",
            font=fonts["body"],
            foreground=colors["text"],
            background=colors["background"],
        )
        style.configure(
            "Title.TLabel",
            font=fonts["title"],
            foreground=colors["primary"],
            background=colors["background"],
        )
        style.configure(
            "Secondary.TLabel",
            font=fonts["body"],
            foreground=colors["text_secondary"],
            background=colors["background"],
        )
        style.configure(
            "Card.TLabel",
            font=fonts["body"],
            foreground=colors["text"],
            background=colors["card_translucent"],
        )
        style.configure(
            "Accent.TLabel",
            font=fonts["accent_value"],
            foreground=colors["primary_light"],
            background=colors["card_translucent"],
        )
        style.configure(
            "Card.TLabelframe",
            background=colors["card_translucent"],
            borderwidth=1,
            relief="solid",
            bordercolor=colors["border"],
        )
        style.configure(
            "Card.TLabelframe.Label",
            font=fonts["section"],
            foreground=colors["text"],
            background=colors["card_translucent"],
        )
        style.configure(
            "TNotebook",
            background=colors["background"],
            borderwidth=0,
            tabmargins=[4, 0, 4, 0],
        )
        style.configure(
            "TNotebook.Tab",
            font=fonts["tab"],
            padding=[20, 10],
            background=colors["fill"],
            foreground=colors["text_secondary"],
            borderwidth=0,
        )
        style.map(
            "TNotebook.Tab",
            padding=[
                ("selected", [18, 9]),
                ("!selected", [20, 10]),
            ],
            background=[
                ("selected", colors["primary"]),
                ("active", colors["fill_light"]),
                ("!selected", colors["fill"]),
            ],
            foreground=[
                ("selected", "#FFFFFF"),
                ("active", colors["text"]),
                ("!selected", colors["text_secondary"]),
            ],
        )
        style.configure(
            "TEntry",
            fieldbackground=colors["fill_light"],
            borderwidth=1,
            relief="solid",
            bordercolor=colors["border"],
            insertcolor=colors["primary_light"],
            font=fonts["body"],
            padding=[6, 4],
        )
        style.map(
            "TEntry",
            fieldbackground=[
                ("focus", colors["card"]),
                ("!focus", colors["fill_light"]),
            ],
            bordercolor=[
                ("focus", colors["focus_ring"]),
                ("!focus", colors["border"]),
            ],
        )
        style.configure(
            "TCombobox",
            fieldbackground=colors["fill_light"],
            borderwidth=1,
            relief="solid",
            bordercolor=colors["border"],
            insertcolor=colors["primary_light"],
            font=fonts["body"],
            padding=[6, 4],
        )
        style.map(
            "TCombobox",
            fieldbackground=[
                ("focus", colors["card"]),
                ("readonly", colors["fill_light"]),
                ("!focus", colors["fill_light"]),
            ],
            bordercolor=[
                ("focus", colors["focus_ring"]),
                ("!focus", colors["border"]),
            ],
        )
        style.configure(
            "Treeview",
            background=colors["card_translucent"],
            foreground=colors["text"],
            fieldbackground=colors["card_translucent"],
            borderwidth=1,
            relief="solid",
            bordercolor=colors["border"],
            font=fonts["body"],
            rowheight=30,
        )
        style.configure(
            "Treeview.Heading",
            background=colors["fill_light"],
            foreground=colors["text_secondary"],
            font=fonts["label_bold"],
            borderwidth=0,
            relief="flat",
            padding=[8, 6],
        )
        style.map(
            "Treeview",
            background=[("selected", colors["primary_light"])],
            foreground=[("selected", "#FFFFFF")],
        )
        style.configure(
            "Vertical.TScrollbar",
            background=colors["fill"],
            troughcolor=colors["background"],
            borderwidth=0,
            arrowsize=12,
        )
        style.configure(
            "Horizontal.TProgressbar",
            background=colors["primary_light"],
            troughcolor=colors["fill_light"],
            bordercolor=colors["border"],
            lightcolor=colors["primary_light"],
            darkcolor=colors["primary"],
            borderwidth=0,
            thickness=12,
        )

    def _build_object_height_tab(self):
        main = ttk.Frame(self.object_height_tab)
        main.pack(fill=tk.BOTH, expand=True)

        left_panel = ttk.Frame(main, width=440)
        left_panel.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 20))
        left_panel.pack_propagate(False)

        right_panel = ttk.Frame(main)
        right_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        ttk.Label(left_panel, text="工作距离计算", style="Title.TLabel").pack(
            anchor=tk.W, pady=(0, 12)
        )

        self._build_input_panel(left_panel)
        self._build_formula_panel(left_panel)
        self._build_action_panel(left_panel)

        self._build_output_panel(right_panel)
        self._show_initial_state()

    def _build_input_panel(self, parent):
        input_group = ttk.LabelFrame(
            parent, text="配置参数", padding=12, style="Card.TLabelframe"
        )
        input_group.pack(fill=tk.X)
        input_group.columnconfigure(1, weight=1)

        self.target_length_var = tk.StringVar()
        self.target_width_var = tk.StringVar()
        self.half_fov_var = tk.StringVar()
        self.entrance_pupil_diameter_var = tk.StringVar()
        self.focal_length_var = tk.StringVar()

        self._add_input_row(input_group, 0, "目标长度", self.target_length_var, "mm")
        self._add_input_row(input_group, 1, "目标宽度", self.target_width_var, "mm")
        self._add_input_row(input_group, 2, "FOV 半视场角", self.half_fov_var, "deg")
        self._add_input_row(
            input_group, 3, "入瞳直径", self.entrance_pupil_diameter_var, "mm"
        )
        self._add_input_row(input_group, 4, "焦距", self.focal_length_var, "mm")

    def _add_input_row(self, parent, row, label, variable, unit):
        ttk.Label(parent, text=label, style="Card.TLabel").grid(
            row=row, column=0, sticky=tk.W, padx=(0, 8), pady=7
        )
        ttk.Entry(parent, textvariable=variable).grid(
            row=row, column=1, sticky=tk.EW, padx=(0, 8), pady=7
        )
        ttk.Label(parent, text=unit, style="Card.TLabel").grid(
            row=row, column=2, sticky=tk.W, pady=7
        )

    def _build_formula_panel(self, parent):
        formula_group = ttk.LabelFrame(
            parent, text="计算基准", padding=12, style="Card.TLabelframe"
        )
        formula_group.pack(fill=tk.X, pady=(14, 0))

        rows = [
            ("目标对角线", "sqrt(L^2 + W^2)"),
            ("对角线半高", "目标对角线 / 2"),
            ("工作距离", "对角线半高 / tan(半视场角)"),
            ("2°观测口径", "2 * 工作距离 * tan(1°)"),
            ("可探测半锥角", "atan((入瞳直径/2) / 工作距离)"),
            ("衍射极限DPI", "25.4 / 物面Rayleigh极限"),
        ]
        for row, (name, formula) in enumerate(rows):
            ttk.Label(formula_group, text=name, style="Card.TLabel").grid(
                row=row, column=0, sticky=tk.W, padx=(0, 10), pady=4
            )
            ttk.Label(formula_group, text=formula, style="Accent.TLabel").grid(
                row=row, column=1, sticky=tk.W, pady=4
            )

    def _build_action_panel(self, parent):
        action_frame = ttk.Frame(parent)
        action_frame.pack(fill=tk.X, pady=18)

        RoundedButton(
            action_frame,
            text="计算",
            command=self.calculate_working_distance,
            bg=THEME_COLORS["accent"],
            fg="#FFFFFF",
            activebackground=THEME_COLORS["accent_dark"],
            font=THEME_FONTS["button"],
        ).pack(side=tk.LEFT, padx=(0, 10))

        RoundedButton(
            action_frame,
            text="清空",
            command=self.clear_object_height_inputs,
            bg=THEME_COLORS["button_secondary"],
            fg=THEME_COLORS["button_secondary_text"],
            activebackground=THEME_COLORS["fill"],
            font=THEME_FONTS["button_small"],
        ).pack(side=tk.LEFT)

        self.status_var = tk.StringVar(value="等待输入参数")
        ttk.Label(parent, textvariable=self.status_var, style="Secondary.TLabel").pack(
            anchor=tk.W
        )

    def _build_output_panel(self, parent):
        result_group = ttk.LabelFrame(
            parent, text="输出数据", padding=10, style="Card.TLabelframe"
        )
        result_group.pack(fill=tk.BOTH, expand=True)
        result_group.rowconfigure(0, weight=1)
        result_group.columnconfigure(0, weight=1)

        columns = ("parameter", "value", "unit")
        self.result_table = ttk.Treeview(
            result_group, columns=columns, show="headings", height=10
        )
        self.result_table.heading("parameter", text="参数")
        self.result_table.heading("value", text="数值")
        self.result_table.heading("unit", text="单位")
        self.result_table.column("parameter", width=210, minwidth=160, anchor=tk.W)
        self.result_table.column("value", width=160, minwidth=120, anchor=tk.E)
        self.result_table.column("unit", width=120, minwidth=90, anchor=tk.W)
        self.result_table.grid(row=0, column=0, sticky=tk.NSEW)

        scrollbar = ttk.Scrollbar(
            result_group,
            orient=tk.VERTICAL,
            command=self.result_table.yview,
            style="Vertical.TScrollbar",
        )
        scrollbar.grid(row=0, column=1, sticky=tk.NS)
        self.result_table.configure(yscrollcommand=scrollbar.set)

        detail_group = ttk.LabelFrame(
            parent, text="计算过程", padding=10, style="Card.TLabelframe"
        )
        detail_group.pack(fill=tk.BOTH, expand=True, pady=(14, 0))

        self.detail_text = tk.Text(
            detail_group,
            height=10,
            wrap=tk.WORD,
            bd=0,
            padx=10,
            pady=10,
            font=THEME_FONTS["mono"],
            bg=THEME_COLORS["card"],
            fg=THEME_COLORS["text"],
            insertbackground=THEME_COLORS["primary_light"],
            relief=tk.FLAT,
        )
        self.detail_text.pack(fill=tk.BOTH, expand=True)

    def _build_colorimetry_tab(self):
        main = ttk.Frame(self.colorimetry_tab)
        main.pack(fill=tk.BOTH, expand=True)

        left_panel = ttk.Frame(main, width=440)
        left_panel.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 20))
        left_panel.pack_propagate(False)

        right_panel = ttk.Frame(main)
        right_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        ttk.Label(left_panel, text="波长漂移敏感度", style="Title.TLabel").pack(
            anchor=tk.W, pady=(0, 12)
        )

        scroll_canvas = tk.Canvas(
            left_panel,
            bg=THEME_COLORS["background"],
            highlightthickness=0,
            bd=0,
        )
        scroll_frame = ttk.Frame(scroll_canvas)
        scrollbar = ttk.Scrollbar(
            left_panel,
            orient=tk.VERTICAL,
            command=scroll_canvas.yview,
            style="Vertical.TScrollbar",
        )
        scroll_window = scroll_canvas.create_window(
            (0, 0), window=scroll_frame, anchor=tk.NW
        )
        scroll_canvas.configure(yscrollcommand=scrollbar.set)

        def update_scroll_region(event):
            scroll_canvas.configure(scrollregion=scroll_canvas.bbox("all"))

        def update_scroll_width(event):
            scroll_canvas.itemconfigure(scroll_window, width=event.width)

        def bind_mousewheel(event):
            scroll_canvas.bind_all("<MouseWheel>", on_mousewheel)

        def unbind_mousewheel(event):
            scroll_canvas.unbind_all("<MouseWheel>")

        def on_mousewheel(event):
            scroll_canvas.yview_scroll(int(-event.delta / 120), "units")

        scroll_frame.bind("<Configure>", update_scroll_region)
        scroll_canvas.bind("<Configure>", update_scroll_width)
        scroll_canvas.bind("<Enter>", bind_mousewheel)
        scroll_canvas.bind("<Leave>", unbind_mousewheel)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        scroll_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self._build_colorimetry_input_panel(scroll_frame)
        self._build_colorimetry_formula_panel(scroll_frame)
        self._build_colorimetry_action_panel(scroll_frame)
        self._build_colorimetry_output_panel(right_panel)
        self._show_colorimetry_initial_state()

    def _build_colorimetry_input_panel(self, parent):
        input_group = ttk.LabelFrame(
            parent, text="配置参数", padding=12, style="Card.TLabelframe"
        )
        input_group.pack(fill=tk.X)
        input_group.columnconfigure(1, weight=1)

        self.reflectance_csv_var = tk.StringVar(value=DEFAULT_REFLECTANCE_CSV)
        self.sampling_start_var = tk.StringVar(value="380")
        self.sampling_end_var = tk.StringVar(value="780")
        self.sampling_step_var = tk.StringVar(value="10")
        self.wavelength_drift_var = tk.StringVar(value="1")
        self.illuminant_var = tk.StringVar(value="D50")
        self.fwhm_model_var = tk.StringVar(value=FWHM_MODEL_FIXED)
        self.fixed_fwhm_var = tk.StringVar(value="15")
        self.fwhm_map_csv_var = tk.StringVar(value=DEFAULT_FWHM_MAP_CSV)
        self.fwhm_field_var = tk.StringVar(value=FWHM_FIELD_AVERAGE)
        self.fwhm_manual_x_var = tk.StringVar(value="")
        self.fwhm_manual_y_var = tk.StringVar(value="")
        self.mc_samples_var = tk.StringVar(value="1000")
        self.mc_seed_var = tk.StringVar(value="0")

        ttk.Label(input_group, text="反射率 CSV", style="Card.TLabel").grid(
            row=0, column=0, sticky=tk.W, padx=(0, 8), pady=7
        )
        ttk.Entry(input_group, textvariable=self.reflectance_csv_var).grid(
            row=0, column=1, sticky=tk.EW, padx=(0, 8), pady=7
        )
        RoundedButton(
            input_group,
            text="浏览",
            command=self.browse_reflectance_csv,
            bg=THEME_COLORS["button_secondary"],
            fg=THEME_COLORS["button_secondary_text"],
            activebackground=THEME_COLORS["fill"],
            font=THEME_FONTS["button_small"],
            padx=12,
            pady=5,
        ).grid(row=0, column=2, sticky=tk.W, pady=7)

        self._add_input_row(input_group, 1, "起始波长", self.sampling_start_var, "nm")
        self._add_input_row(input_group, 2, "结束波长", self.sampling_end_var, "nm")
        self._add_input_row(input_group, 3, "采样间隔", self.sampling_step_var, "nm")
        self._add_input_row(
            input_group, 4, "通道漂移量", self.wavelength_drift_var, "nm"
        )

        ttk.Label(input_group, text="Lab 白点", style="Card.TLabel").grid(
            row=5, column=0, sticky=tk.W, padx=(0, 8), pady=7
        )
        ttk.Combobox(
            input_group,
            textvariable=self.illuminant_var,
            values=("D50", "D65", "A"),
            state="readonly",
            width=12,
        ).grid(row=5, column=1, sticky=tk.EW, padx=(0, 8), pady=7)
        ttk.Label(input_group, text="参考原脚本默认 D50", style="Card.TLabel").grid(
            row=5, column=2, sticky=tk.W, pady=7
        )

        ttk.Label(input_group, text="FWHM 模型", style="Card.TLabel").grid(
            row=6, column=0, sticky=tk.W, padx=(0, 8), pady=7
        )
        ttk.Combobox(
            input_group,
            textvariable=self.fwhm_model_var,
            values=FWHM_MODELS,
            state="readonly",
            width=12,
        ).grid(row=6, column=1, sticky=tk.EW, padx=(0, 8), pady=7)
        ttk.Label(input_group, text="高斯光谱响应", style="Card.TLabel").grid(
            row=6, column=2, sticky=tk.W, pady=7
        )

        self._add_input_row(input_group, 7, "固定 FWHM", self.fixed_fwhm_var, "nm")

        ttk.Label(input_group, text="FWHM CSV", style="Card.TLabel").grid(
            row=8, column=0, sticky=tk.W, padx=(0, 8), pady=7
        )
        ttk.Entry(input_group, textvariable=self.fwhm_map_csv_var).grid(
            row=8, column=1, sticky=tk.EW, padx=(0, 8), pady=7
        )
        RoundedButton(
            input_group,
            text="浏览",
            command=self.browse_fwhm_map_csv,
            bg=THEME_COLORS["button_secondary"],
            fg=THEME_COLORS["button_secondary_text"],
            activebackground=THEME_COLORS["fill"],
            font=THEME_FONTS["button_small"],
            padx=12,
            pady=5,
        ).grid(row=8, column=2, sticky=tk.W, pady=7)

        ttk.Label(input_group, text="视场位置", style="Card.TLabel").grid(
            row=9, column=0, sticky=tk.W, padx=(0, 8), pady=7
        )
        ttk.Combobox(
            input_group,
            textvariable=self.fwhm_field_var,
            values=FWHM_FIELD_OPTIONS,
            state="readonly",
            width=12,
        ).grid(row=9, column=1, sticky=tk.EW, padx=(0, 8), pady=7)
        ttk.Label(input_group, text="过滤非 ok ROI", style="Card.TLabel").grid(
            row=9, column=2, sticky=tk.W, pady=7
        )

        manual_frame = ttk.Frame(input_group, style="Card.TFrame")
        manual_frame.grid(row=10, column=1, sticky=tk.EW, padx=(0, 8), pady=7)
        manual_frame.columnconfigure(1, weight=1)
        manual_frame.columnconfigure(3, weight=1)
        ttk.Label(input_group, text="手动 X/Y", style="Card.TLabel").grid(
            row=10, column=0, sticky=tk.W, padx=(0, 8), pady=7
        )
        ttk.Label(manual_frame, text="X", style="Card.TLabel").grid(
            row=0, column=0, sticky=tk.W, padx=(0, 4)
        )
        ttk.Entry(manual_frame, textvariable=self.fwhm_manual_x_var, width=8).grid(
            row=0, column=1, sticky=tk.EW, padx=(0, 8)
        )
        ttk.Label(manual_frame, text="Y", style="Card.TLabel").grid(
            row=0, column=2, sticky=tk.W, padx=(0, 4)
        )
        ttk.Entry(manual_frame, textvariable=self.fwhm_manual_y_var, width=8).grid(
            row=0, column=3, sticky=tk.EW
        )
        ttk.Label(input_group, text="像面坐标", style="Card.TLabel").grid(
            row=10, column=2, sticky=tk.W, pady=7
        )

        self._add_input_row(input_group, 11, "模拟次数", self.mc_samples_var, "次")
        self._add_input_row(input_group, 12, "随机种子", self.mc_seed_var, "")

    def _build_colorimetry_formula_panel(self, parent):
        formula_group = ttk.LabelFrame(
            parent, text="计算基准", padding=12, style="Card.TLabelframe"
        )
        formula_group.pack(fill=tk.X, pady=(14, 0))

        rows = [
            ("基准采样", "380-780 nm，默认 10 nm"),
            ("漂移模型", "蒙特卡洛整体，每通道独立 U[-D,+D]"),
            ("FWHM", "高斯响应加权完整反射光谱"),
            ("色差", "实测反射率 -> Lab -> ΔE00"),
            ("P95 ΔE00", "95% 场景不超过该色差值"),
            ("P99 ΔE00", "99% 场景不超过该色差值"),
        ]
        for row, (name, formula) in enumerate(rows):
            ttk.Label(formula_group, text=name, style="Card.TLabel").grid(
                row=row, column=0, sticky=tk.W, padx=(0, 10), pady=4
            )
            ttk.Label(formula_group, text=formula, style="Accent.TLabel").grid(
                row=row, column=1, sticky=tk.W, pady=4
            )

    def _build_colorimetry_action_panel(self, parent):
        action_frame = ttk.Frame(parent)
        action_frame.pack(fill=tk.X, pady=18)

        RoundedButton(
            action_frame,
            text="计算",
            command=self.calculate_colorimetry,
            bg=THEME_COLORS["accent"],
            fg="#FFFFFF",
            activebackground=THEME_COLORS["accent_dark"],
            font=THEME_FONTS["button"],
        ).pack(side=tk.LEFT, padx=(0, 10))

        RoundedButton(
            action_frame,
            text="清空",
            command=self.clear_colorimetry_inputs,
            bg=THEME_COLORS["button_secondary"],
            fg=THEME_COLORS["button_secondary_text"],
            activebackground=THEME_COLORS["fill"],
            font=THEME_FONTS["button_small"],
        ).pack(side=tk.LEFT)

        self.colorimetry_status_var = tk.StringVar(value="等待输入参数")
        ttk.Label(
            parent, textvariable=self.colorimetry_status_var, style="Secondary.TLabel"
        ).pack(anchor=tk.W)

        self.mc_progress = ttk.Progressbar(
            parent,
            mode="determinate",
            maximum=100,
            style="Horizontal.TProgressbar",
        )
        self.mc_progress.pack(fill=tk.X, pady=(8, 0))

    def _build_colorimetry_output_panel(self, parent):
        result_group = ttk.LabelFrame(
            parent, text="输出数据", padding=10, style="Card.TLabelframe"
        )
        result_group.pack(fill=tk.BOTH, expand=True)
        result_group.rowconfigure(0, weight=1)
        result_group.columnconfigure(0, weight=1)

        columns = ("sample", "mean", "max", "p95")
        self.colorimetry_result_table = ttk.Treeview(
            result_group, columns=columns, show="headings", height=10
        )
        self.colorimetry_result_table.heading("sample", text="样品")
        self.colorimetry_result_table.heading("mean", text="平均 ΔE00")
        self.colorimetry_result_table.heading("max", text="最大 ΔE00")
        self.colorimetry_result_table.heading("p95", text="P95 ΔE00")
        self.colorimetry_result_table.column("sample", width=170, minwidth=120, anchor=tk.CENTER)
        self.colorimetry_result_table.column("mean", width=130, minwidth=100, anchor=tk.CENTER)
        self.colorimetry_result_table.column("max", width=130, minwidth=100, anchor=tk.CENTER)
        self.colorimetry_result_table.column("p95", width=130, minwidth=100, anchor=tk.CENTER)
        self.colorimetry_result_table.grid(row=0, column=0, sticky=tk.NSEW)

        scrollbar = ttk.Scrollbar(
            result_group,
            orient=tk.VERTICAL,
            command=self.colorimetry_result_table.yview,
            style="Vertical.TScrollbar",
        )
        scrollbar.grid(row=0, column=1, sticky=tk.NS)
        self.colorimetry_result_table.configure(yscrollcommand=scrollbar.set)

        detail_group = ttk.LabelFrame(
            parent, text="计算过程", padding=10, style="Card.TLabelframe"
        )
        detail_group.pack(fill=tk.BOTH, expand=True, pady=(14, 0))

        self.colorimetry_detail_text = tk.Text(
            detail_group,
            height=10,
            wrap=tk.WORD,
            bd=0,
            padx=10,
            pady=10,
            font=THEME_FONTS["mono"],
            bg=THEME_COLORS["card"],
            fg=THEME_COLORS["text"],
            insertbackground=THEME_COLORS["primary_light"],
            relief=tk.FLAT,
        )
        self.colorimetry_detail_text.pack(fill=tk.BOTH, expand=True)

    def calculate_working_distance(self):
        try:
            target_length = parse_positive_float(
                self.target_length_var.get().strip(), "目标长度"
            )
            target_width = parse_positive_float(
                self.target_width_var.get().strip(), "目标宽度"
            )
            half_fov_deg = parse_positive_float(
                self.half_fov_var.get().strip(), "FOV 半视场角"
            )
            entrance_pupil_diameter = parse_positive_float(
                self.entrance_pupil_diameter_var.get().strip(), "入瞳直径"
            )
            focal_length = parse_positive_float(
                self.focal_length_var.get().strip(), "焦距"
            )

            result = compute_object_height(
                target_length,
                target_width,
                half_fov_deg,
                entrance_pupil_diameter,
                focal_length,
            )

            self._set_result_rows(result["rows"])
            self._set_detail_text("\n".join(result["details"]))
            self.status_var.set("计算完成")
        except ValueError as exc:
            self._set_result_rows([("输入错误", str(exc), "")])
            self._set_detail_text(f"输入错误：{exc}")
            self.status_var.set("参数错误")

    def clear_object_height_inputs(self):
        self.target_length_var.set("")
        self.target_width_var.set("")
        self.half_fov_var.set("")
        self.entrance_pupil_diameter_var.set("")
        self.focal_length_var.set("")
        self._show_initial_state()

    def calculate_colorimetry(self):
        if self._mc_busy:
            return
        try:
            csv_path = self.reflectance_csv_var.get().strip()
            if not csv_path:
                raise ValueError("请先选择反射率 CSV 文件。")

            start_nm = parse_positive_float(
                self.sampling_start_var.get().strip(), "起始波长"
            )
            end_nm = parse_positive_float(self.sampling_end_var.get().strip(), "结束波长")
            step_nm = parse_positive_float(
                self.sampling_step_var.get().strip(), "采样间隔"
            )
            drift_nm = parse_positive_float(
                self.wavelength_drift_var.get().strip(), "通道漂移量"
            )
            n_samples_value = parse_positive_float(
                self.mc_samples_var.get().strip(), "模拟次数"
            )
            if n_samples_value != int(n_samples_value):
                raise ValueError("模拟次数必须是整数。")
            n_samples = int(n_samples_value)
            seed = parse_float(self.mc_seed_var.get().strip(), "随机种子")
            illuminant = self.illuminant_var.get().strip()
            fwhm_config = build_fwhm_config(
                self.fwhm_model_var.get().strip(),
                self.fixed_fwhm_var.get(),
                self.fwhm_map_csv_var.get(),
                self.fwhm_field_var.get().strip(),
                self.fwhm_manual_x_var.get(),
                self.fwhm_manual_y_var.get(),
            )

            if fwhm_config["fwhm_nm"] is None:
                raise ValueError(
                    "漂移 ΔE00 需要带宽响应，请在「FWHM 模型」中选择"
                    "「固定 FWHM」或「面阵标定表」，不支持「忽略 FWHM」。"
                )
        except ValueError as exc:
            self._show_colorimetry_error(str(exc))
            return

        self._mc_busy = True
        self.colorimetry_status_var.set("正在准备计算…")
        self.mc_progress["value"] = 0
        threading.Thread(
            target=self._run_mc,
            args=(
                csv_path,
                start_nm,
                end_nm,
                step_nm,
                drift_nm,
                n_samples,
                seed,
                illuminant,
                fwhm_config,
            ),
            daemon=True,
        ).start()

    def _run_mc(
        self,
        csv_path,
        start_nm,
        end_nm,
        step_nm,
        drift_nm,
        n_samples,
        seed,
        illuminant,
        fwhm_config,
    ):
        try:
            self.after(0, self._set_mc_phase, "正在计算基准 Lab…", 5)
            summary, sample_rows = analyze_reflectance_mc_drift(
                csv_path,
                start_nm,
                end_nm,
                step_nm,
                drift_nm,
                illuminant,
                fwhm_config["fwhm_nm"],
                n_samples,
                seed,
                progress_callback=self._on_mc_progress,
            )
            fwhm_field_summary = None
            fwhm_field_rows = []
            if fwhm_config.get("fwhm_map"):
                self.after(0, self._set_mc_phase, "正在计算 FWHM 场偏差…", 92)
                fwhm_field_summary, fwhm_field_rows = analyze_fwhm_field_delta_e(
                    csv_path,
                    start_nm,
                    end_nm,
                    step_nm,
                    illuminant,
                    fwhm_config["fwhm_map"],
                )

            details = self._build_mc_details(
                csv_path,
                start_nm,
                end_nm,
                step_nm,
                drift_nm,
                n_samples,
                seed,
                illuminant,
                fwhm_config,
                summary,
                fwhm_field_summary,
                fwhm_field_rows,
            )
            self.after(0, self._apply_mc_result, summary, sample_rows, details)
        except ValueError as exc:
            self.after(0, self._show_colorimetry_error, str(exc))
        finally:
            self.after(0, self._release_mc_busy)

    def _set_mc_phase(self, text, value):
        self.colorimetry_status_var.set(text)
        self.mc_progress["value"] = value

    def _on_mc_progress(self, done, total):
        self.after(0, self._update_mc_progress, done, total)

    def _update_mc_progress(self, done, total):
        self.colorimetry_status_var.set(f"蒙特卡洛模拟中… {done}/{total}")
        self.mc_progress["value"] = 5 + 85 * done / total if total else 5

    def _release_mc_busy(self):
        self._mc_busy = False

    def _apply_mc_result(self, summary, sample_rows, details):
        self._set_mc_sample_rows(sample_rows)
        self._set_colorimetry_detail_text("\n".join(details))
        self.colorimetry_status_var.set("计算完成")
        self.mc_progress["value"] = 100

    def _show_colorimetry_error(self, message):
        self._set_mc_sample_rows(
            [{"sample": "输入错误", "mean": message, "max": "", "p95": ""}]
        )
        self._set_colorimetry_detail_text(f"输入错误：{message}")
        self.colorimetry_status_var.set("参数错误")
        self.mc_progress["value"] = 0

    def _build_mc_details(
        self,
        csv_path,
        start_nm,
        end_nm,
        step_nm,
        drift_nm,
        n_samples,
        seed,
        illuminant,
        fwhm_config,
        summary,
        fwhm_field_summary,
        fwhm_field_rows,
    ):
        details = [
            "=" * 60,
            "蒙特卡洛整体 CWL 漂移与 ΔE00 敏感度",
            "=" * 60,
            "",
            "配置参数:",
            f"  反射率 CSV: {csv_path}",
            f"  采样范围: {start_nm:g}-{end_nm:g} nm",
            f"  采样间隔: {step_nm:g} nm",
            f"  漂移幅度 D: ±{drift_nm:g} nm（每通道独立均匀分布）",
            f"  模拟次数 N: {n_samples}",
            f"  随机种子: {seed}",
            f"  Lab 白点: {illuminant}",
            "",
            *fwhm_config["detail_lines"],
            "",
            "数据概况:",
            f"  反射率数据范围: {summary['source_range'][0]:g}-{summary['source_range'][1]:g} nm",
            f"  样品数量: {summary['sample_count']}",
            f"  通道数量: {summary['channel_count']}",
            "",
            "全局统计（所有样品 × N 次场景）:",
            f"  平均 ΔE00 = {summary['mean_delta_e']:.6g}",
            f"  最大 ΔE00 = {summary['max_delta_e']:.6g}",
            f"  P95 ΔE00 = {summary['p95_delta_e']:.6g}",
            f"  P99 ΔE00 = {summary['p99_delta_e']:.6g}",
            f"  最差样品 = {summary['worst_sample']}",
            "",
            "计算基准:",
            "  每个 CWL 通道均为带宽(FWHM)高斯响应，对完整连续反射光谱加权积分。",
            "  蒙特卡洛：每次给所有通道各抽一个独立 U[-D,+D] 漂移量，整体重算 Lab，",
            "  对每个样品计算相对基准的 ΔE00，重复 N 次。",
            "  固定随机种子，相同输入结果完全可复现。",
            "  ΔE00 使用 CIEDE2000 公式计算。",
        ]
        if fwhm_field_summary:
            details.extend(
                [
                    "",
                    "FWHM 场偏差:",
                    f"  基准 ROI: {fwhm_field_summary['center_roi']}，FWHM = {fwhm_field_summary['center_fwhm']:.6g} nm",
                    f"  参与 ROI: {fwhm_field_summary['roi_count']} 个",
                    f"  相对中心 FWHM 的平均 ΔE00 = {fwhm_field_summary['mean_delta_e']:.6g}",
                    f"  相对中心 FWHM 的最大 ΔE00 = {fwhm_field_summary['max_delta_e']:.6g}",
                    f"  最差 ROI = {fwhm_field_summary['worst_roi']}",
                    f"  最差样品 = {fwhm_field_summary['worst_sample']}",
                    "",
                    "FWHM 场偏差 Top 5 ROI:",
                ]
            )
            for row in fwhm_field_rows[:5]:
                details.append(
                    "  ROI {roi_id}: x={center_x:.0f}, y={center_y:.0f}, "
                    "FWHM={fwhm_nm:.6g} nm, 平均 ΔE00={mean:.6g}, "
                    "最大 ΔE00={max:.6g}, 最差样品={worst_sample}".format(
                        **row
                    )
                )
        return details

    def clear_colorimetry_inputs(self):
        self.reflectance_csv_var.set(DEFAULT_REFLECTANCE_CSV)
        self.sampling_start_var.set("380")
        self.sampling_end_var.set("780")
        self.sampling_step_var.set("10")
        self.wavelength_drift_var.set("1")
        self.illuminant_var.set("D50")
        self.fwhm_model_var.set(FWHM_MODEL_FIXED)
        self.fixed_fwhm_var.set("15")
        self.fwhm_map_csv_var.set(DEFAULT_FWHM_MAP_CSV)
        self.fwhm_field_var.set(FWHM_FIELD_AVERAGE)
        self.fwhm_manual_x_var.set("")
        self.fwhm_manual_y_var.set("")
        self.mc_samples_var.set("1000")
        self.mc_seed_var.set("0")
        self._show_colorimetry_initial_state()

    def browse_reflectance_csv(self):
        file_path = filedialog.askopenfilename(
            title="选择反射率 CSV",
            filetypes=(("CSV 文件", "*.csv"), ("所有文件", "*.*")),
        )
        if file_path:
            self.reflectance_csv_var.set(file_path)

    def browse_fwhm_map_csv(self):
        file_path = filedialog.askopenfilename(
            title="选择 FWHM 标定 CSV",
            filetypes=(("CSV 文件", "*.csv"), ("所有文件", "*.*")),
        )
        if file_path:
            self.fwhm_map_csv_var.set(file_path)

    def _show_initial_state(self):
        self._set_result_rows([("等待计算", "请输入左侧参数", "")])
        self._set_detail_text("请输入目标长宽、FOV 半视场角、入瞳直径和焦距后点击计算。")
        self.status_var.set("等待输入参数")

    def _show_colorimetry_initial_state(self):
        self._set_mc_sample_rows(
            [{"sample": "等待计算", "mean": "请输入左侧参数", "max": "", "p95": ""}]
        )
        self._set_colorimetry_detail_text(
            "请选择反射率 CSV，设置采样、漂移量、模拟次数和 FWHM 模型后点击计算。"
        )
        self.colorimetry_status_var.set("等待输入参数")

    def _set_result_rows(self, rows):
        for item in self.result_table.get_children():
            self.result_table.delete(item)

        for parameter, value, unit in rows:
            if isinstance(value, float):
                value = f"{value:.6g}"
            self.result_table.insert("", tk.END, values=(parameter, value, unit))

    def _set_detail_text(self, text):
        self.detail_text.configure(state=tk.NORMAL)
        self.detail_text.delete("1.0", tk.END)
        self.detail_text.insert(tk.END, text)
        self.detail_text.configure(state=tk.DISABLED)

    def _set_mc_sample_rows(self, rows):
        for item in self.colorimetry_result_table.get_children():
            self.colorimetry_result_table.delete(item)

        for row in rows:
            sample = row["sample"]
            mean_value = row["mean"]
            max_value = row["max"]
            p95_value = row["p95"]
            if isinstance(mean_value, float):
                mean_value = f"{mean_value:.6g}"
            if isinstance(max_value, float):
                max_value = f"{max_value:.6g}"
            if isinstance(p95_value, float):
                p95_value = f"{p95_value:.6g}"
            self.colorimetry_result_table.insert(
                "",
                tk.END,
                values=(sample, mean_value, max_value, p95_value),
            )

    def _set_colorimetry_detail_text(self, text):
        self.colorimetry_detail_text.configure(state=tk.NORMAL)
        self.colorimetry_detail_text.delete("1.0", tk.END)
        self.colorimetry_detail_text.insert(tk.END, text)
        self.colorimetry_detail_text.configure(state=tk.DISABLED)

    def _settings_dict(self):
        return {attr: getattr(self, attr).get() for attr in _COLORIMETRY_VAR_ATTRS}

    def _apply_loaded_settings(self):
        data = self._load_settings()
        for attr in _COLORIMETRY_VAR_ATTRS:
            if attr in data:
                getattr(self, attr).set(data[attr])

    def _load_settings(self):
        try:
            with open(SETTINGS_PATH, "r", encoding="utf-8") as handle:
                return json.load(handle)
        except (OSError, ValueError):
            return {}

    def _save_settings(self):
        try:
            with open(SETTINGS_PATH, "w", encoding="utf-8") as handle:
                json.dump(
                    self._settings_dict(), handle, ensure_ascii=False, indent=2
                )
        except OSError:
            pass

    def _on_close(self):
        self._save_settings()
        self.destroy()
