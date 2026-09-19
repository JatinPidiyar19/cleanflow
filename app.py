"""
CleanFlow — Universal Data Cleaner
A Streamlit application that turns messy CSV / XLSX / JSON / PDF data
into clean, validated, review-ready datasets.

Run with:
    streamlit run app.py
"""

import os
import io
import tempfile
import traceback
from datetime import datetime

import pandas as pd
import streamlit as st

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer

from file_loader import load_file
from cleaner import (
    remove_duplicates,
    standardize_text,
    clean_dates,
    analyze_numeric_columns,
    clean_invalid_values,
)
from data_analyzer import (
    is_date_like,
    is_categorical,
    detect_column_type,
    analyze_data,
)
from validator import (
    validate_data,
    check_missing_values,
    create_review_report,
    validate_revenue,
)

# --------------------------------------------------------------------------
# PAGE CONFIG
# --------------------------------------------------------------------------

st.set_page_config(
    page_title="CleanFlow — Universal Data Cleaner",
    page_icon="🧬",
    layout="wide",
    initial_sidebar_state="collapsed",
)

SUPPORTED_EXTENSIONS = [".csv", ".xlsx", ".json", ".pdf"]
SALES_COLUMNS = ["Quantity", "Unit_Price", "Discount", "Revenue"]
PREVIEW_ROW_LIMIT = 50


# --------------------------------------------------------------------------
# STYLE
# --------------------------------------------------------------------------

def inject_global_styles():
    """Inject the CleanFlow visual identity once, via st.html (never
    st.markdown with unsafe_allow_html)."""
    st.html("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Sora:wght@400;500;600;700;800&family=Inter:wght@400;500;600;700&display=swap');

    :root {
        --bg-0: #0A0F1C;
        --bg-1: #10182B;
        --surface: rgba(255,255,255,0.045);
        --surface-border: rgba(255,255,255,0.09);
        --accent: #2DD4BF;
        --accent-soft: rgba(45,212,191,0.14);
        --accent-2: #818CF8;
        --text-hi: #EEF2F9;
        --text-mid: #A9B4C7;
        --text-low: #6B7690;
        --success: #34D399;
        --warning: #FBBF24;
        --danger: #F87171;
        --radius-lg: 20px;
        --radius-md: 14px;
        --radius-sm: 9px;
    }

    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }

    .stApp {
        background:
            radial-gradient(circle at 12% -10%, rgba(45,212,191,0.10), transparent 42%),
            radial-gradient(circle at 88% 0%, rgba(129,140,248,0.10), transparent 40%),
            var(--bg-0);
    }

    #MainMenu, footer, header { visibility: hidden; }
    .block-container { padding-top: 2rem; max-width: 1180px; }

    h1, h2, h3, .cf-display {
        font-family: 'Sora', sans-serif;
        color: var(--text-hi);
        letter-spacing: -0.01em;
    }

    /* ---------- Hero ---------- */
    .cf-hero {
        position: relative;
        border-radius: var(--radius-lg);
        border: 1px solid var(--surface-border);
        background: linear-gradient(160deg, rgba(45,212,191,0.08), rgba(129,140,248,0.05) 60%, transparent);
        padding: 52px 48px;
        overflow: hidden;
        margin-bottom: 28px;
    }
    .cf-hero::after {
        content: "";
        position: absolute;
        top: -120px; right: -120px;
        width: 340px; height: 340px;
        border-radius: 50%;
        background: radial-gradient(circle, rgba(45,212,191,0.22), transparent 70%);
        pointer-events: none;
    }
    .cf-kicker {
        display: inline-flex; align-items: center; gap: 8px;
        color: var(--accent);
        font-size: 13px; font-weight: 600;
        margin-bottom: 18px;
    }
    .cf-kicker .dot {
        width: 6px; height: 6px; border-radius: 50%;
        background: var(--accent);
        box-shadow: 0 0 10px var(--accent);
    }
    .cf-hero h1 {
        font-size: 42px; font-weight: 800; line-height: 1.15;
        max-width: 640px; margin: 0 0 14px 0;
    }
    .cf-hero p {
        color: var(--text-mid); font-size: 16px; line-height: 1.6;
        max-width: 560px; margin: 0 0 26px 0;
    }
    .cf-formats {
        display: flex; gap: 10px; flex-wrap: wrap;
    }
    .cf-format-chip {
        border: 1px solid var(--surface-border);
        background: var(--surface);
        color: var(--text-mid);
        padding: 7px 14px;
        border-radius: 999px;
        font-size: 13px; font-weight: 500;
    }

    /* ---------- Workflow stepper ---------- */
    .cf-steps {
        display: flex; align-items: center;
        gap: 0; margin: 6px 0 30px 0;
    }
    .cf-step {
        display: flex; align-items: center; gap: 10px;
        color: var(--text-low); font-size: 13px; font-weight: 600;
    }
    .cf-step .bubble {
        width: 26px; height: 26px; border-radius: 50%;
        display: flex; align-items: center; justify-content: center;
        border: 1px solid var(--surface-border);
        background: var(--surface);
        font-size: 12px; color: var(--text-low);
    }
    .cf-step.done .bubble {
        background: var(--accent); border-color: var(--accent);
        color: #06231F; font-weight: 700;
    }
    .cf-step.active .bubble {
        border-color: var(--accent); color: var(--accent);
        box-shadow: 0 0 0 4px var(--accent-soft);
    }
    .cf-step.done, .cf-step.active { color: var(--text-hi); }
    .cf-connector {
        width: 34px; height: 1px;
        background: var(--surface-border);
        margin: 0 10px;
    }
    .cf-connector.done { background: var(--accent); }

    /* ---------- Cards ---------- */
    .cf-card {
        border: 1px solid var(--surface-border);
        background: var(--surface);
        border-radius: var(--radius-md);
        padding: 22px 24px;
    }
    .cf-empty {
        border: 1px dashed var(--surface-border);
        border-radius: var(--radius-lg);
        padding: 40px;
        text-align: center;
        color: var(--text-mid);
    }
    .cf-empty h3 { margin-bottom: 8px; font-size: 19px; }
    .cf-empty p { color: var(--text-low); font-size: 14px; max-width: 460px; margin: 0 auto; }

    /* ---------- Metrics ---------- */
    .cf-metric {
        border: 1px solid var(--surface-border);
        background: var(--surface);
        border-radius: var(--radius-md);
        padding: 18px 20px;
    }
    .cf-metric .label {
        color: var(--text-low); font-size: 12.5px; font-weight: 600;
        text-transform: none; margin-bottom: 6px;
    }
    .cf-metric .value {
        font-family: 'Sora', sans-serif;
        font-size: 28px; font-weight: 700; color: var(--text-hi);
    }
    .cf-metric.accent .value { color: var(--accent); }
    .cf-metric.warn .value { color: var(--warning); }
    .cf-metric.danger .value { color: var(--danger); }

    /* ---------- Report lines ---------- */
    .cf-report-title {
        font-size: 13px; font-weight: 700; color: var(--text-mid);
        margin: 4px 0 12px 0;
    }
    .cf-line {
        display: flex; align-items: flex-start; gap: 10px;
        padding: 9px 0;
        border-bottom: 1px solid rgba(255,255,255,0.05);
        font-size: 14px; color: var(--text-hi);
    }
    .cf-line:last-child { border-bottom: none; }
    .cf-line .icon {
        width: 18px; text-align: center; flex-shrink: 0; margin-top: 1px;
    }
    .cf-line.ok .icon { color: var(--success); }
    .cf-line.warn .icon { color: var(--warning); }
    .cf-line.err .icon { color: var(--danger); }
    .cf-line .sub { color: var(--text-low); font-size: 12.5px; margin-top: 2px; }

    .cf-badge {
        display: inline-block; padding: 3px 10px;
        border-radius: 999px; font-size: 11.5px; font-weight: 700;
    }
    .cf-badge.ok { background: rgba(52,211,153,0.14); color: var(--success); }
    .cf-badge.warn { background: rgba(251,191,36,0.14); color: var(--warning); }
    .cf-badge.err { background: rgba(248,113,113,0.14); color: var(--danger); }

    .cf-section-title {
        font-size: 20px; font-weight: 700; color: var(--text-hi);
        margin: 34px 0 14px 0;
    }
    .cf-caption { color: var(--text-low); font-size: 13px; margin-top: -8px; margin-bottom: 16px; }

    /* ---------- Streamlit widget polish ---------- */
    div[data-testid="stFileUploader"] {
        border: 1px dashed var(--surface-border);
        border-radius: var(--radius-md);
        padding: 6px;
        background: var(--surface);
    }
    .stButton > button {
        background: linear-gradient(135deg, var(--accent), var(--accent-2));
        color: #06131F; border: none; font-weight: 700;
        border-radius: var(--radius-sm); padding: 10px 22px;
        transition: transform 0.15s ease, box-shadow 0.15s ease;
    }
    .stButton > button:hover {
        transform: translateY(-1px);
        box-shadow: 0 8px 24px rgba(45,212,191,0.25);
    }
    .stDownloadButton > button {
        background: var(--accent); color: #06131F; font-weight: 700;
        border: none; border-radius: var(--radius-sm); padding: 10px 22px;
    }
    div[data-testid="stMetric"] { display: none; }
    </style>
    """)


# --------------------------------------------------------------------------
# SMALL HTML HELPERS
# --------------------------------------------------------------------------

def render_hero():
    st.html("""
    <div class="cf-hero">
        <div class="cf-kicker"><span class="dot"></span>UNIVERSAL DATA CLEANER</div>
        <h1>Turn messy spreadsheets into clean, trustworthy data.</h1>
        <p>CleanFlow reads your file, detects data-quality problems, fixes what's
        safe to fix automatically, and flags everything else for your review —
        so you always know exactly what changed and why.</p>
        <div class="cf-formats">
            <span class="cf-format-chip">CSV</span>
            <span class="cf-format-chip">XLSX</span>
            <span class="cf-format-chip">JSON</span>
            <span class="cf-format-chip">PDF (tables)</span>
        </div>
    </div>
    """)


def render_workflow(stage: int):
    """stage: 0=Upload,1=Analyze,2=Clean,3=Validate,4=Review,5=Download"""
    labels = ["Upload", "Analyze", "Clean", "Validate", "Review", "Download"]
    parts = []
    for i, label in enumerate(labels):
        if i < stage:
            cls, mark = "done", "✓"
        elif i == stage:
            cls, mark = "active", str(i + 1)
        else:
            cls, mark = "", str(i + 1)
        parts.append(
            f'<div class="cf-step {cls}"><div class="bubble">{mark}</div>{label}</div>'
        )
        if i < len(labels) - 1:
            conn_cls = "done" if i < stage else ""
            parts.append(f'<div class="cf-connector {conn_cls}"></div>')
    st.html(f'<div class="cf-steps">{"".join(parts)}</div>')


def render_empty_state():
    st.html("""
    <div class="cf-empty">
        <h3>Nothing uploaded yet</h3>
        <p>Drop in a CSV, XLSX, JSON, or table-based PDF below. CleanFlow will
        analyze the structure, remove duplicates, standardize formatting,
        fix clearly-safe issues, and flag anything uncertain for you to review —
        without ever overwriting your original file.</p>
    </div>
    """)


def render_metric(label, value, tone=""):
    tone_cls = f"cf-metric {tone}".strip()
    st.html(f"""
    <div class="{tone_cls}">
        <div class="label">{label}</div>
        <div class="value">{value}</div>
    </div>
    """)


def render_line(status, text, sub=None):
    icon = {"ok": "✓", "warn": "!", "err": "✕"}.get(status, "•")
    sub_html = f'<div class="sub">{sub}</div>' if sub else ""
    st.html(f"""
    <div class="cf-line {status}">
        <div class="icon">{icon}</div>
        <div><div>{text}</div>{sub_html}</div>
    </div>
    """)


def render_section_title(title, caption=None):
    st.html(f'<div class="cf-section-title">{title}</div>')
    if caption:
        st.html(f'<div class="cf-caption">{caption}</div>')


# --------------------------------------------------------------------------
# FILE HANDLING
# --------------------------------------------------------------------------

def save_uploaded_file(uploaded_file) -> str:
    """Save a Streamlit UploadedFile to a temp path, preserving its
    original extension so the backend's extension-based dispatch works."""
    extension = os.path.splitext(uploaded_file.name)[1].lower()
    with tempfile.NamedTemporaryFile(delete=False, suffix=extension) as tmp:
        tmp.write(uploaded_file.getbuffer())
        return tmp.name


def read_uploaded_file(uploaded_file):
    """Writes the uploaded file to a temp path, loads it through the
    existing backend, and always removes the temp file afterward.
    Returns (dataframe, error_message, technical_detail).
    """
    temp_path = None
    try:
        temp_path = save_uploaded_file(uploaded_file)
        df = load_file(temp_path)

        if df is None:
            return None, "The file could not be read. It may be empty or in an unsupported format.", None
        if not isinstance(df, pd.DataFrame):
            return None, "The file loader returned something other than a table. Please check the source file.", str(type(df))
        if df.empty:
            return None, "The file was read successfully, but it contains no rows.", None

        return df, None, None

    except Exception as exc:
        friendly = "We couldn't read this file. It may be corrupted, malformed, or in a format CleanFlow can't parse."
        return None, friendly, traceback.format_exc()
    finally:
        if temp_path and os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except OSError:
                pass


# --------------------------------------------------------------------------
# ANALYSIS / CLEANING / VALIDATION
# --------------------------------------------------------------------------

def safe_call(func, *args, default=None, label=""):
    """Run a backend function defensively; on failure, return (default, error_text)."""
    try:
        return func(*args), None
    except Exception:
        return default, f"'{label}' raised an error:\n{traceback.format_exc()}"


def count_cell_diff(before: pd.DataFrame, after: pd.DataFrame):
    """Count differing cell values between two same-shaped frames.
    Returns None if shapes don't line up (e.g. rows were removed)."""
    try:
        if before.shape != after.shape:
            return None
        common_cols = [c for c in before.columns if c in after.columns]
        b = before[common_cols].astype(str).reset_index(drop=True)
        a = after[common_cols].astype(str).reset_index(drop=True)
        return int((b != a).values.sum())
    except Exception:
        return None


def run_analysis(df: pd.DataFrame):
    """Runs data_analyzer.analyze_data plus a light per-column type pass."""
    result, err = safe_call(analyze_data, df, label="analyze_data")
    column_types = {}
    for col in df.columns:
        col_type, col_err = safe_call(detect_column_type, df[col], label=f"detect_column_type({col})")
        if col_type is not None:
            column_types[col] = col_type
    return {"summary": result, "column_types": column_types}, err


def unpack_backend_result(result, fallback_df=None):
    """
    Normalize backend cleaning results.

    Cleaning functions return:
        (DataFrame, report)

    Informational functions may return:
        dict

    This helper keeps the app's working dataset as a DataFrame.
    """
    if isinstance(result, pd.DataFrame):
        return result, {}

    if (
        isinstance(result, tuple)
        and len(result) == 2
        and isinstance(result[0], pd.DataFrame)
    ):
        backend_df = result[0]
        backend_report = result[1] if isinstance(result[1], dict) else {}
        return backend_df, backend_report

    return fallback_df, {}


def run_cleaning(df: pd.DataFrame):
    """Run the existing cleaner functions and build a UI-friendly report."""

    report = {
        "safe_changes": [],
        "errors": [],
        "technical": []
    }

    # The uploaded file must always enter this function as a DataFrame.
    if not isinstance(df, pd.DataFrame):
        raise TypeError(
            f"run_cleaning expected a DataFrame, got {type(df).__name__}"
        )

    working = df.copy()
    rows_before = len(working)

    # ---------------------------------------------------------
    # 1. Remove duplicate rows
    # ---------------------------------------------------------
    step_before = working.copy()

    result, err = safe_call(
        remove_duplicates,
        working,
        default=working,
        label="remove_duplicates"
    )

    if err:
        report["errors"].append(
            "Duplicate removal step failed — skipped."
        )
        report["technical"].append(err)
    else:
        working, backend_report = unpack_backend_result(
            result,
            fallback_df=working
        )

        removed = int(
            backend_report.get(
                "duplicates_removed",
                len(step_before) - len(working)
            )
        )

        report["safe_changes"].append(
            (
                f"Removed {removed} duplicate row(s)"
                if removed > 0
                else "No duplicate rows found",
                None
            )
        )

    # ---------------------------------------------------------
    # 2. Standardize text
    # ---------------------------------------------------------
    step_before = working.copy()

    result, err = safe_call(
        standardize_text,
        working,
        default=working,
        label="standardize_text"
    )

    if err:
        report["errors"].append(
            "Text standardization step failed — skipped."
        )
        report["technical"].append(err)
    else:
        working, backend_report = unpack_backend_result(
            result,
            fallback_df=working
        )

        standardized_columns = int(
            backend_report.get(
                "text_columns_standardized",
                0
            )
        )

        changed = count_cell_diff(
            step_before,
            working
        )

        if standardized_columns > 0:
            sub = (
                f"{changed} cell value(s) adjusted"
                if changed is not None
                else f"{standardized_columns} text column(s)"
            )
            report["safe_changes"].append(
                (
                    "Text formatting standardized",
                    sub
                )
            )
        else:
            report["safe_changes"].append(
                ("No text formatting changes were needed", None)
            )

    # ---------------------------------------------------------
    # 3. Clean dates
    # ---------------------------------------------------------
    step_before = working.copy()

    result, err = safe_call(
        clean_dates,
        working,
        default=working,
        label="clean_dates"
    )

    if err:
        report["errors"].append(
            "Date cleaning step failed — skipped."
        )
        report["technical"].append(err)
    else:
        working, backend_report = unpack_backend_result(
            result,
            fallback_df=working
        )

        invalid_dates = int(
            backend_report.get(
                "invalid_dates",
                0
            )
        )

        changed = count_cell_diff(
            step_before,
            working
        )

        if invalid_dates > 0:
            report["safe_changes"].append(
                (
                    "Invalid dates converted to missing values for review",
                    f"{invalid_dates} invalid date(s)"
                )
            )
        else:
            report["safe_changes"].append(
                (
                    "Dates checked and standardized",
                    (
                        f"{changed} cell value(s) converted"
                        if changed is not None and changed > 0
                        else None
                    )
                )
            )

    # ---------------------------------------------------------
    # 4. Clean clearly invalid sales values
    # ---------------------------------------------------------
    step_before = working.copy()

    result, err = safe_call(
        clean_invalid_values,
        working,
        default=working,
        label="clean_invalid_values"
    )

    if err:
        report["errors"].append(
            "Invalid-value cleanup step failed — skipped."
        )
        report["technical"].append(err)
    else:
        working, backend_report = unpack_backend_result(
            result,
            fallback_df=working
        )

        rows_removed = int(
            backend_report.get(
                "rows_removed",
                len(step_before) - len(working)
            )
        )

        quantity_count = int(
            backend_report.get(
                "invalid_quantity_rows",
                0
            )
        )
        discount_count = int(
            backend_report.get(
                "invalid_discount_rows",
                0
            )
        )
        revenue_count = int(
            backend_report.get(
                "negative_revenue_rows",
                0
            )
        )

        total_invalid = (
            quantity_count
            + discount_count
            + revenue_count
        )

        if rows_removed > 0:
            report["safe_changes"].append(
                (
                    f"Removed {rows_removed} row(s) with clearly invalid values",
                    (
                        f"{quantity_count} invalid quantity, "
                        f"{discount_count} invalid discount, "
                        f"{revenue_count} negative revenue"
                    )
                )
            )
        else:
            report["safe_changes"].append(
                (
                    "Clearly invalid values checked",
                    (
                        f"{total_invalid} invalid value issue(s) found"
                        if total_invalid > 0
                        else "No clearly invalid sales values found"
                    )
                )
            )

    # ---------------------------------------------------------
    # 5. Numeric analysis
    # ---------------------------------------------------------
    numeric_summary, err = safe_call(
        analyze_numeric_columns,
        working,
        default={},
        label="analyze_numeric_columns"
    )

    if err:
        report["technical"].append(err)
    elif isinstance(numeric_summary, dict):
        report["numeric_summary"] = numeric_summary
    else:
        report["numeric_summary"] = {}

    report["rows_before"] = rows_before
    report["rows_after"] = len(working)

    return working, report

def run_validation(cleaned_df: pd.DataFrame):
    """Runs the existing validator functions and organizes the results
    into ok / review / missing buckets for display."""
    validation = {"checks": [], "missing": None, "review_report": None, "technical": []}

    result, err = safe_call(validate_data, cleaned_df, label="validate_data")
    if err:
        validation["technical"].append(err)
        validation["checks"].append(("err", "Core validation could not complete"))
    else:
        passed = bool(result) if not isinstance(result, (list, dict, pd.DataFrame)) else (
            len(result) == 0 if hasattr(result, "__len__") else True
        )
        if passed:
            validation["checks"].append(("ok", "Basic validation passed"))
        else:
            validation["checks"].append(("warn", "Some records did not pass basic validation"))

    missing, err = safe_call(check_missing_values, cleaned_df, label="check_missing_values")
    if err:
        validation["technical"].append(err)
    else:
        validation["missing"] = missing
        has_missing = False
        try:
            if isinstance(missing, dict):
                has_missing = any(v for v in missing.values())
            elif isinstance(missing, pd.Series):
                has_missing = bool((missing > 0).any())
            elif isinstance(missing, pd.DataFrame):
                has_missing = not missing.empty
        except Exception:
            has_missing = False
        if has_missing:
            validation["checks"].append(("warn", "Some columns still have missing values"))
        else:
            validation["checks"].append(("ok", "No missing values remain"))

    review_report, err = safe_call(create_review_report, cleaned_df, label="create_review_report")
    if err:
        validation["technical"].append(err)
    else:
        validation["review_report"] = review_report

    present_sales_cols = [c for c in SALES_COLUMNS if c in cleaned_df.columns]
    if len(present_sales_cols) == len(SALES_COLUMNS):
        revenue_result, err = safe_call(validate_revenue, cleaned_df, label="validate_revenue")
        if err:
            validation["technical"].append(err)
            validation["checks"].append(("err", "Revenue validation could not complete"))
        else:
            revenue_ok = bool(revenue_result) if not isinstance(revenue_result, (list, dict, pd.DataFrame)) else (
                len(revenue_result) == 0 if hasattr(revenue_result, "__len__") else True
            )
            if revenue_ok:
                validation["checks"].append(("ok", "Revenue calculation validated (Quantity × Unit_Price × (1 − Discount))"))
            else:
                validation["checks"].append(("warn", "Some rows have a Revenue value that doesn't match the expected formula"))
    else:
        validation["checks"].append(("ok", "Sales-specific validation skipped — sales columns not present in this dataset"))

    return validation


def calculate_metrics(original_df, cleaned_df, report, validation):
    duplicates_removed = report["rows_before"] - report["rows_after"] if report["rows_before"] >= report["rows_after"] else 0
    issues_fixed = len(report["safe_changes"])

    needs_review = 0
    missing = validation.get("missing")
    try:
        if isinstance(missing, dict):
            needs_review = sum(v for v in missing.values() if isinstance(v, (int, float)))
        elif isinstance(missing, pd.Series):
            needs_review = int(missing.sum())
        elif isinstance(missing, pd.DataFrame) and "missing" in [c.lower() for c in missing.columns]:
            col = [c for c in missing.columns if c.lower() == "missing"][0]
            needs_review = int(missing[col].sum())
    except Exception:
        needs_review = 0

    return {
        "original_rows": len(original_df),
        "clean_rows": len(cleaned_df),
        "duplicates_removed": duplicates_removed,
        "issues_fixed": issues_fixed,
        "needs_review": needs_review,
    }


# --------------------------------------------------------------------------
# RENDER RESULTS
# --------------------------------------------------------------------------

def render_metrics_row(metrics):
    cols = st.columns(5)
    with cols[0]:
        render_metric("Original Rows", metrics["original_rows"])
    with cols[1]:
        render_metric("Clean Rows", metrics["clean_rows"], tone="accent")
    with cols[2]:
        render_metric("Duplicates Removed", metrics["duplicates_removed"])
    with cols[3]:
        render_metric("Issues Fixed", metrics["issues_fixed"], tone="accent")
    with cols[4]:
        tone = "warn" if metrics["needs_review"] > 0 else ""
        render_metric("Needs Review", metrics["needs_review"], tone=tone)


def render_cleaning_report_section(report):
    render_section_title("Cleaning report", "Exactly what CleanFlow changed, in plain language.")
    left, right = st.columns(2)
    with left:
        st.html('<div class="cf-card"><div class="cf-report-title">SAFE CHANGES</div></div>')
        with st.container():
            st.html('<div class="cf-card" style="margin-top:-58px;">')
            for text, sub in report["safe_changes"]:
                render_line("ok", text, sub)
            st.html("</div>")
    with right:
        st.html('<div class="cf-card"><div class="cf-report-title">ISSUES</div></div>')
        st.html('<div class="cf-card" style="margin-top:-58px;">')
        if report["errors"]:
            for e in report["errors"]:
                render_line("err", e)
        else:
            render_line("ok", "No cleaning steps failed")
        st.html("</div>")

    if report["technical"]:
        with st.expander("Technical details"):
            for t in report["technical"]:
                st.code(t)


def render_validation_section(validation):
    render_section_title("Validation")
    st.html('<div class="cf-card">')
    for status, text in validation["checks"]:
        render_line(status, text)
    st.html("</div>")

    if validation["technical"]:
        with st.expander("Technical details"):
            for t in validation["technical"]:
                st.code(t)


def render_missing_values_section(validation):
    missing = validation.get("missing")
    if missing is None:
        return

    rows = []
    try:
        if isinstance(missing, dict):
            rows = [(k, v) for k, v in missing.items() if isinstance(v, (int, float)) and v > 0]
        elif isinstance(missing, pd.Series):
            rows = [(idx, val) for idx, val in missing.items() if val > 0]
        elif isinstance(missing, pd.DataFrame):
            numeric_col = None
            for c in missing.columns:
                if pd.api.types.is_numeric_dtype(missing[c]):
                    numeric_col = c
                    break
            if numeric_col:
                for _, r in missing.iterrows():
                    val = r[numeric_col]
                    if val and val > 0:
                        label_col = [c for c in missing.columns if c != numeric_col]
                        label = r[label_col[0]] if label_col else "Column"
                        rows.append((label, val))
    except Exception:
        rows = []

    if not rows:
        return

    render_section_title("Needs review — missing values", "CleanFlow never invents replacement values.")
    st.html('<div class="cf-card">')
    for col_name, count in rows:
        render_line("warn", str(col_name), f"{int(count)} missing")
    st.html("</div>")


def render_preview_section(cleaned_df):
    render_section_title("Cleaned data preview")
    total_rows = len(cleaned_df)
    shown = min(PREVIEW_ROW_LIMIT, total_rows)
    st.html(f'<div class="cf-caption">Showing {shown} of {total_rows} rows.</div>')
    st.dataframe(cleaned_df.head(PREVIEW_ROW_LIMIT), use_container_width=True, height=420)


def make_excel_bytes(cleaned_df: pd.DataFrame) -> bytes:
    """Create an Excel workbook in memory."""
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        cleaned_df.to_excel(writer, index=False, sheet_name="Cleaned Data")
        summary = pd.DataFrame([
            ["Rows", len(cleaned_df)],
            ["Columns", len(cleaned_df.columns)],
            ["Generated", datetime.now().strftime("%Y-%m-%d %H:%M:%S")],
        ], columns=["Metric", "Value"])
        summary.to_excel(writer, index=False, sheet_name="Summary")
    output.seek(0)
    return output.getvalue()


def make_pdf_bytes(cleaned_df: pd.DataFrame, original_filename: str) -> bytes:
    """Create a readable PDF preview of the cleaned dataset."""
    output = io.BytesIO()
    doc = SimpleDocTemplate(
        output,
        pagesize=landscape(A4),
        rightMargin=10 * mm,
        leftMargin=10 * mm,
        topMargin=10 * mm,
        bottomMargin=10 * mm,
    )

    styles = getSampleStyleSheet()
    story = [
        Paragraph("CleanFlow — Cleaned Data", styles["Title"]),
        Paragraph(
            f"Source: {original_filename}<br/>"
            f"Rows: {len(cleaned_df)} | Columns: {len(cleaned_df.columns)}<br/>"
            f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            styles["BodyText"],
        ),
        Spacer(1, 8),
    ]

    preview = cleaned_df.head(30).copy()
    max_columns = 8
    if len(preview.columns) > max_columns:
        preview = preview.iloc[:, :max_columns]

    data = [[str(c)[:24] for c in preview.columns]]
    for _, row in preview.iterrows():
        data.append([
            "" if pd.isna(v) else str(v)[:24]
            for v in row
        ])

    table = Table(data, repeatRows=1)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E8EEF7")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#172033")),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 7),
        ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#C9D2E3")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    story.append(table)

    if len(cleaned_df.columns) > max_columns or len(cleaned_df) > 30:
        story.append(Spacer(1, 6))
        story.append(Paragraph(
            "This PDF is a preview. Use CSV or Excel for the complete cleaned dataset.",
            styles["BodyText"],
        ))

    doc.build(story)
    output.seek(0)
    return output.getvalue()


def render_download_section(cleaned_df, original_filename):
    render_section_title(
        "Download",
        "Choose the format that fits your workflow. Your original file was never modified.",
    )

    base_name = os.path.splitext(original_filename)[0]
    csv_bytes = cleaned_df.to_csv(index=False).encode("utf-8")
    excel_bytes = make_excel_bytes(cleaned_df)

    try:
        pdf_bytes = make_pdf_bytes(cleaned_df, original_filename)
        pdf_error = False
    except Exception:
        pdf_bytes = None
        pdf_error = True

    col1, col2, col3 = st.columns(3)

    with col1:
        st.download_button(
            "⬇ Download CSV",
            data=csv_bytes,
            file_name=f"{base_name}_cleaned.csv",
            mime="text/csv",
            use_container_width=True,
        )

    with col2:
        st.download_button(
            "⬇ Download Excel",
            data=excel_bytes,
            file_name=f"{base_name}_cleaned.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
        )

    with col3:
        if pdf_bytes is not None:
            st.download_button(
                "⬇ Download PDF",
                data=pdf_bytes,
                file_name=f"{base_name}_cleaned.pdf",
                mime="application/pdf",
                use_container_width=True,
            )
        else:
            st.button("PDF unavailable", disabled=True, use_container_width=True)

    if pdf_error:
        st.warning("CSV and Excel are available, but PDF generation failed.")

    st.html(
        '<div class="cf-caption" style="margin-top:10px;">'
        "CSV and Excel contain the complete cleaned dataset. "
        "PDF is a readable preview for sharing."
        "</div>"
    )


# --------------------------------------------------------------------------
# MAIN
# --------------------------------------------------------------------------

def init_session_state():
    defaults = {
        "processed": False,
        "original_df": None,
        "cleaned_df": None,
        "report": None,
        "validation": None,
        "metrics": None,
        "file_name": None,
        "file_size": None,
        "load_error": None,
        "load_error_detail": None,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def reset_pipeline_state():
    st.session_state.processed = False
    st.session_state.original_df = None
    st.session_state.cleaned_df = None
    st.session_state.report = None
    st.session_state.validation = None
    st.session_state.metrics = None
    st.session_state.load_error = None
    st.session_state.load_error_detail = None


def main():
    init_session_state()
    inject_global_styles()
    render_hero()

    stage = 0
    if st.session_state.file_name is not None:
        stage = 1
    if st.session_state.processed:
        stage = 5
    render_workflow(stage)

    uploaded_file = st.file_uploader(
        "Upload a data file",
        type=["csv", "xlsx", "json", "pdf"],
        label_visibility="collapsed",
    )

    if uploaded_file is None:
        render_empty_state()
        return

    # New file uploaded -> reset any previous run
    if st.session_state.file_name != uploaded_file.name:
        reset_pipeline_state()
        st.session_state.file_name = uploaded_file.name
        st.session_state.file_size = uploaded_file.size

    file_col, action_col = st.columns([3, 1])
    with file_col:
        size_kb = st.session_state.file_size / 1024
        st.html(f"""
        <div class="cf-card">
            <div class="cf-report-title">FILE READY</div>
            <div style="color:var(--text-hi); font-weight:600;">{uploaded_file.name}</div>
            <div style="color:var(--text-low); font-size:13px; margin-top:4px;">
                {os.path.splitext(uploaded_file.name)[1].upper().replace('.', '')} file · {size_kb:.1f} KB
            </div>
        </div>
        """)
    with action_col:
        st.write("")
        run_clicked = st.button("Analyze & Clean", use_container_width=True)

    if run_clicked:
        with st.spinner("Reading file..."):
            df, load_error, load_detail = read_uploaded_file(uploaded_file)

        if load_error:
            reset_pipeline_state()
            st.session_state.load_error = load_error
            st.session_state.load_error_detail = load_detail
        else:
            with st.spinner("Analyzing structure..."):
                _analysis, _analysis_err = run_analysis(df)

            with st.spinner("Detecting issues and cleaning safe problems..."):
                cleaned_df, report = run_cleaning(df)

            with st.spinner("Validating results..."):
                validation = run_validation(cleaned_df)

            with st.spinner("Preparing output..."):
                metrics = calculate_metrics(df, cleaned_df, report, validation)

            st.session_state.original_df = df
            st.session_state.cleaned_df = cleaned_df
            st.session_state.report = report
            st.session_state.validation = validation
            st.session_state.metrics = metrics
            st.session_state.processed = True

    if st.session_state.load_error:
        st.html(f"""
        <div class="cf-card" style="border-color: rgba(248,113,113,0.4);">
            <div class="cf-badge err" style="margin-bottom:10px;">COULD NOT PROCESS FILE</div>
            <div style="color:var(--text-hi);">{st.session_state.load_error}</div>
        </div>
        """)
        if st.session_state.load_error_detail:
            with st.expander("Technical details"):
                st.code(st.session_state.load_error_detail)
        return

    if not st.session_state.processed:
        return

    # ---- Results dashboard ----
    render_section_title("Results")
    render_metrics_row(st.session_state.metrics)
    render_cleaning_report_section(st.session_state.report)
    render_validation_section(st.session_state.validation)
    render_missing_values_section(st.session_state.validation)
    render_preview_section(st.session_state.cleaned_df)
    render_download_section(st.session_state.cleaned_df, st.session_state.file_name)


if __name__ == "__main__":
    main()