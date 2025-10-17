import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from combined4 import report_missing_data, change_data, Overlap_Checker, Energy_Checker, plot_gantt_chart

st.title('Hello Bus Planner ')

name = st.text_input('what is your name?')
if name:
    st.success(f'Welkom {name}! ready to check your bus planner?')


st.title('Bus Planner Checker')

uploaded = st.file_uploader("choose an Excel-bestand", type=["xlsx"])
if uploaded:
    df = pd.read_excel(uploaded, engine='openpyxl')
    st.subheader("First 5 rowes of the data:")
    st.dataframe(df.head())

    st.subheader("Missing data per column:")
    missing = report_missing_data(df)
    st.write(missing.isnull().sum())  # Or display the missing data report as needed

    df_filled = change_data(df)
    st.subheader("Custom data (first 5 rows):")
    st.dataframe(df_filled.head())

    # Overlap checker
    overlaps = Overlap_Checker(df_filled)
    if overlaps:
        st.subheader("Overlap found:")
        for o in overlaps:
            st.write(o)
        else:
            st.success("No overlaps found!")

    # Gantt chart
    st.subheader("Gantt Chart:")
    fig = plot_gantt_chart(df_filled)
    st.pyplot(fig)

    # Energy checker
    st.subheader("Energie-checker output:")
    energy_output = Energy_Checker(df_filled)
    for line in energy_output:
        st.write(line)