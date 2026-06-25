# -*- coding: utf-8 -*-
"""io_utils 输入解析、插值、采样波长与 CSV 读取测试。"""

import pytest

from src.io_utils import (
    parse_positive_float,
    parse_float,
    linear_interpolate,
    make_sampling_wavelengths,
    read_reflectance_csv,
    read_fwhm_map_csv,
)


def test_parse_positive_float_ok():
    assert parse_positive_float("3.5", "x") == 3.5


def test_parse_positive_float_rejects_non_number_and_non_positive():
    with pytest.raises(ValueError):
        parse_positive_float("abc", "x")
    with pytest.raises(ValueError):
        parse_positive_float("0", "x")
    with pytest.raises(ValueError):
        parse_positive_float("-1", "x")


def test_parse_float_allows_any_real():
    assert parse_float("-2.5", "x") == -2.5
    assert parse_float("0", "x") == 0.0
    with pytest.raises(ValueError):
        parse_float("na", "x")


def test_linear_interpolate_endpoints_and_mid():
    xs = [380.0, 390.0, 400.0]
    ys = [0.0, 10.0, 30.0]
    assert linear_interpolate(xs, ys, 380.0) == 0.0
    assert linear_interpolate(xs, ys, 400.0) == 30.0
    assert linear_interpolate(xs, ys, 390.0) == 10.0
    assert linear_interpolate(xs, ys, 385.0) == 5.0


def test_linear_interpolate_out_of_range_raises():
    with pytest.raises(ValueError):
        linear_interpolate([380.0, 400.0], [0.0, 1.0], 379.0)
    with pytest.raises(ValueError):
        linear_interpolate([380.0, 400.0], [0.0, 1.0], 401.0)


def test_make_sampling_wavelengths_basic():
    assert make_sampling_wavelengths(380.0, 400.0, 10.0) == [380.0, 390.0, 400.0]


def test_make_sampling_wavelengths_validates_bounds():
    with pytest.raises(ValueError):
        make_sampling_wavelengths(370.0, 780.0, 10.0)
    with pytest.raises(ValueError):
        make_sampling_wavelengths(380.0, 790.0, 10.0)
    with pytest.raises(ValueError):
        make_sampling_wavelengths(500.0, 500.0, 10.0)
    with pytest.raises(ValueError):
        make_sampling_wavelengths(380.0, 500.0, 0.0)


def test_read_reflectance_csv_parses_columns(tmp_path):
    path = tmp_path / "refl.csv"
    path.write_text(
        "wavelength,sampleA,sampleB\n380,0.1,0.2\n390,0.3,0.4\n400,0.5,0.6\n",
        encoding="utf-8",
    )
    data = read_reflectance_csv(str(path))
    assert data["sample_names"] == ["sampleA", "sampleB"]
    assert data["wavelengths"] == [380.0, 390.0, 400.0]
    assert data["samples"][0] == [0.1, 0.3, 0.5]
    assert data["samples"][1] == [0.2, 0.4, 0.6]


def test_read_reflectance_csv_errors(tmp_path):
    with pytest.raises(ValueError):
        read_reflectance_csv(str(tmp_path / "missing.csv"))
    empty = tmp_path / "empty.csv"
    empty.write_text("", encoding="utf-8")
    with pytest.raises(ValueError):
        read_reflectance_csv(str(empty))


def test_read_fwhm_map_csv_filters_non_ok_and_computes_stats(tmp_path):
    # center = roi_x + roi_width/2 ; r1->(5,5) r3->(25,25)，r2 为 bad 被过滤
    path = tmp_path / "fwhm.csv"
    path.write_text(
        "roi_id,roi_x,roi_y,roi_width,roi_height,fwhm_nm,metric_status\n"
        "r1,0,0,10,10,15.0,ok\n"
        "r2,40,0,10,10,99.0,bad\n"
        "r3,20,20,10,10,17.0,ok\n",
        encoding="utf-8",
    )
    m = read_fwhm_map_csv(str(path))
    assert m["count"] == 2
    assert m["skipped_status_count"] == 1
    assert m["fwhm_min"] == 15.0
    assert m["fwhm_max"] == 17.0
    assert m["fwhm_mean"] == 16.0
    assert m["center_x_min"] == 5.0
    assert m["center_x_max"] == 25.0
    assert {p["roi_id"] for p in m["points"]} == {"r1", "r3"}


def test_read_fwhm_map_csv_no_valid_roi_raises(tmp_path):
    path = tmp_path / "fwhm.csv"
    path.write_text(
        "roi_id,roi_x,roi_y,roi_width,roi_height,fwhm_nm,metric_status\n"
        "r1,0,0,10,10,15.0,bad\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError):
        read_fwhm_map_csv(str(path))
