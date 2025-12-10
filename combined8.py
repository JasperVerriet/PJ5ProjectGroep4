import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

def Data_Collection():
    """
    Loads the data from the excel file
    Returns the DataFrame
    """
    file_path = input("Put your Excel file in here: ")
    # Gebruik 'openpyxl' engine voor betere compatibiliteit
    df = pd.read_excel(file_path, engine='openpyxl')
    return df

def report_missing_data(df):
    """
    Reports when data is missing in the DataFrame
    """
    copy = df.copy()
    copy = copy.drop("line", axis=1)
    missing_data = copy.isnull()
      
    for i in range(len(copy)):
        if missing_data.iloc[i,:].any():
            print(f'Missing data in row {i+2}')

    return missing_data

def change_data(df):

    def read_and_change_data(df):
        """
        Loads the data from the excel file
        Changes all the start and end times to HH-MM-SS
        Changes the routes that are ran in night time to 1 day later
        """
        df = df.copy()
        
        datum = "31-10-2025"
        
        # OPLOSSING VOOR DE FOUTMELDING:
        # Converteer de tijdskolommen expliciet naar string (HH:MM:SS) 
        # voordat je ze met de datum concateneert. Dit voorkomt de fout 
        # bij het inlezen van datetime.time objecten uit Excel.
        df["start time"] = df["start time"].astype(str)
        df["end time"] = df["end time"].astype(str)

        # Nu kunnen we de datum en tijd veilig combineren en converteren naar datetime objecten
        df["start time"] = pd.to_datetime(datum + " " + df["start time"], format="%d-%m-%Y %H:%M:%S")
        df["end time"] = pd.to_datetime(datum + " " + df["end time"], format="%d-%m-%Y %H:%M:%S")
        
        df["start_seconds"] = df["start time"].dt.hour * 3600 + df["start time"].dt.minute * 60 + df["start time"].dt.second
        df["end_seconds"] = df["end time"].dt.hour * 3600 + df["end time"].dt.minute * 60 + df["end time"].dt.second

        df.loc[df["end_seconds"] < df["start_seconds"], "end_seconds"] += 24 * 3600

        night_rides = (df["start_seconds"] >= 0) & (df["start_seconds"] < 2 * 3600)
        df.loc[night_rides, "start_seconds"] += 24 * 3600
        df.loc[night_rides, "end_seconds"] += 24 * 3600

        return df

    def replace_empty_gaps_with_idle(df):

        """
        Changes the activity of the bus to idle, if there is no activity planned for the bus
        Removes gaps in the bus planning with idle
        param df: The data set where all bus routes are located in
        """
        df1 = df.copy()

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
                        "activity": "idle"
                    })

                filled_rows.append(row.to_dict())
                prev_end = current_end

        df_filled = pd.DataFrame(filled_rows)
        df_filled = df_filled[df_filled["end_seconds"] > df_filled["start_seconds"]]

        if "energy consumption" not in df_filled.columns:
            df_filled["energy consumption"] = 0.0

        idle_mask = df_filled["activity"] == "idle"
        df_filled.loc[idle_mask, "energy consumption"] = (
            (df_filled.loc[idle_mask, "end_seconds"] - df_filled.loc[idle_mask, "start_seconds"]) / 3600
        ) * 5   # 5 kW idle-verbruik

        return df_filled 

    def night_rides_next_day(df_filled):
        """
        Changes routes that are run after 23:59 to the next day in the schedule
        param df_filled: the data set filled with idles 
        """

        night_rides = (df_filled["start_seconds"] >= 0) & (df_filled["start_seconds"] < 2 * 3600)
        df_filled.loc[night_rides, "start_seconds"] += 24 * 3600
        df_filled.loc[night_rides, "end_seconds"] += 24 * 3600

        bus_max_end = df_filled.groupby("bus")["end_seconds"].max()
        night_buses = bus_max_end[bus_max_end > 24 * 3600].index
        day_buses = bus_max_end[bus_max_end <= 24 * 3600].index
        bus_order = list(day_buses) + list(night_buses)
        df_filled["bus"] = pd.Categorical(df_filled["bus"], categories=bus_order, ordered=True)

        df_filled["start_shifted"] = df_filled["start_seconds"] - 4 * 3600
        df_filled["end_shifted"] = df_filled["end_seconds"] - 4 * 3600
        df_filled.loc[df_filled["start_shifted"] < 0, "start_shifted"] += 24 * 3600
        df_filled.loc[df_filled["end_shifted"] < 0, "end_shifted"] += 24 * 3600

        return df_filled
    
    df = read_and_change_data(df)
    df_filled = replace_empty_gaps_with_idle(df)
    df_filled = night_rides_next_day(df_filled)

    return df_filled

def Overlap_Checker(df_filled):
    """
    Checks if the in the current busplan if there are overlapping trips for each bus.
    :param df: The given dataframe
    """
    def check_overlaps(group):
        """
        Function to check overlapping time in trips for a single bus.
        :param group: Group of trips for a single bus
        :return: List of overlapping trips (with row numbers)
        """
        overlaps = []
        # .groupby resets the index, this prevents the reset of the original index when sorting by bus later in the code.
        group = group.reset_index(drop=False)

        for i in range(len(group)):
            for j in range(i + 1, len(group)):
                # It is an overlap if the end time of a trip is after the start time of a trip after the first.
                # Start time of a trip should be before the end of a trip after the first, so that there is no overlap with midnight trips.
                if (group.loc[i, 'start time'] < group.loc[j, 'end time'] and
                    group.loc[j, 'start time'] < group.loc[i, 'end time']):
                    #appends in a in a tuple, so that there is a list with tuples of the data of the overlapping trips.
                    overlaps.append((
                        group.loc[i, 'index'],
                        group.loc[j, 'index'],
                        group.loc[i, 'start location'], group.loc[i, 'end location'],
                        group.loc[i, 'start time'], group.loc[i, 'end time'],
                        group.loc[j, 'start location'], group.loc[j, 'end location'],
                        group.loc[j, 'start time'], group.loc[j, 'end time'],
                    ))
        return overlaps
    # Group by bus and run the check_overlaps function.
    overlap_results = []
    grouped = df_filled.groupby('bus')
    # For each bus, repeats the amount that the group is long.
    for bus, group in grouped:
        overlaps = check_overlaps(group)
        for o in overlaps:
            overlap_results.append((bus, *o))
    
    return overlap_results

def Timetable_comparison(df):
    """
    Function to check if the bus plan correctly compares to the time table.
    The file name of the timetable should always be 'Timetable.xlsx'
    """
    # Let op: De df die hier binnenkomt is df_filled en bevat datetime objecten
    
    # Gebruik de originele Timetable.xlsx, welke bij mij lokaal als CSV beschikbaar is.
    # Als deze file in jouw omgeving Timetable.xlsx heet, werkt de read_excel
    table = pd.read_excel('Timetable.xlsx', engine='openpyxl')
    table = table.copy()
    dfc = df.copy()

    # Zorgen dat de departure_time in de timetable ook als string wordt behandeld
    table['departure_time'] = table['departure_time'].astype(str)
    table['departure_time'] = pd.to_datetime(table['departure_time'], format='%H:%M', errors='coerce')
    
    # dfc['start time'] is al een datetime object, dus direct .dt.hour etc. gebruiken
    
    dfc['start time'] = (
        dfc['start time'].dt.hour * 3600 +
        dfc['start time'].dt.minute * 60 +
        dfc['start time'].dt.second)

    table['departure_time'] = (
        table['departure_time'].dt.hour * 3600 +
        table['departure_time'].dt.minute * 60 +
        table['departure_time'].dt.second)

    table.sort_values('departure_time', inplace=True)
    dfc.sort_values('start time', inplace=True)

    dfc.reset_index(drop=True, inplace=True)
    table.reset_index(drop=True, inplace=True)

    dfc = dfc[dfc['activity'] == 'service trip']
    if dfc['start time'].isin(table['departure_time']).all():
        print(f'\nThe current bus plan corresponds to the timetable.')
    else:
        table['departure_time'] = pd.to_datetime(table['departure_time'],unit='s').dt.strftime('%H:%M:%S')
        dfc['start time'] = pd.to_datetime(dfc['start time'],unit='s').dt.strftime('%H:%M:%S')
        
        print(f'\nThe current bus plan does not correspond to the timetable in the following rows:')
        for i in range(len(dfc)):
            if not dfc['start time'].iloc[i] in table['departure_time'].values:
                print(f"\nRow {i}   The start time {dfc['start time'].iloc[i]} does not correspond to {table['departure_time'].iloc[i]} in the timetable.")
    
def Energy_Checker(df_filled):
    """
    calculates the total amount of energy used
    calculates the total idle time
    calculates total charge time
    shows feasibilty of the routes in terms of energy levels
    param df_filled: the dataset filled with idles

    """

    soh = 255
    min_battery_level = 0.1 * soh
    max_battery_level = 0.9 * soh
    total_charge_time = 0
    total_idle_time = 0
    charge_per_hour = 450

    total_energy_used = 0

    df_filled['bus'] = df_filled['bus'].astype(int)
    df_filled = df_filled.sort_values('bus')
    group_bus = df_filled.groupby('bus', observed=False)

    messages = []

    for bus_id, bus_routes in group_bus:
        total_energy_used_on_route = 0
        total_charge_time_on_route = 0
        current_battery_level = max_battery_level
        idle_per_route = 0

        feasible = True

        for route_index, route in bus_routes.iterrows():
            energy_consumption = route["energy consumption"]

            if current_battery_level - energy_consumption < min_battery_level:
                feasible = False

            if route.get("activity", "") == 'idle':
                idle_period = (route["end_seconds"] - route["start_seconds"]) / 3600
                idle_per_route += idle_period

            if energy_consumption > 0:
                total_energy_used_on_route += energy_consumption
            else:
                total_charge_time_on_route += (energy_consumption / charge_per_hour)

            current_battery_level -= energy_consumption

        total_energy_used += total_energy_used_on_route
        total_charge_time += total_charge_time_on_route
        total_idle_time += idle_per_route

        if feasible:
            messages.append(f"Bus plan for Bus {bus_id} is feasible. Amount of energy used: {total_energy_used_on_route:.2f} kWh")
        
        if feasible == False:
            messages.append(f"Bus {bus_id}: Battery level will drop below 10% during route {route_index+1}. Route is infeasible.")

    messages.append(f"Total Energy Used is {total_energy_used}")
    messages.append(f"Total Charge Time: {total_charge_time}")
    messages.append(f"Total Idle Time:{total_idle_time}")
    messages.append(f"Amount of Buses used: {bus_id}")




    return messages
def plot_gantt_chart(df_filled):

    """
    Plots the Gantt chart
    Sets the axis to 04:00-02:00 the next day
    gives each activity an unique color
    param df_filled: the data set filled with idle and no gaps
    """
    activities = df_filled["activity"].unique()
    colours = plt.cm.tab20.colors
    colour_per_activity = {type: colours[i % len(colours)] for i, type in enumerate(activities)}

    fig, ax = plt.subplots(figsize=(12, 5))
    for _, row in df_filled.iterrows():
        ax.barh(
            row["bus"],
            left=row["start_shifted"],
            width=row["end_shifted"] - row["start_shifted"],
            color=colour_per_activity[row["activity"]],
            edgecolor="black",
            alpha=0.7,
        )

    patches = [plt.Rectangle((0, 0), 1, 1, fc=colour_per_activity[type]) for type in activities]
    ax.legend(patches, activities, loc="upper right")

    xticks = range(0, 22 * 3600 + 1, 3600)
    xlabels = [f"{(t // 3600 + 4) % 24:02d}:00" for t in xticks]
    ax.set_xticks(xticks)
    ax.set_xticklabels(xlabels)
    ax.set_xlim(0, 22 * 3600)
    ax.set_xlabel("Time")
    ax.set_ylabel("Bus number")
    ax.set_title("Bus Planning lines 400 and 401 for 1 day")

    bus_labels = sorted(df_filled["bus"].unique())
    ax.set_yticks(bus_labels)
    ax.set_yticklabels([str(b) for b in bus_labels])

    plt.tight_layout()
    plt.savefig('Bus Planning Gantt Chart.png')
    plt.show()


def main():
    df = Data_Collection()
    report_missing_data(df)

    df_filled =change_data(df)
    df_filled.to_excel("BusPlanning_filled.xlsx", index=False)
    
    Overlap_Checker(df_filled)     
    
    Timetable_comparison(df_filled)
    
    messages = Energy_Checker(df_filled)
    print("\n--- Energy Checker Results ---")
    for msg in messages:
        print(msg)

    plot_gantt_chart(df_filled)


if __name__ == "__main__":
    main()