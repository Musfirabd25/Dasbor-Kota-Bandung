import re
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

if year_col and df[year_col].notna().any():
    years = sorted(df[year_col].dropna().astype(int).unique())
    if years:
        with st.sidebar:
            st.markdown("### Filter tahun")
            if len(years) > 1:
                yr = st.slider("Rentang tahun", int(min(years)), int(max(years)), (int(min(years)), int(max(years))))
                df = df[df[year_col].between(yr[0], yr[1])]
            else:
                st.caption(f"Tahun tersedia: {years[0]}")

st.caption(f"Sumber: {source} · Observasi Kota Bandung: {len(df):,} · Kolom: {len(df.columns)}")

def summary(cols):
    cols = [c for c in cols if c in df.columns]
    return df[cols].describe().T.reset_index().rename(columns={"index":"Variabel"})

def line_chart(col):
    if not year_col or year_col not in df.columns or df[year_col].notna().sum() == 0:
        st.warning("Kolom tahun belum terdeteksi.")
        return
    d = df[[year_col,col]].dropna().groupby(year_col,as_index=False)[col].mean().sort_values(year_col)
    if d.empty:
        st.info("Data belum cukup untuk membuat tren.")
        return
    fig, ax = plt.subplots(figsize=(9,4))
    ax.plot(d[year_col],d[col],marker="o",linewidth=2.5)
    ax.set(title=f"Tren {col}",xlabel="Tahun",ylabel=col)
    ax.grid(True,alpha=.25); fig.tight_layout(); st.pyplot(fig); plt.close(fig)

if menu == "Ringkasan":
    st.subheader("Ringkasan data Kota Bandung")
    a,b,c = st.columns(3)
    a.metric("Jumlah observasi", f"{len(df):,}")
    b.metric("Variabel numerik", f"{len(num_cols):,}")
    c.metric("Data kosong", f"{int(df.isna().sum().sum()):,}")
    st.markdown("### Cuplikan data"); table(df.head(12))
    st.markdown("### Statistik deskriptif"); table(summary(num_cols),420)

elif menu == "Analisis Fiskal":
    st.subheader("Analisis indikator fiskal")
    chosen = st.multiselect("Pilih indikator fiskal", fiscal, default=fiscal[:min(4,len(fiscal))])
    if chosen:
        table(summary(chosen))
        col = st.selectbox("Distribusi indikator", chosen)
        vals = df[col].dropna()
        if not vals.empty:
            fig,ax=plt.subplots(figsize=(9,4)); ax.hist(vals,bins="auto",edgecolor="white")
            ax.set(title=f"Distribusi {col}",xlabel=col,ylabel="Frekuensi"); ax.grid(axis="y",alpha=.2)
            fig.tight_layout(); st.pyplot(fig); plt.close(fig)

elif menu == "Analisis Belanja":
    st.subheader("Analisis indikator belanja")
    chosen = st.multiselect("Pilih indikator belanja", spending, default=spending[:min(5,len(spending))])
    if chosen:
        table(summary(chosen))
        col = st.selectbox("Variabel untuk grafik", chosen)
        vals = df[col].dropna().reset_index(drop=True)
        if not vals.empty:
            fig,ax=plt.subplots(figsize=(9,4)); ax.bar(np.arange(1,len(vals)+1),vals.values)
            ax.set(title=f"Nilai {col} per observasi",xlabel="Urutan observasi",ylabel=col); ax.grid(axis="y",alpha=.2)
            fig.tight_layout(); st.pyplot(fig); plt.close(fig)

elif menu == "Sosial-Ekonomi":
    st.subheader("Indikator sosial-ekonomi")
    chosen = st.multiselect("Pilih indikator sosial-ekonomi", social, default=social[:min(5,len(social))])
    if chosen:
        table(summary(chosen))
        col = st.selectbox("Pilih indikator", chosen)
        vals = df[col].dropna().reset_index(drop=True)
        if not vals.empty:
            st.line_chart(vals, height=300)

elif menu == "Tren Tahunan":
    st.subheader("Tren indikator tahunan")
    candidates = [c for c in num_cols if c != year_col]
    if year_col and candidates:
        col = st.selectbox("Pilih indikator", candidates)
        line_chart(col)
        table(df.groupby(year_col)[col].agg(["mean","min","max","count"]).reset_index())
    else:
        st.warning("Kolom tahun atau variabel numerik belum tersedia.")

elif menu == "Hubungan Variabel":
    st.subheader("Eksplorasi hubungan antarvariabel")
    candidates = [c for c in num_cols if c != year_col]
    if len(candidates) >= 2:
        x = st.selectbox("Variabel X", candidates)
        y = st.selectbox("Variabel Y", [c for c in candidates if c != x])
        pair = df[[x,y]].dropna()
        if len(pair) >= 2:
            corr = pair[x].corr(pair[y])
            st.metric("Korelasi Pearson", f"{corr:.3f}" if pd.notna(corr) else "Tidak tersedia")
            fig,ax=plt.subplots(figsize=(8,4)); ax.scatter(pair[x],pair[y],alpha=.75)
            ax.set(xlabel=x,ylabel=y,title=f"Hubungan {x} dan {y}"); ax.grid(True,alpha=.2)
            fig.tight_layout(); st.pyplot(fig); plt.close(fig)
            st.caption("Korelasi menunjukkan pola hubungan, bukan bukti sebab-akibat.")
        else:
            st.info("Data lengkap tidak cukup untuk pasangan variabel ini.")
    else:
        st.info("Diperlukan minimal dua variabel numerik.")

elif menu == "Data & Unduh":
    st.subheader("Data dan kualitas dataset")
    a,b=st.columns(2); a.metric("Baris data",len(df)); b.metric("Kolom data",len(df.columns))
    missing=df.isna().sum().rename("Jumlah kosong").to_frame()
    missing["Persentase kosong (%)"]=(missing["Jumlah kosong"]/max(len(df),1)*100).round(2)
    st.markdown("### Data kosong"); table(missing.reset_index().rename(columns={"index":"Variabel"}),400)
    st.markdown("### Pratinjau data"); table(df,430)
    st.download_button("⬇️ Unduh data Kota Bandung (CSV)",df.to_csv(index=False).encode("utf-8-sig"),"data_kota_bandung.csv","text/csv",use_container_width=True)
    report=pd.DataFrame({"Variabel":df.columns,"Tipe data":[str(df[c].dtype) for c in df.columns],"Jumlah kosong":[int(df[c].isna().sum()) for c in df.columns],"Jumlah unik":[int(df[c].nunique(dropna=True)) for c in df.columns]})
    st.download_button("⬇️ Unduh laporan kualitas data",report.to_csv(index=False).encode("utf-8-sig"),"laporan_kualitas_data_bandung.csv","text/csv")
