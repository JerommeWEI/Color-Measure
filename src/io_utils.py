# -*- coding: utf-8 -*-
"""输入解析、反射率与 FWHM 标定 CSV 读取、插值与采样波长生成。"""

import bisect
import csv
import math
import os

from .constants import SPECTRAL_MIN_NM, SPECTRAL_MAX_NM


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
