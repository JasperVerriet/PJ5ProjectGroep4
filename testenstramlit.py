import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from combined4 import report_missing_data, change_data, Overlap_Checker, Energy_Checker, plot_gantt_chart

st.set_page_config(layout="wide")

# Top buttons
col1, col2, col3 = st.columns([1,1,1])
with col1:
    st.button("Insert planning", type="primary")
with col2:
    st.button("Calculate feasibility", type="primary")
with col3:
    st.button("Save planning", type="primary")

st.markdown("---")

# Main layout: Gantt chart and results
main_col, result_col = st.columns([2,1])

with main_col:
    st.title("Bus Planning lines 400 and 401 for 1 day")
    uploaded = st.file_uploader("Kies een Excel-bestand", type=["xlsx"])
    if uploaded:
        df = pd.read_excel(uploaded, engine='openpyxl')
        df_filled = change_data(df)
        fig = plot_gantt_chart(df_filled)
        st.pyplot(fig)

with result_col:
    st.markdown("""
    <div style="border:3px solid #FFD700; border-radius:25px; padding:20px; background-color:#FFFBEA;">
    <ul style="font-size:18px;">
    <li>✅ All necessary data is present</li>
    <li>✅ There are no overlaps in the current planning.</li>
    <li style="color:red;">❌ Bus 1: Battery level will drop below 10% during route 67. Route is infeasible.</li>
    <li>Bus 2: Battery level will drop below 10% during route 147. Route is infeasible.</li>
    <li>✅ All other buses are feasible</li>
    </ul>
    </div>
    """, unsafe_allow_html=True)

st.markdown("---")

# Bottom summary
sum_col1, sum_col2, sum_col3 = st.columns([1,1,1])
with sum_col1:
    st.markdown('<div style="background-color:#D6FFB7; border-radius:15px; padding:20px; text-align:center;">'
                '<b>Total energy used:</b><br>4161,85 kW</div>', unsafe_allow_html=True)
with sum_col2:
    st.markdown('<div style="background-color:#D6FFB7; border-radius:15px; padding:20px; text-align:center;">'
                '<b>Time spent idle:</b><br>x H : x M</div>', unsafe_allow_html=True)
with sum_col3:
    st.markdown('<div style="background-color:#D6FFB7; border-radius:15px; padding:20px; text-align:center;">'
                '<b>Time spent charging:</b><br>x H : x M</div>', unsafe_allow_html=True)