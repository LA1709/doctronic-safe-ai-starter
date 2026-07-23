import streamlit as st
import sqlite3
import pandas as pd
import plotly.express as px

# ----------------------------------------------------
# Page Configuration
# ----------------------------------------------------

st.set_page_config(
    page_title="AI Prescription Governance",
    page_icon="💊",
    layout="wide",
)

st.title("💊 AI Prescription Governance")
st.caption(
    "Monitoring AI-assisted prescription renewals, validation failures, and audit logs."
)

# ----------------------------------------------------
# Load Data
# ----------------------------------------------------

conn = sqlite3.connect("audit.db")
df = pd.read_sql_query("SELECT * FROM decisions", conn)
conn.close()

df["timestamp"] = pd.to_datetime(df["timestamp"])

# ----------------------------------------------------
# Sidebar Filters
# ----------------------------------------------------

st.sidebar.header("Filters")

min_date = df["timestamp"].min().date()
max_date = df["timestamp"].max().date()

date_range = st.sidebar.date_input("Date Range", value=(min_date, max_date))

status_options = sorted(df["status"].unique())

status_filter = st.sidebar.multiselect("Status", status_options, default=status_options)

filtered = df.copy()

if len(date_range) == 2:
    start_date, end_date = date_range

    filtered = filtered[
        (filtered["timestamp"].dt.date >= start_date)
        & (filtered["timestamp"].dt.date <= end_date)
    ]

filtered = filtered[filtered["status"].isin(status_filter)]

# ----------------------------------------------------
# Clean Reason Labels
# ----------------------------------------------------


def clean_reason(reason):
    if pd.isna(reason):
        return "Approved"

    reason = str(reason)

    mappings = [
        ("age out of plausible range", "Invalid Age"),
        ("not a recognized trusted source", "Untrusted Source"),
        ("Field required", "Missing Required Field"),
        ("Input should be a valid integer", "Invalid Data Type"),
        ("approved medication", "Unknown Medication"),
        ("existing prescription history", "Missing Previous Prescription"),
        ("under 18", "Underage Controlled Substance"),
        ("outside the clinically accepted range", "Unsafe Dosage"),
        ("Dosage increased", "Excessive Dosage Increase"),
        ("controlled substance", "Requires Physician Review"),
        ("dosage exceeds hard safety ceiling", "Above Safety Ceiling"),
    ]

    for key, label in mappings:
        if key.lower() in reason.lower():
            return label

    return "Other"


filtered["reason_clean"] = filtered["reason"].apply(clean_reason)

# ----------------------------------------------------
# KPI Cards
# ----------------------------------------------------

total_requests = len(filtered)
processed = len(filtered[filtered["status"] == "processed"])
validation_failures = len(filtered[filtered["status"] == "rejected_at_validation"])

success_rate = processed / total_requests * 100 if total_requests else 0

c1, c2, c3, c4 = st.columns(4)

c1.metric("Total Requests", total_requests)
c2.metric("Processed", processed)
c3.metric("Validation Failures", validation_failures)
c4.metric("Validation Success", f"{success_rate:.1f}%")

st.divider()

# ----------------------------------------------------
# Charts
# ----------------------------------------------------

left, right = st.columns(2)

# ---------------- Decision Outcomes ----------------

with left:

    st.subheader("Decision Outcomes")

    status_counts = (
        filtered["status"]
        .value_counts()
        .rename_axis("Status")
        .reset_index(name="Count")
    )

    status_counts["Status"] = status_counts["Status"].str.replace("_", " ").str.title()

    fig = px.bar(status_counts, x="Status", y="Count", text="Count", color="Status")

    fig.update_traces(textposition="outside")

    fig.update_layout(
        showlegend=False, xaxis_title="", yaxis_title="Requests", height=420
    )

    st.plotly_chart(fig, use_container_width=True)

# ---------------- Validation Reasons ----------------

with right:

    st.subheader("Top Validation Failures")

    failures = filtered[filtered["status"] == "rejected_at_validation"]

    if len(failures):

        reason_counts = failures["reason_clean"].value_counts().reset_index()

        reason_counts.columns = ["Reason", "Count"]

        fig = px.bar(
            reason_counts,
            x="Count",
            y="Reason",
            orientation="h",
            text="Count",
            color="Reason",
        )

        fig.update_traces(textposition="outside")

        fig.update_layout(
            showlegend=False, xaxis_title="Requests", yaxis_title="", height=420
        )

        st.plotly_chart(fig, use_container_width=True)

    else:
        st.success("No validation failures.")

st.divider()

# ----------------------------------------------------
# Top Patients with Multiple Requests
# ----------------------------------------------------

st.subheader("Top Patients by Number of Requests")

patient_counts = filtered["patient_id"].value_counts().reset_index()

patient_counts.columns = ["Patient ID", "Requests"]

# Only show patients with more than one request
patient_counts = patient_counts[patient_counts["Requests"] > 1]

if len(patient_counts):

    fig = px.bar(
        patient_counts,
        x="Patient ID",
        y="Requests",
        text="Requests",
        color="Requests",
        color_continuous_scale="Blues",
    )

    fig.update_traces(textposition="outside")

    fig.update_layout(
        xaxis_title="Patient ID",
        yaxis_title="Number of Requests",
        coloraxis_showscale=False,
        height=400,
    )

    st.plotly_chart(fig, use_container_width=True)

else:
    st.info("No patients have submitted multiple requests in the selected period.")

# ----------------------------------------------------
# Validation Failure Table
# ----------------------------------------------------

st.subheader("Recent Validation Failures")

failures = filtered[filtered["status"] == "rejected_at_validation"].copy()

if len(failures):

    failures["Reason"] = failures["reason_clean"]

    st.dataframe(
        failures[
            [
                "patient_id",
                "Reason",
                "timestamp",
            ]
        ].sort_values("timestamp", ascending=False),
        use_container_width=True,
        hide_index=True,
    )

else:
    st.success("No validation failures recorded.")

st.divider()

# ----------------------------------------------------
# Search
# ----------------------------------------------------

st.subheader("Search Audit Log")

search = st.text_input("Patient ID")

display = filtered.copy()

if search:

    display = display[
        display["patient_id"].astype(str).str.contains(search, case=False)
    ]

display["Reason"] = display["reason_clean"]
display["Status"] = display["status"].str.replace("_", " ").str.title()

# ----------------------------------------------------
# Audit Trail
# ----------------------------------------------------

st.subheader("Decision Audit Log")

st.dataframe(
    display[
        [
            "patient_id",
            "Status",
            "Reason",
            "timestamp",
        ]
    ].sort_values("timestamp", ascending=False),
    use_container_width=True,
    hide_index=True,
)
