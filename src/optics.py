# -*- coding: utf-8 -*-
"""物高 / 工作距离几何光学计算（纯函数）。"""

import math


def compute_object_height(
    target_length,
    target_width,
    half_fov_deg,
    entrance_pupil_diameter,
    focal_length,
):
    """根据目标尺寸与光学参数计算工作距离及衍射分辨能力。

    入参均为已解析的正浮点数。返回 {"rows": [(参数, 数值, 单位), ...],
    "details": [str, ...]}。业务校验失败时抛 ValueError。
    """
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

    return {"rows": rows, "details": details}
