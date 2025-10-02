import pandas as pd


def set_energy_variables():
    
    soh = 255  # kWh
    min_battery_level = 0.10 * soh  # 25.5 kWh
    max_battery_level = 0.90 * soh   # 239.5 kWh


    return( min_battery_level, max_battery_level,)


def check_feasible_per_route(min_battery_level, max_battery_level, group_bus):

    total_energy_used = 0


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
        
        total_energy_used += total_energy_used_on_route


        if feasible:
            print(f"\nBus planning for Bus {bus_id} is feasible. Amount of energy used: {total_energy_used_on_route:.2f} kWh")
              
    return total_energy_used


def main():
    
    df = pd.read_excel("Bus Planning-1.xlsx")
    group_bus = df.groupby('bus')
    min_battery_level,max_battery_level = set_energy_variables()
    total_energy_used = check_feasible_per_route(min_battery_level, max_battery_level, group_bus)
    print(f"Total Energy Used for Bus Plan is: {total_energy_used}")

if __name__ == "__main__":
    main()