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
        df["start_seconds"] = df["start time"].dt.hour * 3600 + df["start time"].dt.minute * 60 + df["start time"].dt.second
        df["end_seconds"] = df["end time"].dt.hour * 3600 + df["end time"].dt.minute * 60 + df["end time"].dt.second
        df.loc[df["end_seconds"] < df["start_seconds"], "end_seconds"] += 24 * 3600
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
                        "start location": "EHVBST",
                        "end location": "EHVBST"
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
                    "start location": "EHVBST",
                    "end location": "EHVBST"
                })
                battery -= idle_energy

            if battery - energy_needed < min_level:
                charge_needed = max_level - battery
                charge_time_hr = charge_needed / charge_rate
                charge_time_sec = max(charge_time_hr * 3600, min_charge_minutes * 60)
                charge_start = prev_end if prev_end else start_s - charge_time_sec
                charge_end = charge_start + charge_time_sec

                all_rows.append({
                    "bus": bus,
                    "activity": "charging",
                    "start_seconds": charge_start,
                    "end_seconds": charge_end,
                    "energy consumption": -(charge_time_sec / 3600) * charge_rate,
                    "start location": "EHVGAR",
                    "end location": "EHVGAR"
                })
                battery = max_level
                prev_end = charge_end

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
    df_feasible.to_excel("BusPlanning_feasible.xlsx", index=False)
    print("\nFeasible bus plan saved as 'BusPlanning_feasible.xlsx'")
    print("\nEnergy check results:")
    for msg in Energy_Checker(df_feasible):
        print(msg)
    plot_gantt_chart(df_feasible)


if __name__ == "__main__":
    main()