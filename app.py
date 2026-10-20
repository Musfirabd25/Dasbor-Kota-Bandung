            compare_data = filtered.copy()
            if year_col:
                latest = int(compare_data[year_col].max())
                compare_data = compare_data[compare_data[year_col] == latest]
                st.caption(f"Perbandingan memakai tahun terakhir yang tersedia pada filter: {latest}.")
            summary = compare_data.groupby(city_col, as_index=False)[compare_metric].mean().dropna()
            summary = summary.sort_values(compare_metric, ascending=False)

            if summary.empty:
                st.info("Tidak ada data wilayah yang bisa ditampilkan untuk indikator ini.")
            else:
                # Pastikan batas slider selalu valid, termasuk jika data kurang dari 5 wilayah.
                max_wilayah = min(30, len(summary))
                default_wilayah = min(15, max_wilayah)
                top_n = st.slider(
                    "Jumlah wilayah pada grafik",
                    min_value=1,
                    max_value=max_wilayah,
                    value=default_wilayah,
                    key="jumlah_wilayah_grafik",
                )
                chart_df = summary.head(top_n)
                fig = px.bar(
                    chart_df.sort_values(compare_metric),
                    x=compare_metric,
                    y=city_col,
                    orientation="h",
                    title=f"{display_label(compare_metric)} — peringkat tertinggi",
                    color=compare_metric,
                    color_continuous_scale="Blues",
                )
                st.plotly_chart(style_fig(fig, max(420, top_n * 25)), use_container_width=True)
                st.markdown("#### Tabel peringkat")
                ranked_summary = summary.copy()
                ranked_summary.insert(0, "Peringkat", range(1, len(ranked_summary) + 1))
                ranked_summary = ranked_summary.rename(
                    columns={city_col: "Wilayah", compare_metric: display_label(compare_metric)}
                )
                st.dataframe(ranked_summary, use_container_width=True, hide_index=True)
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
