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

# Get list of all tables
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
st.title("SQLite Table Viewer and  Bar Graphs for the columns")

# Sidebar selectors
st.sidebar.header("Filters")
# Sidebar date selector

# Select table
selected_table = st.sidebar.selectbox("Choose a table:", table_names)

# Sidebar date selector
if "Date" in dfs[selected_table].columns:
    df = dfs[selected_table].copy()
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce").dt.date

    min_date = df["Date"].min()
    max_date = df["Date"].max()

    # Range selector
    date_range = st.sidebar.date_input(
        "Select date range:",
        [min_date, max_date],
        min_value=min_date,
        max_value=max_date
    )

    # Apply filter
    if isinstance(date_range, list) and len(date_range) == 2:
        start_date, end_date = date_range
        df = df[(df["Date"] >= start_date) & (df["Date"] <= end_date)]





# Select granularity
granularity = st.sidebar.radio("Select granularity:", ["Daily", "Weekly", "Monthly"])

if selected_table in dfs:
    df = dfs[selected_table].copy()
    #st.write(f"### Table: {selected_table}")

    # Identify second column
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

    # Format Date column
    if "Date" in filtered_df.columns:
        filtered_df["Date"] = pd.to_datetime(filtered_df["Date"], errors="coerce")
        #filtered_df["Date"] = pd.to_datetime(filtered_df["Date"], errors="coerce").dt.date
        filtered_df = filtered_df.sort_values("Date", ascending=True)

        # --- Apply granularity ---
        if granularity == "Weekly":
            filtered_df["Period"] = filtered_df["Date"].dt.to_period("W").apply(lambda r: r.start_time)
            #filtered_df["Period"] = filtered_df["Date"]
        elif granularity == "Monthly":
            filtered_df["Period"] = filtered_df["Date"].dt.to_period("M").apply(lambda r: r.start_time)
            #filtered_df["Period"] = filtered_df["Date"]
        else:  # Daily
            filtered_df["Period"] = filtered_df["Date"]
            #filtered_df["Period"] = filtered_df["Date"]

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

        # Show filtered table
        #st.dataframe(filtered_df, use_container_width=True)
        st.write(f"Rows: {len(filtered_df)}, Columns: {len(filtered_df.columns)}")

        # --- Grouped Bar Graphs ---
        st.subheader(f"{selected_table} Bar Graphs ({granularity})")
        plot_df = agg_df.copy()
        plot_df["Period"] = pd.to_datetime(plot_df["Period"], errors="coerce").dt.strftime("%Y-%m-%d")

        # Remove duplicates
        plot_df = plot_df.drop_duplicates(subset=["Period", second_col])

        for col in numeric_cols:
            st.write(f"#### {col}")
            chart = (
                alt.Chart(plot_df)
                .mark_bar()
                .encode(
                    x=alt.X(
                        "Period:O",
                        title=granularity,
                        scale=alt.Scale(paddingInner=0.2, paddingOuter=0.1),
                        axis=alt.Axis(labelAngle=-45)  # no gridlines
                    ),
                    y=alt.Y(f"{col}:Q", title=col),
                    # Explicit color scheme or palette
                    color=alt.Color(
                        second_col,
                        legend=alt.Legend(title=second_col),
                        scale=alt.Scale(scheme="category20")  # distinct colors
                    ),
                    xOffset=second_col,   # group bars side-by-side
                    tooltip=["Period", second_col, col],
                )
                .properties(width=800, height=300)
            )
            st.altair_chart(chart, use_container_width=True)
        # Show filtered table
        st.write(f"### Table: {selected_table}")
        filtered_df["Date"] = pd.to_datetime(filtered_df["Date"], errors="coerce").dt.date 
        filtered_df = filtered_df.sort_values("Date", ascending=False)
        st.dataframe(filtered_df, use_container_width=True)

        ###

