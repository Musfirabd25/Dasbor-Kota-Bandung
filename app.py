import re
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import streamlit as st

DATA_URL = "https://raw.githubusercontent.com/Alam-A99/DATAAKSI/main/dataset_fiskal_97_hipoFull.csv"

st.set_page_config(page_title="Bandung Fiscal Insight", page_icon="🏙️", layout="wide")
st.markdown("""
<style>
.stApp {background:#F3F6FB;color:#1F2E43}
[data-testid="stSidebar"] {background:#10233F}
[data-testid="stSidebar"] * {color:#F5F8FC !important}
.hero {background:linear-gradient(115deg,#10233F,#2359A8);padding:1.5rem 1.8rem;border-radius:18px;color:white;margin-bottom:1rem}
.hero h1 {color:white;margin:0}.hero p {color:#DDEBFA;margin:.4rem 0 0}
div[data-testid="stMetric"] {background:white;padding:1rem;border-radius:14px;border:1px solid #E0E8F2}
</style>
<div class="hero"><h1>🏙️ Bandung Fiscal Insight</h1>
<p>Dashboard analisis fiskal, belanja, dan indikator sosial-ekonomi Kota Bandung</p></div>
""", unsafe_allow_html=True)

@st.cache_data(show_spinner=False)
def load_data():
    return pd.read_csv(DATA_URL, low_memory=False)

def find_col(cols, patterns):
    for pat in patterns:
        for col in cols:
            if re.search(pat, str(col), re.I):
                return col
    return None

def numeric_clean(s):
    if pd.api.types.is_numeric_dtype(s):
        return s
    t = s.astype(str).str.strip().replace({"":np.nan,"nan":np.nan,"None":np.nan,"-":np.nan})
    t = t.str.replace(r"(?<=\d)\.(?=\d{3}(\D|$))", "", regex=True)
    t = t.str.replace(",", ".", regex=False).str.replace(r"[^\d.\-]", "", regex=True)
    v = pd.to_numeric(t, errors="coerce")
    if s.notna().sum() and v.notna().sum() >= max(3, int(.65*s.notna().sum())):
        return v
    return s

def table(df, height=360):
    st.dataframe(df, use_container_width=True, height=height, hide_index=True)

with st.sidebar:
    st.markdown("## BANDUNG FISCAL")
    menu = st.radio("Navigasi", ["Ringkasan","Analisis Fiskal","Analisis Belanja","Sosial-Ekonomi","Tren Tahunan","Hubungan Variabel","Data & Unduh"])
    uploaded = st.file_uploader("Unggah CSV jika sumber gagal", type=["csv"])
    if st.button("Muat ulang data"):
        load_data.clear()
        st.rerun()

try:
    raw = pd.read_csv(uploaded, low_memory=False) if uploaded else load_data()
    source = "CSV yang diunggah" if uploaded else "Dataset GitHub"
except Exception as e:
    st.error("Data tidak berhasil dimuat. Coba unggah CSV dari sumber dataset.")
    st.code(DATA_URL)
    st.caption(str(e))
    st.stop()

raw.columns = [str(c).strip() for c in raw.columns]
city_col = find_col(raw.columns, [r"kabupaten.?kota",r"nama.?kota",r"wilayah",r"daerah",r"city",r"kabupaten",r"\bkota\b"])
year_col = find_col(raw.columns, [r"^tahun$",r"\byear\b",r"periode",r"tahun.?anggaran"])
if city_col is None:
    st.error("Kolom wilayah tidak terdeteksi. Pilih kolom yang berisi nama wilayah.")
    city_col = st.selectbox("Kolom wilayah", list(raw.columns))

names = raw[city_col].astype(str).str.strip()
match = names.str.fullmatch(r"(?i)(kota\s+bandung|bandung)", na=False)
exclude = ~names.str.contains(r"(?i)kabupaten\s+bandung|kab\.?\s+bandung|bandung\s+barat", na=False)
df = raw.loc[match & exclude].copy()
if df.empty:
    st.error("Tidak ditemukan data yang cocok persis dengan Kota Bandung. Dashboard dihentikan agar tidak menghasilkan angka rekaan.")
    st.write("Contoh nilai wilayah yang tersedia:", sorted(names.dropna().unique().tolist())[:100])
    st.stop()

if year_col:
    df[year_col] = pd.to_numeric(df[year_col], errors="coerce")
for col in df.columns:
    if col != city_col:
        df[col] = numeric_clean(df[col])

num_cols = [c for c in df.columns if c != city_col and pd.api.types.is_numeric_dtype(df[c]) and df[c].notna().any()]
if not num_cols:
    st.error("Tidak ditemukan variabel numerik pada data Kota Bandung.")
    table(df.head(30))
    st.stop()

fiscal = [c for c in num_cols if re.search(r"fiskal|pendapatan|penerimaan|pajak|retribusi|transfer|dana|apbd|pad|belanja|pengeluaran|anggaran", str(c), re.I)] or num_cols
spending = [c for c in num_cols if re.search(r"belanja|pengeluaran|modal|pegawai|barang|jasa|operasi|infrastruktur", str(c), re.I)] or num_cols
social = [c for c in num_cols if re.search(r"kemiskinan|miskin|pengangguran|pendidikan|kesehatan|ipm|harapan hidup|gini|penduduk|pdrb|ekonomi|sosial|tenaga kerja", str(c), re.I)] or num_cols
