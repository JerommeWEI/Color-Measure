# -*- coding: utf-8 -*-
"""colorimetry 色度学核心测试：CIEDE2000 官方算例、Lab、CIE 插值、
FWHM 采样、蒙特卡洛可复现。"""

import numpy as np
import pytest

from src.colorimetry import (
    delta_e_2000,
    xyz_to_lab,
    interpolate_cie_1931_2deg,
    sample_channel_reflectance,
    _percentile,
    _delta_e_2000_vectorized,
    analyze_reflectance_mc_drift,
    build_fwhm_config,
)
from src.constants import (
    WHITE_POINTS,
    FWHM_MODEL_NONE,
    FWHM_MODEL_FIXED,
    FWHM_MODEL_MAP,
)


# Sharma, Wu, Dalal (2005) CIEDE2000 参考算例 —— 验证实现的权威数据。
@pytest.mark.parametrize(
    "lab1,lab2,expected",
    [
        ((50.0000, 2.6772, -79.7751), (50.0000, 0.0000, -82.7485), 2.0425),
        ((50.0000, 3.1571, -77.2803), (50.0000, 0.0000, -82.7485), 2.8615),
        ((50.0000, 2.8361, -74.0200), (50.0000, 0.0000, -82.7485), 3.4412),
        ((60.2574, -34.0099, 36.2677), (60.4626, -34.1751, 39.4387), 1.2644),
        ((63.0109, -31.0961, -5.8663), (62.8187, -29.7946, -4.0864), 1.2630),
        ((22.7233, 20.0904, -46.6940), (23.0331, 14.9730, -42.5619), 2.0373),
    ],
)
def test_delta_e_2000_reference_pairs(lab1, lab2, expected):
    assert delta_e_2000(lab1, lab2) == pytest.approx(expected, rel=1e-3)


def test_delta_e_2000_symmetric_and_zero():
    a = (50.0, 2.5, -3.0)
    b = (52.0, -1.0, 4.0)
    assert delta_e_2000(a, b) == pytest.approx(delta_e_2000(b, a))
    assert delta_e_2000(a, a) == 0.0


def test_delta_e_2000_vectorized_matches_scalar():
    # 随机 500 对 Lab（覆盖各象限），向量化结果必须与标量逐元素一致
    rng = np.random.default_rng(123)
    n = 500
    lab1 = np.stack(
        [rng.uniform(0, 100, n), rng.uniform(-128, 128, n), rng.uniform(-128, 128, n)],
        axis=1,
    )
    lab2 = np.stack(
        [rng.uniform(0, 100, n), rng.uniform(-128, 128, n), rng.uniform(-128, 128, n)],
        axis=1,
    )
    # 注入边界：a=b=0 触发 c'=0 的 hue 分支
    lab1[:5, 1] = 0.0
    lab1[:5, 2] = 0.0
    lab2[:5, 1] = 0.0
    lab2[:5, 2] = 0.0
    vec = _delta_e_2000_vectorized(lab1, lab2)
    scalar = np.array([delta_e_2000(lab1[i], lab2[i]) for i in range(n)])
    assert np.allclose(vec, scalar, rtol=1e-9, atol=1e-12)


def test_xyz_to_lab_white_point_is_pure_white():
    for illuminant in ("D50", "D65", "A"):
        light, a, b = xyz_to_lab(WHITE_POINTS[illuminant], illuminant)
        assert light == pytest.approx(100.0)
        assert a == pytest.approx(0.0, abs=1e-9)
        assert b == pytest.approx(0.0, abs=1e-9)


def test_cie_exact_table_value_at_500nm():
    assert interpolate_cie_1931_2deg(500.0) == pytest.approx(
        (0.0049, 0.323, 0.272)
    )


def test_cie_interpolated_midpoint():
    # 502.5 nm 应为 500 与 505 表值的线性中点
    result = interpolate_cie_1931_2deg(502.5)
    assert result[0] == pytest.approx((0.0049 + 0.0024) / 2)
    assert result[1] == pytest.approx((0.323 + 0.4073) / 2)


def test_cie_out_of_range_raises():
    with pytest.raises(ValueError):
        interpolate_cie_1931_2deg(379.0)
    with pytest.raises(ValueError):
        interpolate_cie_1931_2deg(781.0)


def test_sample_channel_reflectance_no_fwhm_is_linear():
    xs = [380.0, 400.0]
    ys = [0.0, 10.0]
    assert sample_channel_reflectance(xs, ys, 390.0, None) == pytest.approx(5.0)


def test_sample_channel_reflectance_with_fwhm_near_center():
    # 数据范围两侧留余量，避免积分步进的浮点累积碰到数据边界
    xs = [370.0, 410.0]
    ys = [0.0, 10.0]
    value = sample_channel_reflectance(xs, ys, 390.0, 8.0)
    # 对称高斯加权，中心波长 390 的线性值为 5.0，加权结果应在其附近
    assert 4.5 < value < 5.5


def test_sample_channel_reflectance_fwhm_at_data_boundary():
    # 回归：FWHM 积分步进末点的浮点累积不得超出数据上界
    # （曾导致 linear_interpolate 抛 "超出反射率数据范围"）
    xs = [380.0, 400.0]
    ys = [0.0, 10.0]
    value = sample_channel_reflectance(xs, ys, 390.0, 8.0)
    assert 4.0 < value < 6.0


def test_percentile_known_values():
    values = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
    assert _percentile(values, 0.0) == 1
    assert _percentile(values, 1.0) == 10
    assert _percentile(values, 0.5) == pytest.approx(5.5)
    assert _percentile(values, 0.95) == pytest.approx(9.55)


def _write_reflectance(tmp_path, text):
    path = tmp_path / "refl.csv"
    path.write_text(text, encoding="utf-8")
    return str(path)


def test_mc_drift_reproducible_with_same_seed(tmp_path):
    path = _write_reflectance(
        tmp_path, "wl,s1,s2\n380,0.2,0.3\n500,0.5,0.6\n700,0.7,0.8\n"
    )
    args = (path, 380.0, 700.0, 100.0, 1.0, "D65", 15.0, 50)
    summary_a, _ = analyze_reflectance_mc_drift(*args, seed=42)
    summary_b, _ = analyze_reflectance_mc_drift(*args, seed=42)
    assert summary_a == summary_b


def test_mc_drift_zero_drift_gives_zero_delta(tmp_path):
    path = _write_reflectance(
        tmp_path, "wl,s1\n380,0.2\n500,0.5\n700,0.8\n"
    )
    summary, _rows = analyze_reflectance_mc_drift(
        path, 380.0, 700.0, 100.0, 0.0, "D65", 15.0, 10, seed=1
    )
    assert summary["mean_delta_e"] == pytest.approx(0.0, abs=1e-9)
    assert summary["max_delta_e"] == pytest.approx(0.0, abs=1e-9)


def test_mc_drift_accepts_float_seed(tmp_path):
    # app 层种子来自 parse_float，是 float（如默认 0.0）；不得因 float seed 崩溃
    path = _write_reflectance(tmp_path, "wl,s1\n380,0.2\n500,0.5\n700,0.8\n")
    summary, _rows = analyze_reflectance_mc_drift(
        path, 380.0, 700.0, 100.0, 1.0, "D65", 15.0, 10, seed=0.0
    )
    assert summary["n_samples"] == 10
    assert summary["mean_delta_e"] >= 0.0


def test_build_fwhm_config_models(tmp_path):
    none_cfg = build_fwhm_config(FWHM_MODEL_NONE, "15", "", "平均", "", "")
    assert none_cfg["fwhm_nm"] is None

    fixed_cfg = build_fwhm_config(FWHM_MODEL_FIXED, "15", "", "平均", "", "")
    assert fixed_cfg["fwhm_nm"] == 15.0

    map_path = tmp_path / "f.csv"
    map_path.write_text(
        "roi_id,roi_x,roi_y,roi_width,roi_height,fwhm_nm,metric_status\n"
        "r1,0,0,10,10,15.0,ok\n"
        "r2,20,0,10,10,20.0,ok\n",
        encoding="utf-8",
    )
    map_cfg = build_fwhm_config(
        FWHM_MODEL_MAP, "15", str(map_path), "最大", "", ""
    )
    assert map_cfg["fwhm_nm"] == 20.0
