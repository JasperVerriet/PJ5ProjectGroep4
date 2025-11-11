import pandas as pd
import numpy as np
import matplotlib.pyplot as plt


# 1. DATA COLLECTION
def Data_Collection():
    file_path = input("Put your Excel file in here: ")
    df = pd.read_excel(file_path, engine='openpyxl')
    return df



# 2. MISSING DATA CHECK
def report_missing_data(df):
    copy = df.copy()
    if "line" in copy.columns:
        copy = copy.drop("line", axis=1)
    missing_data = copy.isnull()

    for i in range(len(copy)):
        if missing_data.iloc[i, :].any():
            print(f"Missing data in row {i + 2}")
    return missing_data



# 3. DATA CLEANING + IDLE INSERTION
def change_data(df):
    def read_and_change_data(df):
        datum = "31-10-2025"
        df["start time"] = pd.to_datetime(datum + " " + df["start time"], format="%d-%m-%Y %H:%M:%S")
        df["end time"] = pd.to_datetime(datum + " " + df["end time"], format="%d-%m-%Y %H:%M:%S")
        # If end time is before start time, add one day to end time
        mask = df["end time"] < df["start time"]
        df.loc[mask, "end time"] += pd.Timedelta(days=1)
        # Calculate seconds since planning day midnight for both start and end
        planning_midnight = pd.to_datetime(datum + " 00:00:00", format="%d-%m-%Y %H:%M:%S")
        df["start_seconds"] = (df["start time"] - planning_midnight).dt.total_seconds()
        df["end_seconds"] = (df["end time"] - planning_midnight).dt.total_seconds()
        return df

    def replace_empty_gaps_with_idle(df):
        df1 = df[df['start time'] != df['end time']]
        filled_rows = []

        for bus, bus_df in df1.groupby("bus"):
            bus_df = bus_df.sort_values("start_seconds").reset_index(drop=True)
            prev_end = None
            for _, row in bus_df.iterrows():
                current_start = row["start_seconds"]
                current_end = row["end_seconds"]

                if prev_end is not None and current_start > prev_end:
                    filled_rows.append({
                        "bus": bus,
                        "start_seconds": prev_end,
                        "end_seconds": current_start,
                        "activity": "idle",
                        "energy consumption": ((current_start - prev_end) / 3600) * 5,
                        "start location": "ehvbst",
                        "end location": "ehvbst"
                    })
                filled_rows.append(row.to_dict())
                prev_end = current_end

        df_filled = pd.DataFrame(filled_rows)
        df_filled = df_filled[df_filled["end_seconds"] > df_filled["start_seconds"]]
        return df_filled

    df = read_and_change_data(df)
    df_filled = replace_empty_gaps_with_idle(df)
    return df_filled



# 4. INSERT CHARGING PERIODS TO MAKE PLAN FEASIBLE
def make_feasible_busplan(df_filled):
    battery_capacity = 255
    min_level = 0.1 * battery_capacity
    max_level = 0.9 * battery_capacity
    charge_rate = 450  # kWh per hour
    idle_consumption = 5  # kW
    min_charge_minutes = 15

    all_rows = []

    for bus, bus_df in df_filled.groupby("bus"):
        bus_df = bus_df.sort_values("start_seconds").reset_index(drop=True)
        prev_end = None
        battery = max_level

        for i, row in bus_df.iterrows():
            start_s, end_s = row["start_seconds"], row["end_seconds"]
            energy_needed = row.get("energy consumption", 0)

            if prev_end and start_s > prev_end:
                idle_dur = start_s - prev_end
                idle_energy = (idle_dur / 3600) * idle_consumption
                all_rows.append({
                    "bus": bus,
                    "activity": "idle",
                    "start_seconds": prev_end,
                    "end_seconds": start_s,
                    "energy consumption": idle_energy,
                    "start location": "ehvbst",
                    "end location": "ehvbst"
                })
                battery -= idle_energy

            if battery - energy_needed < min_level:
                charge_needed = max_level - battery
                charge_time_hr = charge_needed / charge_rate   # hours
                charge_time_min = max(charge_time_hr * 60, min_charge_minutes)  # in minutes

                # Determine start and end times in minutes
                charge_start_min = prev_end / 60 if prev_end else start_s / 60 - charge_time_min
                charge_end_min = charge_start_min + charge_time_min

                all_rows.append({
                    "bus": bus,
                    "activity": "charging",
                    "start_seconds": prev_end,
                    "end_seconds": start_s,
                    "energy consumption": -(charge_time_min / 60) * charge_rate,  # convert min to hr for energy
                    "start location": "ehvgar",
                    "end location": "ehvgar"
                })

                battery = max_level
                prev_end = charge_end_min * 60  # keep prev_end in seconds if used elsewhere


            row_dict = row.to_dict()
            all_rows.append(row_dict)
            battery -= energy_needed
            prev_end = end_s

    df_new = pd.DataFrame(all_rows)
    df_new["start time"] = pd.to_datetime("00:00:00") + pd.to_timedelta(df_new["start_seconds"], unit='s')
    df_new["end time"] = pd.to_datetime("00:00:00") + pd.to_timedelta(df_new["end_seconds"], unit='s')
    df_new["start time"] = df_new["start time"].dt.strftime("%H:%M:%S")
    df_new["end time"] = df_new["end time"].dt.strftime("%H:%M:%S")
    return df_new

def remove_overlaps(df):
    df_sorted = df.sort_values(['bus', 'start_seconds']).reset_index(drop=True)
    cleaned_rows = []
    for bus, group in df_sorted.groupby('bus'):
        prev_end = None
        for idx, row in group.iterrows():
            start = row['start_seconds']
            end = row['end_seconds']
            # If overlap, shift start to prev_end
            if prev_end is not None and start < prev_end:
                duration = end - start
                start = prev_end
                end = start + duration
            cleaned_row = row.copy()
            cleaned_row['start_seconds'] = start
            cleaned_row['end_seconds'] = end
            cleaned_rows.append(cleaned_row)
            prev_end = end
    df_cleaned = pd.DataFrame(cleaned_rows)
    # Recalculate start/end time columns
    df_cleaned["start time"] = pd.to_datetime("00:00:00") + pd.to_timedelta(df_cleaned["start_seconds"], unit='s')
    df_cleaned["end time"] = pd.to_datetime("00:00:00") + pd.to_timedelta(df_cleaned["end_seconds"], unit='s')
    df_cleaned["start time"] = df_cleaned["start time"].dt.strftime("%H:%M:%S")
    df_cleaned["end time"] = df_cleaned["end time"].dt.strftime("%H:%M:%S")
    return df_cleaned


# 5. ENERGY CHECK
def Energy_Checker(df):
    soh = 255
    min_battery_level = 0.1 * soh
    max_battery_level = 0.9 * soh
    messages = []

    for bus, group in df.groupby("bus"):
        battery = max_battery_level
        feasible = True
        for _, row in group.iterrows():
            consumption = row.get("energy consumption", 0)
            if battery - consumption < min_battery_level:
                messages.append(f"Bus {bus}: Infeasible (battery < 10%)")
                feasible = False
                break
            battery -= consumption
        if feasible:
            messages.append(f"Bus {bus}: Feasible ✅")
    return messages



# 6. GANTT CHART
def plot_gantt_chart(df):
    activities = df["activity"].unique()
    colours = plt.cm.tab20.colors
    colour_per_activity = {a: colours[i % len(colours)] for i, a in enumerate(activities)}

    fig, ax = plt.subplots(figsize=(12, 5))
    for _, row in df.iterrows():
        ax.barh(
            row["bus"],
            left=row["start_seconds"],
            width=row["end_seconds"] - row["start_seconds"],
            color=colour_per_activity[row["activity"]],
            edgecolor="black",
            alpha=0.7,
        )

    patches = [plt.Rectangle((0, 0), 1, 1, fc=colour_per_activity[a]) for a in activities]
    ax.legend(patches, activities, loc="upper right")

    plt.xlabel("Seconds of the day")
    plt.ylabel("Bus number")
    plt.title("Feasible Bus Plan Gantt Chart")
    plt.tight_layout()
    plt.savefig("Feasible_BusPlan_Gantt.png")
    plt.show()


# 7. MAIN PIPELINE
def main():
    df = Data_Collection()
    report_missing_data(df)
    df_filled = change_data(df)
    df_feasible = make_feasible_busplan(df_filled)
    df_no_overlap = remove_overlaps(df_feasible)  # <-- Add this line
    df_no_overlap.to_excel("BusPlanning_feasible.xlsx", index=False)
    print("\nFeasible bus plan saved as 'BusPlanning_feasible.xlsx'")
    print("\nEnergy check results:")
    for msg in Energy_Checker(df_no_overlap):
        print(msg)
    plot_gantt_chart(df_no_overlap)


if __name__ == "__main__":
    main()