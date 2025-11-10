import pandas as pd
import numpy as np

def make_feasible_busplan(input_file="Bus Planning.xlsx", output_file="BusPlanning_feasible.xlsx"):
    # Parameters
    battery_capacity = 255
    min_level = 0.1 * battery_capacity
    max_level = 0.9 * battery_capacity
    charge_rate = 450  # kWh per hour
    idle_consumption = 5  # kW
    min_charge_minutes = 15

    # Load data
    df = pd.read_excel(input_file, engine="openpyxl")
    orig_cols = list(df.columns)

    # Parse times
    df["start time"] = pd.to_datetime(df["start time"], errors="coerce")
    df["end time"] = pd.to_datetime(df["end time"], errors="coerce")

    # Convert to seconds
    df["start_seconds"] = df["start time"].dt.hour * 3600 + df["start time"].dt.minute * 60 + df["start time"].dt.second
    df["end_seconds"] = df["end time"].dt.hour * 3600 + df["end time"].dt.minute * 60 + df["end time"].dt.second

    all_rows = []

    for bus, bus_df in df.groupby("bus"):
        bus_df = bus_df.sort_values("start_seconds").reset_index(drop=True)
        prev_end = None
        battery = max_level

        for i, row in bus_df.iterrows():
            start_s, end_s = row["start_seconds"], row["end_seconds"]
            activity = str(row["activity"]).lower() if pd.notna(row["activity"]) else ""

            # Add idle gap if exists
            if prev_end is not None and start_s > prev_end:
                idle_dur = start_s - prev_end
                idle_energy = (idle_dur / 3600) * idle_consumption
                all_rows.append({
                    "bus": bus,
                    "activity": "idle",
                    "start time": pd.to_datetime("00:00:00") + pd.to_timedelta(prev_end, unit='s'),
                    "end time": pd.to_datetime("00:00:00") + pd.to_timedelta(start_s, unit='s'),
                    "energy consumption": idle_energy,
                    "start location": "EHVBST",
                    "end location": "EHVBST"
                })
                battery -= idle_energy

            # Check if charging needed before next trip
            energy_needed = row.get("energy consumption", 0)
            if battery - energy_needed < min_level:
                charge_needed = max_level - battery
                charge_time_hr = charge_needed / charge_rate
                charge_time_sec = max(charge_time_hr * 3600, min_charge_minutes * 60)

                charge_start = prev_end if prev_end else start_s - charge_time_sec
                charge_end = charge_start + charge_time_sec

                all_rows.append({
                    "bus": bus,
                    "activity": "charging",
                    "start time": pd.to_datetime("00:00:00") + pd.to_timedelta(charge_start, unit='s'),
                    "end time": pd.to_datetime("00:00:00") + pd.to_timedelta(charge_end, unit='s'),
                    "energy consumption": -(charge_time_sec / 3600) * charge_rate,
                    "start location": "EHVGAR",
                    "end location": "EHVGAR"
                })

                battery = max_level
                prev_end = charge_end

            # Add the original trip
            row_dict = row.to_dict()
            row_dict["start time"] = pd.to_datetime("00:00:00") + pd.to_timedelta(start_s, unit='s')
            row_dict["end time"] = pd.to_datetime("00:00:00") + pd.to_timedelta(end_s, unit='s')
            all_rows.append(row_dict)

            battery -= energy_needed
            prev_end = end_s

    # Combine results
    df_new = pd.DataFrame(all_rows)

    # Convert times back to HH:MM:SS
    df_new["start time"] = df_new["start time"].dt.strftime("%H:%M:%S")
    df_new["end time"] = df_new["end time"].dt.strftime("%H:%M:%S")

    # Ensure all original columns exist
    for col in orig_cols:
        if col not in df_new.columns:
            df_new[col] = np.nan
    df_new = df_new[orig_cols]

    # Save final Excel
    df_new.to_excel(output_file, index=False)
    print(f"✅ Feasible bus plan saved to: {output_file}")