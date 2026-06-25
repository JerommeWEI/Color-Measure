# -*- coding: utf-8 -*-
"""色度学核心：CIE 配色函数插值、XYZ/Lab 转换、CIEDE2000、
FWHM 高斯采样与面阵选择、蒙特卡洛整体 CWL 漂移 ΔE00 分析与 FWHM 场偏差分析。"""

import math

import numpy as np

from .constants import (
    WHITE_POINTS,
    ILLUMINANT_SPD,
    CIE_1931_2DEG_5NM,
    SPECTRAL_MIN_NM,
    SPECTRAL_MAX_NM,
    FWHM_MODEL_NONE,
    FWHM_MODEL_FIXED,
    FWHM_MODEL_MAP,
    FWHM_FIELD_AVERAGE,
    FWHM_FIELD_MAX,
    FWHM_FIELD_MIN,
    FWHM_FIELD_CENTER,
    FWHM_FIELD_EDGE_AVERAGE,
    FWHM_FIELD_MANUAL,
)
from .io_utils import (
    parse_positive_float,
    parse_float,
    read_reflectance_csv,
    read_fwhm_map_csv,
    linear_interpolate,
    make_sampling_wavelengths,
)


def get_center_fwhm_point(fwhm_map):
    target_x = (fwhm_map["center_x_min"] + fwhm_map["center_x_max"]) / 2
    target_y = (fwhm_map["center_y_min"] + fwhm_map["center_y_max"]) / 2
    return min(
        fwhm_map["points"],
        key=lambda item: math.hypot(
            item["center_x"] - target_x, item["center_y"] - target_y
        ),
    )


def select_fwhm_from_map(fwhm_map, field_mode, manual_x=None, manual_y=None):
    points = fwhm_map["points"]

    if field_mode == FWHM_FIELD_AVERAGE:
        return {
            "fwhm_nm": fwhm_map["fwhm_mean"],
            "selection": f"全部 {fwhm_map['count']} 个有效 ROI 平均",
        }

    if field_mode == FWHM_FIELD_MAX:
        point = max(points, key=lambda item: item["fwhm_nm"])
        return {
            "fwhm_nm": point["fwhm_nm"],
            "selection": f"最大 FWHM ROI {point['roi_id']}",
        }

    if field_mode == FWHM_FIELD_MIN:
        point = min(points, key=lambda item: item["fwhm_nm"])
        return {
            "fwhm_nm": point["fwhm_nm"],
            "selection": f"最小 FWHM ROI {point['roi_id']}",
        }

    if field_mode == FWHM_FIELD_CENTER:
        point = get_center_fwhm_point(fwhm_map)
        return {
            "fwhm_nm": point["fwhm_nm"],
            "selection": f"中心最近 ROI {point['roi_id']}",
        }

    if field_mode == FWHM_FIELD_EDGE_AVERAGE:
        tolerance = 1e-9
        edge_points = [
            point
            for point in points
            if (
                abs(point["center_x"] - fwhm_map["center_x_min"]) <= tolerance
                or abs(point["center_x"] - fwhm_map["center_x_max"]) <= tolerance
                or abs(point["center_y"] - fwhm_map["center_y_min"]) <= tolerance
                or abs(point["center_y"] - fwhm_map["center_y_max"]) <= tolerance
            )
        ]
        if not edge_points:
            edge_points = points
        return {
            "fwhm_nm": sum(point["fwhm_nm"] for point in edge_points)
            / len(edge_points),
            "selection": f"边缘 {len(edge_points)} 个 ROI 平均",
        }

    if field_mode == FWHM_FIELD_MANUAL:
        if manual_x is None or manual_y is None:
            raise ValueError("手动坐标模式需要输入 X 和 Y。")
        point = min(
            points,
            key=lambda item: math.hypot(
                item["center_x"] - manual_x, item["center_y"] - manual_y
            ),
        )
        return {
            "fwhm_nm": point["fwhm_nm"],
            "selection": f"手动坐标最近 ROI {point['roi_id']}",
        }

    raise ValueError("视场位置必须是平均、最大、最小、中心、边缘平均或手动坐标。")


def build_fwhm_config(
    model,
    fixed_fwhm_text,
    map_csv_path,
    field_mode,
    manual_x_text,
    manual_y_text,
):
    if model == FWHM_MODEL_NONE:
        return {
            "model": model,
            "fwhm_nm": None,
            "detail_lines": ["  FWHM 模型: 忽略 FWHM"],
        }

    if model == FWHM_MODEL_FIXED:
        fixed_fwhm = parse_positive_float(fixed_fwhm_text.strip(), "固定 FWHM")
        return {
            "model": model,
            "fwhm_nm": fixed_fwhm,
            "detail_lines": [
                "  FWHM 模型: 固定 FWHM",
                f"  有效 FWHM: {fixed_fwhm:g} nm",
            ],
        }

    if model == FWHM_MODEL_MAP:
        map_csv_path = map_csv_path.strip()
        if not map_csv_path:
            raise ValueError("请选择 FWHM 标定 CSV。")

        manual_x = manual_y = None
        if field_mode == FWHM_FIELD_MANUAL:
            manual_x = parse_float(manual_x_text.strip(), "手动 X")
            manual_y = parse_float(manual_y_text.strip(), "手动 Y")

        fwhm_map = read_fwhm_map_csv(map_csv_path)
        selected = select_fwhm_from_map(fwhm_map, field_mode, manual_x, manual_y)
        return {
            "model": model,
            "fwhm_nm": selected["fwhm_nm"],
            "fwhm_map": fwhm_map,
            "detail_lines": [
                "  FWHM 模型: 面阵标定表",
                f"  FWHM 标定 CSV: {map_csv_path}",
                f"  有效 ROI: {fwhm_map['count']} 个",
                f"  忽略非 ok ROI: {fwhm_map['skipped_status_count']} 个",
                f"  FWHM 范围: {fwhm_map['fwhm_min']:.6g}-{fwhm_map['fwhm_max']:.6g} nm",
                f"  视场选择: {field_mode}（{selected['selection']}）",
                f"  有效 FWHM: {selected['fwhm_nm']:.6g} nm",
            ],
        }

    raise ValueError("FWHM 模型必须是忽略、固定 FWHM 或面阵标定表。")


def sample_channel_reflectance(
    source_wavelengths,
    reflectance_values,
    center_wavelength,
    fwhm_nm,
):
    if fwhm_nm is None:
        return linear_interpolate(
            source_wavelengths, reflectance_values, center_wavelength
        )

    sigma = fwhm_nm / (2 * math.sqrt(2 * math.log(2)))
    radius = sigma * 3
    start = max(source_wavelengths[0], center_wavelength - radius)
    end = min(source_wavelengths[-1], center_wavelength + radius)
    if start >= end:
        return linear_interpolate(
            source_wavelengths, reflectance_values, center_wavelength
        )

    integration_step = min(1.0, max(0.2, fwhm_nm / 12))
    weighted_total = 0.0
    weight_total = 0.0
    wavelength = start
    tolerance = integration_step * 1e-9
    while wavelength <= end + tolerance:
        weight = math.exp(-0.5 * ((wavelength - center_wavelength) / sigma) ** 2)
        # 步进浮点累积可能使 wavelength 略超 end（=数据上界），clamp 到数据范围
        sample_wavelength = max(
            source_wavelengths[0], min(source_wavelengths[-1], wavelength)
        )
        reflectance = linear_interpolate(
            source_wavelengths, reflectance_values, sample_wavelength
        )
        weighted_total += reflectance * weight
        weight_total += weight
        wavelength += integration_step

    if weight_total == 0:
        return linear_interpolate(
            source_wavelengths, reflectance_values, center_wavelength
        )
    return weighted_total / weight_total


def _xyz_to_lab_from_white(xyz, white_xyz):
    """由样品 XYZ 与参考白 XYZ（同光源积分得到）直接转 Lab，不查 WHITE_POINTS。"""
    x, y, z = xyz
    wx, wy, wz = white_xyz

    def f(value):
        delta = 6 / 29
        if value > delta ** 3:
            return value ** (1 / 3)
        return value / (3 * delta ** 2) + 4 / 29

    fx, fy, fz = f(x / wx), f(y / wy), f(z / wz)
    return 116 * fy - 16, 500 * (fx - fy), 200 * (fy - fz)


def sampled_reflectance_to_lab(sample_wavelengths, reflectance_values, illuminant):
    spd_table = ILLUMINANT_SPD[illuminant]
    spd_wl = [row[0] for row in spd_table]
    spd_val = [row[1] for row in spd_table]

    x_total = y_total = z_total = 0.0
    white_x = white_y = white_z = 0.0
    for wavelength, reflectance in zip(sample_wavelengths, reflectance_values):
        x_bar, y_bar, z_bar = interpolate_cie_1931_2deg(wavelength)
        spd = linear_interpolate(spd_wl, spd_val, wavelength)
        x_total += reflectance * spd * x_bar
        y_total += reflectance * spd * y_bar
        z_total += reflectance * spd * z_bar
        # 参考白：完全漫反射体（反射率≡1）在该光源下的 XYZ
        white_x += spd * x_bar
        white_y += spd * y_bar
        white_z += spd * z_bar

    return _xyz_to_lab_from_white(
        (x_total, y_total, z_total), (white_x, white_y, white_z)
    )


def calculate_sample_lab_for_fwhm(
    source_wavelengths,
    sample_curve,
    sample_wavelengths,
    illuminant,
    fwhm_nm,
):
    reflectance = [
        sample_channel_reflectance(
            source_wavelengths, sample_curve, wavelength, fwhm_nm
        )
        for wavelength in sample_wavelengths
    ]
    return sampled_reflectance_to_lab(sample_wavelengths, reflectance, illuminant)


def analyze_fwhm_field_delta_e(
    csv_path,
    start_nm,
    end_nm,
    step_nm,
    illuminant,
    fwhm_map,
):
    if illuminant not in ILLUMINANT_SPD:
        raise ValueError("Lab 白点必须是 D50、D65 或 A。")

    reflectance_data = read_reflectance_csv(csv_path)
    source_wavelengths = reflectance_data["wavelengths"]
    sample_wavelengths = make_sampling_wavelengths(start_nm, end_nm, step_nm)
    center_point = get_center_fwhm_point(fwhm_map)
    center_fwhm = center_point["fwhm_nm"]

    reference_labs = []
    for sample_curve in reflectance_data["samples"]:
        reference_labs.append(
            calculate_sample_lab_for_fwhm(
                source_wavelengths,
                sample_curve,
                sample_wavelengths,
                illuminant,
                center_fwhm,
            )
        )

    rows = []
    global_values = []
    worst_roi = ""
    worst_sample = ""
    worst_delta_e = -1.0

    for point in fwhm_map["points"]:
        roi_values = []
        roi_worst_sample = ""
        roi_worst_delta_e = -1.0

        for sample_name, sample_curve, reference_lab in zip(
            reflectance_data["sample_names"],
            reflectance_data["samples"],
            reference_labs,
        ):
            lab = calculate_sample_lab_for_fwhm(
                source_wavelengths,
                sample_curve,
                sample_wavelengths,
                illuminant,
                point["fwhm_nm"],
            )
            delta_e = delta_e_2000(reference_lab, lab)
            roi_values.append(delta_e)
            global_values.append(delta_e)

            if delta_e > roi_worst_delta_e:
                roi_worst_delta_e = delta_e
                roi_worst_sample = sample_name
            if delta_e > worst_delta_e:
                worst_delta_e = delta_e
                worst_roi = point["roi_id"]
                worst_sample = sample_name

        rows.append(
            {
                "roi_id": point["roi_id"],
                "center_x": point["center_x"],
                "center_y": point["center_y"],
                "fwhm_nm": point["fwhm_nm"],
                "mean": sum(roi_values) / len(roi_values),
                "max": max(roi_values),
                "worst_sample": roi_worst_sample,
            }
        )

    rows.sort(key=lambda item: item["max"], reverse=True)
    return {
        "center_roi": center_point["roi_id"],
        "center_fwhm": center_fwhm,
        "roi_count": len(fwhm_map["points"]),
        "sample_count": len(reflectance_data["sample_names"]),
        "channel_count": len(sample_wavelengths),
        "mean_delta_e": sum(global_values) / len(global_values),
        "max_delta_e": max(global_values),
        "worst_roi": worst_roi,
        "worst_sample": worst_sample,
    }, rows


def _mean(values):
    return sum(values) / len(values) if values else 0.0


def _percentile(values, p):
    """线性插值分位数，p∈[0,1]。"""
    if not values:
        return 0.0
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    rank = p * (len(ordered) - 1)
    lower = math.floor(rank)
    upper = math.ceil(rank)
    if lower == upper:
        return ordered[lower]
    return ordered[lower] + (ordered[upper] - ordered[lower]) * (rank - lower)


def _interpolate_cie_vectorized(wavelengths):
    """对 CIE 1931 2° 5nm 表做向量化线性插值。

    wavelengths: [n] nm 数组（380-780）。返回 [n, 3] 的 (x̄, ȳ, z̄)，
    与标量 interpolate_cie_1931_2deg 数值一致。
    """
    cie = np.asarray(CIE_1931_2DEG_5NM, dtype=float)
    cie_wl = cie[:, 0]
    cie_xyz = cie[:, 1:]
    idx = np.searchsorted(cie_wl, wavelengths)
    idx_lo = np.clip(idx - 1, 0, len(cie_wl) - 2)
    idx_hi = np.clip(idx_lo + 1, 0, len(cie_wl) - 1)
    wl_lo = cie_wl[idx_lo]
    wl_hi = cie_wl[idx_hi]
    span = np.where(wl_hi == wl_lo, 1.0, wl_hi - wl_lo)
    ratio = (wavelengths - wl_lo) / span
    return cie_xyz[idx_lo] + (cie_xyz[idx_hi] - cie_xyz[idx_lo]) * ratio[:, None]


def _interpolate_spd_vectorized(wavelengths, illuminant):
    """对指定光源的 SPD（5nm 表）做向量化线性插值，返回 [n, 1]。"""
    spd = np.asarray(ILLUMINANT_SPD[illuminant], dtype=float)
    spd_wl = spd[:, 0]
    spd_val = spd[:, 1]
    idx = np.searchsorted(spd_wl, wavelengths)
    idx_lo = np.clip(idx - 1, 0, len(spd_wl) - 2)
    idx_hi = np.clip(idx_lo + 1, 0, len(spd_wl) - 1)
    wl_lo = spd_wl[idx_lo]
    wl_hi = spd_wl[idx_hi]
    span = np.where(wl_hi == wl_lo, 1.0, wl_hi - wl_lo)
    ratio = (wavelengths - wl_lo) / span
    return (spd_val[idx_lo] + (spd_val[idx_hi] - spd_val[idx_lo]) * ratio)[:, None]


def _ratios_to_lab(ratios):
    """由 X/Xn、Y/Yn、Z/Zn 比值数组（[..., 3]）转 Lab，返回同形状。"""
    delta = 6 / 29
    threshold = delta ** 3

    def f(value):
        return np.where(
            value > threshold,
            np.cbrt(np.maximum(value, 0.0)),
            value / (3 * delta ** 2) + 4 / 29,
        )

    fx, fy, fz = f(ratios[..., 0]), f(ratios[..., 1]), f(ratios[..., 2])
    return np.stack([116 * fy - 16, 500 * (fx - fy), 200 * (fy - fz)], axis=-1)


def _xyz_to_lab_vectorized(xyz, white):
    """xyz: [N, 3]，white: [3]。返回 [N, 3] Lab，与标量 xyz_to_lab 对齐。"""
    return _ratios_to_lab(xyz / white[None, :])


def _delta_e_2000_vectorized(lab1, lab2):
    """lab1, lab2: [N, 3]。返回 [N] ΔE00，与标量 delta_e_2000 逐分支对齐。"""
    l1, a1, b1 = lab1[:, 0], lab1[:, 1], lab1[:, 2]
    l2, a2, b2 = lab2[:, 0], lab2[:, 1], lab2[:, 2]

    c1 = np.hypot(a1, b1)
    c2 = np.hypot(a2, b2)
    c_bar = (c1 + c2) / 2
    c_bar_7 = c_bar ** 7
    g = 0.5 * (1 - np.sqrt(c_bar_7 / (c_bar_7 + 25 ** 7)))

    a1p = (1 + g) * a1
    a2p = (1 + g) * a2
    c1p = np.hypot(a1p, b1)
    c2p = np.hypot(a2p, b2)

    h1p = np.degrees(np.arctan2(b1, a1p)) % 360
    h2p = np.degrees(np.arctan2(b2, a2p)) % 360
    h1p = np.where(c1p == 0, 0.0, h1p)
    h2p = np.where(c2p == 0, 0.0, h2p)

    delta_l = l2 - l1
    delta_c = c2p - c1p

    dh_raw = h2p - h1p
    dh = np.where(
        dh_raw > 180, dh_raw - 360, np.where(dh_raw < -180, dh_raw + 360, dh_raw)
    )
    delta_h_prime = np.where(c1p * c2p == 0, 0.0, dh)
    delta_h = 2 * np.sqrt(c1p * c2p) * np.sin(np.radians(delta_h_prime / 2))

    l_bar = (l1 + l2) / 2
    c_bar_p = (c1p + c2p) / 2

    cond_zero = c1p * c2p == 0
    cond_far = np.abs(h1p - h2p) > 180
    cond_far_lt = cond_far & (h1p + h2p < 360)
    cond_far_ge = cond_far & (h1p + h2p >= 360)
    h_bar_prime = np.where(
        cond_zero, h1p + h2p,
        np.where(
            cond_far_lt, (h1p + h2p + 360) / 2,
            np.where(cond_far_ge, (h1p + h2p - 360) / 2, (h1p + h2p) / 2),
        ),
    )

    t = (
        1
        - 0.17 * np.cos(np.radians(h_bar_prime - 30))
        + 0.24 * np.cos(np.radians(2 * h_bar_prime))
        + 0.32 * np.cos(np.radians(3 * h_bar_prime + 6))
        - 0.20 * np.cos(np.radians(4 * h_bar_prime - 63))
    )
    delta_theta = 30 * np.exp(-((h_bar_prime - 275) / 25) ** 2)
    c_bar_p_7 = c_bar_p ** 7
    r_c = 2 * np.sqrt(c_bar_p_7 / (c_bar_p_7 + 25 ** 7))
    s_l = 1 + (0.015 * (l_bar - 50) ** 2) / np.sqrt(20 + (l_bar - 50) ** 2)
    s_c = 1 + 0.045 * c_bar_p
    s_h = 1 + 0.015 * c_bar_p * t
    r_t = -np.sin(np.radians(2 * delta_theta)) * r_c

    l_term = delta_l / s_l
    c_term = delta_c / s_c
    h_term = delta_h / s_h
    return np.sqrt(l_term ** 2 + c_term ** 2 + h_term ** 2 + r_t * c_term * h_term)


def _drifted_labs(source_wl_np, curves_np, centers, fwhm_nm, illuminant):
    """给定通道中心波长，批量计算每条样品曲线在指定光源下的 Lab。

    centers 为 [n_channels]（返回 [n_curves, 3]）或 [m, n_channels]
    （返回 [m, n_curves, 3]）。每个通道以带宽(FWHM)高斯响应对完整反射光谱
    加权积分，再乘光源 SPD 与 CIE 配色函数积分成 XYZ，以完全漫反射体为参考白转 Lab。
    """
    sigma = fwhm_nm / (2 * math.sqrt(2 * math.log(2)))
    radius = sigma * 3

    if centers.ndim == 1:
        diff = source_wl_np[None, :] - centers[:, None]
        weight = np.exp(-0.5 * (diff / sigma) ** 2) * (np.abs(diff) <= radius)
        row_sum = weight.sum(axis=1, keepdims=True)
        weight = weight / np.where(row_sum == 0, 1.0, row_sum)
        refl = curves_np @ weight.T
        weighted_cie = _interpolate_cie_vectorized(centers) * _interpolate_spd_vectorized(centers, illuminant)
        xyz = refl @ weighted_cie
        white_totals = weighted_cie.sum(axis=0)
        return _xyz_to_lab_vectorized(xyz, white_totals)

    m, n_channels = centers.shape
    diff = source_wl_np[None, None, :] - centers[:, :, None]
    weight = np.exp(-0.5 * (diff / sigma) ** 2) * (np.abs(diff) <= radius)
    row_sum = weight.sum(axis=2, keepdims=True)
    weight = weight / np.where(row_sum == 0, 1.0, row_sum)
    refl = np.einsum("is,mcs->mic", curves_np, weight)
    cie = _interpolate_cie_vectorized(centers.reshape(-1)).reshape(m, n_channels, 3)
    spd = _interpolate_spd_vectorized(centers.reshape(-1), illuminant).reshape(m, n_channels, 1)
    weighted_cie = cie * spd
    xyz = np.einsum("mic,mck->mik", refl, weighted_cie)
    white_totals = weighted_cie.sum(axis=1)
    ratios = xyz / white_totals[:, None, :]
    return _ratios_to_lab(ratios)


def analyze_reflectance_mc_drift(
    csv_path,
    start_nm,
    end_nm,
    step_nm,
    drift_nm,
    illuminant,
    fwhm_nm,
    n_samples,
    seed=0,
    progress_callback=None,
):
    """蒙特卡洛整体 CWL 漂移敏感度分析（numpy 向量化）。

    每次随机给所有采样通道各抽一个独立 U[-drift_nm, +drift_nm] 漂移量，整体重算
    Lab 并对每个样品计算相对基准的 ΔE00；重复 n_samples 次。progress_callback
    (done, total) 可选，用于进度反馈。返回 (summary, sample_rows)，sample_rows
    按最大 ΔE00 降序。固定随机种子，相同输入结果完全可复现。
    """
    if illuminant not in ILLUMINANT_SPD:
        raise ValueError("Lab 白点必须是 D50、D65 或 A。")
    if fwhm_nm is None:
        raise ValueError("蒙特卡洛漂移分析需要 FWHM（带宽响应）。")
    if n_samples <= 0:
        raise ValueError("模拟次数必须大于 0。")

    reflectance_data = read_reflectance_csv(csv_path)
    source_wavelengths = reflectance_data["wavelengths"]
    sample_wavelengths = make_sampling_wavelengths(start_nm, end_nm, step_nm)
    sample_names = reflectance_data["sample_names"]
    sample_curves = reflectance_data["samples"]
    n_channels = len(sample_wavelengths)
    n_curves = len(sample_curves)

    source_wl_np = np.asarray(source_wavelengths, dtype=float)
    curves_np = np.asarray(sample_curves, dtype=float)
    sample_wl_np = np.asarray(sample_wavelengths, dtype=float)

    base_lab = _drifted_labs(source_wl_np, curves_np, sample_wl_np, fwhm_nm, illuminant)

    def _zero_result():
        rows = [
            {"sample": name, "mean": 0.0, "max": 0.0, "p95": 0.0}
            for name in sample_names
        ]
        summary = {
            "file_path": csv_path,
            "sample_count": n_curves,
            "channel_count": n_channels,
            "n_samples": n_samples,
            "seed": seed,
            "source_range": (source_wavelengths[0], source_wavelengths[-1]),
            "mean_delta_e": 0.0,
            "max_delta_e": 0.0,
            "p95_delta_e": 0.0,
            "p99_delta_e": 0.0,
            "worst_sample": rows[0]["sample"] if rows else "",
        }
        return summary, rows

    # drift=0：漂移后等于基准，ΔE00 恒为 0（满足零漂移测试 abs 1e-9）
    if drift_nm == 0:
        if progress_callback:
            progress_callback(n_samples, n_samples)
        return _zero_result()

    rng = np.random.default_rng(int(seed))
    drift = rng.uniform(-drift_nm, drift_nm, size=(n_samples, n_channels))
    centers_drifted = np.clip(
        sample_wl_np[None, :] + drift, SPECTRAL_MIN_NM, SPECTRAL_MAX_NM
    )

    chunk = 64
    per_sample_deltas = [[] for _ in range(n_curves)]
    all_deltas = []
    progress_step = max(1, n_samples // 100)

    for t0 in range(0, n_samples, chunk):
        t1 = min(n_samples, t0 + chunk)
        lab_blk = _drifted_labs(
            source_wl_np, curves_np, centers_drifted[t0:t1], fwhm_nm, illuminant
        )
        m = t1 - t0
        base_rep = np.broadcast_to(base_lab[None, :, :], (m, n_curves, 3))
        de_blk = _delta_e_2000_vectorized(
            base_rep.reshape(-1, 3), lab_blk.reshape(-1, 3)
        ).reshape(m, n_curves)

        all_deltas.append(de_blk.reshape(-1))
        for i in range(n_curves):
            per_sample_deltas[i].extend(de_blk[:, i].tolist())

        if progress_callback and (t1 % progress_step == 0 or t1 == n_samples):
            progress_callback(t1, n_samples)

    delta_list = np.concatenate(all_deltas).tolist()
    sample_rows = [
        {
            "sample": name,
            "mean": float(_mean(bucket)),
            "max": float(max(bucket)),
            "p95": float(_percentile(bucket, 0.95)),
        }
        for name, bucket in zip(sample_names, per_sample_deltas)
    ]
    sample_rows.sort(key=lambda item: item["max"], reverse=True)

    summary = {
        "file_path": csv_path,
        "sample_count": n_curves,
        "channel_count": n_channels,
        "n_samples": n_samples,
        "seed": seed,
        "source_range": (source_wavelengths[0], source_wavelengths[-1]),
        "mean_delta_e": float(_mean(delta_list)),
        "max_delta_e": float(max(delta_list)),
        "p95_delta_e": float(_percentile(delta_list, 0.95)),
        "p99_delta_e": float(_percentile(delta_list, 0.99)),
        "worst_sample": sample_rows[0]["sample"] if sample_rows else "",
    }
    return summary, sample_rows


def interpolate_cie_1931_2deg(wavelength):
    if wavelength < SPECTRAL_MIN_NM or wavelength > SPECTRAL_MAX_NM:
        raise ValueError("波长必须在 380-780 nm 范围内。")

    offset = wavelength - SPECTRAL_MIN_NM
    lower_index = int(offset // 5)
    upper_index = min(lower_index + 1, len(CIE_1931_2DEG_5NM) - 1)
    lower = CIE_1931_2DEG_5NM[lower_index]
    upper = CIE_1931_2DEG_5NM[upper_index]

    if lower[0] == upper[0]:
        return lower[1], lower[2], lower[3]

    ratio = (wavelength - lower[0]) / (upper[0] - lower[0])
    return (
        lower[1] + (upper[1] - lower[1]) * ratio,
        lower[2] + (upper[2] - lower[2]) * ratio,
        lower[3] + (upper[3] - lower[3]) * ratio,
    )


def xyz_to_lab(xyz, illuminant):
    white_x, white_y, white_z = WHITE_POINTS[illuminant]
    x, y, z = xyz

    def f(value):
        delta = 6 / 29
        if value > delta**3:
            return value ** (1 / 3)
        return value / (3 * delta**2) + 4 / 29

    fx = f(x / white_x)
    fy = f(y / white_y)
    fz = f(z / white_z)
    return 116 * fy - 16, 500 * (fx - fy), 200 * (fy - fz)


def delta_e_2000(lab1, lab2):
    l1, a1, b1 = lab1
    l2, a2, b2 = lab2

    c1 = math.hypot(a1, b1)
    c2 = math.hypot(a2, b2)
    c_bar = (c1 + c2) / 2
    c_bar_7 = c_bar**7
    g = 0.5 * (1 - math.sqrt(c_bar_7 / (c_bar_7 + 25**7)))

    a1_prime = (1 + g) * a1
    a2_prime = (1 + g) * a2
    c1_prime = math.hypot(a1_prime, b1)
    c2_prime = math.hypot(a2_prime, b2)

    h1_prime = math.degrees(math.atan2(b1, a1_prime)) % 360
    h2_prime = math.degrees(math.atan2(b2, a2_prime)) % 360
    if c1_prime == 0:
        h1_prime = 0
    if c2_prime == 0:
        h2_prime = 0

    delta_l_prime = l2 - l1
    delta_c_prime = c2_prime - c1_prime

    if c1_prime * c2_prime == 0:
        delta_h_prime = 0
    else:
        delta_h_prime = h2_prime - h1_prime
        if delta_h_prime > 180:
            delta_h_prime -= 360
        elif delta_h_prime < -180:
            delta_h_prime += 360

    delta_h = 2 * math.sqrt(c1_prime * c2_prime) * math.sin(
        math.radians(delta_h_prime / 2)
    )

    l_bar_prime = (l1 + l2) / 2
    c_bar_prime = (c1_prime + c2_prime) / 2

    if c1_prime * c2_prime == 0:
        h_bar_prime = h1_prime + h2_prime
    elif abs(h1_prime - h2_prime) > 180:
        if h1_prime + h2_prime < 360:
            h_bar_prime = (h1_prime + h2_prime + 360) / 2
        else:
            h_bar_prime = (h1_prime + h2_prime - 360) / 2
    else:
        h_bar_prime = (h1_prime + h2_prime) / 2

    t = (
        1
        - 0.17 * math.cos(math.radians(h_bar_prime - 30))
        + 0.24 * math.cos(math.radians(2 * h_bar_prime))
        + 0.32 * math.cos(math.radians(3 * h_bar_prime + 6))
        - 0.20 * math.cos(math.radians(4 * h_bar_prime - 63))
    )
    delta_theta = 30 * math.exp(-((h_bar_prime - 275) / 25) ** 2)
    c_bar_prime_7 = c_bar_prime**7
    r_c = 2 * math.sqrt(c_bar_prime_7 / (c_bar_prime_7 + 25**7))
    s_l = 1 + (0.015 * (l_bar_prime - 50) ** 2) / math.sqrt(
        20 + (l_bar_prime - 50) ** 2
    )
    s_c = 1 + 0.045 * c_bar_prime
    s_h = 1 + 0.015 * c_bar_prime * t
    r_t = -math.sin(math.radians(2 * delta_theta)) * r_c

    l_term = delta_l_prime / s_l
    c_term = delta_c_prime / s_c
    h_term = delta_h / s_h
    return math.sqrt(l_term**2 + c_term**2 + h_term**2 + r_t * c_term * h_term)
