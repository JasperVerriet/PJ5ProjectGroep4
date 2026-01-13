import streamlit as st 
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from io import BytesIO
from matplotlib.backends.backend_pdf import PdfPages
import os

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
# Timetable uploader/state (required — always visible)
if "show_timetable_uploader" not in st.session_state:
    # Make the timetable uploader visible by default (timetable is required)
    st.session_state.show_timetable_uploader = True
if "timetable_file" not in st.session_state:
    st.session_state.timetable_file = None
if "timetable_output" not in st.session_state:
    st.session_state.timetable_output = None

# Top buttons
# Determine if a timetable has been loaded (in session state or as a local Timetable.xlsx file)
has_timetable = st.session_state.get("timetable_file") is not None or os.path.exists("Timetable.xlsx")
col1, col2, col3, col4 = st.columns([1,1,1,1])
with col1:
    insert_clicked = st.button("Insert planning")
with col2:
    timetable_clicked = st.button("Load timetable")
with col3:
    # Disable calculate until a timetable is present
    calc_clicked = st.button("Calculate feasibility", disabled=not has_timetable, key="calc_button")
    if not has_timetable:
        st.caption("Disabled — load timetable first using 'Load timetable'.")
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
        uploaded = st.file_uploader("Choose an Excel file", type=["xlsx"], key="uploader")
        if uploaded is not None:
            st.session_state.uploaded_file = uploaded
            import os
            has_timetable = st.session_state.get("timetable_file") is not None or os.path.exists("Timetable.xlsx")
            # Always confirm upload, but give a clear warning when the timetable is missing
            st.success("File uploaded.")
            if not has_timetable:
                st.warning("Timetable not found. Please load the timetable using 'Load timetable' before calculating feasibility.")
                # Small convenience - open the timetable uploader for the user
                if st.button("Open timetable uploader", key="open_timetable_from_upload"):
                    st.session_state.show_timetable_uploader = True
            else:
                st.info("if Timetable present — click 'Calculate feasibility' to process the uploaded schedule.")

    # Timetable uploader (required — always visible)
    if st.session_state.show_timetable_uploader:
        timetable_up = st.file_uploader("Choose Timetable.xlsx (required)", type=["xlsx"], key="timetable_uploader")

        # Show current timetable status
        has_timetable_local = st.session_state.get("timetable_file") is not None or os.path.exists("Timetable.xlsx")
        if has_timetable_local:
            st.info("Timetable is required to calculate feasibility — please upload it below.")
        else:
            st.warning("Timetable is required to calculate feasibility — please upload it below.")

        if timetable_up is not None:
            st.session_state.timetable_file = timetable_up
            try:
                with open("Timetable.xlsx", "wb") as f:
                    f.write(timetable_up.getvalue())
                st.success("Timetable uploaded and saved as 'Timetable.xlsx'.")
                if st.session_state.get("uploaded_file") is not None:
                    st.success("Timetable loaded. Click 'Calculate feasibility' to process the uploaded schedule.")
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
        import os
        has_timetable = st.session_state.get("timetable_file") is not None or os.path.exists("Timetable.xlsx")
        if st.session_state.uploaded_file is None:
            st.error("Upload an Excel file first using 'Insert planning'.")
        elif not has_timetable:
            st.error("Please load the timetable first using 'Load timetable' before calculating feasibility.")
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

                        # Bar plot: energy consumption per bus (share of total)
                        try:
                            df_energy = st.session_state.df_filled
                            if 'energy consumption' in df_energy.columns:
                                cons = df_energy[df_energy['energy consumption'] > 0].groupby('bus')['energy consumption'].sum()
                            else:
                                cons = pd.Series(dtype=float)

                            if cons.empty:
                                st.info("No positive energy consumption data available to plot per-bus usage.")
                            else:
                                total = cons.sum()
                                perc = (cons / total) * 100
                                cons_df = pd.DataFrame({'kWh': cons, 'percentage': perc}).sort_values('kWh', ascending=False)

                                # Size: expand width based on number of buses for spacing, make height smaller
                                fig2_width = max(6, len(cons_df) * 0.6)
                                fig2_height = 2.2
                                fig2, ax2 = plt.subplots(figsize=(fig2_width, fig2_height))

                                # Use sequential numeric x-axis labels (1,2,3,...) and map them to actual bus IDs in a caption
                                positions = np.arange(1, len(cons_df) + 1)
                                bars = ax2.bar(positions, cons_df['kWh'], width=0.6, color='tab:blue')
                                ax2.set_ylabel('Energy consumption (kWh)')
                                ax2.set_xlabel('Bus (number)')
                                ax2.set_title('Energy consumption per bus (share of total)')
                                ax2.set_xticks(positions)
                                ax2.set_xticklabels(positions)
                                ax2.grid(axis='y', linestyle='--', alpha=0.5)

                                for pos, height, pct in zip(positions, cons_df['kWh'], cons_df['percentage']):
                                    ax2.text(pos, height * 1.01, f'{pct:.1f}%', ha='center', va='bottom', fontsize=9)

                                plt.tight_layout()
                                st.pyplot(fig2)
                        except Exception as e:
                            st.error(f"Error plotting per-bus energy: {e}")
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
    st.header("Results")

    if st.session_state.df_filled is None:
        st.info("No processed schedule yet. Click 'Insert schedule' and then 'Load timetable' and then 'Calculate feasibility'.")
    else:
        # Overlap result
        overlaps = st.session_state.overlaps
        if overlaps:
            st.markdown("#### ❌ Overlap found")
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
            st.info("No energy check.")

        # Timetable comparison output (if available)
        timetable_out = st.session_state.get("timetable_output", None)
        if timetable_out:
            # Determine if timetable comparison was successful based on printed message
            if "corresponds to the timetable" in timetable_out.lower():
                st.success("✅ Timetable comparison: schedule matches the timetable.")
                # still show the (short) output for context
                st.text(timetable_out)
            else:
                st.markdown("#### ❌ Timetable comparison: mismatches found")
                st.text(timetable_out)

   

st.markdown("---")

# Buttons below (Buses used, total energy, idle time, charging time)
sum_col1, sum_col2, sum_col3, sum_col4 = st.columns([1,1,1,1])
box_style = 'background-color:#F0F2F6; color:#111; border-radius:15px; padding:20px; text-align:center; font-weight:600; border:1px solid #ddd;'

# Compute energy KPIs using the same logic as in combined8 -> ensures KPI numbers match Results
def compute_energy_kpis(df):
    charge_per_hour = 450
    total_energy_used = 0.0
    charging_energy = 0.0
    total_charge_time = 0.0
    total_idle_time = 0.0
    try:
        dfc = df.copy()
        for _, row in dfc.iterrows():
            ec = float(row.get('energy consumption', 0.0) or 0.0)
            if ec > 0:
                total_energy_used += ec
            else:
                charging_energy += -ec
                total_charge_time += (-ec) / charge_per_hour
            if row.get('activity', '') == 'idle':
                total_idle_time += (row['end_seconds'] - row['start_seconds']) / 3600
    except Exception:
        pass
    return total_energy_used, charging_energy, total_charge_time, total_idle_time

with sum_col1:
    if st.session_state.df_filled is not None:
        try:
            try:
                buses_used = int(st.session_state.df_filled["bus"].nunique())
            except Exception:
                buses_used = len(st.session_state.df_filled["bus"].unique())

            st.markdown(f'<div style="{box_style}"><b>Buses used:</b><br>{buses_used}</div>', unsafe_allow_html=True)
        except Exception:
            st.markdown(f'<div style="{box_style}">Buses used:<br>N/A</div>', unsafe_allow_html=True)
    else:
        st.markdown(f'<div style="{box_style}">Buses used:<br>—</div>', unsafe_allow_html=True)

with sum_col2:
    if st.session_state.df_filled is not None:
        try:
            te, ce, ctime, itime = compute_energy_kpis(st.session_state.df_filled)
            st.markdown(f'<div style="{box_style}"><b>Total energy used:</b><br>{te:.2f} kWh<br><b>Charging energy:</b><br>{ce:.2f} kWh</div>', unsafe_allow_html=True)
        except Exception:
            st.markdown(f'<div style="{box_style}">Total energy used:<br>N/A</div>', unsafe_allow_html=True)
    else:
        st.markdown(f'<div style="{box_style}">Total energy used:<br>—</div>', unsafe_allow_html=True)

with sum_col3:
    if st.session_state.df_filled is not None:
        try:
            te, ce, ctime, itime = compute_energy_kpis(st.session_state.df_filled)
            h = int(itime)
            m = int(round((itime - h) * 60))
            st.markdown(f'<div style="{box_style}"><b>Idle time:</b><br>{h}H : {m}M</div>', unsafe_allow_html=True)
        except Exception:
            st.markdown(f'<div style="{box_style}">Idle time:<br>N/A</div>', unsafe_allow_html=True)
    else:
        st.markdown(f'<div style="{box_style}">Idle time:<br>—</div>', unsafe_allow_html=True)

with sum_col4:
    if st.session_state.df_filled is not None:
        try:
            te, ce, ctime, itime = compute_energy_kpis(st.session_state.df_filled)
            h = int(ctime)
            m = int(round((ctime - h) * 60))
            st.markdown(f'<div style="{box_style}"><b>Charging time:</b><br>{h}H : {m}M</div>', unsafe_allow_html=True)
        except Exception:
            st.markdown(f'<div style="{box_style}">Charging time:<br>N/A</div>', unsafe_allow_html=True)
    else:
        st.markdown(f'<div style="{box_style}">Charging time:<br>—</div>', unsafe_allow_html=True)

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
                    text_lines.append("Energy-checker result:")
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

