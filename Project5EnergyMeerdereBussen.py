import pandas as pd


def set_energy_variables():

    """
    Sets the SOH and the minimum and maximum battery level to the desired amount
    Returns the minimum and maximun battery level

    """
    
    soh = 255  # kWh
    min_battery_level = 0.10 * soh  # 25.5 kWh
    max_battery_level = 0.90 * soh   # 239.5 kWh


    return( min_battery_level, max_battery_level)


def check_feasible_per_route(min_battery_level, max_battery_level, group_bus):
    """
    Checks if each route is feasible in terms of energy levels
    param min_battery_level: the minimum amount of battery that has to be available in the bus
    param max_battery_level: the maximum amount of battery the bus can be
    return: the feasibility of each route plus the energy consumed on all busroutes

    """

    total_energy_used = 0


    for bus_id, bus_routes in group_bus:
        total_energy_used_on_route = 0
        current_battery_level = max_battery_level
        feasible = True

        for route_index, route in bus_routes.iterrows():
            energy_consumption = route["energy consumption"]



            if current_battery_level - energy_consumption < min_battery_level:
                print(f"Bus {bus_id}: Battery level will drop below 10% during route {route_index+1}. Route is infeasible.")
                feasible = False
                break

            current_battery_level -= energy_consumption    


            if energy_consumption > 0:
                total_energy_used_on_route += energy_consumption



        
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
