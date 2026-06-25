# -*- coding: utf-8 -*-
"""optics 物高 / 工作距离几何计算测试。"""

import math

import pytest

from src.optics import compute_object_height


def _row_map(result):
    return {name: value for name, value, _unit in result["rows"]}


def test_compute_object_height_typical_values():
    rows = _row_map(
        compute_object_height(
            target_length=100.0,
            target_width=100.0,
            half_fov_deg=20.0,
            entrance_pupil_diameter=10.0,
            focal_length=25.0,
        )
    )

    diagonal = math.hypot(100.0, 100.0)
    half_height = diagonal / 2
    working_distance = half_height / math.tan(math.radians(20.0))

    assert rows["目标对角线"] == pytest.approx(diagonal)
    assert rows["工作距离"] == pytest.approx(working_distance)
    assert rows["F/#"] == pytest.approx(25.0 / 10.0)
    # 像面 Rayleigh = 1.22 * 0.55um * F#，输出单位 um
    assert rows["像面Rayleigh极限"] == pytest.approx(1.22 * 0.00055 * 2.5 * 1000)


def test_compute_object_height_half_fov_must_be_under_90():
    with pytest.raises(ValueError):
        compute_object_height(100.0, 100.0, 90.0, 10.0, 25.0)


def test_compute_object_height_working_distance_le_focal_raises():
    # 半视场角极大 → 工作距离极小 → 薄透镜放大率 <= 0
    with pytest.raises(ValueError):
        compute_object_height(100.0, 100.0, 89.0, 10.0, 25.0)
