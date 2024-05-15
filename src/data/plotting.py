import pandas as pd
import matplotlib.pyplot as plt

# Load the data
df = pd.read_csv('output_no_duplicates_4.csv')

df['time'] = pd.to_datetime(df['time'])

fig, ax1 = plt.subplots()

color = 'tab:red'
ax1.set_xlabel('time (s)')
ax1.set_ylabel('speed', color=color)
ax1.plot(df['time'], df['speed'], color=color)
ax1.tick_params(axis='y', labelcolor=color)

# Instantiate a second y-axis for the same x-axis
ax2 = ax1.twinx()
color = 'tab:blue'
ax2.set_ylabel('throttle', color=color) 
ax2.plot(df['time'], df['throttle'], color=color)
ax2.tick_params(axis='y', labelcolor=color)

fig.tight_layout()
plt.title('Time vs Speed and Throttle')
plt.show()

# Second figure for time vs heart rate and breathing rate
fig, ax1 = plt.subplots()

color = 'tab:green'
ax1.set_xlabel('time (s)')
ax1.set_ylabel('heart_rate', color=color)
ax1.plot(df['time'], df['heart_rate'], color=color)
ax1.tick_params(axis='y', labelcolor=color)

ax2 = ax1.twinx()
color = 'tab:purple'
ax2.set_ylabel('breathing_rate', color=color)
ax2.plot(df['time'], df['breathing_rate'], color=color)
ax2.tick_params(axis='y', labelcolor=color)

fig.tight_layout()
plt.title('Time vs Heart Rate and Breathing Rate')
plt.show()
