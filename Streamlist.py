import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from combined4 import report_missing_data, change_data, Overlap_Checker, Energy_Checker, plot_gantt_chart

st.title('Hallo Bus Planner ')

name = st.text_input('Wat is je naam?')
if name:
    st.success(f'Welkom {name}! Klaar om timetables te controleren?')


st.title('Bus Planner Checker')

uploaded = st.file_uploader("Kies een Excel-bestand", type=["xlsx"])
if uploaded:
    df = pd.read_excel(uploaded, engine='openpyxl')
    st.subheader("Eerste 5 rijen van je data:")
    st.dataframe(df.head())

    st.subheader("Missende data per kolom:")
    missing = report_missing_data(df)
    st.write(missing.isnull().sum())  # Of toon je eigen output

    df_filled = change_data(df)
    st.subheader("Aangepaste data (eerste 5 rijen):")
    st.dataframe(df_filled.head())

    # Overlap checker
    overlaps = Overlap_Checker(df_filled)
    if overlaps:
        st.subheader("Overlappingen gevonden:")
        for o in overlaps:
            st.write(o)
        else:
            st.success("Geen overlappingen gevonden!")

     # Overlap checker
    overlaps = Overlap_Checker(df_filled)
    st.subheader("Overlappingen gevonden:")
    if overlaps:
        for o in overlaps:
            st.write(o)
    else:
        st.success("Geen overlappingen gevonden!")

    # Energy checker
    st.subheader("Energie-checker output:")
    # Pas Energy_Checker aan zodat hij tekst returned in plaats van print
    # Bijvoorbeeld:
    # result = Energy_Checker(df_filled)
    # st.write(result)

    # Gantt chart
    st.subheader("Gantt Chart:")
    fig = plot_gantt_chart(df_filled)
    st.pyplot(fig)