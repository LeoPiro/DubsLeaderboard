import altair as alt
import numpy as np
import pandas as pd
import streamlit as st
from datetime import datetime, timedelta

# Load CSV
df = pd.read_csv("leaderboard_data.csv")

df['timestamp'] = pd.to_datetime(df['timestamp'], format="%Y-%m-%d %H:%M:%S")
df = df.rename(columns={"number_int": "score"})

st.title("🏆 Top Gainers Leaderboards")

# Optional name filter input
name_filter = st.text_area("Filter by specific player names (comma or newline separated)", height=100)
filtered_names = set()
if name_filter.strip():
    filtered_names = set([name.strip() for name in name_filter.replace(",", "\n").split("\n") if name.strip()])

# Function to calculate gain within a time window
def get_gain_leaderboard(time_window=None):
    if time_window:
        cutoff = datetime.now() - time_window
        df_filtered = df[df['timestamp'] >= cutoff]
    else:
        df_filtered = df.copy()

    if filtered_names:
        df_filtered = df_filtered[df_filtered['name'].isin(filtered_names)]

    counts = df_filtered['name'].value_counts()
    valid_names = counts[counts > 1].index
    df_filtered = df_filtered[df_filtered['name'].isin(valid_names)]

    if df_filtered.empty:
        return pd.DataFrame(columns=["name", "Gain"])

    latest = df_filtered.groupby("name")["score"].max()
    earliest = df_filtered.groupby("name")["score"].min()
    gain = (latest - earliest).sort_values(ascending=False)
    return gain.reset_index().rename(columns={0: "Gain"})

# Layout in columns
col1, col2, col3 = st.columns(3)

with col1:
    st.subheader("Last 24 Hours")
    df_1d = get_gain_leaderboard(timedelta(days=1))
    st.dataframe(df_1d, hide_index=True, column_config={
        "name": st.column_config.TextColumn("Player Name", width="large"),
        "Gain": st.column_config.NumberColumn("Gain", format="%d", width="medium"),
    })

with col2:
    st.subheader("Last 7 Days")
    df_7d = get_gain_leaderboard(timedelta(days=7))
    st.dataframe(df_7d, hide_index=True, column_config={
        "name": st.column_config.TextColumn("Player Name", width="large"),
        "Gain": st.column_config.NumberColumn("Gain", format="%d", width="medium"),
    })

with col3:
    st.subheader("All Time")
    df_all = get_gain_leaderboard()
    st.dataframe(df_all, hide_index=True, column_config={
        "name": st.column_config.TextColumn("Player Name", width="large"),
        "Gain": st.column_config.NumberColumn("Gain", format="%d", width="medium"),
    })

# Optional: Show a bar chart of the top all-time gainers
st.subheader("📊 All-Time Gainers Chart with Top 3 Labels")

if not df_all.empty and "Gain" in df_all.columns:
    # Create base bar chart
    base = alt.Chart(df_all).mark_bar().encode(
        x=alt.X('name:N', title="Player", sort='-y'),
        y=alt.Y('Gain:Q', title="Gain")
    )

    # Add text labels only for top 3
    text = base.transform_window(
        rank='rank()',
        sort=[alt.SortField('Gain', order='descending')]
    ).transform_filter(
        'datum.rank <= 3'
    ).mark_text(
        align='center',
        baseline='bottom',
        dy=-5,  # distance above the bar
        fontSize=12
    ).encode(
        text='name'
    )

    chart = (base + text).properties(width=800, height=400)
    st.altair_chart(chart, use_container_width=True)

else:
    st.info("No data available to display the chart.")


# Optional: Custom time range leaderboard
st.subheader("🕒 Custom Time Range Leaderboard")

custom_hours = st.slider("Select a time range (in hours)", min_value=1, max_value=168, value=12)
df_custom = get_gain_leaderboard(timedelta(hours=custom_hours))

if not df_custom.empty:
    st.dataframe(df_custom, hide_index=True, column_config={
        "name": st.column_config.TextColumn("Player Name", width="large"),
        "Gain": st.column_config.NumberColumn("Gain", format="%d", width="medium"),
    })
else:
    st.info("No data available for the selected time range.")

st.subheader("📈 Top 20 Players Progression Over Time (Smoothed)")

# 1. Get top 20 players by max score
top20_names = df.groupby("name")["score"].max().sort_values(ascending=False).head(20).index.tolist()

# 2. Filter dataframe for top 20 only
df_top20 = df[df["name"].isin(top20_names)]

# 3. Pivot to time series structure
df_pivot = df_top20.pivot_table(index="timestamp", columns="name", values="score", aggfunc="max")

# 4. Sort timestamps & forward fill missing data
df_pivot = df_pivot.sort_index().ffill()

# 5. Remove negative or zero scores (if they exist)
df_pivot[df_pivot < 0] = 0

# 6. Melt for Altair
df_long = df_pivot.reset_index().melt(id_vars=["timestamp"], var_name="Player", value_name="Score")

# # Get top 3 players
# top3_names = df.groupby("name")["score"].max().sort_values(ascending=False).head(3).index.tolist()

# Smooth line chart
# Get top 5 players
top5_names = df.groupby("name")["score"].max().sort_values(ascending=False).head(5).index.tolist()

# Smooth line chart base
base_chart = alt.Chart(df_long).mark_line(interpolate='monotone').encode(
    x=alt.X('timestamp:T', title="Time"),
    y=alt.Y('Score:Q', scale=alt.Scale(zero=True), title="Dubs"),
    color=alt.Color('Player:N', legend=alt.Legend(title="Player"))
)

# Latest points of top 5
latest_points = df_long[df_long['Player'].isin(top5_names)].sort_values('timestamp').groupby('Player').tail(1)

# Text labels for top 5 (WITH proper padding inside chart)
text_labels = alt.Chart(latest_points).mark_text(
    align='right',
    dx=5,     # small nudge right
    dy=-5,    # small nudge up
    fontSize=12,
    fontWeight='bold'
).encode(
    x='timestamp:T',
    y='Score:Q',
    text='Player',
    color='Player:N'
)

# Compose chart (without clipping)
chart = (base_chart + text_labels).properties(
    width=850,
    height=500,
    title="Top 20 Player Progression (Smooth) with Top 5 Labels"
).configure_legend(
    orient='right',       # move legend to right
    padding=20,           # add padding
    labelLimit=200
).configure_view(
    stroke=None           # remove the outer border
)

st.altair_chart(chart, use_container_width=True)




st.subheader("💥 Biggest Gain Detected Over Rolling Time Window (All Players)")

rolling_hours = st.slider("Select rolling window (hours):", min_value=1, max_value=24, value=4)

biggest_changes = []

for player, group in df.groupby('name'):
    group = group.sort_values('timestamp')

    max_gain = 0

    for i, row in group.iterrows():
        window_end = row['timestamp'] + timedelta(hours=rolling_hours)
        future_window = group[(group['timestamp'] > row['timestamp']) & (group['timestamp'] <= window_end)]

        if not future_window.empty:
            gain = future_window['score'].max() - row['score']
            if gain > max_gain:
                max_gain = gain

    if max_gain > 0:
        biggest_changes.append({'name': player, 'max_gain': int(max_gain)})

# Display
if biggest_changes:
    biggest_changes_df = pd.DataFrame(biggest_changes)
    biggest_changes_df = biggest_changes_df.sort_values('max_gain', ascending=False)
    st.dataframe(biggest_changes_df.rename(columns={'name': 'Player', 'max_gain': f'Max Gain in {rolling_hours}h'}), hide_index=True)
else:
    st.warning("No valid gains detected for the selected window.")


st.subheader("GG Seasonal Leaderboard")

# Load from file
try:
    with open("selected_users.txt", "r") as f:
        selected_users = [line.strip() for line in f if line.strip()]
except FileNotFoundError:
    st.error("❌ 'selected_users.txt' not found. Please add it to the working directory.")
    selected_users = []

# Filter and process
df_selected = df[df['name'].isin(selected_users)]
max_scores = df_selected.groupby("name")["score"].max().reset_index()

# Ensure the score column is numeric and drop any bad rows
max_scores["score"] = pd.to_numeric(max_scores["score"], errors="coerce")
max_scores = max_scores.dropna(subset=["score"])

# 🔒 Force type to int64 — critical to prevent exclamation warning
max_scores["score"] = max_scores["score"].astype("int64")
max_scores["score_formatted"] = max_scores["score"].apply(lambda x: f"{x:,}")


# Sort and rank
max_scores = max_scores.sort_values("score", ascending=False).reset_index(drop=True)
max_scores.insert(0, "Rank", max_scores.index + 1)
max_scores = max_scores.rename(columns={
    "name": "Player Name",
    "score_formatted": "Highest Score Seen"
})

max_scores = max_scores.drop(columns=["score"])
# Display
if not max_scores.empty:
    st.dataframe(
        max_scores,
        height=1000,
        hide_index=True,
        column_config={
            "Rank": st.column_config.NumberColumn("Rank", format="%d", width="small"),
            "Player Name": st.column_config.TextColumn("Player Name", width="large"),
            "Highest Score Seen": st.column_config.TextColumn("Highest Score Seen", width="medium"),


        }
    )
else:
    st.warning("No data found for the selected users.")








