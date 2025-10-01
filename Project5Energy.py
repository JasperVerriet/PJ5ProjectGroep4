import pandas as pd

df = pd.read_excel("Bus Planning Casus 1.xlsx")

soh = 255  # kWh
min_battery_level = 0.10 * soh  # 25.5 kWh
max_battery_level = 0.90 * soh   # 239.5 kWh
total_energy_used = 0
current_battery_level = max_battery_level  
feasible = True

for route_index in range(len(df)):
    route = df.iloc[route_index]  
    energy_consumption_on_route = route["energy consumption"]
    current_battery_level -= energy_consumption_on_route

    if energy_consumption_on_route > 0:
        total_energy_used += energy_consumption_on_route

    if current_battery_level < min_battery_level:
        print("Battery level below 10%, Route is infeasible.")
        print(f"Bus plan infeasible after busroute {route_index + 1} with battery level: {current_battery_level:.2f} kWh")
        feasible = False
        break




if feasible:
    print(f"\nBus Plan is feasible. Amount of energy used: {total_energy_used:.2f} kWh")
else:
    print("\nBusplan is not feasible.")