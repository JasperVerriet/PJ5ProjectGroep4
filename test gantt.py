import pandas as pd
import matplotlib.pyplot as plt

df = pd.read_excel("Bus Planning-1.xlsx")

datum = "02-10-2025"
df["start time"] = pd.to_datetime(datum + " " + df["start time"], format="%d-%m-%Y %H:%M:%S")
df["end time"] = pd.to_datetime(datum + " " + df["end time"], format="%d-%m-%Y %H:%M:%S")

df["start_seconds"] = df["start time"].dt.hour * 3600 + df["start time"].dt.minute * 60 + df["start time"].dt.second
df["end_seconds"] = df["end time"].dt.hour * 3600 + df["end time"].dt.minute * 60 + df["end time"].dt.second

activities = df["activity"].unique()
colours = plt.cm.tab20.colors
colour_per_activity = {type: colours[i % len(colours)] for i, type in enumerate(activities)}

fig, ax = plt.subplots(figsize=(10, 6))

for bus, begin, eind, type in zip(df["bus"], df["start_seconds"], df["end_seconds"], df["activity"]):
    ax.barh(
        bus,
        left=begin,
        width=eind - begin,
        color=colour_per_activity[type],
        edgecolor="black",
        alpha=0.7,
    )

patches = [plt.Rectangle((0, 0), 1, 1, fc=colour_per_activity[type]) for type in activities]
ax.legend(patches, activities, loc="upper right")

xticks = range(0, 24 * 3600, 3600)  # Elke 3600 seconden = 1 uur
xlabels = [f"{t//3600}" for t in xticks]  # Labels als "0", "1", "2", etc.
ax.set_xticks(xticks)
ax.set_xticklabels(xlabels)

ax.set_xlabel("Time")
ax.set_ylabel("Bus number")

plt.tight_layout()
plt.show()
