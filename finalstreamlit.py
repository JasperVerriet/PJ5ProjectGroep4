import streamlit as st 
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from io import BytesIO
from matplotlib.backends.backend_pdf import PdfPages

from combined8 import report_missing_data, change_data, Overlap_Checker, Energy_Checker, plot_gantt_chart, Timetable_comparison

# Streamlit page settings
st.set_page_config(layout="wide")

# Status variabelse in session state
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
# Timetable uploader/state
if "show_timetable_uploader" not in st.session_state:
    st.session_state.show_timetable_uploader = False
if "timetable_file" not in st.session_state:
    st.session_state.timetable_file = None
if "timetable_output" not in st.session_state:
    st.session_state.timetable_output = None

# Top buttons
col1, col2, col3, col4 = st.columns([1,1,1,1])
with col1:
    insert_clicked = st.button("Insert planning")
with col2:
    timetable_clicked = st.button("Load timetable")
with col3:
    calc_clicked = st.button("Calculate feasibility")
with col4:
    save_clicked = st.button("Save planning")

if timetable_clicked:
    st.session_state.show_timetable_uploader = True

if insert_clicked:
    st.session_state.show_uploader = True

st.markdown("---")

# Main layout for streamlit: Gantt chart and results
main_col, result_col = st.columns([2,1])

with main_col:
    st.title("Bus Planning lines 400 and 401 for 1 day")
    if st.session_state.show_uploader:
        uploaded = st.file_uploader("choice an Excel-file", type=["xlsx"], key="uploader")
        if uploaded is not None:
            st.session_state.uploaded_file = uploaded
            st.success("file geüploaded. click 'Calculate feasibility' to proces.")

    # Timetable uploader (optional)
    if st.session_state.show_timetable_uploader:
        timetable_up = st.file_uploader("Choose Timetable.xlsx", type=["xlsx"], key="timetable_uploader")
        if timetable_up is not None:
            st.session_state.timetable_file = timetable_up
            try:
                with open("Timetable.xlsx", "wb") as f:
                    f.write(timetable_up.getvalue())
                st.success("Timetable uploaded and saved as 'Timetable.xlsx'.")
            except Exception as e:
                st.error(f"Error saving timetable: {e}")

            # Run comparison immediately if a processed schedule exists
            if st.session_state.df_filled is not None:
                try:
                    import io, sys
                    buf = io.StringIO()
                    old_stdout = sys.stdout
                    sys.stdout = buf
                    try:
                        Timetable_comparison(st.session_state.df_filled)
                    finally:
                        sys.stdout = old_stdout
                    st.session_state.timetable_output = buf.getvalue()
                    st.success("Timetable comparison completed.")
                except Exception as e:
                    st.error(f"Error running timetable comparison: {e}")
                    st.session_state.timetable_output = None

    # If the user has pressed calculate or the file has already been uploaded and calc_clicked. The processing will be done
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
                # Chows first 5 rows data
                st.subheader("First 5 rows of your data:")
                st.dataframe(st.session_state.df.head())

                # Chows missing data per column
                st.subheader("Missing data per column:")
                try:
                    missing = report_missing_data(st.session_state.df)
                    # Chows if you report_missing_data 
                    try:
                        st.write(missing.sum())
                    except Exception:
                        st.write(missing)
                except Exception as e:
                    st.error(f"Error missing data: {e}")

                # Change data to fit the model
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

                    # Perform overlaps and energy checks and save the output
                    try:
                        st.session_state.overlaps = Overlap_Checker(st.session_state.df_filled)
                    except Exception:
                        st.session_state.overlaps = None
                    try:
                        st.session_state.energy_output = Energy_Checker(st.session_state.df_filled)
                    except Exception:
                        st.session_state.energy_output = None
                    energy_output = st.session_state.get("energy_output", None)

                    # Run timetable comparison automatically if a timetable has been uploaded or exists locally
                    try:
                        import os, io, sys
                        if st.session_state.get("timetable_file") is not None or os.path.exists("Timetable.xlsx"):
                            buf = io.StringIO()
                            old_stdout = sys.stdout
                            sys.stdout = buf
                            try:
                                Timetable_comparison(st.session_state.df_filled)
                            finally:
                                sys.stdout = old_stdout
                            st.session_state.timetable_output = buf.getvalue()
                    except Exception:
                        st.session_state.timetable_output = None
        
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
        # Energy result per bus (if available) — show per-bus status with icons
        energy_output = st.session_state.get("energy_output", None)
        if energy_output:
            st.markdown("#### Energy result per bus")
            try:
                # Normalize into a list of strings
                if isinstance(energy_output, dict):
                    lines = [f"Bus {k}: {v}" for k, v in energy_output.items()]
                elif isinstance(energy_output, (list, tuple, pd.Series)):
                    lines = [str(x) for x in energy_output]
                else:
                    try:
                        lines = [str(x) for x in energy_output]
                    except Exception:
                        lines = [str(energy_output)]

                import re
                bus_status = {}
                other_lines = []
                for s in lines:
                    # Try to detect "feasible" messages like "Bus plan for Bus 1 is feasible..."
                    m1 = re.search(r"Bus plan for Bus\s*(\d+)\D.*feasible", s, flags=re.IGNORECASE)
                    # Try to detect messages like "Bus 1: ..."
                    m2 = re.search(r"Bus\s*(\d+):", s)
                    if m1:
                        bid = int(m1.group(1))
                        bus_status[bid] = (True, s)
                    elif m2:
                        bid = int(m2.group(1))
                        # If already recorded as feasible, only overwrite if this message indicates an issue
                        is_issue = bool(re.search(r"infeasible|will drop|below", s, flags=re.IGNORECASE))
                        if bid in bus_status:
                            if is_issue:
                                bus_status[bid] = (False, s)
                        else:
                            bus_status[bid] = (not is_issue, s)
                    else:
                        other_lines.append(s)

                if bus_status:
                    overall_ok = all(status for status, _ in bus_status.values())
                    if overall_ok:
                        st.success("✅ All buses are feasible.")
                    else:
                        st.markdown("#### ❌ Energy issues found")

                    for bid in sorted(bus_status):
                        status, msg = bus_status[bid]
                        if status:
                            st.markdown(f"**✅ Bus {bid}:** {msg}")
                        else:
                            st.markdown(f"**❌ Bus {bid}:** {msg}")

                # Show any extra lines that couldn't be parsed per-bus
                for l in other_lines:
                    st.write(l)

            except Exception as e:
                st.error("Error displaying energy results: " + str(e))
        else:
            st.info("No energie-check.")

        # Timetable comparison output (if available)
        timetable_out = st.session_state.get("timetable_output", None)
        if timetable_out:
            st.markdown("#### Timetable comparison result")
            st.text(timetable_out)

    st.markdown("</div>", unsafe_allow_html=True)

st.markdown("---")

# Buttons below (total energy, idle time, charging time, busses used)
sum_col1, sum_col2, sum_col3, sum_col4 = st.columns([1,1,1,1])
with sum_col1:
    if st.session_state.df_filled is not None:
        try:
            # Netto energie (positief rijden + negatief laden)
            total_energy = st.session_state.df_filled.get("energy consumption", pd.Series([0])).sum()

            # 1 extra: laadenergie apart, positief weergegeven
            charging_energy = -st.session_state.df_filled.loc[
                st.session_state.df_filled["energy consumption"] < 0,
                "energy consumption"
            ].sum()

            st.markdown(
                f'<div style="background-color:#030600; border-radius:15px; padding:20px; text-align:center;">'
                f'<b>Charging energy:</b><br>{charging_energy:.2f} kWh</div>',
                unsafe_allow_html=True
            )
        except Exception:
            st.markdown(
                '<div style="background-color:#030600; border-radius:15px; padding:20px; text-align:center;">'
                'Total energy used:<br>N/A</div>',
                unsafe_allow_html=True
            )
    else:
        st.markdown(
            '<div style="background-color:#030600; border-radius:15px; padding:20px; text-align:center;">'
            'Total energy used:<br>—</div>',
            unsafe_allow_html=True
        )

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

with sum_col4:
    if st.session_state.df_filled is not None:
        try:
            # Count unique buses used in the Gantt chart
            try:
                buses_used = int(st.session_state.df_filled["bus"].nunique())
            except Exception:
                buses_used = len(st.session_state.df_filled["bus"].unique())

            st.markdown(f'<div style="background-color:#030600; border-radius:15px; padding:20px; text-align:center;">'
                        f'<b>Busses used:</b><br>{buses_used}</div>', unsafe_allow_html=True)
        except Exception:
            st.markdown('<div style="background-color:#030600; border-radius:15px; padding:20px; text-align:center;">'
                        'Busses used:<br>N/A</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div style="background-color:#030600; border-radius:15px; padding:20px; text-align:center;">'
                    'Busses used:<br>—</div>', unsafe_allow_html=True)

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
                # Energy
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

