import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from io import BytesIO
from matplotlib.backends.backend_pdf import PdfPages

from combined7 import report_missing_data, change_data, Overlap_Checker, Energy_Checker, plot_gantt_chart

st.set_page_config(layout="wide")

# status variabelse in session state
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

# Top buttons
col1, col2, col3 = st.columns([1,1,1])
with col1:
    insert_clicked = st.button("Insert planning")
with col2:
    calc_clicked = st.button("Calculate feasibility")
with col3:
    save_clicked = st.button("Save planning")

if insert_clicked:
    st.session_state.show_uploader = True

st.markdown("---")

# Main layout: Gantt chart and results
main_col, result_col = st.columns([2,1])

with main_col:
    st.title("Bus Planning lines 400 and 401 for 1 day")
    if st.session_state.show_uploader:
        uploaded = st.file_uploader("choise an Excel-file", type=["xlsx"], key="uploader")
        if uploaded is not None:
            st.session_state.uploaded_file = uploaded
            st.success("file geüploaded. click 'Calculate feasibility' to proces.")

    # If the user has pressed calculate or the file has already been uploaded and calc_clicked, the processing will be performed
    if calc_clicked:
        if st.session_state.uploaded_file is None:
            st.error("Upload first an Excel-file with 'Insert planning'.")
        else:
            try:
                df = pd.read_excel(st.session_state.uploaded_file, engine="openpyxl")
                st.session_state.df = df
            except Exception as e:
                st.error(f"Error reading file: {e}")
                st.session_state.df = None

            if st.session_state.df is not None:
                # chows first 5 rows data
                st.subheader("First 5 rows of your data:")
                st.dataframe(st.session_state.df.head())

                # Missing data 
                st.subheader("Missing data per column:")
                try:
                    missing = report_missing_data(st.session_state.df)
                    # report_missing_data may return a Boolean DF or array; try a sensible representation
                    try:
                        st.write(missing.sum())
                    except Exception:
                        st.write(missing)
                except Exception as e:
                    st.error(f"Error missing data: {e}")

                # change data
                try:
                    df_filled = change_data(st.session_state.df)
                    st.session_state.df_filled = df_filled
                    st.subheader("Custom data (first 5 rows):")
                    st.dataframe(df_filled.head())
                except Exception as e:
                    st.error(f"Error while adjusting data: {e}")
                    st.session_state.df_filled = None

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
                        st.error(f"Error with drawing Gantt chart: {e}")
                        st.session_state.gantt_fig = None

                    # perform overlaps and energy checks and save output
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
        st.info("No processed schedule yet. Click 'Insert schedule' and then 'Calculate feasibility'.")
    else:
        # Overlap result
        overlaps = st.session_state.overlaps
        if overlaps:
            st.markdown("#### ❌ Overlappingen found")
            for o in overlaps:
                st.write(o)
        else:
            st.success("✅ No overlap was found in the planning.")

        # Energy checker result
        energy_output = st.session_state.energy_output
        st.markdown("#### Energie-checker result:")
        if energy_output is None:
            st.info("No energy output (or function returns None).")
        elif isinstance(energy_output, (list, tuple)):
            for line in energy_output:
                st.write(line)
        else:
            st.write(energy_output)

    st.markdown("</div>", unsafe_allow_html=True)

st.markdown("---")

# buttons below (total energy, idle time, charging time)
sum_col1, sum_col2, sum_col3 = st.columns([1,1,1])
with sum_col1:
    if st.session_state.df_filled is not None:
        try:
            total_energy = st.session_state.df_filled.get("energy consumption", pd.Series([0])).sum()
            st.markdown(f'<div style="background-color:#030600; border-radius:15px; padding:20px; text-align:center;">'
                        f'<b>Total energy used:</b><br>{total_energy:.2f} kWh</div>', unsafe_allow_html=True)
        except Exception:
            st.markdown('<div style="background-color:#030600; border-radius:15px; padding:20px; text-align:center;">'
                        'Total energy used:<br>N/A</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div style="background-color:#030600; border-radius:15px; padding:20px; text-align:center;">'
                    'Total energy used:<br>—</div>', unsafe_allow_html=True)

with sum_col2:
    if st.session_state.df_filled is not None:
        try:
            idle_mask = st.session_state.df_filled.get("activity", pd.Series()).eq("idle")
            if idle_mask.any():
                idle_seconds = (st.session_state.df_filled.loc[idle_mask, "end_shifted"] - st.session_state.df_filled.loc[idle_mask, "start_shifted"]).sum()
                h = int(idle_seconds // 3600)
                m = int((idle_seconds % 3600) // 60)
                st.markdown(f'<div style="background-color:#030600; border-radius:15px; padding:20px; text-align:center;">'
                            f'<b>Idle time:</b><br>{h}H : {m}M</div>', unsafe_allow_html=True)
            else:
                st.markdown('<div style="background-color:#030600; border-radius:15px; padding:20px; text-align:center;">'
                            'Idle time:<br>0 H : 0 M</div>', unsafe_allow_html=True)
        except Exception:
            st.markdown('<div style="background-color:#030600; border-radius:15px; padding:20px; text-align:center;">'
                        'Idle time:<br>N/A</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div style="background-color:#030600; border-radius:15px; padding:20px; text-align:center;">'
                    'Idle time:<br>—</div>', unsafe_allow_html=True)

with sum_col3:
    if st.session_state.df_filled is not None:
        try:
            charging_mask = (st.session_state.df_filled.get("activity", pd.Series()) == "charging") | (st.session_state.df_filled.get("energy consumption", pd.Series()) < 0)
            if charging_mask.any():
                charging_seconds = (st.session_state.df_filled.loc[charging_mask, "end_shifted"] - st.session_state.df_filled.loc[charging_mask, "start_shifted"]).sum()
                h = int(charging_seconds // 3600)
                m = int((charging_seconds % 3600) // 60)
                st.markdown(f'<div style="background-color:#030600; border-radius:15px; padding:20px; text-align:center;">'
                            f'<b>Charging time:</b><br>{h}H : {m}M</div>', unsafe_allow_html=True)
            else:
                st.markdown('<div style="background-color:#030600; border-radius:15px; padding:20px; text-align:center;">'
                            'Charging time:<br>0 H : 0 M</div>', unsafe_allow_html=True)
        except Exception:
            st.markdown('<div style="background-color:#030600; border-radius:15px; padding:20px; text-align:center;">'
                        'Charging time:<br>N/A</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div style="background-color:#030600; border-radius:15px; padding:20px; text-align:center;">'
                    'Charging time:<br>—</div>', unsafe_allow_html=True)

# Save planning: create a PDF and offer a download
if save_clicked:
    if st.session_state.df_filled is None or st.session_state.gantt_fig is None:
        st.error("No processed schedule to save. Run 'Calculate schedule feasibility' first.")
    else:
        buf = BytesIO()
        try:
            with PdfPages(buf) as pdf:
                # First page: gantt chart
                pdf.savefig(st.session_state.gantt_fig)
                plt.close(st.session_state.gantt_fig)
                # Second page: overlaps and energy results
                fig2, ax2 = plt.subplots(figsize=(8.27, 11.69))  # A4 size
                ax2.axis("off")
                text_lines = []
                # Overlap
                if st.session_state.overlaps:
                    text_lines.append("Overlaps found:")
                    for o in st.session_state.overlaps:
                        text_lines.append(str(o))
                else:
                    text_lines.append("No overlaps found.")
                # energy
                if st.session_state.energy_output:
                    text_lines.append("")
                    text_lines.append("Energie-checker result:")
                    if isinstance(st.session_state.energy_output, (list, tuple)):
                        text_lines.extend([str(x) for x in st.session_state.energy_output])
                    else:
                        text_lines.append(str(st.session_state.energy_output))
                # write text to figure
                ax2.text(0.01, 0.99, "\n".join(text_lines), va="top", wrap=True, fontsize=10)
                pdf.savefig(fig2)
                plt.close(fig2)
            buf.seek(0)
            st.success("Bus schedule saved as a PDF. Download below:")
            st.download_button("Download BusPlanning.pdf", data=buf.getvalue(), file_name="BusPlanning.pdf", mime="application/pdf")
            # Also save to local file system
            with open("BusPlanning.pdf", "wb") as f:
                f.write(buf.getvalue())
        except Exception as e:
            st.error(f"Error saving PDF: {e}")