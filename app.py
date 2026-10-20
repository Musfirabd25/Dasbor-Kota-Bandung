from __future__ import annotations

import io
import re
import requests
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# =========================================================
# Dashboard Fiskal Kota Bandung — Akademik & Statistik
# Sumber CSV: repositori GitHub yang diberikan pengguna
# =========================================================
st.set_page_config(
    page_title="Dashboard Fiskal Kota Bandung",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

DATA_URL = (
    "https://raw.githubusercontent.com/Musfirabd25/Dasbor-Kota-Bandung/"
    "2fb11c296cea1b3d2db1bd19d469540638a434be/"
    "dataset_fiskal_97_hipoFull.csv"
)
REPO_URL = "https://github.com/Musfirabd25/Dasbor-Kota-Bandung"

# Palet akademik
NAVY = "#17324D"
BLUE = "#2878B5"
TEAL = "#1B998B"
GOLD = "#D9A441"
RED = "#C94C4C"
MUTED = "#627386"

st.markdown("""
<style>
    .block-container {padding-top: 1.5rem; padding-bottom: 2.2rem; max-width: 1500px;}
    .hero {
        background: linear-gradient(115deg, #17324D 0%, #22577A 58%, #1B998B 100%);
        padding: 1.45rem 1.7rem; border-radius: 14px; color: #fff; margin-bottom: 1rem;
    }
    .hero h1 {color: #fff; font-size: 2rem; margin: 0 0 .35rem 0;}
    .hero p {color: #e9f4f8; margin: 0; font-size: 1rem;}
    .section-note {color: #627386; font-size: .88rem;}
    div[data-testid="stMetric"] {
        background: #f6f9fc; border: 1px solid #dce6ee;
        padding: 12px 14px; border-radius: 10px;
    }
    [data-testid="stSidebar"] {background-color: #f6f8fb;}
</style>
<div class="hero">
  <h1>📊 Dashboard Fiskal Kota Bandung</h1>
  <p>Analisis deskriptif, perbandingan antarkota, dinamika tahunan, dan hubungan indikator fiskal–sosial.</p>
</div>
""", unsafe_allow_html=True)


@st.cache_data(ttl=3600, show_spinner="Mengambil dataset dari GitHub...")
def fetch_csv(url: str) -> pd.DataFrame:
    response = requests.get(url, timeout=30)
    response.raise_for_status()
    response.encoding = "utf-8"
    # Dataset berformat CSV dengan koma sebagai delimiter.
    return pd.read_csv(io.StringIO(response.text), low_memory=False)


def to_numeric_safely(series: pd.Series) -> pd.Series:
    """Convert angka yang tersimpan sebagai teks tanpa memaksa kategori jadi angka."""
    if pd.api.types.is_numeric_dtype(series):
        return series
    text = series.astype("string").str.strip()
    cleaned = text.str.replace(",", "", regex=False)
    converted = pd.to_numeric(cleaned, errors="coerce")
    nonempty = text.notna() & text.ne("")
    if nonempty.sum() and converted[nonempty].notna().mean() >= 0.85:
        return converted
    return series


def fmt_number(value, decimals=2):
    if pd.isna(value):
        return "—"
    return f"{value:,.{decimals}f}".replace(",", "_").replace(".", ",").replace("_", ".")


def display_label(col: str) -> str:
    labels = {
        "Kota": "Kota/Kabupaten",
        "Tahun": "Tahun",
        "DBH_PAJAK": "DBH Pajak",
        "DBH_SDA": "DBH Sumber Daya Alam",
        "DBH_Lainnya": "DBH Lainnya",
        "DAU_Grant": "DAU Grant",
