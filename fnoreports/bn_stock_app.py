import streamlit as st
import sqlite3
import pandas as pd
import os
import altair as alt

# --- Page config for full-width layout ---
st.set_page_config(layout="wide")

BASE_DIR_db = "/home/shail/db"
db_path = os.path.join(BASE_DIR_db, "fnodailydata.db")

# Connect to SQLite
conn = sqlite3.connect(db_path)
tables = pd.read_sql("SELECT name FROM sqlite_master WHERE type='table';", conn)
table_names = tables['name'].tolist()

dfs = {}
for name in table_names:
    try:
        query = f'SELECT * FROM "{name}"'
        df = pd.read_sql_query(query, conn)
        dfs[name] = df
    except Exception as e:
        st.warning(f"Skipped table {name} due to error: {e}")
conn.close()

# --- Streamlit UI ---
st.title("SQLite Table Viewer and Bar Graphs")

st.sidebar.header("Filters")
selected_table = st.sidebar.selectbox("Choose a table:", table_names)

df = dfs[selected_table].copy()

# --- Days slider filter ---
if "Date" in df.columns:
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    df = df.sort_values("Date", ascending=True)

    # Slider for number of days
    max_days = len(df["Date"].unique())
    num_days = st.sidebar.slider(
        "Show last N days:",
        min_value=1,
        max_value=max_days,
        value=min(30, max_days)  # default 30 days or less if fewer available
    )

    # Filter to last N days
    latest_date = df["Date"].max()
    cutoff_date = latest_date - pd.Timedelta(days=num_days-1)
    df = df[df["Date"] >= cutoff_date]

# --- Granularity selector ---
granularity = st.sidebar.radio("Select granularity:", ["Daily", "Weekly", "Monthly"])

# --- Second column filter ---
if len(df.columns) >= 2:
    second_col = df.columns[1]
    unique_vals = df[second_col].dropna().unique().tolist()
    selected_vals = st.sidebar.multiselect(
        f"Select {second_col} value(s):", unique_vals, default=unique_vals
    )
    if selected_vals:
        filtered_df = df[df[second_col].isin(selected_vals)]
    else:
        filtered_df = df
else:
    st.warning("This table does not have a second column.")
    filtered_df = df

# --- Apply granularity ---
if "Date" in filtered_df.columns:
    if granularity == "Weekly":
        filtered_df["Period"] = filtered_df["Date"].dt.to_period("W").apply(lambda r: r.start_time)
    elif granularity == "Monthly":
        filtered_df["Period"] = filtered_df["Date"].dt.to_period("M").apply(lambda r: r.start_time)
    else:  # Daily
        filtered_df["Period"] = filtered_df["Date"]

    # Identify numeric columns
    numeric_cols = filtered_df.select_dtypes(include=["number"]).columns

    # Separate percentage vs non-percentage
    pct_cols = [c for c in numeric_cols if c.endswith("_pct")]
    non_pct_cols = [c for c in numeric_cols if c not in pct_cols]

    # Build aggregation dictionary
    agg_dict = {col: "sum" for col in non_pct_cols}
    agg_dict.update({col: "mean" for col in pct_cols})  # average for percentages

    # Aggregate numeric columns by Period + selector
    group_cols = ["Period", second_col]
    agg_df = filtered_df.groupby(group_cols).agg(agg_dict).reset_index()

    # Show filtered table info
    st.write(f"Rows: {len(filtered_df)}, Columns: {len(filtered_df.columns)}")

    # --- Grouped Bar Graphs ---
    st.subheader(f"{selected_table} Bar Graphs ({granularity})")
    plot_df = agg_df.copy()
    plot_df["Period"] = pd.to_datetime(plot_df["Period"], errors="coerce").dt.strftime("%Y-%m-%d")
    plot_df = plot_df.drop_duplicates(subset=["Period", second_col])

###
###
    for col in numeric_cols:
        st.write(f"#### {col}")
        base = alt.Chart(plot_df).encode(
            x=alt.X("Period:O", title=granularity,
                    scale=alt.Scale(paddingInner=0.2, paddingOuter=0.1),
                    axis=alt.Axis(labelAngle=-45)),
            y=alt.Y(f"{col}:Q", title=col),
            color=alt.Color(second_col,
                            legend=alt.Legend(title=second_col),
                            scale=alt.Scale(scheme="category20")),
            xOffset=second_col,
            tooltip=["Period", second_col, col],
        )   

        bars = base.mark_bar()  

        # Add text labels above bars
        text = base.mark_text(
            align="center",
            baseline="bottom",
            dy=-2,  # adjust vertical position
            fontSize=12
        ).encode(
            text=alt.Text(f"{col}:Q", format=".2f")  # format to 2 decimals
        )   

        chart = (bars + text).properties(width=800, height=300) 

        st.altair_chart(chart, use_container_width=True)

    # --- Show filtered table ---
    st.write(f"### Table: {selected_table}")
    filtered_df["Date"] = filtered_df["Date"].dt.date
    filtered_df = filtered_df.sort_values("Date", ascending=False)
    st.dataframe(filtered_df, use_container_width=True)
