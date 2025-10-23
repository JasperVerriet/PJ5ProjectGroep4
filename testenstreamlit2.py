import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from io import BytesIO
from matplotlib.backends.backend_pdf import PdfPages

from combined6 import report_missing_data, change_data, Overlap_Checker, Energy_Checker, plot_gantt_chart

st.set_page_config(layout="wide")

# status variabelen in session state
if "show_uploader" not in st.session_state:
    st.session_state.show_uploader = False
if "uploaded_file" not in st.session_state:
    st.session_state.uploaded_file = None
if "df" not in st.session_state:
    st.session_state.df = None
if "df_filled" not in st.session_state:
    st.session_state.df_filled = None
if "gantt_fig" not in st.session_state:
    st.session_state.gantt_fig = None
if "energy_output" not in st.session_state:
    st.session_state.energy_output = None
if "overlaps" not in st.session_state:
    st.session_state.overlaps = None

# boven knoppen
col1, col2, col3 = st.columns([1,1,1])
with col1:
    insert_clicked = st.button("plaats planning")
with col2:
    calc_clicked = st.button("bereken haalbaarheid planning")
with col3:
    save_clicked = st.button("sla planning op")

if insert_clicked:
    st.session_state.show_uploader = True

st.markdown("---")

# Hooft layout: Gantt chart en resultaten
main_col, result_col = st.columns([2,1])

with main_col:
    st.title("Bus Planning lines 400 and 401 for 1 day")
    if st.session_state.show_uploader:
        uploaded = st.file_uploader("Kies een Excel-bestand", type=["xlsx"], key="uploader")
        if uploaded is not None:
            st.session_state.uploaded_file = uploaded
            st.success("Bestand geüpload. Klik 'bereken haalbaarheid planning' om te verwerken.")

    # Als de gebruiker op berekenen heeft gedrukt of het bestand is al geüpload en calc_clicked, wordt de verwerking uitgevoerd
    if calc_clicked:
        if st.session_state.uploaded_file is None:
            st.error("Upload eerst een Excel-bestand met 'plaats planning'.")
        else:
            try:
                df = pd.read_excel(st.session_state.uploaded_file, engine="openpyxl")
                st.session_state.df = df
            except Exception as e:
                st.error(f"Fout bij inlezen bestand: {e}")
                st.session_state.df = None

            if st.session_state.df is not None:
                # laat eerste 5 rijen zien
                st.subheader("Eerste 5 rijen van je data:")
                st.dataframe(st.session_state.df.head())

                # missende data 
                st.subheader("Missende data per kolom:")
                try:
                    missing = report_missing_data(st.session_state.df)
                    # report_missing_data kan een Boolean DF of reeks retourneren; probeer een verstandige weergave
                    try:
                        st.write(missing.sum())
                    except Exception:
                        st.write(missing)
                except Exception as e:
                    st.error(f"Fout bij missende data: {e}")

                # verander data
                try:
                    df_filled = change_data(st.session_state.df)
                    st.session_state.df_filled = df_filled
                    st.subheader("Aangepaste data (eerste 5 rijen):")
                    st.dataframe(df_filled.head())
                except Exception as e:
                    st.error(f"Fout bij aanpassen data: {e}")
                    st.session_state.df_filled = None
                # --- EFFICIENTE METRICS (bereken één keer en sla op) ---
                if st.session_state.df_filled is not None:
                    # werk op een view (vermijd zware kopieën in grote datasets)
                    dfm = st.session_state.df_filled

                    # normaliseer kolomnaam voor energy (veilig maken, numeriek)
                    if "energy consumption" not in dfm.columns and "energy verbruik" in dfm.columns:
                        dfm["energy consumption"] = pd.to_numeric(dfm["energy verbruik"], errors="coerce").fillna(0.0)
                    else:
                        dfm["energy consumption"] = pd.to_numeric(dfm.get("energy consumption", 0.0), errors="coerce").fillna(0.0)

                    # vectorized durations (zorg dat end_shifted/start_shifted bestaan)
                    durations = (dfm["end_shifted"] - dfm["start_shifted"]).clip(lower=0).astype(float)

                    # idle tijd (vectorized)
                    activity_col = dfm.columns[dfm.columns.str.lower().isin(["activity", "activiteit"])]
                    if len(activity_col) > 0:
                        act = dfm[activity_col[0]]
                    else:
                        act = pd.Series([""]*len(dfm), index=dfm.index)

                    idle_mask = act.eq("idle")
                    idle_seconds = float(durations.loc[idle_mask].sum()) if idle_mask.any() else 0.0

                    # charging tijd (activity == 'charging' of negatieve energy)
                    charging_mask = act.eq("charging") | (dfm["energy consumption"] < 0)
                    charging_seconds = float(durations.loc[charging_mask].sum()) if charging_mask.any() else 0.0

                    # totaal energie (vectorized)
                    total_energy = float(dfm["energy consumption"].sum())

                    # bewaar in session_state (zodat onderkant alleen leest)
                    st.session_state.total_energy = total_energy
                    st.session_state.idle_seconds = int(idle_seconds)
                    st.session_state.charging_seconds = int(charging_seconds)
                # Gantt chart
                if st.session_state.df_filled is not None:
                    st.subheader("Gantt Chart:")
                    try:
                        fig = plot_gantt_chart(st.session_state.df_filled)
                        if fig is None:
                            fig = plt.gcf()
                        st.session_state.gantt_fig = fig
                        st.pyplot(fig)
                    except Exception as e:
                        st.error(f"Fout bij tekenen Gantt chart: {e}")
                        st.session_state.gantt_fig = None

                    # overlappingen en energiecontroles uitvoeren en uitvoer opslaan
                    try:
                        st.session_state.overlaps = Overlap_Checker(st.session_state.df_filled)
                    except Exception:
                        st.session_state.overlaps = None
                    try:
                        st.session_state.energy_output = Energy_Checker(st.session_state.df_filled)
                    except Exception:
                        st.session_state.energy_output = None

with result_col:
    st.markdown("""
    <div style="border:3px solid #FFD700; border-radius:12px; padding:12px; background-color:#FFFBEA;">
    <h4 style="margin-top:0;">Resultaten</h4>
    """, unsafe_allow_html=True)

    if st.session_state.df_filled is None:
        st.info("Nog geen verwerkte planning. Klik 'Insert planning' en daarna 'Calculate feasibility'.")
    else:
        # Overlap resultaat
        overlaps = st.session_state.overlaps
        if overlaps:
            st.markdown("#### ❌ Overlappingen gevonden")
            for o in overlaps:
                st.write(o)
        else:
            st.success("✅ Er is geen overlap gevonden in de planning.")

        # Energy checker uitvoer
        energy_output = st.session_state.energy_output
        st.markdown("#### Energie-checker uitkomst:")
        if energy_output is None:
            st.info("Geen energie-uitvoer (of functie geeft None terug).")
        elif isinstance(energy_output, (list, tuple)):
            for line in energy_output:
                st.write(line)
        else:
            st.write(energy_output)

    st.markdown("</div>", unsafe_allow_html=True)

st.markdown("---")

# buttons onder (totale energy, stilstaan tijd, oplaad tijd)
sum_col1, sum_col2, sum_col3 = st.columns([1,1,1])
with sum_col1:
    if st.session_state.df_filled is not None:
        try:
            total_energy = st.session_state.df_filled.get("energy verbruik", pd.Series([0])).sum()
            st.markdown(f'<div style="background-color:#030600; border-radius:15px; padding:20px; text-align:center;">'
                        f'<b>Totale energy gebruikt:</b><br>{total_energy:.2f} kWh</div>', unsafe_allow_html=True)
        except Exception:
            st.markdown('<div style="background-color:#030600; border-radius:15px; padding:20px; text-align:center;">'
                        'Totale energy gebruikt:<br>N/A</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div style="background-color:#030600; border-radius:15px; padding:20px; text-align:center;">'
                    'Totale energy gebruikt:<br>—</div>', unsafe_allow_html=True)

with sum_col2:
    if st.session_state.df_filled is not None:
        try:
            idle_mask = st.session_state.df_filled.get("activiteit", pd.Series()).eq("idle")
            if idle_mask.any():
                idle_seconds = (st.session_state.df_filled.loc[idle_mask, "end_shifted"] - st.session_state.df_filled.loc[idle_mask, "start_shifted"]).sum()
                h = int(idle_seconds // 3600)
                m = int((idle_seconds % 3600) // 60)
                st.markdown(f'<div style="background-color:#030600; border-radius:15px; padding:20px; text-align:center;">'
                            f'<b>stilstaan tijd:</b><br>{h}H : {m}M</div>', unsafe_allow_html=True)
            else:
                st.markdown('<div style="background-color:#030600; border-radius:15px; padding:20px; text-align:center;">'
                            'stilstaan tijd:<br>0 H : 0 M</div>', unsafe_allow_html=True)
        except Exception:
            st.markdown('<div style="background-color:#030600; border-radius:15px; padding:20px; text-align:center;">'
                        'stilstaan tijd:<br>N/A</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div style="background-color:#030600; border-radius:15px; padding:20px; text-align:center;">'
                    'stilstaan tijd:<br>—</div>', unsafe_allow_html=True)

with sum_col3:
    if st.session_state.df_filled is not None:
        try:
            charging_mask = (st.session_state.df_filled.get("activiteit", pd.Series()) == "charging") | (st.session_state.df_filled.get("energy consumption", pd.Series()) < 0)
            if charging_mask.any():
                charging_seconds = (st.session_state.df_filled.loc[charging_mask, "end_shifted"] - st.session_state.df_filled.loc[charging_mask, "start_shifted"]).sum()
                h = int(charging_seconds // 3600)
                m = int((charging_seconds % 3600) // 60)
                st.markdown(f'<div style="background-color:#030600; border-radius:15px; padding:20px; text-align:center;">'
                            f'<b>oplaad tijd:</b><br>{h}H : {m}M</div>', unsafe_allow_html=True)
            else:
                st.markdown('<div style="background-color:#030600; border-radius:15px; padding:20px; text-align:center;">'
                            'oplaad tijd:<br>0 H : 0 M</div>', unsafe_allow_html=True)
        except Exception:
            st.markdown('<div style="background-color:#030600; border-radius:15px; padding:20px; text-align:center;">'
                        'oplaad tijd:<br>N/A</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div style="background-color:#030600; border-radius:15px; padding:20px; text-align:center;">'
                    'oplaad tijd:<br>—</div>', unsafe_allow_html=True)

# planning opslaan: maak een PDF en bied een download aan
if save_clicked:
    if st.session_state.df_filled is None or st.session_state.gantt_fig is None:
        st.error("Geen verwerkte planning om op te slaan. Run 'bereken haalbaarheid planning' eerst.")
    else:
        buf = BytesIO()
        try:
            with PdfPages(buf) as pdf:
                # eerste pagina: gantt figuur
                pdf.savefig(st.session_state.gantt_fig)
                plt.close(st.session_state.gantt_fig)
                # tweede pagina: eenvoudige tekstuele samenvatting als figuur
                fig2, ax2 = plt.subplots(figsize=(8.27, 11.69))  # A4n formaat
                ax2.axis("off")
                text_lines = []
                # overlap
                if st.session_state.overlaps:
                    text_lines.append("Overlappingen gevonden:")
                    for o in st.session_state.overlaps:
                        text_lines.append(str(o))
                else:
                    text_lines.append("Geen overlappingen gevonden.")
                # energy
                if st.session_state.energy_output:
                    text_lines.append("")
                    text_lines.append("Energie-checker uitkomst:")
                    if isinstance(st.session_state.energy_output, (list, tuple)):
                        text_lines.extend([str(x) for x in st.session_state.energy_output])
                    else:
                        text_lines.append(str(st.session_state.energy_output))
                # schrijf text
                ax2.text(0.01, 0.99, "\n".join(text_lines), va="top", wrap=True, fontsize=10)
                pdf.savefig(fig2)
                plt.close(fig2)
            buf.seek(0)
            st.success("Busplanning opgeslagen in PDF. Download hieronder:")
            st.download_button("Download BusPlanning.pdf", data=buf.getvalue(), file_name="BusPlanning.pdf", mime="application/pdf")
            # opstineel: sla het bestand ook lokaal op
            with open("BusPlanning.pdf", "wb") as f:
                f.write(buf.getvalue())
        except Exception as e:
            st.error(f"Fout bij opslaan PDF: {e}")