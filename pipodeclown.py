import pandas as pd
import numpy as np

# Here is the function that loads the Excel file and returns the DataFrame
def Data_Collection():
    file_path = input("Put your Excel file in here:")
    df = pd.read_excel(file_path)
    return df

# Here is the function that reports missing data in the DataFrame
def report_missing_data(df):
    copy = df.copy()
    copy = copy.drop("line", axis=1)
    missing_data = copy.isnull()
      
    for i in range(len(copy)):
        if missing_data.iloc[i,:].any():
            print(f'missing data in row {i+2}')

    return missing_data

def Overlap_Checker(df):
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
    grouped = df.groupby('bus')
    # For each bus, repeats the amount that the group is long.
    for bus, group in grouped:
        overlaps = check_overlaps(group)
        for o in overlaps:
            # At the start of each tuple, append the number of the bus of that group.
            # So that later when printing the results, it is possible to state wich bus has overlap.
            overlap_results.append((bus, *o))



    for o in overlap_results:
        # For each tuple in overlap_results, the first character is the bus number.
        bus = o[0]
        print(f"Bus {bus} has overlap:")
        print(f"  row {o[1]}: {o[3]} -> {o[4]} ({o[5]} - {o[6]})")
        print(f"  row {o[2]}: {o[7]} -> {o[8]} ({o[9]} - {o[10]})")

    if len(overlap_results) == 0:
        print('There are no overlaps in the current planning.') 

Overlap_Checker(df)

def Energy_Checker():   
    soh = 255  # kWh
    min_battery_level = 0.10 * soh  # 25.5 kWh
    max_battery_level = 0.90 * soh   # 239.5 kWh
    total_energy_used = 0

    group_bus = df.groupby('bus')

    for bus_id, bus_routes in group_bus:
        total_energy_used_on_route = 0
        current_battery_level = max_battery_level
        feasible = True

        for route_index, route in bus_routes.iterrows():
            energy_consumption = route["energy consumption"]

            if energy_consumption > 0:
                total_energy_used_on_route += energy_consumption

            current_battery_level -= energy_consumption

            if current_battery_level < min_battery_level:
                print(f"Bus {bus_id}: Battery level below 10%, Route is infeasible.")
                print(f"Bus plan infeasible after busroute {route_index + 1} with battery level: {current_battery_level:.2f} kWh")
                feasible = False
                break
        
        total_energy_used = total_energy_used + total_energy_used_on_route


        if feasible:
            print(f"\nBus plan for Bus {bus_id} is feasible. Amount of energy used: {total_energy_used_on_route:.2f} kWh")



    print(f"Total Energy Used on Bus Plan is: {total_energy_used}")

    def main():
        df = Data_Collection()
        report_missing_data(df)
        
        Overlap_Checker(df)    
        
        Energy_Checker(df)
    

if __name__ == "__main__":
    main()

