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
        "DAU_Earmark": "DAU Earmark",
        "DAK_Fisik": "DAK Fisik",
        "DAK_Nonfisik": "DAK Nonfisik",
        "PAD": "Pendapatan Asli Daerah (PAD)",
        "ICT": "ICT",
        "bm_pendidikan": "Belanja Pendidikan",
        "bm_kesehatan": "Belanja Kesehatan",
        "bm_perumahan": "Belanja Perumahan",
        "bm_lingkungan": "Belanja Lingkungan",
        "bm_ekonomi": "Belanja Ekonomi",
        "bm_infrastruktur": "Belanja Infrastruktur",
        "bm_pariwisata": "Belanja Pariwisata",
        "bm_perlindungan_sosial": "Belanja Perlindungan Sosial",
        "KEMISKINAN": "Kemiskinan",
        "PENGANGGURAN": "Pengangguran",
        "KETIMPANGAN": "Ketimpangan",
        "IPM": "Indeks Pembangunan Manusia (IPM)",
    }
    if col in labels:
        return labels[col]
    return re.sub(r"[_]+", " ", str(col)).strip().title()


def style_fig(fig, height=430):
    fig.update_layout(
        template="plotly_white",
        height=height,
        margin=dict(l=18, r=18, t=62, b=25),
        font=dict(family="Arial, sans-serif", color=NAVY),
        title=dict(font=dict(size=17, color=NAVY)),
        legend_title_text="",
        hoverlabel=dict(bgcolor="white"),
    )
    fig.update_xaxes(showgrid=False, zeroline=False)
    fig.update_yaxes(gridcolor="#e8eef3", zeroline=False)
    return fig


try:
    raw_df = fetch_csv(DATA_URL)
except Exception as err:
    st.error("Dataset tidak dapat diambil dari GitHub.")
    st.markdown(f"Periksa akses internet atau buka [repositori sumber]({REPO_URL}).")
    uploaded = st.file_uploader("Unggah salinan dataset CSV sebagai alternatif", type=["csv"])
    if uploaded is None:
        with st.expander("Detail teknis"):
            st.code(str(err))
        st.stop()
    raw_df = pd.read_csv(uploaded, low_memory=False)

if raw_df.empty:
    st.error("Dataset tidak berisi baris data.")
    st.stop()

raw_df.columns = [str(c).strip() for c in raw_df.columns]
df = raw_df.copy()
for c in df.columns:
    df[c] = to_numeric_safely(df[c])

# Kolom identitas yang tersedia pada dataset ini
city_col = next((c for c in df.columns if c.lower() in ["kota", "kabupaten_kota", "nama_kota", "wilayah"]), None)
year_col = next((c for c in df.columns if c.lower() in ["tahun", "year", "periode"]), None)
numeric_cols = df.select_dtypes(include="number").columns.tolist()
if year_col and year_col not in numeric_cols:
    df[year_col] = pd.to_numeric(df[year_col], errors="coerce")
    if pd.api.types.is_numeric_dtype(df[year_col]):
        numeric_cols = df.select_dtypes(include="number").columns.tolist()

# Kelompok variabel yang dikenal dari header dataset; kolom lain tetap tersedia.
fiscal_revenue = [c for c in ["DBH_PAJAK", "DBH_SDA", "DBH_Lainnya", "DAU_Grant", "DAU_Earmark", "DAK_Fisik", "DAK_Nonfisik", "PAD"] if c in df.columns]
fiscal_spending = [c for c in ["bm_pendidikan", "bm_kesehatan", "bm_perumahan", "bm_lingkungan", "bm_ekonomi", "bm_infrastruktur", "bm_pariwisata", "bm_perlindungan_sosial"] if c in df.columns]
social_vars = [c for c in ["KEMISKINAN", "PENGANGGURAN", "KETIMPANGAN", "IPM"] if c in df.columns]
other_numeric = [c for c in numeric_cols if c not in fiscal_revenue + fiscal_spending + social_vars + ([year_col] if year_col else [])]

# Sidebar filters
with st.sidebar:
    st.header("Filter analisis")
    st.caption("Filter diterapkan pada seluruh tab dashboard.")
    if city_col:
        cities = sorted(df[city_col].dropna().astype(str).unique().tolist())
        preferred = next((x for x in cities if x.casefold() == "kota bandung"), None)
        default_cities = [preferred] if preferred else cities[:1]
        selected_cities = st.multiselect(
            "Kota/kabupaten",
            options=cities,
            default=default_cities,
            help="Pilih Kota Bandung untuk analisis fokus atau beberapa kota untuk perbandingan."
        )
    else:
        selected_cities = []
        st.info("Kolom identitas kota tidak terdeteksi; filter kota tidak tersedia.")

    if year_col and df[year_col].notna().any():
        years = sorted(df[year_col].dropna().astype(int).unique().tolist())
        if len(years) > 1:
            year_range = st.slider("Rentang tahun", min_value=int(min(years)), max_value=int(max(years)),
                                   value=(int(min(years)), int(max(years))), step=1)
        else:
            year_range = (int(years[0]), int(years[0]))
    else:
        year_range = None

    st.divider()
    st.markdown("**Sumber dataset**")
    st.markdown(f"[Lihat repositori GitHub]({REPO_URL})")
    st.caption("Data dibaca dari URL raw GitHub. Cache aplikasi berlaku selama 1 jam.")

filtered = df.copy()
if city_col and selected_cities:
    filtered = filtered[filtered[city_col].astype(str).isin(selected_cities)]
elif city_col and not selected_cities:
    filtered = filtered.iloc[0:0]
if year_col and year_range:
    filtered = filtered[filtered[year_col].between(year_range[0], year_range[1])]

if filtered.empty:
    st.warning("Tidak ada baris yang cocok dengan filter. Pilih kota atau rentang tahun lain.")
    st.stop()

# For a single-city time-series panel use filtered rows; comparison rankings use latest selected year.
n_cities = filtered[city_col].nunique() if city_col else 1
year_min = int(filtered[year_col].min()) if year_col and filtered[year_col].notna().any() else None
year_max = int(filtered[year_col].max()) if year_col and filtered[year_col].notna().any() else None
missing_cells = int(filtered.isna().sum().sum())
complete_pct = 100 * (1 - missing_cells / max(filtered.shape[0] * filtered.shape[1], 1))

st.caption(
    f"Periode analisis: {year_min if year_min is not None else '—'}–{year_max if year_max is not None else '—'}"
    f" · Wilayah terpilih: {n_cities:,} · Baris terfilter: {len(filtered):,}"
)

# KPI utama
kpi_cols = st.columns(4)
kpi_cols[0].metric("Observasi", f"{len(filtered):,}")
kpi_cols[1].metric("Wilayah terpilih", f"{n_cities:,}")
kpi_cols[2].metric("Variabel numerik", f"{len(numeric_cols):,}")
kpi_cols[3].metric("Kelengkapan sel", f"{complete_pct:.1f}%".replace(".", ","))

tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "Ringkasan", "Pendapatan & Belanja", "Indikator Sosial", "Perbandingan Wilayah",
    "Hubungan Statistik", "Data & Metodologi"
])

with tab1:
    st.subheader("Ringkasan statistik")
    if city_col and len(selected_cities) == 1:
        st.markdown(f"Analisis terfokus pada **{selected_cities[0]}**.")
    elif city_col:
        st.markdown(f"Analisis gabungan untuk **{n_cities} wilayah** yang dipilih.")
    else:
        st.markdown("Analisis dataset berdasarkan seluruh observasi yang lolos filter.")

    a, b = st.columns(2)
    with a:
        st.markdown("#### Perkembangan indikator numerik")
        candidates = [c for c in fiscal_revenue + social_vars if c in numeric_cols]
        if not candidates:
            candidates = [c for c in numeric_cols if c != year_col][:8]
        if year_col and candidates:
            metric = st.selectbox("Indikator tren", candidates, format_func=display_label, key="overview_trend")
            trend = filtered.groupby(year_col, as_index=False)[metric].mean().sort_values(year_col)
            fig = px.line(trend, x=year_col, y=metric, markers=True,
                          title=f"Rata-rata {display_label(metric)} per tahun")
            fig.update_traces(line=dict(color=BLUE, width=3), marker=dict(size=7))
            st.plotly_chart(style_fig(fig), use_container_width=True)
        else:
            st.info("Grafik tren membutuhkan kolom tahun dan variabel numerik.")
    with b:
        st.markdown("#### Sebaran indikator")
        if numeric_cols:
            metric_dist = st.selectbox("Variabel untuk distribusi", [c for c in numeric_cols if c != year_col] or numeric_cols,
                                       format_func=display_label, key="overview_dist")
            fig = px.histogram(filtered, x=metric_dist, nbins=25, marginal="box",
                               title=f"Distribusi {display_label(metric_dist)}")
            fig.update_traces(marker_color=TEAL)
            st.plotly_chart(style_fig(fig), use_container_width=True)
        else:
            st.info("Tidak ada variabel numerik untuk ditampilkan.")

    st.markdown("#### Statistik deskriptif")
    if numeric_cols:
        stats = filtered[numeric_cols].describe().T
        stats.index = [display_label(x) for x in stats.index]
        stats = stats.rename(columns={
            "count": "Jumlah", "mean": "Rata-rata", "std": "Simpangan baku",
            "min": "Minimum", "25%": "Kuartil 1", "50%": "Median", "75%": "Kuartil 3", "max": "Maksimum"
        })
        st.dataframe(stats.round(3), use_container_width=True)
    else:
        st.info("Statistik deskriptif tidak tersedia karena tidak ada kolom numerik.")

with tab2:
    st.subheader("Analisis pendapatan dan belanja")
    left, right = st.columns(2)
    with left:
        st.markdown("#### Komponen pendapatan daerah")
        if fiscal_revenue:
            rev_col = st.selectbox("Ukuran pendapatan", ["Rata-rata", "Total"], key="rev_agg")
            if city_col and n_cities > 1:
                rev = filtered.groupby(city_col)[fiscal_revenue].mean() if rev_col == "Rata-rata" else filtered.groupby(city_col)[fiscal_revenue].sum()
                rev = rev.mean(axis=0) if rev_col == "Rata-rata" else rev.sum(axis=0)
            else:
                rev = filtered[fiscal_revenue].mean() if rev_col == "Rata-rata" else filtered[fiscal_revenue].sum()
            rev_df = rev.rename_axis("Komponen").reset_index(name="Nilai")
            rev_df["Komponen"] = rev_df["Komponen"].map(display_label)
            fig = px.bar(rev_df, x="Komponen", y="Nilai", title=f"{rev_col} komponen pendapatan",
                         color="Nilai", color_continuous_scale="Blues")
            fig.update_xaxes(tickangle=-35)
            st.plotly_chart(style_fig(fig), use_container_width=True)
        else:
            st.info("Komponen pendapatan fiskal tidak ditemukan pada kolom dataset.")
    with right:
        st.markdown("#### Komponen belanja menurut bidang")
        if fiscal_spending:
            spend = filtered[fiscal_spending].mean() if n_cities > 1 else filtered[fiscal_spending].mean()
            spend_df = spend.rename_axis("Bidang").reset_index(name="Rata-rata")
            spend_df["Bidang"] = spend_df["Bidang"].map(display_label)
            fig = px.bar(spend_df.sort_values("Rata-rata"), x="Rata-rata", y="Bidang",
                         orientation="h", title="Rata-rata indikator belanja",
                         color="Rata-rata", color_continuous_scale="Teal")
            st.plotly_chart(style_fig(fig), use_container_width=True)
        else:
            st.info("Variabel belanja sektoral tidak ditemukan pada kolom dataset.")

    if year_col and (fiscal_revenue or fiscal_spending):
        st.markdown("#### Tren tahunan komponen fiskal")
        available_fiscal = fiscal_revenue + fiscal_spending
        selected_fiscal = st.multiselect(
            "Pilih komponen untuk dibandingkan",
            available_fiscal,
            default=available_fiscal[:min(4, len(available_fiscal))],
            format_func=display_label,
            key="fiscal_trend_vars"
        )
        if selected_fiscal:
            trend = filtered.groupby(year_col, as_index=False)[selected_fiscal].mean().sort_values(year_col)
            long = trend.melt(id_vars=year_col, var_name="Variabel", value_name="Nilai")
            long["Variabel"] = long["Variabel"].map(display_label)
            fig = px.line(long, x=year_col, y="Nilai", color="Variabel", markers=True,
                          title="Rata-rata indikator fiskal per tahun")
            st.plotly_chart(style_fig(fig, 470), use_container_width=True)

with tab3:
    st.subheader("Indikator sosial dan pembangunan")
    if social_vars:
        selected_social = st.multiselect(
            "Indikator sosial yang ditampilkan", social_vars,
            default=social_vars, format_func=display_label
        )
        left, right = st.columns(2)
        with left:
            if year_col and selected_social:
                tr = filtered.groupby(year_col, as_index=False)[selected_social].mean().sort_values(year_col)
                long = tr.melt(id_vars=year_col, var_name="Indikator", value_name="Nilai")
                long["Indikator"] = long["Indikator"].map(display_label)
                fig = px.line(long, x=year_col, y="Nilai", color="Indikator", markers=True,
                              title="Perkembangan indikator sosial")
                st.plotly_chart(style_fig(fig), use_container_width=True)
            else:
                st.info("Pilih setidaknya satu indikator dan pastikan kolom tahun tersedia.")
        with right:
            if selected_social:
                means = filtered[selected_social].mean().rename_axis("Indikator").reset_index(name="Rata-rata")
                means["Indikator"] = means["Indikator"].map(display_label)
                fig = px.bar(means.sort_values("Rata-rata"), x="Rata-rata", y="Indikator",
                             orientation="h", title="Rata-rata pada filter terpilih", color="Rata-rata",
                             color_continuous_scale="Viridis")
                st.plotly_chart(style_fig(fig), use_container_width=True)
    else:
        st.info("Kolom sosial yang dikenali tidak ditemukan. Gunakan tab Data & Metodologi untuk memilih variabel lain.")

    if social_vars and fiscal_revenue:
        st.markdown("#### Ringkasan korelasi fiskal–sosial")
        corr_vars = fiscal_revenue + social_vars
        corr = filtered[corr_vars].corr(numeric_only=True)
        corr.index = [display_label(c) for c in corr.index]
        corr.columns = [display_label(c) for c in corr.columns]
        fig = px.imshow(corr, text_auto=".2f", aspect="auto", zmin=-1, zmax=1,
                        color_continuous_scale="RdBu_r", title="Korelasi Pearson antarindikator")
        st.plotly_chart(style_fig(fig, 600), use_container_width=True)
        st.caption("Korelasi menunjukkan asosiasi linear, bukan bukti hubungan sebab-akibat.")

with tab4:
    st.subheader("Perbandingan antarkota/kabupaten")
    if city_col:
        compare_vars = [c for c in numeric_cols if c != year_col]
        if compare_vars:
            compare_metric = st.selectbox("Indikator pembanding", compare_vars, format_func=display_label, key="compare_metric")
            compare_data = filtered.copy()
            if year_col:
                latest = int(compare_data[year_col].max())
                compare_data = compare_data[compare_data[year_col] == latest]
                st.caption(f"Perbandingan memakai tahun terakhir yang tersedia pada filter: {latest}.")
            summary = compare_data.groupby(city_col, as_index=False)[compare_metric].mean().dropna()
            summary = summary.sort_values(compare_metric, ascending=False)
            top_n = st.slider("Jumlah wilayah pada grafik", 5, min(30, max(5, len(summary))), min(15, max(5, len(summary))))
            chart_df = summary.head(top_n)
            fig = px.bar(chart_df.sort_values(compare_metric), x=compare_metric, y=city_col,
                         orientation="h", title=f"{display_label(compare_metric)} — peringkat tertinggi",
                         color=compare_metric, color_continuous_scale="Blues")
            st.plotly_chart(style_fig(fig, max(420, top_n * 25)), use_container_width=True)
            st.markdown("#### Tabel peringkat")
            summary.insert(0, "Peringkat", range(1, len(summary) + 1))
            summary = summary.rename(columns={city_col: "Wilayah", compare_metric: display_label(compare_metric)})
            st.dataframe(summary, use_container_width=True, hide_index=True)
        else:
            st.info("Tidak ada variabel numerik untuk perbandingan.")
    else:
        st.info("Perbandingan wilayah memerlukan kolom kota/kabupaten.")

with tab5:
    st.subheader("Eksplorasi hubungan statistik")
    possible = [c for c in numeric_cols if c != year_col]
    if len(possible) >= 2:
        c1, c2, c3 = st.columns(3)
        with c1:
            xvar = st.selectbox("Variabel X", possible, index=0, format_func=display_label)
        with c2:
            y_default = 1 if len(possible) > 1 else 0
            yvar = st.selectbox("Variabel Y", possible, index=y_default, format_func=display_label)
        with c3:
            method = st.selectbox("Metode korelasi", ["Pearson", "Spearman"])
        scatter = filtered[[xvar, yvar] + ([city_col] if city_col else [])].dropna()
        if xvar == yvar:
            st.warning("Pilih dua variabel yang berbeda untuk melihat hubungan.")
        elif scatter.empty:
            st.warning("Tidak ada pasangan data lengkap untuk kedua variabel.")
        else:
            color_arg = city_col if city_col and scatter[city_col].nunique() <= 12 else None
            fig = px.scatter(scatter, x=xvar, y=yvar, color=color_arg,
                             trendline="ols" if len(scatter) >= 3 else None,
                             hover_data=[city_col] if city_col and color_arg is None else None,
                             title=f"Hubungan {display_label(xvar)} dan {display_label(yvar)}")
            st.plotly_chart(style_fig(fig, 470), use_container_width=True)
            corr_val = scatter[xvar].corr(scatter[yvar], method=method.lower())
            st.metric(f"Korelasi {method}", fmt_number(corr_val, 3))
            st.caption("Interpretasikan koefisien sesuai skala, konteks data, jumlah observasi, dan kemungkinan variabel perancu.")
    else:
        st.info("Diperlukan minimal dua variabel numerik.")

    if len(numeric_cols) >= 2:
        st.markdown("#### Matriks korelasi")
        corr_cols = st.multiselect("Pilih variabel untuk matriks korelasi",
                                   [c for c in numeric_cols if c != year_col],
                                   default=[c for c in (fiscal_revenue[:3] + social_vars[:3]) if c in numeric_cols])
        if len(corr_cols) >= 2:
            corr = filtered[corr_cols].corr(numeric_only=True)
            fig = px.imshow(corr, text_auto=".2f", zmin=-1, zmax=1, aspect="auto",
                            color_continuous_scale="RdBu_r", title="Matriks korelasi Pearson")
            st.plotly_chart(style_fig(fig, 520), use_container_width=True)

with tab6:
    st.subheader("Data, kualitas, dan metodologi")
    st.markdown("#### Informasi struktur dataset")
    s1, s2 = st.columns(2)
    with s1:
        st.write(f"**Sumber:** [Repositori GitHub]({REPO_URL})")
        st.write(f"**Ukuran data asli:** {raw_df.shape[0]:,} baris × {raw_df.shape[1]:,} kolom")
        st.write(f"**Ukuran setelah filter:** {filtered.shape[0]:,} baris × {filtered.shape[1]:,} kolom")
        st.write(f"**Kolom identitas wilayah:** {city_col or 'Tidak terdeteksi'}")
        st.write(f"**Kolom waktu:** {year_col or 'Tidak terdeteksi'}")
    with s2:
        st.markdown("**Kelengkapan nilai per kolom**")
        missing_df = pd.DataFrame({
            "Variabel": [display_label(c) for c in filtered.columns],
            "Nilai kosong": [int(filtered[c].isna().sum()) for c in filtered.columns],
            "Persentase kosong (%)": [round(100 * filtered[c].isna().mean(), 2) for c in filtered.columns],
            "Tipe data": [str(filtered[c].dtype) for c in filtered.columns],
        }).sort_values("Persentase kosong (%)", ascending=False)
        st.dataframe(missing_df, use_container_width=True, hide_index=True)

    st.markdown("#### Data terfilter")
    show_cols = st.multiselect("Kolom untuk tabel", filtered.columns.tolist(),
                               default=filtered.columns.tolist()[:min(10, len(filtered.columns))],
                               format_func=display_label)
    st.dataframe(filtered[show_cols] if show_cols else filtered.iloc[:, 0:0],
                 use_container_width=True, height=420)
    csv_data = filtered.to_csv(index=False).encode("utf-8-sig")
    st.download_button("⬇️ Unduh seluruh data terfilter (CSV)", data=csv_data,
                       file_name="dataset_fiskal_kota_bandung_filtered.csv",
                       mime="text/csv")

    st.markdown("#### Catatan metodologis")
    st.markdown("""
- **Unit analisis:** mengikuti struktur baris pada dataset; aplikasi mengasumsikan kolom `Kota` dan `Tahun` sebagai identitas wilayah dan periode jika tersedia.
- **Agregasi:** grafik lintas tahun menggunakan rata-rata per tahun; peringkat wilayah menggunakan tahun terbaru dalam filter.
- **Satuan:** tidak dikonversi ke rupiah atau persen karena metadata satuan tidak tersedia di aplikasi. Periksa dokumentasi sumber sebelum menafsirkan besaran nilai.
- **Kualitas data:** nilai kosong dihitung apa adanya; aplikasi tidak mengimputasi nilai yang hilang.
- **Interpretasi:** statistik deskriptif dan korelasi berguna untuk eksplorasi, tetapi tidak membuktikan hubungan kausal.
- **Keterulangan:** data diambil dari URL raw GitHub pada commit yang ditentukan di kode ini. Cache dibersihkan setelah satu jam.
""")

st.divider()
st.caption("Dashboard akademik berbasis Streamlit, pandas, dan Plotly. Disiapkan untuk eksplorasi data; validasi metadata tetap diperlukan sebelum menyimpulkan temuan.")
