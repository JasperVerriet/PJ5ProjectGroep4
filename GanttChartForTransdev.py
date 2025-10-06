import pandas as pd
import matplotlib.pyplot as plt

def read_and_change_data():
    """
    Loads the data from the excel file
    Changes all the start and end times to HH-MM-SS
    Changes the routes that are ran in night time to 1 day later (+24*3600 minutes)
    """
    
    df = pd.read_excel("Bus Planning-1.xlsx")
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
    df_filled = df_filled[df_filled["end_seconds"] > df_filled["start_seconds"]]

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

    # Tijdas: van 04:00 tot 02:00 (22 uur)
    xticks = range(0, 22 * 3600 + 1, 3600)
    xlabels = [f"{(t // 3600 + 4) % 24:02d}:00" for t in xticks]
    ax.set_xticks(xticks)
    ax.set_xticklabels(xlabels)
    ax.set_xlim(0, 22 * 3600)
    ax.set_xlabel("Time")
    ax.set_ylabel("Bus number")
    ax.set_title("Bus Planning lines 400 and 401 for 1 day")


    # Zorg dat alle busnummers zichtbaar zijn op de y-as
    bus_labels = sorted(df_filled["bus"].unique())
    ax.set_yticks(bus_labels)
    ax.set_yticklabels([str(b) for b in bus_labels])


    plt.tight_layout()
    plt.savefig('Bus Planning Gantt Chart.png')
    plt.show()

def print_routes_for_bus(df, bus_number):
    bus_df = df[df["bus"] == bus_number].sort_values("start_seconds").reset_index(drop=True)
    print(f"\n📋 Ritten voor bus {bus_number}:")
    for i, row in bus_df.iterrows():
        start = row["start_seconds"]
        end = row["end_seconds"]
        activity = row.get("activity", "rit")
        print(f"  {i+1:02d}. {activity:<6} van {start:>5} sec tot {end:>5} sec ({(end - start)/60:.1f} min)")


def main():

    df = read_and_change_data()
    df_filled = replace_empty_gaps_with_idle(df)
    df_filled = night_rides_next_day(df_filled)
    print_routes_for_bus(df_filled, bus_number=1)
    plot_gantt_chart(df_filled)

if __name__ == "__main__":
    main()
