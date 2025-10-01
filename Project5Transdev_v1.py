# Jaap
import pandas as pd
import numpy as np

# Here is the function that loads the Excel file and returns the DataFrame
def Data_Collection():
    file_path = input("Put your Excel file in here:")
    df = pd.read_excel(file_path)
    return df

# Here is the function that reports missing data in the DataFrame
def report_missing_data(df):
    missing_data = df.isnull()
    print("Missing data report:")
    return missing_data

df = Data_Collection()
report_missing_data(df)

