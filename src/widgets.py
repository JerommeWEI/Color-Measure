# -*- coding: utf-8 -*-
"""自绘控件。"""

import tkinter as tk
import tkinter.font as tkfont

from .constants import THEME_COLORS


class RoundedButton(tk.Canvas):
    def __init__(
        self,
        parent,
        text,
        command,
        bg,
        fg,
        activebackground,
        font,
        padx=18,
        pady=8,
        radius=8,
    ):
        self._command = command
        self._bg = bg
        self._fg = fg
        self._activebackground = activebackground
        self._font = font
        self._text = text
        self._radius = radius
        self._hover = False
        self._pressed = False

        measure = tkfont.Font(font=font)
        width = measure.measure(text) + padx * 2
        height = measure.metrics("linespace") + pady * 2
        super().__init__(
            parent,
            width=width,
            height=height,
            bg=THEME_COLORS["background"],
            highlightthickness=0,
            bd=0,
            cursor="hand2",
        )

        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
        self.bind("<ButtonPress-1>", self._on_press)
        self.bind("<ButtonRelease-1>", self._on_release)
        self._draw()

    def _draw(self):
        self.delete("all")
        width = int(self.cget("width"))
        height = int(self.cget("height"))
        color = self._activebackground if self._pressed else self._bg
        if self._hover and not self._pressed:
            color = self._lighten(self._bg, 0.08)

        self._rounded_rectangle(1, 1, width - 1, height - 1, self._radius, fill=color)
        self.create_text(
            width / 2,
            height / 2,
            text=self._text,
            fill=self._fg,
            font=self._font,
            anchor="center",
        )

    def _rounded_rectangle(self, x1, y1, x2, y2, radius, **kwargs):
        points = [
            x1 + radius,
            y1,
            x2 - radius,
            y1,
            x2,
            y1,
            x2,
            y1 + radius,
            x2,
            y2 - radius,
            x2,
            y2,
            x2 - radius,
            y2,
            x1 + radius,
            y2,
            x1,
            y2,
            x1,
            y2 - radius,
            x1,
            y1 + radius,
            x1,
            y1,
        ]
        return self.create_polygon(points, smooth=True, outline="", **kwargs)

    @staticmethod
    def _lighten(hex_color, factor):
        hex_color = hex_color.lstrip("#")
        red = int(hex_color[0:2], 16)
        green = int(hex_color[2:4], 16)
        blue = int(hex_color[4:6], 16)
        red = min(255, int(red + (255 - red) * factor))
        green = min(255, int(green + (255 - green) * factor))
        blue = min(255, int(blue + (255 - blue) * factor))
        return f"#{red:02x}{green:02x}{blue:02x}"

    def _on_enter(self, _event):
        self._hover = True
        self._draw()

    def _on_leave(self, _event):
        self._hover = False
        self._pressed = False
        self._draw()

    def _on_press(self, _event):
        self._pressed = True
        self._draw()

    def _on_release(self, _event):
        was_pressed = self._pressed
        self._pressed = False
        self._hover = False
        self._draw()
        if was_pressed and self._command:
            self._command()
