# imports
import os, re, streamlit as st, pandas as pd
from bokeh.plotting import figure
from bokeh.models import ColumnDataSource, Whisker, HoverTool

st.set_page_config(page_title="Functional Assessments (Cylinder & Grip Strength)", layout="wide")

st.title("Functional Recovery Plotter (Cylinder Paw Preference & Grip Strength)")

def _read_file(uploaded_file: "st.runtime.uploaded_file_manager.UploadedFile") -> pd.DataFrame:
    """Read an uploaded CSV/XLSX into a DataFrame, preserving headers."""
    if uploaded_file.name.lower().endswith("csv"):
        return pd.read_csv(uploaded_file)
    return pd.read_excel(uploaded_file)

tab_cyl, tab_grip = st.tabs(["Cylinder Assessment", "Grip Strength"])

with tab_cyl:
    st.subheader("Cylinder Assessment (Paw Preference)")
    cyl_file = st.file_uploader(
        "Upload cylinder CSV or Excel — required columns: Animal ID, Date, Left, Right, Time, Type", 
        type=["csv","xlsx"], key="cyl_uploader")

    if cyl_file:
        df = _read_file(cyl_file)
        df.columns = df.columns.map(str)
        expected_cols = {"Animal ID","Date","Left","Right","Time","Type"}
        if not expected_cols.issubset(df.columns):
            st.error(f"Missing columns: {expected_cols - set(df.columns)}")
            st.stop()

        df = df.rename(columns={"Animal ID":"Animal"}).copy()
        df["Time"] = df["Time"].astype(str).str.strip()
        df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
        df["Type"] = df["Type"].astype(str).str.strip()
        df["Score"] = df["Right"] / (df["Left"] + df["Right"]) * 100
        agg = (df.groupby(["Time","Type"], as_index=False)["Score"].agg(mean="mean", sd="std", count="count"))
        agg["sem"]   = agg["sd"] / agg["count"].pow(0.5)
        agg["upper"] = agg["mean"] + agg["sem"]
        agg["lower"] = agg["mean"] - agg["sem"]
        time_order = (df.groupby("Time")["Date"].min().sort_values().index.tolist())
        agg = agg[agg["Time"].isin(time_order)]
        agg["Time"] = pd.Categorical(agg["Time"], categories=time_order, ordered=True)
        agg = agg.sort_values("Time")
        p = figure(
            x_range=time_order,
            height=500, width=900,
            title="Cylinder Paw Preference",
            toolbar_location="above",
            tools="pan,wheel_zoom,box_zoom,reset,save,hover")

        colors = {"VNS":"red","Sham":"blue"}
        hover = HoverTool(tooltips=[
            ("Type","@Type"),
            ("Time","@Time"),
            ("Mean","@mean{0.2f}"),
            ("SEM","@sem{0.2f}")])
        p.add_tools(hover)

        for t in agg["Type"].unique():
            sub = agg[agg["Type"]==t]
            source = ColumnDataSource({
                "Time": sub["Time"].astype(str),
                "mean": sub["mean"],
                "sem": sub["sem"],
                "upper": sub["upper"],
                "lower": sub["lower"],
                "Type": sub["Type"]})
            color = colors.get(t, "gray")
            p.line("Time","mean",source=source,line_width=2,color=color,legend_label=t)
            p.circle("Time","mean",source=source,size=8,color=color,legend_label=t)
            p.add_layout(Whisker(source=source,base="Time",upper="upper",lower="lower",line_color=color))

        p.xaxis.major_label_orientation = 0.785
        p.xaxis.axis_label = "Time Point"
        p.yaxis.axis_label = "Paw Preference (%)"
        p.legend.title = "Type"
        p.legend.click_policy = "hide"
        st.bokeh_chart(p,use_container_width=True)

with tab_grip:
    st.subheader("Grip Strength Plotter - Sham vs VNS")
    uploaded_file = st.file_uploader("Upload your CSV or Excel file", type=["csv","xlsx"], key="gs_uploader")
    if uploaded_file:
        if uploaded_file.name.endswith("csv"):
            data = pd.read_csv(uploaded_file)
        else:
            data = pd.read_excel(uploaded_file)
        data.columns = data.columns.map(str)
        expected_columns = {"Trial","Average","Week","Type"}
        if not expected_columns.issubset(data.columns):
            st.error(f"File must contain columns: {expected_columns}")
        elif not set(data["Type"].unique()).issubset({"Sham","VNS"}):
            st.error("Type column must only contain 'Sham' and 'VNS' values.")
        else:
            st.success("File format looks good!")
            summary = (data.groupby(["Week","Type"])["Average"].agg(mean="mean", sd="std", count="count").reset_index())
            summary["sem"]   = summary["sd"] / summary["count"].pow(0.5)
            summary["upper"] = summary["mean"] + summary["sem"]
            summary["lower"] = summary["mean"] - summary["sem"]
            sham_summary = summary[summary["Type"]=="Sham"]
            vns_summary  = summary[summary["Type"]=="VNS"]
            source_sham = ColumnDataSource(sham_summary)
            source_vns  = ColumnDataSource(vns_summary)
            p = figure(width=900, height=600,
                       title="Grip Strength",
                       x_axis_label="Weeks After Nerve Injury",
                       y_axis_label="Grip Strength",
                       tools="pan,wheel_zoom,box_zoom,reset,save,hover")
            for trial in data["Trial"].unique():
                trial_data = data[data["Trial"]==trial]
                rat_type   = trial_data["Type"].iloc[0]
                color      = "lightcoral" if rat_type=="Sham" else "lightskyblue"
                source     = ColumnDataSource(trial_data)
                p.line("Week","Average",source=source,line_width=1,alpha=0.5,color=color)
                p.circle("Week","Average",source=source,size=4,alpha=0.5,color=color)
            p.line("Week","mean",source=source_sham,color="blue",line_width=3,legend_label="Sham")
            p.circle("Week","mean",source=source_sham,size=6,color="blue")
            p.line("Week","mean",source=source_vns,color="red",line_width=3,legend_label="VNS")
            p.circle("Week","mean",source=source_vns,size=6,color="red")
            p.add_layout(Whisker(source=source_sham,base="Week",upper="upper",lower="lower",line_color="blue"))
            p.add_layout(Whisker(source=source_vns,base="Week",upper="upper",lower="lower",line_color="red"))
            hover = p.select(dict(type=HoverTool))
            hover.tooltips=[("Week","@Week"),("Grip Strength","@mean{0.2f}")]
            p.legend.location="top_right"
            p.legend.click_policy="hide"
            st.bokeh_chart(p,use_container_width=True)
    else:
        st.info("Please upload a CSV or Excel file to continue.")