
"""Graphical interface for the real-time CPU scheduling simulator."""

from __future__ import annotations

import html
import math
import textwrap
import time
from pathlib import Path
from tkinter import BOTH, END, LEFT, StringVar, ttk, filedialog, messagebox
import tkinter as tk

import customtkinter as ctk

from algorithms import ALGORITHMS, SchedulerEngine

try:
    from matplotlib.figure import Figure
    from matplotlib.backends.backend_agg import FigureCanvasAgg
except Exception:
    Figure = None
    FigureCanvasAgg = None


class MetricCard(ctk.CTkFrame):
    def __init__(self, master, title: str, accent: str):
        super().__init__(master, corner_radius=14, fg_color="#111827", border_width=1, border_color="#263244")
        self.accent = accent
        self.title_label = ctk.CTkLabel(self, text=title, text_color="#94A3B8", font=ctk.CTkFont(size=12, weight="bold"))
        self.title_label.pack(anchor="w", padx=14, pady=(12, 0))
        self.value_label = ctk.CTkLabel(self, text="0", text_color=accent, font=ctk.CTkFont(size=23, weight="bold"))
        self.value_label.pack(anchor="w", padx=14, pady=(0, 12))

    def set_value(self, value: str):
        self.value_label.configure(text=value)

    def set_theme(self, light_mode: bool):
        if light_mode:
            self.configure(fg_color="#FFFFFF", border_color="#CBD5E1")
            self.title_label.configure(text_color="#475569")
            self.value_label.configure(text_color=self.accent)
        else:
            self.configure(fg_color="#111827", border_color="#263244")
            self.title_label.configure(text_color="#94A3B8")
            self.value_label.configure(text_color=self.accent)


class SchedulingSimulatorApp(ctk.CTk):
    """Premium CustomTkinter desktop application for CPU scheduling."""

    def __init__(self):
        super().__init__()
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")
        self.title("Real-Time Interactive CPU Scheduling Simulator")
        self.geometry("1460x880")
        self.minsize(1180, 740)
        self.configure(fg_color="#070B14")
        self.light_presentation_mode = False

        self.engine = SchedulerEngine(self.add_log)
        self.is_running = False
        self.simulation_speed_ms = 650
        self._last_tick_ms = 0
        self._animation_phase = 0.0
        self._visual_time = 0.0
        self._console_height = 96
        self._console_min_height = 86
        self._console_max_height = 280
        self._console_drag_start_y = 0
        self._console_drag_start_height = self._console_height
        self._selected_pid: str | None = None
        self._create_variables()
        self._show_splash()
        self.after(1400, self._build_application)

    def _create_variables(self):
        self.pid_var = StringVar(value="P1")
        self.arrival_var = StringVar(value="0")
        self.burst_var = StringVar(value="6")
        self.priority_var = StringVar(value="2")
        self.algorithm_var = StringVar(value=ALGORITHMS[0])
        self.status_var = StringVar(value="READY")
        self.clock_var = StringVar(value="00:00:00")
        self.quantum_var = tk.IntVar(value=3)
        self.levels_var = tk.IntVar(value=3)
        self.aging_var = tk.IntVar(value=8)
        self.boost_var = tk.IntVar(value=24)
        self.mlfq_quantum_vars = [StringVar(value=str(value)) for value in (2, 4, 8, 12, 16)]
        self.export_format_var = StringVar(value="PDF Report")

    def _show_splash(self):
        self.splash = ctk.CTkFrame(self, fg_color="#070B14")
        self.splash.pack(fill=BOTH, expand=True)
        ctk.CTkLabel(
            self.splash,
            text="CPU Scheduling Simulator",
            font=ctk.CTkFont(family="Segoe UI", size=36, weight="bold"),
            text_color="#E5F2FF",
        ).pack(pady=(240, 10))
        ctk.CTkLabel(
            self.splash,
            text="Real-time adaptive operating system analysis console",
            font=ctk.CTkFont(size=15),
            text_color="#7DD3FC",
        ).pack()
        self.splash_bar = ctk.CTkProgressBar(self.splash, width=440, height=12, corner_radius=10, progress_color="#00D4FF")
        self.splash_bar.pack(pady=34)
        self.splash_bar.set(0)
        self._animate_splash(0)

    def _animate_splash(self, step: int):
        if not hasattr(self, "splash_bar"):
            return
        self.splash_bar.set(min(1, step / 24))
        if step < 24:
            self.after(45, lambda: self._animate_splash(step + 1))

    def _build_application(self):
        self.splash.destroy()
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(1, weight=1)
        self._build_topbar()
        self._build_sidebar()
        self._build_main_panel()
        self._build_right_panel()
        self._build_console()
        self._seed_demo_processes()
        self._apply_table_style()
        self._apply_presentation_theme()
        self._update_loop()

    def _build_topbar(self):
        top = ctk.CTkFrame(self, height=70, corner_radius=0, fg_color="#0B1020")
        top.grid(row=0, column=0, columnspan=3, sticky="ew")
        top.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(top, text="Real-Time Interactive CPU Scheduling Simulator",
                     font=ctk.CTkFont(size=22, weight="bold"), text_color="#F8FAFC").grid(row=0, column=0, padx=22, pady=18, sticky="w")
        self.top_status = ctk.CTkLabel(top, textvariable=self.status_var, width=140, height=34, corner_radius=18,
                                       fg_color="#172554", text_color="#7DD3FC", font=ctk.CTkFont(size=13, weight="bold"))
        self.top_status.grid(row=0, column=1, padx=10, pady=18, sticky="e")
        self.algorithm_badge = ctk.CTkLabel(top, text=ALGORITHMS[0], width=210, height=34, corner_radius=18,
                                            fg_color="#111827", text_color="#2EE59D", font=ctk.CTkFont(size=13, weight="bold"))
        self.algorithm_badge.grid(row=0, column=2, padx=(0, 12), pady=18)
        ctk.CTkLabel(top, textvariable=self.clock_var, font=ctk.CTkFont(size=15, weight="bold"),
                     text_color="#CBD5E1").grid(row=0, column=3, padx=(0, 22), pady=18)

    def _build_sidebar(self):
        side_outer = ctk.CTkFrame(self, width=280, corner_radius=0, fg_color="#0A0F1D")
        side_outer.grid(row=1, column=0, sticky="nsew")
        side_outer.grid_propagate(False)
        side_outer.grid_rowconfigure(0, weight=1)
        side_outer.grid_columnconfigure(0, weight=1)
        side = ctk.CTkScrollableFrame(side_outer, corner_radius=0, fg_color="#0A0F1D", scrollbar_button_color="#263244",
                                      scrollbar_button_hover_color="#38BDF8")
        side.grid(row=0, column=0, sticky="nsew")

        ctk.CTkLabel(side, text="Algorithms", font=ctk.CTkFont(size=15, weight="bold"), text_color="#E2E8F0").pack(anchor="w", padx=18, pady=(18, 8))
        self.algorithm_menu = ctk.CTkOptionMenu(side, values=ALGORITHMS, variable=self.algorithm_var, command=self.change_algorithm,
                                                fg_color="#111827", button_color="#0EA5E9", button_hover_color="#0284C7",
                                                dropdown_fg_color="#111827", width=240, height=38)
        self.algorithm_menu.pack(padx=18, fill="x")

        ctk.CTkLabel(side, text="Simulation Controls", font=ctk.CTkFont(size=15, weight="bold"), text_color="#E2E8F0").pack(anchor="w", padx=18, pady=(18, 8))
        controls = ctk.CTkFrame(side, fg_color="transparent")
        controls.pack(fill="x", padx=18)
        for column in range(2):
            controls.grid_columnconfigure(column, weight=1)
        self.start_button = self._button(controls, "Start", self.start_simulation, "#16A34A")
        self.start_button.grid(row=0, column=0, padx=(0, 5), pady=5, sticky="ew")
        self.pause_button = self._button(controls, "Pause", self.pause_simulation, "#CA8A04")
        self.pause_button.grid(row=0, column=1, padx=(5, 0), pady=5, sticky="ew")
        self.reset_button = self._button(controls, "Reset", self.reset_simulation, "#DC2626")
        self.reset_button.grid(row=1, column=0, padx=(0, 5), pady=5, sticky="ew")
        self.export_button = self._button(controls, "Export", self.export_metrics, "#2563EB")
        self.export_button.grid(row=1, column=1, padx=(5, 0), pady=5, sticky="ew")
        self.export_menu = ctk.CTkOptionMenu(
            side,
            values=["PDF Report", "PNG Report", "Excel Report"],
            variable=self.export_format_var,
            fg_color="#111827",
            button_color="#2563EB",
            button_hover_color="#1D4ED8",
            dropdown_fg_color="#111827",
            width=240,
            height=34,
        )
        self.export_menu.pack(padx=18, pady=(6, 0), fill="x")

        ctk.CTkLabel(side, text="Add / Edit Process", font=ctk.CTkFont(size=15, weight="bold"), text_color="#E2E8F0").pack(anchor="w", padx=18, pady=(18, 8))
        form = ctk.CTkFrame(side, fg_color="#101827", corner_radius=16, border_width=1, border_color="#1E293B")
        form.pack(fill="x", padx=18)
        self._entry(form, "Process ID", self.pid_var, 0)
        self._entry(form, "Arrival", self.arrival_var, 1)
        self._entry(form, "Burst", self.burst_var, 2)
        self._entry(form, "Priority", self.priority_var, 3)
        self._button(form, "+ Add Process", self.add_process, "#0EA5E9").grid(row=4, column=0, columnspan=2, padx=12, pady=(12, 6), sticky="ew")
        self._button(form, "Edit Selected", self.edit_selected_process, "#7C3AED").grid(row=5, column=0, columnspan=2, padx=12, pady=6, sticky="ew")
        self._button(form, "Delete Selected", self.remove_selected_process, "#BE123C").grid(row=6, column=0, columnspan=2, padx=12, pady=(6, 14), sticky="ew")

        ctk.CTkLabel(side, text="Live Settings", font=ctk.CTkFont(size=15, weight="bold"), text_color="#E2E8F0").pack(anchor="w", padx=18, pady=(18, 8))
        settings = ctk.CTkFrame(side, fg_color="#101827", corner_radius=16, border_width=1, border_color="#1E293B")
        settings.pack(fill="x", padx=18, pady=(0, 14))
        self.quantum_label = ctk.CTkLabel(settings, text="RR Quantum: 3", text_color="#CBD5E1")
        self.quantum_label.pack(anchor="w", padx=14, pady=(12, 0))
        ctk.CTkSlider(settings, from_=1, to=12, number_of_steps=11, variable=self.quantum_var,
                      command=self.update_quantum, progress_color="#00D4FF").pack(fill="x", padx=14, pady=7)
        self.level_label = ctk.CTkLabel(settings, text="MLFQ Levels: 3", text_color="#CBD5E1")
        self.level_label.pack(anchor="w", padx=14)
        ctk.CTkSlider(settings, from_=2, to=5, number_of_steps=3, variable=self.levels_var,
                      command=self.update_mlfq_levels, progress_color="#7C5CFF").pack(fill="x", padx=14, pady=7)
        self.aging_label = ctk.CTkLabel(settings, text="Aging: 8", text_color="#CBD5E1")
        self.aging_label.pack(anchor="w", padx=14)
        ctk.CTkSlider(settings, from_=3, to=20, number_of_steps=17, variable=self.aging_var,
                      command=self.update_aging, progress_color="#2EE59D").pack(fill="x", padx=14, pady=7)
        self.boost_label = ctk.CTkLabel(settings, text="Boost: 24", text_color="#CBD5E1")
        self.boost_label.pack(anchor="w", padx=14)
        ctk.CTkSlider(settings, from_=10, to=60, number_of_steps=25, variable=self.boost_var,
                      command=self.update_boost, progress_color="#FFB703").pack(fill="x", padx=14, pady=(7, 12))
        ctk.CTkLabel(settings, text="MLFQ Queue Quantums", text_color="#CBD5E1").pack(anchor="w", padx=14)
        quantum_row = ctk.CTkFrame(settings, fg_color="transparent")
        quantum_row.pack(fill="x", padx=12, pady=(6, 12))
        for index, variable in enumerate(self.mlfq_quantum_vars):
            entry = ctk.CTkEntry(quantum_row, textvariable=variable, width=42, height=28, corner_radius=8,
                                 fg_color="#0B1120", border_color="#263244", justify="center")
            entry.grid(row=0, column=index, padx=2, sticky="ew")
            entry.bind("<FocusOut>", self.update_mlfq_quantums)
            entry.bind("<Return>", self.update_mlfq_quantums)
            quantum_row.grid_columnconfigure(index, weight=1)
        self.theme_switch = ctk.CTkSwitch(side, text="Light presentation mode", command=self.toggle_theme,
                                          progress_color="#0EA5E9", text_color="#CBD5E1")
        self.theme_switch.pack(anchor="w", padx=22, pady=(0, 12))

    def _button(self, master, text, command, color):
        return ctk.CTkButton(master, text=text, command=command, height=36, corner_radius=10,
                             fg_color=color, hover_color=self._dim(color), font=ctk.CTkFont(size=13, weight="bold"))

    def _entry(self, master, label, variable, row):
        ctk.CTkLabel(master, text=label, text_color="#94A3B8").grid(row=row, column=0, padx=(12, 8), pady=(12 if row == 0 else 6, 0), sticky="w")
        entry = ctk.CTkEntry(master, textvariable=variable, height=32, corner_radius=9, fg_color="#0B1120", border_color="#263244")
        entry.grid(row=row, column=1, padx=(0, 12), pady=(12 if row == 0 else 6, 0), sticky="ew")
        master.grid_columnconfigure(1, weight=1)

    def _build_main_panel(self):
        main = ctk.CTkFrame(self, corner_radius=0, fg_color="#070B14")
        main.grid(row=1, column=1, sticky="nsew")
        main.grid_rowconfigure(1, weight=1)
        main.grid_columnconfigure(0, weight=1)

        chart_card = ctk.CTkFrame(main, corner_radius=18, fg_color="#0F172A", border_width=1, border_color="#1E293B")
        chart_card.grid(row=0, column=0, padx=18, pady=(18, 10), sticky="ew")
        chart_card.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(chart_card, text="Live Animated Gantt Chart", font=ctk.CTkFont(size=17, weight="bold"), text_color="#E2E8F0").grid(row=0, column=0, padx=18, pady=(14, 4), sticky="w")
        self.timeline_label = ctk.CTkLabel(chart_card, text="Timeline: 0", text_color="#7DD3FC", font=ctk.CTkFont(size=13, weight="bold"))
        self.timeline_label.grid(row=0, column=1, padx=18, pady=(14, 4), sticky="e")
        self.gantt_canvas = tk.Canvas(chart_card, height=220, bg="#0B1120", bd=0, highlightthickness=0)
        self.gantt_canvas.grid(row=1, column=0, columnspan=2, padx=14, pady=(8, 14), sticky="ew")

        middle = ctk.CTkFrame(main, fg_color="transparent")
        middle.grid(row=1, column=0, padx=18, pady=0, sticky="nsew")
        middle.grid_columnconfigure(0, weight=2)
        middle.grid_columnconfigure(1, weight=1)
        middle.grid_rowconfigure(0, weight=1)

        table_card = ctk.CTkFrame(middle, corner_radius=18, fg_color="#0F172A", border_width=1, border_color="#1E293B")
        table_card.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        table_card.grid_rowconfigure(1, weight=1)
        table_card.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(table_card, text="Live Process Table", font=ctk.CTkFont(size=17, weight="bold"), text_color="#E2E8F0").grid(row=0, column=0, padx=16, pady=14, sticky="w")
        columns = ("pid", "arrival", "burst", "remaining", "priority", "state", "queue", "waiting", "turnaround", "response")
        self.process_table = ttk.Treeview(table_card, columns=columns, show="headings", height=15)
        headings = {
            "pid": "PID", "arrival": "AT", "burst": "BT", "remaining": "RT", "priority": "PR",
            "state": "State", "queue": "Q", "waiting": "WT", "turnaround": "TAT", "response": "RES",
        }
        widths = {"pid": 75, "arrival": 55, "burst": 55, "remaining": 55, "priority": 55, "state": 100, "queue": 50, "waiting": 60, "turnaround": 65, "response": 65}
        for column in columns:
            self.process_table.heading(column, text=headings[column])
            self.process_table.column(column, width=widths[column], anchor="center", stretch=True)
        self.process_table.grid(row=1, column=0, padx=(14, 0), pady=(0, 14), sticky="nsew")
        table_scrollbar = ttk.Scrollbar(table_card, orient="vertical", command=self.process_table.yview)
        table_scrollbar.grid(row=1, column=1, padx=(0, 14), pady=(0, 14), sticky="ns")
        self.process_table.configure(yscrollcommand=table_scrollbar.set)
        self.process_table.bind("<<TreeviewSelect>>", self.on_table_select)

        queue_card = ctk.CTkFrame(middle, corner_radius=18, fg_color="#0F172A", border_width=1, border_color="#1E293B")
        queue_card.grid(row=0, column=1, sticky="nsew", padx=(10, 0))
        queue_card.grid_columnconfigure(0, weight=1)
        queue_card.grid_rowconfigure(2, weight=1)
        ctk.CTkLabel(queue_card, text="Ready Queue & CPU", font=ctk.CTkFont(size=17, weight="bold"), text_color="#E2E8F0").grid(row=0, column=0, padx=16, pady=14, sticky="w")
        self.cpu_canvas = tk.Canvas(queue_card, height=120, bg="#0B1120", bd=0, highlightthickness=0)
        self.cpu_canvas.grid(row=1, column=0, padx=14, pady=(0, 10), sticky="ew")
        self.queue_canvas = tk.Canvas(queue_card, height=280, bg="#0B1120", bd=0, highlightthickness=0)
        self.queue_canvas.grid(row=2, column=0, padx=14, pady=(0, 14), sticky="nsew")

    def _build_right_panel(self):
        right_outer = ctk.CTkFrame(self, width=330, corner_radius=0, fg_color="#0A0F1D")
        right_outer.grid(row=1, column=2, sticky="nsew")
        right_outer.grid_propagate(False)
        right_outer.grid_rowconfigure(0, weight=1)
        right_outer.grid_columnconfigure(0, weight=1)
        right = ctk.CTkScrollableFrame(right_outer, corner_radius=0, fg_color="#0A0F1D", scrollbar_button_color="#263244",
                                       scrollbar_button_hover_color="#38BDF8")
        right.grid(row=0, column=0, sticky="nsew")

        ctk.CTkLabel(right, text="Performance Metrics", font=ctk.CTkFont(size=17, weight="bold"), text_color="#E2E8F0").pack(anchor="w", padx=18, pady=(18, 10))
        self.metric_cards = {
            "avg_waiting": MetricCard(right, "Average Waiting Time", "#00D4FF"),
            "avg_turnaround": MetricCard(right, "Average Turnaround Time", "#2EE59D"),
            "cpu_utilization": MetricCard(right, "CPU Utilization", "#FFB703"),
            "throughput": MetricCard(right, "Throughput", "#C084FC"),
            "avg_response": MetricCard(right, "Average Response Time", "#FB7185"),
        }
        for card in self.metric_cards.values():
            card.pack(fill="x", padx=18, pady=5)

        self.completion_card = ctk.CTkFrame(right, corner_radius=14, fg_color="#111827", border_width=1, border_color="#263244")
        self.completion_card.pack(fill="x", padx=18, pady=(8, 5))
        ctk.CTkLabel(self.completion_card, text="Completion Order", text_color="#94A3B8", font=ctk.CTkFont(size=12, weight="bold")).pack(anchor="w", padx=14, pady=(12, 0))
        self.completion_label = ctk.CTkLabel(self.completion_card, text="None yet", text_color="#E2E8F0", wraplength=260, justify=LEFT)
        self.completion_label.pack(anchor="w", padx=14, pady=(4, 12))

        ctk.CTkLabel(right, text="Adaptive Feedback", font=ctk.CTkFont(size=17, weight="bold"), text_color="#E2E8F0").pack(anchor="w", padx=18, pady=(16, 8))
        self.feedback_card = ctk.CTkFrame(right, corner_radius=16, fg_color="#111827", border_width=1, border_color="#263244")
        self.feedback_card.pack(fill="x", padx=18, pady=5)
        self.feedback_title = ctk.CTkLabel(self.feedback_card, text="System Balanced", text_color="#2EE59D", font=ctk.CTkFont(size=16, weight="bold"))
        self.feedback_title.pack(anchor="w", padx=14, pady=(14, 4))
        self.feedback_text = ctk.CTkTextbox(
            self.feedback_card,
            height=178,
            corner_radius=10,
            fg_color="#0B1120",
            text_color="#CBD5E1",
            border_width=0,
            wrap="word",
            font=ctk.CTkFont(size=13),
        )
        self.feedback_text.pack(fill="x", padx=14, pady=(0, 14))
        self.feedback_text.configure(state="disabled")

        self.cpu_state_card = ctk.CTkFrame(right, corner_radius=16, fg_color="#111827", border_width=1, border_color="#263244")
        self.cpu_state_card.pack(fill="x", padx=18, pady=(14, 5))
        ctk.CTkLabel(self.cpu_state_card, text="CPU State", text_color="#94A3B8", font=ctk.CTkFont(size=12, weight="bold")).pack(anchor="w", padx=14, pady=(12, 0))
        self.cpu_state_label = ctk.CTkLabel(self.cpu_state_card, text="IDLE", text_color="#7DD3FC", font=ctk.CTkFont(size=26, weight="bold"))
        self.cpu_state_label.pack(anchor="w", padx=14, pady=(0, 12))

        self.requirements_card = ctk.CTkFrame(right, corner_radius=16, fg_color="#111827", border_width=1, border_color="#263244")
        self.requirements_card.pack(fill="x", padx=18, pady=(14, 18))
        ctk.CTkLabel(self.requirements_card, text="Project Checklist", text_color="#94A3B8",
                     font=ctk.CTkFont(size=12, weight="bold")).pack(anchor="w", padx=14, pady=(12, 4))
        checklist = (
            "Live Gantt chart\n"
            "Ready queue visualization\n"
            "Running / waiting / completed states\n"
            "Adaptive recommendation panel\n"
            "All mandatory performance metrics"
        )
        ctk.CTkLabel(self.requirements_card, text=checklist, text_color="#CBD5E1",
                     wraplength=260, justify=LEFT).pack(anchor="w", padx=14, pady=(0, 14))

    def _build_console(self):
        self.console_panel = ctk.CTkFrame(self, height=self._console_height, corner_radius=0, fg_color="#050816")
        self.console_panel.grid(row=2, column=0, columnspan=3, sticky="ew")
        self.console_panel.grid_propagate(False)
        self.console_panel.grid_columnconfigure(0, weight=1)
        self.console_panel.grid_rowconfigure(2, weight=1)

        self.console_resize_handle = ctk.CTkLabel(
            self.console_panel,
            text="▲",
            width=42,
            height=14,
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color="#7DD3FC",
            cursor="sb_v_double_arrow",
        )
        self.console_resize_handle.grid(row=0, column=0, pady=(2, 0))
        self.console_resize_handle.bind("<ButtonPress-1>", self._start_console_resize)
        self.console_resize_handle.bind("<B1-Motion>", self._resize_console)

        ctk.CTkLabel(
            self.console_panel,
            text="Event Console",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color="#94A3B8",
        ).grid(row=1, column=0, padx=18, pady=(0, 0), sticky="w")

        # Internal scrollbars stay hidden; the arrow handle expands the console instead.
        self.log_box = ctk.CTkTextbox(
            self.console_panel,
            height=58,
            corner_radius=10,
            fg_color="#0B1120",
            text_color="#CBD5E1",
            border_width=1,
            border_color="#1E293B",
            activate_scrollbars=False,
        )
        self.log_box.grid(row=2, column=0, padx=18, pady=(4, 10), sticky="nsew")

    def _start_console_resize(self, event):
        self._console_drag_start_y = event.y_root
        self._console_drag_start_height = self._console_height

    def _resize_console(self, event):
        drag_distance = self._console_drag_start_y - event.y_root
        new_height = self._console_drag_start_height + drag_distance
        self._console_height = max(self._console_min_height, min(self._console_max_height, new_height))
        self.console_panel.configure(height=self._console_height)

    def _seed_demo_processes(self):
        sample = [("P1", 0, 7, 2), ("P2", 1, 4, 1), ("P3", 3, 9, 4), ("P4", 5, 3, 3)]
        for pid, arrival, burst, priority in sample:
            self.engine.add_process(pid, arrival, burst, priority)
        self.add_log("Demo workload loaded. You can edit, remove, or add new processes live.")

    def _apply_table_style(self):
        style = ttk.Style()
        style.theme_use("default")
        if self.light_presentation_mode:
            style.configure("Treeview", background="#FFFFFF", foreground="#0F172A", fieldbackground="#FFFFFF",
                            rowheight=31, borderwidth=0, font=("Segoe UI", 10))
            style.configure("Treeview.Heading", background="#DBEAFE", foreground="#0F172A", borderwidth=0,
                            font=("Segoe UI", 10, "bold"))
            style.map("Treeview", background=[("selected", "#BAE6FD")])
            self.process_table.tag_configure("RUNNING", background="#CCFBF1", foreground="#0F172A")
            self.process_table.tag_configure("READY", background="#EFF6FF", foreground="#0F172A")
            self.process_table.tag_configure("DONE", background="#F1F5F9", foreground="#64748B")
            self.process_table.tag_configure("NEW", background="#FFFFFF", foreground="#475569")
        else:
            style.configure("Treeview", background="#0B1120", foreground="#E2E8F0", fieldbackground="#0B1120",
                            rowheight=31, borderwidth=0, font=("Segoe UI", 10))
            style.configure("Treeview.Heading", background="#111827", foreground="#7DD3FC", borderwidth=0,
                            font=("Segoe UI", 10, "bold"))
            style.map("Treeview", background=[("selected", "#164E63")])
            self.process_table.tag_configure("RUNNING", background="#123A3D", foreground="#A7F3D0")
            self.process_table.tag_configure("READY", background="#101827", foreground="#BFDBFE")
            self.process_table.tag_configure("DONE", background="#111827", foreground="#64748B")
            self.process_table.tag_configure("NEW", background="#0B1120", foreground="#94A3B8")

    def start_simulation(self):
        self.is_running = True
        self.status_var.set("RUNNING")
        self.add_log("Simulation started/resumed.")

    def pause_simulation(self):
        self.is_running = False
        self.status_var.set("PAUSED")
        self.add_log("Simulation paused.")

    def reset_simulation(self):
        self.is_running = False
        self.status_var.set("READY")
        self.engine.reset()
        self._visual_time = 0.0

    def change_algorithm(self, value: str):
        self.engine.set_algorithm(value)
        self.algorithm_badge.configure(text=value)
        self._visual_time = float(self.engine.current_time)

    def update_quantum(self, value):
        quantum = int(round(float(value)))
        self.engine.rr_quantum = quantum
        self.quantum_label.configure(text=f"RR Quantum: {quantum}")

    def update_mlfq_levels(self, value):
        levels = int(round(float(value)))
        self.engine.mlfq_levels = levels
        self.engine.rebuild_queues()
        self.level_label.configure(text=f"MLFQ Levels: {levels}")

    def update_aging(self, value):
        aging = int(round(float(value)))
        self.engine.aging_threshold = aging
        self.aging_label.configure(text=f"Aging: {aging}")

    def update_boost(self, value):
        boost = int(round(float(value)))
        self.engine.priority_boost_interval = boost
        self.boost_label.configure(text=f"Boost: {boost}")

    def update_mlfq_quantums(self, _event=None):
        quantums = []
        for variable in self.mlfq_quantum_vars:
            try:
                quantums.append(max(1, int(variable.get())))
            except ValueError:
                quantums.append(2)
        self.engine.mlfq_quantums = quantums
        for variable, value in zip(self.mlfq_quantum_vars, quantums):
            variable.set(str(value))
        self.add_log(f"MLFQ quantums updated to {quantums}.")

    def add_process(self):
        try:
            self.engine.add_process(self.pid_var.get(), int(self.arrival_var.get()), int(self.burst_var.get()), int(self.priority_var.get()))
            next_number = len(self.engine.processes) + 1
            self.pid_var.set(f"P{next_number}")
        except Exception as exc:
            messagebox.showerror("Invalid Process", str(exc))

    def edit_selected_process(self):
        if not self._selected_pid:
            messagebox.showinfo("Select Process", "Select a process from the table first.")
            return
        try:
            old_pid = self._selected_pid
            self.engine.edit_process(old_pid, self.pid_var.get(), int(self.arrival_var.get()), int(self.burst_var.get()), int(self.priority_var.get()))
            self._selected_pid = self.pid_var.get().strip() or old_pid
        except Exception as exc:
            messagebox.showerror("Invalid Edit", str(exc))

    def remove_selected_process(self):
        if not self._selected_pid:
            messagebox.showinfo("Select Process", "Select a process from the table first.")
            return
        self.engine.remove_process(self._selected_pid)
        self._selected_pid = None

    def on_table_select(self, _event):
        selected = self.process_table.selection()
        if not selected:
            return
        values = self.process_table.item(selected[0], "values")
        if not values:
            return
        pid = values[0]
        process = self.engine.get_process(pid)
        if process:
            self._selected_pid = pid
            self.pid_var.set(process.pid)
            self.arrival_var.set(str(process.arrival_time))
            self.burst_var.set(str(process.burst_time))
            self.priority_var.set(str(process.priority))

    def toggle_theme(self):
        self.light_presentation_mode = bool(self.theme_switch.get())
        ctk.set_appearance_mode("light" if self.light_presentation_mode else "dark")
        self._apply_presentation_theme()

    def export_metrics(self):
        export_format = self.export_format_var.get()
        if export_format == "PDF Report":
            extension = ".pdf"
            filetypes = [("PDF report", "*.pdf")]
        elif export_format == "PNG Report":
            extension = ".png"
            filetypes = [("PNG image", "*.png")]
        else:
            extension = ".xls"
            filetypes = [("Excel report", "*.xls")]
        path = filedialog.asksaveasfilename(
            title="Export Professional Scheduling Report",
            defaultextension=extension,
            filetypes=filetypes,
            initialfile=f"cpu_scheduling_report{extension}",
        )
        if not path:
            return
        report = self._report_snapshot()
        if export_format == "Excel Report":
            self._export_excel_report(path, report)
        else:
            if not self._export_visual_report(path, report, export_format):
                return
        self.add_log(f"{export_format} exported to {Path(path).name}.")

    def _report_snapshot(self) -> dict:
        metrics = self.engine.metrics()
        feedback_title, feedback_message, _color = self.engine.adaptive_feedback()
        rows = []
        for process in self.engine.processes:
            rows.append([
                process.pid,
                process.arrival_time,
                process.burst_time,
                process.remaining_time,
                process.priority,
                process.state,
                process.start_time if process.start_time is not None else "-",
                process.completion_time if process.completion_time is not None else "-",
                self.engine.live_waiting_time(process),
                self.engine.live_turnaround_time(process),
                process.response_time if process.response_time is not None else "-",
            ])
        summary = [
            ["Algorithm", self.engine.algorithm],
            ["Current Time", self.engine.current_time],
            ["Average Waiting Time", f"{metrics['avg_waiting']:.2f}"],
            ["Average Turnaround Time", f"{metrics['avg_turnaround']:.2f}"],
            ["CPU Utilization", f"{metrics['cpu_utilization']:.2f}%"],
            ["Throughput", f"{metrics['throughput']:.3f} processes/unit"],
            ["Average Response Time", f"{metrics['avg_response']:.2f}"],
            ["Completed Processes", f"{metrics['completed']} / {metrics['total']}"],
            ["Completion Order", metrics["completion_order"]],
        ]
        formulas = [
            "Turnaround Time = Completion Time - Arrival Time",
            "Waiting Time = Turnaround Time - Burst Time",
            "Response Time = First CPU Start Time - Arrival Time",
            "CPU Utilization = Busy CPU Time / Total Simulation Time x 100",
            "Throughput = Completed Processes / Total Simulation Time",
        ]
        return {
            "generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "summary": summary,
            "process_headers": ["PID", "AT", "BT", "RT", "Priority", "State", "Start", "CT", "WT", "TAT", "Response"],
            "process_rows": rows,
            "timeline_headers": ["Start", "End", "Process", "Algorithm"],
            "timeline_rows": [[block["start"], block["end"], block["pid"], block["algorithm"]] for block in self.engine.gantt],
            "feedback_title": feedback_title,
            "feedback_message": feedback_message,
            "formulas": formulas,
        }

    def _export_excel_report(self, path: str, report: dict):
        def td(value, header=False):
            tag = "th" if header else "td"
            return f"<{tag}>{html.escape(str(value))}</{tag}>"

        summary_rows = "\n".join(f"<tr>{td(label)}{td(value)}</tr>" for label, value in report["summary"])
        process_header = "".join(td(header, True) for header in report["process_headers"])
        process_rows = "\n".join("<tr>" + "".join(td(value) for value in row) + "</tr>" for row in report["process_rows"])
        timeline_header = "".join(td(header, True) for header in report["timeline_headers"])
        timeline_rows = "\n".join("<tr>" + "".join(td(value) for value in row) + "</tr>" for row in report["timeline_rows"])
        formulas = "".join(f"<li>{html.escape(item)}</li>" for item in report["formulas"])
        feedback = html.escape(f"{report['feedback_title']}: {report['feedback_message']}").replace("\n", "<br>")
        document = f"""<!doctype html>
<html>
<head>
<meta charset="utf-8">
<style>
body {{ font-family: Segoe UI, Arial, sans-serif; color: #0f172a; }}
h1 {{ color: #0f172a; }}
h2 {{ color: #1d4ed8; margin-top: 24px; }}
table {{ border-collapse: collapse; width: 100%; margin-top: 8px; }}
th {{ background: #1d4ed8; color: white; font-weight: bold; }}
td, th {{ border: 1px solid #cbd5e1; padding: 7px 9px; text-align: left; }}
.panel {{ border: 1px solid #cbd5e1; background: #f8fafc; padding: 12px; margin-top: 8px; }}
</style>
</head>
<body>
<h1>CPU Scheduling Simulator Report</h1>
<p><b>Generated:</b> {html.escape(report['generated_at'])}</p>
<h2>Summary Metrics</h2>
<table>{summary_rows}</table>
<h2>Adaptive Feedback</h2>
<div class="panel">{feedback}</div>
<h2>Calculation Notes</h2>
<ul>{formulas}</ul>
<h2>Process Table</h2>
<table><tr>{process_header}</tr>{process_rows}</table>
<h2>Execution Timeline / Gantt Blocks</h2>
<table><tr>{timeline_header}</tr>{timeline_rows}</table>
</body>
</html>"""
        Path(path).write_text(document, encoding="utf-8")

    def _export_visual_report(self, path: str, report: dict, export_format: str):
        if Figure is None or FigureCanvasAgg is None:
            messagebox.showerror("Matplotlib Required", "PDF and PNG export require matplotlib. Use Excel Report or install matplotlib.")
            return False
        figure = Figure(figsize=(11.7, 8.3), dpi=160, facecolor="white")
        FigureCanvasAgg(figure)
        title_ax = figure.add_axes([0.04, 0.90, 0.92, 0.08])
        summary_ax = figure.add_axes([0.04, 0.58, 0.40, 0.30])
        feedback_ax = figure.add_axes([0.50, 0.63, 0.46, 0.23])
        formula_ax = figure.add_axes([0.50, 0.47, 0.46, 0.12])
        process_ax = figure.add_axes([0.04, 0.19, 0.92, 0.23])
        timeline_ax = figure.add_axes([0.04, 0.04, 0.92, 0.11])
        for axis in (title_ax, summary_ax, feedback_ax, formula_ax, process_ax, timeline_ax):
            axis.axis("off")

        title_ax.text(0.0, 0.92, "CPU Scheduling Simulator Report", fontsize=20, weight="bold", color="#0f172a", va="top")
        title_ax.text(0.0, 0.42, f"Generated: {report['generated_at']}", fontsize=9, color="#475569", va="top")

        summary_table = summary_ax.table(cellText=report["summary"], colLabels=["Metric", "Value"], cellLoc="left",
                                         colLoc="left", bbox=[0, 0, 1, 1])
        self._style_report_table(summary_table, header_color="#1d4ed8")

        feedback_ax.text(0, 0.98, "Adaptive Feedback", fontsize=13, weight="bold", color="#1d4ed8", va="top")
        feedback_lines = [report["feedback_title"]]
        for paragraph in report["feedback_message"].split("\n\n"):
            feedback_lines.extend(textwrap.wrap(paragraph, 68))
            feedback_lines.append("")
        feedback_ax.text(0.02, 0.80, "\n".join(feedback_lines[:10]), fontsize=8.2, color="#0f172a", va="top",
                         bbox={"boxstyle": "round,pad=0.45", "facecolor": "#eff6ff", "edgecolor": "#bfdbfe"})

        formulas = "\n".join(f"- {item}" for item in report["formulas"])
        formula_ax.text(0, 0.98, "Calculation Notes", fontsize=13, weight="bold", color="#1d4ed8", va="top")
        formula_ax.text(0, 0.64, formulas, fontsize=7.2, color="#334155", va="top")

        process_rows = report["process_rows"][:10] or [["-", "-", "-", "-", "-", "No processes", "-", "-", "-", "-", "-"]]
        process_table = process_ax.table(cellText=process_rows, colLabels=report["process_headers"], cellLoc="center",
                                         colLoc="center", bbox=[0, 0, 1, 1])
        self._style_report_table(process_table, header_color="#0f766e")
        if len(report["process_rows"]) > len(process_rows):
            process_ax.text(0, -0.10, f"Showing first {len(process_rows)} process rows out of {len(report['process_rows'])}. Export Excel for full table.",
                            fontsize=8, color="#64748b")
        timeline_rows = report["timeline_rows"][-8:] or [["-", "-", "No execution yet", self.engine.algorithm]]
        timeline_table = timeline_ax.table(cellText=timeline_rows, colLabels=report["timeline_headers"], cellLoc="center",
                                           colLoc="center", bbox=[0, 0, 1, 1])
        self._style_report_table(timeline_table, header_color="#7c3aed")

        figure.savefig(path, format="pdf" if export_format == "PDF Report" else "png")
        return True

    def _style_report_table(self, table, header_color: str):
        table.auto_set_font_size(False)
        table.set_fontsize(8)
        for (row, _column), cell in table.get_celld().items():
            cell.set_edgecolor("#cbd5e1")
            if row == 0:
                cell.set_facecolor(header_color)
                cell.set_text_props(color="white", weight="bold")
            else:
                cell.set_facecolor("#ffffff" if row % 2 else "#f8fafc")

    def _apply_presentation_theme(self):
        colors = self._theme_colors()
        self.configure(fg_color=colors["window"])
        self._apply_widget_theme(self, colors)
        if hasattr(self, "metric_cards"):
            for card in self.metric_cards.values():
                card.set_theme(self.light_presentation_mode)
        if hasattr(self, "completion_card"):
            for card in (self.completion_card, self.feedback_card, self.cpu_state_card, self.requirements_card):
                card.configure(fg_color=colors["card"], border_color=colors["border"])
        if hasattr(self, "feedback_text"):
            self.feedback_text.configure(fg_color=colors["canvas"], text_color=colors["text"], border_color=colors["border"])
        if hasattr(self, "top_status"):
            self.top_status.configure(
                fg_color="#DBEAFE" if self.light_presentation_mode else "#172554",
                text_color="#0F172A" if self.light_presentation_mode else "#7DD3FC",
            )
            self.algorithm_badge.configure(
                fg_color="#E0F2FE" if self.light_presentation_mode else "#111827",
                text_color="#0369A1" if self.light_presentation_mode else "#2EE59D",
            )
        if hasattr(self, "process_table"):
            self._apply_table_style()

    def _apply_widget_theme(self, widget, colors: dict):
        for child in widget.winfo_children():
            class_name = child.__class__.__name__
            try:
                if class_name in {"CTkFrame", "CTkScrollableFrame"}:
                    child.configure(fg_color=colors["panel"])
                elif class_name == "CTkLabel":
                    child.configure(text_color=colors["text"])
                elif class_name == "CTkEntry":
                    child.configure(fg_color=colors["input"], text_color=colors["text"], border_color=colors["border"])
                elif class_name == "CTkTextbox":
                    child.configure(fg_color=colors["canvas"], text_color=colors["text"], border_color=colors["border"])
                elif class_name == "CTkOptionMenu":
                    child.configure(fg_color=colors["input"], text_color=colors["text"], dropdown_fg_color=colors["card"])
            except Exception:
                pass
            self._apply_widget_theme(child, colors)

    def _theme_colors(self) -> dict:
        if self.light_presentation_mode:
            return {
                "window": "#F8FAFC",
                "panel": "#F1F5F9",
                "card": "#FFFFFF",
                "canvas": "#FFFFFF",
                "canvas_alt": "#F8FAFC",
                "grid": "#E2E8F0",
                "grid_major": "#CBD5E1",
                "border": "#CBD5E1",
                "input": "#FFFFFF",
                "text": "#0F172A",
                "muted": "#475569",
                "accent": "#0369A1",
            }
        return {
            "window": "#070B14",
            "panel": "#0A0F1D",
            "card": "#111827",
            "canvas": "#0B1120",
            "canvas_alt": "#0F172A",
            "grid": "#1E293B",
            "grid_major": "#334155",
            "border": "#263244",
            "input": "#0B1120",
            "text": "#E2E8F0",
            "muted": "#94A3B8",
            "accent": "#7DD3FC",
        }

    def _update_loop(self):
        now = int(time.time() * 1000)
        if self.is_running and now - self._last_tick_ms >= self.simulation_speed_ms:
            self.engine.tick()
            self._last_tick_ms = now
        self._animation_phase = (self._animation_phase + 0.08) % (math.pi * 2)
        target_time = float(self.engine.current_time)
        self._visual_time += (target_time - self._visual_time) * 0.18
        if abs(target_time - self._visual_time) < 0.01:
            self._visual_time = target_time
        self.clock_var.set(time.strftime("%H:%M:%S"))
        self._refresh_all()
        self.after(60, self._update_loop)

    def _refresh_all(self):
        self.algorithm_badge.configure(text=self.engine.algorithm)
        self.timeline_label.configure(text=f"Timeline: {self.engine.current_time}")
        self._refresh_table()
        self._draw_gantt()
        self._draw_cpu()
        self._draw_ready_queue()
        self._refresh_metrics()

    def _refresh_table(self):
        selected_pid = self._selected_pid
        self.process_table.delete(*self.process_table.get_children())
        for process in self.engine.processes:
            values = (
                process.pid,
                process.arrival_time,
                process.burst_time,
                process.remaining_time,
                process.priority,
                process.state,
                f"Q{process.queue_level}" if self.engine.algorithm == "MLFQ" else "-",
                self.engine.live_waiting_time(process),
                self.engine.live_turnaround_time(process),
                process.response_time if process.response_time is not None else "-",
            )
            item = self.process_table.insert("", END, values=values, tags=(process.state,))
            if process.pid == selected_pid:
                self.process_table.selection_set(item)

    def _draw_gantt(self):
        canvas = self.gantt_canvas
        canvas.delete("all")
        width = max(1, canvas.winfo_width())
        height = max(1, canvas.winfo_height())
        colors = self._theme_colors()
        self._paint_canvas_background(canvas, width, height)
        visible_window = 28
        visual_time = self._visual_time
        start_time = max(0.0, visual_time - visible_window + 4)
        end_time = max(visible_window, start_time + visible_window)
        unit = width / visible_window
        top = 48
        bar_h = 72

        first_tick = int(math.floor(start_time))
        last_tick = int(math.ceil(end_time))
        shimmer_offset = (self._animation_phase * 18) % 36
        for tick in range(first_tick, last_tick + 1):
            x = (tick - start_time) * unit
            color = colors["grid"] if tick % 5 else colors["grid_major"]
            canvas.create_line(x, 28, x, height - 24, fill=color)
            if tick % 2 == 0:
                canvas.create_text(x + 3, height - 16, text=str(tick), fill=colors["muted"], anchor="w", font=("Segoe UI", 8))

        for block in self.engine.gantt:
            if block["end"] < start_time or block["start"] > end_time:
                continue
            x1 = max(0, (block["start"] - start_time) * unit)
            x2 = min(width, (block["end"] - start_time) * unit)
            if x2 <= 0 or x1 >= width:
                continue
            pulse = 0
            if block["pid"] == self.engine.running_pid:
                pulse = 4 + 3 * math.sin(self._animation_phase)
                x2 = min(width, max(x1 + 8, (visual_time - start_time) * unit))
            canvas.create_rectangle(x1 + 2, top - pulse, x2 - 2, top + bar_h + pulse,
                                    fill=block["color"], outline="", stipple="" if block["pid"] != "IDLE" else "gray50")
            if block["pid"] == self.engine.running_pid:
                highlight_x = x1 - 24 + shimmer_offset
                while highlight_x < x2:
                    canvas.create_line(highlight_x, top - pulse + 4, highlight_x + 22, top + bar_h + pulse - 4,
                                       fill="#FFFFFF", width=2)
                    highlight_x += 36
            canvas.create_rectangle(x1 + 2, top - pulse, x2 - 2, top + bar_h + pulse,
                                    outline=colors["accent"] if block["pid"] == self.engine.running_pid else colors["border"], width=2)
            label = block["pid"] if (x2 - x1) > 24 else ""
            canvas.create_text((x1 + x2) / 2, top + bar_h / 2, text=label, fill="#07111F",
                               font=("Segoe UI", 11, "bold"))
            canvas.create_text(x1 + 5, top + bar_h + 15, text=str(block["start"]), fill=colors["muted"], anchor="w", font=("Segoe UI", 8))

        current_x = (visual_time - start_time) * unit
        scan_tail = 34 + 12 * math.sin(self._animation_phase)
        canvas.create_line(current_x - scan_tail, 24, current_x, 24, fill=colors["accent"], width=3)
        canvas.create_line(current_x, 22, current_x, height - 24, fill=colors["text"], width=2)
        canvas.create_oval(current_x - 5, 20, current_x + 5, 30, fill=colors["text"], outline="")
        canvas.create_text(16, 18, text=f"Algorithm: {self.engine.algorithm}", fill=colors["accent"], anchor="w", font=("Segoe UI", 11, "bold"))

    def _draw_cpu(self):
        canvas = self.cpu_canvas
        canvas.delete("all")
        width = max(1, canvas.winfo_width())
        height = max(1, canvas.winfo_height())
        colors = self._theme_colors()
        self._paint_canvas_background(canvas, width, height)
        running = self.engine.get_process(self.engine.running_pid)
        color = running.color if running else "#334155"
        state_text = running.pid if running else "IDLE"
        glow = 8 + 4 * math.sin(self._animation_phase)
        canvas.create_rectangle(20, 26, width - 20, height - 22, fill=colors["card"], outline=colors["border"], width=2)
        canvas.create_rectangle(28, 34, width - 28, height - 30, fill=color, outline="", stipple="" if running else "gray50")
        canvas.create_rectangle(28 - glow / 2, 34 - glow / 2, width - 28 + glow / 2, height - 30 + glow / 2,
                                outline=colors["accent"] if running else colors["muted"], width=2)
        canvas.create_text(width / 2, height / 2 - 8, text="CPU", fill="#0B1120" if running else colors["text"], font=("Segoe UI", 13, "bold"))
        canvas.create_text(width / 2, height / 2 + 16, text=state_text, fill="#0B1120" if running else colors["text"], font=("Segoe UI", 19, "bold"))
        self.cpu_state_label.configure(text=state_text, text_color=color if running else colors["accent"])

    def _draw_ready_queue(self):
        canvas = self.queue_canvas
        canvas.delete("all")
        width = max(1, canvas.winfo_width())
        height = max(1, canvas.winfo_height())
        colors = self._theme_colors()
        self._paint_canvas_background(canvas, width, height)
        ready = self.engine.ready_processes()
        canvas.create_text(14, 18, text="Waiting / Ready Processes", fill=colors["muted"], anchor="w", font=("Segoe UI", 10, "bold"))
        if not ready:
            canvas.create_text(width / 2, height / 2, text="Ready queue empty", fill=colors["muted"], font=("Segoe UI", 12, "bold"))
            return
        x = 18
        y = 44
        box_w = 82 if width > 320 else 68
        box_h = 44
        row_gap = 56
        max_rows = max(1, int((height - y - 12) / row_gap))
        per_row = max(1, int((width - 32) / (box_w + 10)))
        max_visible = max_rows * per_row
        visible_ready = ready[:max_visible]
        for index, process in enumerate(visible_ready):
            if x + box_w > width - 14:
                x = 18
                y += row_gap
            fade = "gray50" if process.state == "DONE" else ""
            bob = 2 * math.sin(self._animation_phase + index * 0.8)
            tile_x = x + 3 * math.sin(self._animation_phase * 0.7 + index * 0.4)
            tile_y = y + bob
            canvas.create_rectangle(tile_x + 2, tile_y + 2, tile_x + box_w + 2, tile_y + box_h + 2,
                                    fill=colors["grid"], outline="")
            canvas.create_rectangle(tile_x, tile_y, tile_x + box_w, tile_y + box_h, fill=process.color, outline=colors["text"], width=1, stipple=fade)
            canvas.create_text(tile_x + box_w / 2, tile_y + 15, text=process.pid, fill="#08111F", font=("Segoe UI", 11, "bold"))
            detail = f"RT {process.remaining_time} | P {process.priority}"
            if self.engine.algorithm == "MLFQ":
                detail = f"Q{process.queue_level} | RT {process.remaining_time}"
            canvas.create_text(tile_x + box_w / 2, tile_y + 32, text=detail, fill="#08111F", font=("Segoe UI", 8, "bold"))
            x += box_w + 10
        if len(ready) > max_visible:
            canvas.create_text(width - 14, height - 12, text=f"+{len(ready) - max_visible} more in table",
                               fill=colors["accent"], anchor="e", font=("Segoe UI", 9, "bold"))

    def _refresh_metrics(self):
        metrics = self.engine.metrics()
        self.metric_cards["avg_waiting"].set_value(f"{metrics['avg_waiting']:.2f}")
        self.metric_cards["avg_turnaround"].set_value(f"{metrics['avg_turnaround']:.2f}")
        self.metric_cards["cpu_utilization"].set_value(f"{metrics['cpu_utilization']:.1f}%")
        self.metric_cards["throughput"].set_value(f"{metrics['throughput']:.3f}")
        self.metric_cards["avg_response"].set_value(f"{metrics['avg_response']:.2f}")
        self.completion_label.configure(text=metrics["completion_order"])

        title, message, color = self.engine.adaptive_feedback()
        self.feedback_title.configure(text=title, text_color=color)
        self.feedback_text.configure(state="normal")
        self.feedback_text.delete("1.0", END)
        self.feedback_text.insert("1.0", message)
        self.feedback_text.configure(state="disabled")

    def _paint_canvas_background(self, canvas, width, height):
        colors = self._theme_colors()
        canvas.configure(bg=colors["canvas"])
        canvas.create_rectangle(0, 0, width, height, fill=colors["canvas"], outline="")
        for i in range(0, width, 18):
            shade = colors["canvas_alt"] if (i // 18) % 2 else colors["canvas"]
            canvas.create_line(i, 0, i, height, fill=shade)

    def add_log(self, message: str):
        if not hasattr(self, "log_box"):
            return
        self.log_box.insert(END, message + "\n")
        lines = self.log_box.get("1.0", END).splitlines()
        if len(lines) > 90:
            self.log_box.delete("1.0", f"{len(lines) - 80}.0")
        self.log_box.see(END)

    @staticmethod
    def _dim(color: str) -> str:
        color = color.lstrip("#")
        r, g, b = tuple(int(color[i:i + 2], 16) for i in (0, 2, 4))
        return f"#{int(r * 0.82):02x}{int(g * 0.82):02x}{int(b * 0.82):02x}"


