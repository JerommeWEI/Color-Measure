#!/usr/bin/env python
# -*- coding: utf-8 -*-

import bisect
import csv
import math
import os
import tkinter as tk
import tkinter.font as tkfont
from tkinter import filedialog, ttk


def _detect_font():
    probe = tk.Tk()
    probe.withdraw()
    available = tkfont.families(probe)
    probe.destroy()
    for candidate in ("Segoe UI Variable", "Segoe UI", "Helvetica Neue"):
        if candidate in available:
            return candidate
    return "Microsoft YaHei"


_BODY_FONT = _detect_font()

THEME_COLORS = {
    "background": "#F8FAFC",
    "card": "#FFFFFF",
    "card_translucent": "#F1F5F9",
    "primary": "#1E3A5F",
    "primary_dark": "#152C4A",
    "primary_light": "#2563EB",
    "accent": "#059669",
    "accent_dark": "#047857",
    "text": "#0F172A",
    "text_secondary": "#64748B",
    "separator": "#E2E8F0",
    "border": "#E4E7EB",
    "fill": "#E2E8F0",
    "fill_light": "#F1F5F9",
    "danger": "#DC2626",
    "danger_dark": "#B91C1C",
    "button_secondary": "#E2E8F0",
    "button_secondary_text": "#334155",
    "focus_ring": "#2563EB",
}

THEME_FONTS = {
    "title": (_BODY_FONT, 16, "bold"),
    "section": (_BODY_FONT, 13, "bold"),
    "tab": (_BODY_FONT, 11),
    "body": (_BODY_FONT, 10),
    "button": (_BODY_FONT, 12, "bold"),
    "button_small": (_BODY_FONT, 10, "bold"),
    "label_bold": (_BODY_FONT, 10, "bold"),
    "accent_value": (_BODY_FONT, 11, "bold"),
    "mono": ("Consolas", 10),
}

SPECTRAL_MIN_NM = 380
SPECTRAL_MAX_NM = 780
DEFAULT_REFLECTANCE_CSV = (
    r"E:\OneDrive - UnispectralCN\01_研发\00_应用场景\15-LED检测"
    r"\A01-需求输入\20260415-色板测试\03-分析数据"
    r"\20260417-完整分析结果\A组_反射率数据.csv"
)
DEFAULT_FWHM_MAP_CSV = (
    r"E:\GIT_Space\spectral-calculation\test\tmp"
    r"\roi_signal_confidence_check_v2.csv"
)
FWHM_MODEL_NONE = "忽略 FWHM"
FWHM_MODEL_FIXED = "固定 FWHM"
FWHM_MODEL_MAP = "面阵标定表"
FWHM_FIELD_AVERAGE = "平均"
FWHM_FIELD_MAX = "最大"
FWHM_FIELD_MIN = "最小"
FWHM_FIELD_CENTER = "中心"
FWHM_FIELD_EDGE_AVERAGE = "边缘平均"
FWHM_FIELD_MANUAL = "手动坐标"
FWHM_MODELS = (FWHM_MODEL_NONE, FWHM_MODEL_FIXED, FWHM_MODEL_MAP)
FWHM_FIELD_OPTIONS = (
    FWHM_FIELD_AVERAGE,
    FWHM_FIELD_MAX,
    FWHM_FIELD_MIN,
    FWHM_FIELD_CENTER,
    FWHM_FIELD_EDGE_AVERAGE,
    FWHM_FIELD_MANUAL,
)

CIE_1931_2DEG_5NM = (
    (380, 0.001368, 0.000039, 0.006450),
    (385, 0.002236, 0.000064, 0.010550),
    (390, 0.004243, 0.000120, 0.020050),
    (395, 0.007650, 0.000217, 0.036210),
    (400, 0.014310, 0.000396, 0.067850),
    (405, 0.023190, 0.000640, 0.110200),
    (410, 0.043510, 0.001210, 0.207400),
    (415, 0.077630, 0.002180, 0.371300),
    (420, 0.134380, 0.004000, 0.645600),
    (425, 0.214770, 0.007300, 1.039050),
    (430, 0.283900, 0.011600, 1.385600),
    (435, 0.328500, 0.016840, 1.622960),
    (440, 0.348280, 0.023000, 1.747060),
    (445, 0.348060, 0.029800, 1.782600),
    (450, 0.336200, 0.038000, 1.772110),
    (455, 0.318700, 0.048000, 1.744100),
    (460, 0.290800, 0.060000, 1.669200),
    (465, 0.251100, 0.073900, 1.528100),
    (470, 0.195360, 0.090980, 1.287640),
    (475, 0.142100, 0.112600, 1.041900),
    (480, 0.095640, 0.139020, 0.812950),
    (485, 0.057950, 0.169300, 0.616200),
    (490, 0.032010, 0.208020, 0.465180),
    (495, 0.014700, 0.258600, 0.353300),
    (500, 0.004900, 0.323000, 0.272000),
    (505, 0.002400, 0.407300, 0.212300),
    (510, 0.009300, 0.503000, 0.158200),
    (515, 0.029100, 0.608200, 0.111700),
    (520, 0.063270, 0.710000, 0.078250),
    (525, 0.109600, 0.793200, 0.057250),
    (530, 0.165500, 0.862000, 0.042160),
    (535, 0.225750, 0.914850, 0.029840),
    (540, 0.290400, 0.954000, 0.020300),
    (545, 0.359700, 0.980300, 0.013400),
    (550, 0.433450, 0.994950, 0.008750),
    (555, 0.512050, 1.000000, 0.005750),
    (560, 0.594500, 0.995000, 0.003900),
    (565, 0.678400, 0.978600, 0.002750),
    (570, 0.762100, 0.952000, 0.002100),
    (575, 0.842500, 0.915400, 0.001800),
    (580, 0.916300, 0.870000, 0.001650),
    (585, 0.978600, 0.816300, 0.001400),
    (590, 1.026300, 0.757000, 0.001100),
    (595, 1.056700, 0.694900, 0.001000),
    (600, 1.062200, 0.631000, 0.000800),
    (605, 1.045600, 0.566800, 0.000600),
    (610, 1.002600, 0.503000, 0.000340),
    (615, 0.938400, 0.441200, 0.000240),
    (620, 0.854450, 0.381000, 0.000190),
    (625, 0.751400, 0.321000, 0.000100),
    (630, 0.642400, 0.265000, 0.000050),
    (635, 0.541900, 0.217000, 0.000030),
    (640, 0.447900, 0.175000, 0.000020),
    (645, 0.360800, 0.138200, 0.000010),
    (650, 0.283500, 0.107000, 0.000000),
    (655, 0.218700, 0.081600, 0.000000),
    (660, 0.164900, 0.061000, 0.000000),
    (665, 0.121200, 0.044580, 0.000000),
    (670, 0.087400, 0.032000, 0.000000),
    (675, 0.063600, 0.023200, 0.000000),
    (680, 0.046770, 0.017000, 0.000000),
    (685, 0.032900, 0.011920, 0.000000),
    (690, 0.022700, 0.008210, 0.000000),
    (695, 0.015840, 0.005723, 0.000000),
    (700, 0.011359, 0.004102, 0.000000),
    (705, 0.008111, 0.002929, 0.000000),
    (710, 0.005790, 0.002091, 0.000000),
    (715, 0.004109, 0.001484, 0.000000),
    (720, 0.002899, 0.001047, 0.000000),
    (725, 0.002049, 0.000740, 0.000000),
    (730, 0.001440, 0.000520, 0.000000),
    (735, 0.001000, 0.000361, 0.000000),
    (740, 0.000690, 0.000249, 0.000000),
    (745, 0.000476, 0.000172, 0.000000),
    (750, 0.000332, 0.000120, 0.000000),
    (755, 0.000235, 0.000085, 0.000000),
    (760, 0.000166, 0.000060, 0.000000),
    (765, 0.000117, 0.000042, 0.000000),
    (770, 0.000083, 0.000030, 0.000000),
    (775, 0.000059, 0.000021, 0.000000),
    (780, 0.000042, 0.000015, 0.000000),
)

WHITE_POINTS = {
    "D50": (96.42, 100.0, 82.51),
    "D65": (95.05, 100.0, 108.88),
    "A": (109.85, 100.0, 35.58),
}


def parse_positive_float(value, field_name):
    try:
        number = float(value)
    except ValueError as exc:
        raise ValueError(f"{field_name} 必须是数字。") from exc

    if number <= 0:
        raise ValueError(f"{field_name} 必须大于 0。")

    return number


def parse_float(value, field_name):
    try:
        return float(value)
    except ValueError as exc:
        raise ValueError(f"{field_name} 必须是数字。") from exc


def read_reflectance_csv(file_path):
    if not os.path.exists(file_path):
        raise ValueError(f"反射率 CSV 文件不存在：{file_path}")

    with open(file_path, "r", encoding="utf-8-sig", newline="") as file:
        reader = csv.reader(file)
        try:
            header = next(reader)
        except StopIteration as exc:
            raise ValueError("反射率 CSV 文件为空。") from exc

        if len(header) < 2:
            raise ValueError("反射率 CSV 至少需要 1 列波长和 1 列反射率。")

        sample_names = [name.strip() or f"样品{index}" for index, name in enumerate(header[1:], 1)]
        wavelengths = []
        sample_values = [[] for _ in sample_names]

        for row_index, row in enumerate(reader, 2):
            if not row or not row[0].strip():
                continue

            try:
                wavelength = float(row[0])
            except ValueError as exc:
                raise ValueError(f"第 {row_index} 行波长不是数字。") from exc

            values = []
            for col_index in range(len(sample_names)):
                cell = row[col_index + 1].strip() if col_index + 1 < len(row) else ""
                try:
                    values.append(float(cell))
                except ValueError as exc:
                    raise ValueError(
                        f"第 {row_index} 行第 {col_index + 2} 列反射率不是数字。"
                    ) from exc

            wavelengths.append(wavelength)
            for col_index, value in enumerate(values):
                sample_values[col_index].append(value)

    if len(wavelengths) < 2:
        raise ValueError("反射率 CSV 至少需要两个波长点。")

    ordered = sorted(zip(wavelengths, *sample_values), key=lambda item: item[0])
    wavelengths = [item[0] for item in ordered]
    sorted_sample_values = []
    for sample_index in range(len(sample_names)):
        sorted_sample_values.append([item[sample_index + 1] for item in ordered])

    return {
        "sample_names": sample_names,
        "wavelengths": wavelengths,
        "samples": sorted_sample_values,
    }


def linear_interpolate(x_values, y_values, target_x):
    if target_x < x_values[0] or target_x > x_values[-1]:
        raise ValueError(
            f"目标波长 {target_x:g} nm 超出反射率数据范围 "
            f"{x_values[0]:g}-{x_values[-1]:g} nm。"
        )

    index = bisect.bisect_left(x_values, target_x)
    if index < len(x_values) and x_values[index] == target_x:
        return y_values[index]
    if index == 0:
        return y_values[0]
    if index >= len(x_values):
        return y_values[-1]

    x0 = x_values[index - 1]
    x1 = x_values[index]
    y0 = y_values[index - 1]
    y1 = y_values[index]
    return y0 + (y1 - y0) * (target_x - x0) / (x1 - x0)


def make_sampling_wavelengths(start_nm, end_nm, step_nm):
    if start_nm < SPECTRAL_MIN_NM or end_nm > SPECTRAL_MAX_NM:
        raise ValueError("采样波长范围必须在 380-780 nm 内。")
    if start_nm >= end_nm:
        raise ValueError("起始波长必须小于结束波长。")
    if step_nm <= 0:
        raise ValueError("采样间隔必须大于 0。")

    wavelengths = []
    current = start_nm
    tolerance = step_nm * 1e-9
    while current <= end_nm + tolerance:
        wavelengths.append(round(current, 10))
        current += step_nm
    return wavelengths


def read_fwhm_map_csv(file_path):
    if not os.path.exists(file_path):
        raise ValueError(f"FWHM 标定 CSV 文件不存在：{file_path}")

    required_fields = {
        "roi_id",
        "roi_x",
        "roi_y",
        "roi_width",
        "roi_height",
        "fwhm_nm",
    }
    points_by_roi = {}
    skipped_status_roi_ids = set()

    with open(file_path, "r", encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)
        if not reader.fieldnames:
            raise ValueError("FWHM 标定 CSV 文件为空。")

        missing_fields = sorted(required_fields - set(reader.fieldnames))
        if missing_fields:
            missing_text = "、".join(missing_fields)
            raise ValueError(f"FWHM 标定 CSV 缺少字段：{missing_text}。")

        for row_index, row in enumerate(reader, 2):
            roi_id = (row.get("roi_id") or "").strip() or f"row_{row_index}"
            if roi_id in points_by_roi:
                continue

            metric_status = (row.get("metric_status") or "ok").strip()
            if metric_status and metric_status != "ok":
                skipped_status_roi_ids.add(roi_id)
                continue

            try:
                x = float((row.get("roi_x") or "").strip())
                y = float((row.get("roi_y") or "").strip())
                width = float((row.get("roi_width") or "").strip())
                height = float((row.get("roi_height") or "").strip())
                fwhm_nm = float((row.get("fwhm_nm") or "").strip())
            except ValueError as exc:
                raise ValueError(f"FWHM 标定 CSV 第 {row_index} 行包含非数字字段。") from exc

            values = (x, y, width, height, fwhm_nm)
            if not all(math.isfinite(value) for value in values):
                continue
            if width <= 0 or height <= 0 or fwhm_nm <= 0:
                continue

            points_by_roi[roi_id] = {
                "roi_id": roi_id,
                "x": x,
                "y": y,
                "width": width,
                "height": height,
                "center_x": x + width / 2,
                "center_y": y + height / 2,
                "fwhm_nm": fwhm_nm,
            }

    points = list(points_by_roi.values())
    if not points:
        raise ValueError("FWHM 标定 CSV 没有 metric_status=ok 的有效 ROI。")

    fwhm_values = [point["fwhm_nm"] for point in points]
    center_x_values = [point["center_x"] for point in points]
    center_y_values = [point["center_y"] for point in points]
    return {
        "points": points,
        "count": len(points),
        "skipped_status_count": len(skipped_status_roi_ids),
        "fwhm_min": min(fwhm_values),
        "fwhm_max": max(fwhm_values),
        "fwhm_mean": sum(fwhm_values) / len(fwhm_values),
        "center_x_min": min(center_x_values),
        "center_x_max": max(center_x_values),
        "center_y_min": min(center_y_values),
        "center_y_max": max(center_y_values),
    }


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
        reflectance = linear_interpolate(
            source_wavelengths, reflectance_values, wavelength
        )
        weighted_total += reflectance * weight
        weight_total += weight
        wavelength += integration_step

    if weight_total == 0:
        return linear_interpolate(
            source_wavelengths, reflectance_values, center_wavelength
        )
    return weighted_total / weight_total


def sampled_reflectance_to_lab(sample_wavelengths, reflectance_values, illuminant):
    x_total = 0.0
    y_total = 0.0
    z_total = 0.0
    white_x_total = 0.0
    white_y_total = 0.0
    white_z_total = 0.0
    for wavelength, reflectance in zip(sample_wavelengths, reflectance_values):
        x_bar, y_bar, z_bar = interpolate_cie_1931_2deg(wavelength)
        x_total += reflectance * x_bar
        y_total += reflectance * y_bar
        z_total += reflectance * z_bar
        white_x_total += x_bar
        white_y_total += y_bar
        white_z_total += z_bar

    white_x, white_y, white_z = WHITE_POINTS[illuminant]
    xyz = (
        x_total / white_x_total * white_x,
        y_total / white_y_total * white_y,
        z_total / white_z_total * white_z,
    )
    return xyz_to_lab(xyz, illuminant)


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
    if illuminant not in WHITE_POINTS:
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


def analyze_reflectance_channel_drift(
    csv_path,
    start_nm,
    end_nm,
    step_nm,
    drift_nm,
    illuminant,
    fwhm_nm=None,
):
    if illuminant not in WHITE_POINTS:
        raise ValueError("Lab 白点必须是 D50、D65 或 A。")

    reflectance_data = read_reflectance_csv(csv_path)
    source_wavelengths = reflectance_data["wavelengths"]

    sample_wavelengths = make_sampling_wavelengths(start_nm, end_nm, step_nm)
    rows = []
    global_values = []

    for channel_index, channel_wavelength in enumerate(sample_wavelengths):
        plus_values = []
        minus_values = []
        worst_sample = ""
        worst_delta_e = -1.0

        for sample_name, sample_curve in zip(
            reflectance_data["sample_names"], reflectance_data["samples"]
        ):
            base_reflectance = [
                sample_channel_reflectance(
                    source_wavelengths, sample_curve, wavelength, fwhm_nm
                )
                for wavelength in sample_wavelengths
            ]
            base_lab = sampled_reflectance_to_lab(
                sample_wavelengths, base_reflectance, illuminant
            )

            sample_deltas = []
            plus_wavelength = channel_wavelength + drift_nm
            if plus_wavelength <= source_wavelengths[-1]:
                plus_wavelengths = list(sample_wavelengths)
                plus_wavelengths[channel_index] = plus_wavelength
                plus_reflectance = list(base_reflectance)
                plus_reflectance[channel_index] = sample_channel_reflectance(
                    source_wavelengths, sample_curve, plus_wavelength, fwhm_nm
                )
                plus_lab = sampled_reflectance_to_lab(
                    plus_wavelengths, plus_reflectance, illuminant
                )
                plus_delta_e = delta_e_2000(base_lab, plus_lab)
                plus_values.append(plus_delta_e)
                sample_deltas.append(plus_delta_e)

            minus_wavelength = channel_wavelength - drift_nm
            if minus_wavelength >= source_wavelengths[0]:
                minus_wavelengths = list(sample_wavelengths)
                minus_wavelengths[channel_index] = minus_wavelength
                minus_reflectance = list(base_reflectance)
                minus_reflectance[channel_index] = sample_channel_reflectance(
                    source_wavelengths, sample_curve, minus_wavelength, fwhm_nm
                )
                minus_lab = sampled_reflectance_to_lab(
                    minus_wavelengths, minus_reflectance, illuminant
                )
                minus_delta_e = delta_e_2000(base_lab, minus_lab)
                minus_values.append(minus_delta_e)
                sample_deltas.append(minus_delta_e)

            if not sample_deltas:
                continue

            sample_max = max(sample_deltas)
            if sample_max > worst_delta_e:
                worst_delta_e = sample_max
                worst_sample = sample_name

        combined = plus_values + minus_values
        if not combined:
            continue
        global_values.extend(combined)
        rows.append(
            {
                "wavelength": channel_wavelength,
                "mean": sum(combined) / len(combined),
                "max": max(combined),
                "worst_sample": worst_sample,
            }
        )

    rows.sort(key=lambda item: item["max"], reverse=True)
    summary = {
        "file_path": csv_path,
        "sample_count": len(reflectance_data["sample_names"]),
        "channel_count": len(sample_wavelengths),
        "source_range": (source_wavelengths[0], source_wavelengths[-1]),
        "mean_delta_e": sum(global_values) / len(global_values),
        "max_delta_e": max(global_values),
        "worst_channel": rows[0]["wavelength"],
        "worst_sample": rows[0]["worst_sample"],
    }
    return summary, rows


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


class OpticalParameterCalculator(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("光学参数计算工具 v1.1")
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
        self.fwhm_model_var = tk.StringVar(value=FWHM_MODEL_NONE)
        self.fixed_fwhm_var = tk.StringVar(value="15")
        self.fwhm_map_csv_var = tk.StringVar(value=DEFAULT_FWHM_MAP_CSV)
        self.fwhm_field_var = tk.StringVar(value=FWHM_FIELD_AVERAGE)
        self.fwhm_manual_x_var = tk.StringVar(value="")
        self.fwhm_manual_y_var = tk.StringVar(value="")

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

    def _build_colorimetry_formula_panel(self, parent):
        formula_group = ttk.LabelFrame(
            parent, text="计算基准", padding=12, style="Card.TLabelframe"
        )
        formula_group.pack(fill=tk.X, pady=(14, 0))

        rows = [
            ("基准采样", "380-780 nm，默认 10 nm"),
            ("漂移模型", "单通道 ±漂移，其它通道不变"),
            ("FWHM", "可选高斯响应加权反射率"),
            ("色差", "实测反射率 -> Lab -> ΔE00"),
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

    def _build_colorimetry_output_panel(self, parent):
        result_group = ttk.LabelFrame(
            parent, text="输出数据", padding=10, style="Card.TLabelframe"
        )
        result_group.pack(fill=tk.BOTH, expand=True)
        result_group.rowconfigure(0, weight=1)
        result_group.columnconfigure(0, weight=1)

        columns = ("wavelength", "mean", "max", "sample")
        self.colorimetry_result_table = ttk.Treeview(
            result_group, columns=columns, show="headings", height=10
        )
        self.colorimetry_result_table.heading("wavelength", text="通道 nm")
        self.colorimetry_result_table.heading("mean", text="平均 ΔE00")
        self.colorimetry_result_table.heading("max", text="最大 ΔE00")
        self.colorimetry_result_table.heading("sample", text="最差样品")
        self.colorimetry_result_table.column(
            "wavelength", width=110, minwidth=90, anchor=tk.E
        )
        self.colorimetry_result_table.column(
            "mean", width=140, minwidth=110, anchor=tk.E
        )
        self.colorimetry_result_table.column("max", width=140, minwidth=110, anchor=tk.E)
        self.colorimetry_result_table.column("sample", width=160, minwidth=120, anchor=tk.W)
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
            entrance_pupil_diameter = parse_positive_float(
                self.entrance_pupil_diameter_var.get().strip(), "入瞳直径"
            )
            focal_length = parse_positive_float(
                self.focal_length_var.get().strip(), "焦距"
            )

            half_fov_text = self.half_fov_var.get().strip()
            half_fov_deg = parse_positive_float(half_fov_text, "FOV 半视场角")
            if half_fov_deg >= 90:
                raise ValueError("FOV 半视场角必须小于 90 deg。")

            diagonal = math.hypot(target_length, target_width)
            diagonal_half_height = diagonal / 2
            working_distance = diagonal_half_height / math.tan(math.radians(half_fov_deg))
            detectable_half_cone_deg = math.degrees(
                math.atan((entrance_pupil_diameter / 2) / working_distance)
            )
            detectable_full_cone_deg = detectable_half_cone_deg * 2
            observation_aperture_2deg = 2 * working_distance * math.tan(math.radians(1))
            f_number = focal_length / entrance_pupil_diameter
            rayleigh_image_limit_mm = 1.22 * 0.00055 * f_number
            magnification = focal_length / (working_distance - focal_length)
            if magnification <= 0:
                raise ValueError("工作距离必须大于焦距，才能按薄透镜模型计算物面DPI。")
            rayleigh_object_limit_mm = rayleigh_image_limit_mm / magnification
            diffraction_limited_dpi = 25.4 / rayleigh_object_limit_mm
            resolvable_points_x = target_length / rayleigh_object_limit_mm
            resolvable_points_y = target_width / rayleigh_object_limit_mm

            rows = [
                ("目标对角线", diagonal, "mm"),
                ("对角线半高", diagonal_half_height, "mm"),
                ("工作距离", working_distance, "mm"),
                ("2°观察角观测口径", observation_aperture_2deg, "mm"),
                ("中心物点可探测半锥角", detectable_half_cone_deg, "deg"),
                ("中心物点可探测全锥角", detectable_full_cone_deg, "deg"),
                ("F/#", f_number, ""),
                ("像面Rayleigh极限", rayleigh_image_limit_mm * 1000, "um"),
                ("物面Rayleigh极限", rayleigh_object_limit_mm * 1000, "um"),
                ("衍射极限等效DPI", diffraction_limited_dpi, "DPI"),
                ("目标长度方向可分辨点数", resolvable_points_x, "px"),
                ("目标宽度方向可分辨点数", resolvable_points_y, "px"),
            ]
            details = [
                "=" * 60,
                "工作距离计算结果",
                "=" * 60,
                "",
                "配置参数:",
                f"  目标长度: {target_length:g} mm",
                f"  目标宽度: {target_width:g} mm",
                f"  FOV 半视场角: {half_fov_deg:g} deg",
                f"  入瞳直径: {entrance_pupil_diameter:g} mm",
                f"  焦距: {focal_length:g} mm",
                "",
                "计算结果:",
                f"  目标对角线 = {diagonal:.6g} mm",
                f"  对角线半高 = {diagonal_half_height:.6g} mm",
                f"  工作距离 = {working_distance:.6g} mm",
                f"  2°观察角观测口径 = {observation_aperture_2deg:.6g} mm",
                f"  中心物点可探测半锥角 = {detectable_half_cone_deg:.6g} deg",
                f"  中心物点可探测全锥角 = {detectable_full_cone_deg:.6g} deg",
                f"  F/# = {f_number:.6g}",
                f"  像面Rayleigh极限 = {rayleigh_image_limit_mm * 1000:.6g} um",
                f"  薄透镜放大率 = {magnification:.6g}",
                f"  物面Rayleigh极限 = {rayleigh_object_limit_mm * 1000:.6g} um",
                f"  衍射极限等效DPI = {diffraction_limited_dpi:.6g} DPI",
                f"  目标长度方向可分辨点数 = {resolvable_points_x:.6g}",
                f"  目标宽度方向可分辨点数 = {resolvable_points_y:.6g}",
            ]

            details.extend(
                [
                    "",
                    "计算基准:",
                    "  对角线半高 = sqrt(目标长度^2 + 目标宽度^2) / 2",
                    "  工作距离 = 对角线半高 / tan(FOV 半视场角)",
                    "  2°观察角观测口径 = 2 * 工作距离 * tan(1°)",
                    "  中心物点可探测半锥角 = atan((入瞳直径/2) / 工作距离)",
                    "  中心物点可探测全锥角 = 2 * 半锥角",
                    "  F/# = 焦距 / 入瞳直径",
                    "  像面Rayleigh极限 = 1.22 * 0.55um * F/#",
                    "  薄透镜放大率 = 焦距 / (工作距离 - 焦距)",
                    "  物面Rayleigh极限 = 像面Rayleigh极限 / 放大率",
                    "  衍射极限等效DPI = 25.4 / 物面Rayleigh极限(mm)",
                    "  目标长宽与输出工作距离使用同一长度单位。",
                ]
            )

            self._set_result_rows(rows)
            self._set_detail_text("\n".join(details))
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
            illuminant = self.illuminant_var.get().strip()
            fwhm_config = build_fwhm_config(
                self.fwhm_model_var.get().strip(),
                self.fixed_fwhm_var.get(),
                self.fwhm_map_csv_var.get(),
                self.fwhm_field_var.get().strip(),
                self.fwhm_manual_x_var.get(),
                self.fwhm_manual_y_var.get(),
            )

            summary, rows = analyze_reflectance_channel_drift(
                csv_path,
                start_nm,
                end_nm,
                step_nm,
                drift_nm,
                illuminant,
                fwhm_config["fwhm_nm"],
            )
            fwhm_field_summary = None
            fwhm_field_rows = []
            if fwhm_config.get("fwhm_map"):
                fwhm_field_summary, fwhm_field_rows = analyze_fwhm_field_delta_e(
                    csv_path,
                    start_nm,
                    end_nm,
                    step_nm,
                    illuminant,
                    fwhm_config["fwhm_map"],
                )

            details = [
                "=" * 60,
                "光谱相机通道漂移与 ΔE00 敏感度",
                "=" * 60,
                "",
                "配置参数:",
                f"  反射率 CSV: {csv_path}",
                f"  采样范围: {start_nm:g}-{end_nm:g} nm",
                f"  采样间隔: {step_nm:g} nm",
                f"  单通道漂移: ±{drift_nm:g} nm",
                f"  Lab 白点: {illuminant}",
            "",
                *fwhm_config["detail_lines"],
                "",
                "数据概况:",
                f"  反射率数据范围: {summary['source_range'][0]:g}-{summary['source_range'][1]:g} nm",
                f"  样品数量: {summary['sample_count']}",
                f"  通道数量: {summary['channel_count']}",
                "",
                "计算结果:",
                f"  全局平均 ΔE00 = {summary['mean_delta_e']:.6g}",
                f"  全局最大 ΔE00 = {summary['max_delta_e']:.6g}",
                f"  最敏感通道 = {summary['worst_channel']:.6g} nm",
                f"  最差样品 = {summary['worst_sample']}",
                "",
                "计算基准:",
                "  忽略 FWHM 时，基准为标称采样通道对应的实测反射率插值值。",
                "  启用 FWHM 时，每个通道使用高斯光谱响应对反射率加权采样。",
                "  每次只漂移一个通道，其他通道保持标称波长。",
                "  对所有样品分别计算 +漂移和 -漂移，再统计每个通道的平均和最大 ΔE00。",
                "  当前为自包含计算：CIE 1931 2° 配色函数 + 指定白点。",
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

            self._set_channel_drift_rows(rows)
            self._set_colorimetry_detail_text("\n".join(details))
            self.colorimetry_status_var.set("计算完成")
        except ValueError as exc:
            self._set_channel_drift_rows(
                [{"wavelength": "输入错误", "mean": str(exc), "max": "", "worst_sample": ""}]
            )
            self._set_colorimetry_detail_text(f"输入错误：{exc}")
            self.colorimetry_status_var.set("参数错误")

    def clear_colorimetry_inputs(self):
        self.reflectance_csv_var.set(DEFAULT_REFLECTANCE_CSV)
        self.sampling_start_var.set("380")
        self.sampling_end_var.set("780")
        self.sampling_step_var.set("10")
        self.wavelength_drift_var.set("1")
        self.illuminant_var.set("D50")
        self.fwhm_model_var.set(FWHM_MODEL_NONE)
        self.fixed_fwhm_var.set("15")
        self.fwhm_map_csv_var.set(DEFAULT_FWHM_MAP_CSV)
        self.fwhm_field_var.set(FWHM_FIELD_AVERAGE)
        self.fwhm_manual_x_var.set("")
        self.fwhm_manual_y_var.set("")
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
        self._set_channel_drift_rows(
            [{"wavelength": "等待计算", "mean": "请输入左侧参数", "max": "", "worst_sample": ""}]
        )
        self._set_colorimetry_detail_text(
            "请选择反射率 CSV，设置采样、漂移量和可选 FWHM 模型后点击计算。"
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

    def _set_channel_drift_rows(self, rows):
        for item in self.colorimetry_result_table.get_children():
            self.colorimetry_result_table.delete(item)

        for row in rows:
            wavelength = row["wavelength"]
            mean_value = row["mean"]
            max_value = row["max"]
            if isinstance(wavelength, float):
                wavelength = f"{wavelength:.6g}"
            if isinstance(mean_value, float):
                mean_value = f"{mean_value:.6g}"
            if isinstance(max_value, float):
                max_value = f"{max_value:.6g}"
            self.colorimetry_result_table.insert(
                "",
                tk.END,
                values=(wavelength, mean_value, max_value, row["worst_sample"]),
            )

    def _set_colorimetry_detail_text(self, text):
        self.colorimetry_detail_text.configure(state=tk.NORMAL)
        self.colorimetry_detail_text.delete("1.0", tk.END)
        self.colorimetry_detail_text.insert(tk.END, text)
        self.colorimetry_detail_text.configure(state=tk.DISABLED)


if __name__ == "__main__":
    app = OpticalParameterCalculator()
    app.mainloop()
