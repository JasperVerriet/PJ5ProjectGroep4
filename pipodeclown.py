import pandas as pd
import numpy as np

def Data_Collection():
    file_path = input("Put your Excel file in here:")
    df = pd.read_excel(file_path)
    return df

def report_missing_data(df):
    copy = df.copy()
    copy = copy.drop("line", axis=1)
    missing_data = copy.isnull()
    for i in range(len(copy)):
        if missing_data.iloc[i,:].any():
            print(f'missing data in row {i+2}')
    return missing_data

def Overlap_Checker(df):
    # ...jouw bestaande code...
    pass  # Vul hier je Overlap_Checker code in

def Energy_Checker(df):   
    # ...jouw bestaande code.
     pass  # Vul hier je Energy_Checker code in

def main():
    df = Data_Collection()
    report_missing_data(df)
    Overlap_Checker(df)
    Energy_Checker(df)

if __name__ == "__main__":
    main()