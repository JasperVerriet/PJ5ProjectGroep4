import pandas as pd
import numpy as np

# Here is the function that loads the Excel file and returns the DataFrame
def Data_Collection():
    file_path = input("Put your Excel file in here:")
    df = pd.read_excel(file_path, engine='openpyxl')
    return df

# Here is the function that reports missing data in the DataFrame
def report_missing_data(df):
    copy = df.copy()
    copy = copy.drop("line", axis=1)
    missing_data = copy.isnull()
      
    for i in range(len(copy)):
        if missing_data.iloc[i,:].any():
            print(f'missing data in row {i+2}')


    def read_and_change_data(df):

        """
        Loads the data from the excel file
        Changes all the start and end times to HH-MM-SS
        Changes the routes that are ran in night time to 1 day later (+24*3600 minutes)
        """
        
        datum = "02-10-2025"
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

        filled_rows = []
        for bus, bus_df in df.groupby("bus"):
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

        return df_filled 


    def night_rides_next_day(df_filled):
        """
        Changes routes that are run after 23:59 to the next day in the schedule
        param df_filled: the data set filled with idle 
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
    
    df1 = read_and_change_data(df)
    df_filled = replace_empty_gaps_with_idle(df1)
    df_filled = night_rides_next_day(df_filled)

    return missing_data


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



def Energy_Checker(df_filled):   
    soh = 255  # kWh
    min_battery_level = 0.10 * soh  # 25.5 kWh
    max_battery_level = 0.90 * soh   # 239.5 kWh
    total_energy_used = 0

    group_bus = df_filled.groupby('bus')

    for bus_id, bus_routes in group_bus:
        total_energy_used_on_route = 0
        current_battery_level = max_battery_level
        feasible = True

        for route_index, route in bus_routes.iterrows():
            energy_consumption = route["energy consumption"]

            
            if route["activity"] == "idle":
                start_time = pd.to_datetime(route["start time"])
                end_time = pd.to_datetime(route["end time"])
                idle_time_hours = (end_time - start_time).total_seconds() / 3600  
                energy_consumption = 5 * idle_time_hours  

            if energy_consumption > 0:
                total_energy_used_on_route += energy_consumption

            current_battery_level -= energy_consumption    


            if current_battery_level - energy_consumption < min_battery_level:
                print(f"Bus {bus_id}: Battery level will drop below 10% during route {route_index+1}. Route is infeasible.")
                feasible = False
                break




        
        total_energy_used = total_energy_used + total_energy_used_on_route


        if feasible:
            print(f"\nBus plan for Bus {bus_id} is feasible. Amount of energy used: {total_energy_used_on_route:.2f} kWh")



    print(f"Total Energy Used on Bus Plan is: {total_energy_used}")

def main():
    df = Data_Collection()
    df_filled = report_missing_data(df)
    
    Overlap_Checker(df_filled)    
    
    Energy_Checker(df_filled)
    

if __name__ == "__main__":
    main()