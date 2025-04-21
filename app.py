import streamlit as st
import pandas as pd
from bokeh.plotting import figure
from bokeh.models import ColumnDataSource, Whisker, HoverTool
from bokeh.palettes import Category20
from bokeh.models.tools import HoverTool
from bokeh.embed import components

st.set_page_config(page_title="Grip Strength Visualization", layout="wide")
st.title("Grip Strength Plotter (Sham vs VNS)")

uploaded_file = st.file_uploader("Upload your CSV or Excel file", type=["csv", "xlsx"])

if uploaded_file:
    # Read file
    if uploaded_file.name.endswith("csv"):
        data = pd.read_csv(uploaded_file)
    else:
        data = pd.read_excel(uploaded_file)

    # Check necessary columns
    expected_columns = {"Trial", "Average", "Week", "Type"}
    if not expected_columns.issubset(data.columns):
        st.error(f"File must contain columns: {expected_columns}")
    elif not set(data['Type'].unique()).issubset({"Sham", "VNS"}):
        st.error("Type column must only contain 'Sham' and 'VNS' values.")
    else:
        st.success("File format looks good!")

        # Group and calculate mean and std
        summary = data.groupby(['Week', 'Type'])['Average'].agg(['mean', 'std']).reset_index()
        summary['upper'] = summary['mean'] + summary['std']
        summary['lower'] = summary['mean'] - summary['std']

        sham_summary = summary[summary['Type'] == 'Sham']
        vns_summary = summary[summary['Type'] == 'VNS']

        source_sham = ColumnDataSource(sham_summary)
        source_vns = ColumnDataSource(vns_summary)

        # Create Bokeh plot
        p = figure(
            width=900, height=600,
            title='Grip Strength Over Time by Type (With Individual Traces)',
            x_axis_label='Weeks After Nerve Injury',
            y_axis_label='Grip Strength',
            tools="pan,wheel_zoom,box_zoom,reset,save,hover",
        )

        # Plot each Trial
        for trial in data['Trial'].unique():
            trial_data = data[data['Trial'] == trial]
            rat_type = trial_data['Type'].iloc[0]
            color = 'lightcoral' if rat_type == 'Sham' else 'lightskyblue'
            source = ColumnDataSource(trial_data)
            p.line('Week', 'Average', source=source, line_width=1, alpha=0.5, color=color)
            p.circle('Week', 'Average', source=source, size=4, alpha=0.5, color=color)

        # Plot group means
        p.line('Week', 'mean', source=source_sham, color='blue', line_width=3, legend_label='Sham (mean ± SD)')
        p.circle('Week', 'mean', source=source_sham, size=6, color='blue')

        p.line('Week', 'mean', source=source_vns, color='red', line_width=3, legend_label='VNS (mean ± SD)')
        p.circle('Week', 'mean', source=source_vns, size=6, color='red')

        # Whiskers for SD
        p.add_layout(Whisker(source=source_sham, base='Week', upper='upper', lower='lower', line_color='blue'))
        p.add_layout(Whisker(source=source_vns, base='Week', upper='upper', lower='lower', line_color='red'))

        # Set x-axis range
        p.x_range.start = -2
        p.x_range.end = 5

        # Hover tool
        hover = p.select(dict(type=HoverTool))
        hover.tooltips = [
            ("Week", "@Week"),
            ("Grip Strength", "@mean"),
        ]

        p.legend.location = "top_right"
        p.legend.click_policy = "hide"

        # Embed Bokeh plot into Streamlit
        from bokeh.embed import components
        script, div = components(p)
        st.bokeh_chart(p, use_container_width=True)

else:
    st.info("Please upload a CSV or Excel file to continue.")
