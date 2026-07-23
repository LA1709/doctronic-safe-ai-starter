
import streamlit as st
import sqlite3
import pandas as pd

st.title("Prescription Renewal Oversight Dashboard")

conn = sqlite3.connect("audit.db")
df = pd.read_sql_query("SELECT * FROM decisions", conn)

df["timestamp"] = pd.to_datetime(df["timestamp"])
min_date, max_date = df["timestamp"].min().date(), df["timestamp"].max().date()
date_range = st.date_input("Date range", value=(min_date, max_date))

status_filter = st.multiselect("Filter by status", df["status"].unique(), default=df["status"].unique())
filtered = df[df["status"].isin(status_filter)]

st.metric("Total requests logged", len(df))
st.metric("Flagged for physician review", len(df[df["status"] != "processed"]))

st.bar_chart(filtered["status"].value_counts())
st.dataframe(filtered.sort_values("timestamp", ascending=False))
