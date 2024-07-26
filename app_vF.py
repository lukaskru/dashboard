# FIRECRACKER - WEB APPLICATION

# Step 1: Import modules ----------------------------------------------------------------------------------------------------------------------------------------------
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import folium
from streamlit_folium import st_folium
from streamlit_js_eval import streamlit_js_eval



# Step 2: Define function to add custom css styles --------------------------------------------------------------------------------------------------------------------
def add_custom_css():
    st.markdown(
        """
        <style>
        .main {
            padding-top: 1.8rem;
        }
        .block-container {
            padding-top: 0rem;
        }
        </style>
        """,
        unsafe_allow_html=True
    )


# Step 3: Define functions to display filter options ----------------------------------------------------------------------------------------------------------------- 
# 3a: Define function to collect user input for years
def display_year_filters(data):
    start_year, end_year = st.sidebar.slider(
        "Select Year:",
        min_value=int(data["CalYear"].min()),
        max_value=int(data["CalYear"].max()),
        value=(int(data["CalYear"].min()), int(data["CalYear"].max())),
        step=1
    )
    return start_year, end_year


# 3b: Define function to collect user input for incident group
def display_incident_group_filter(data):
    incident_group_list = ["All Incidents", "False Alarm", "Fire", "Special Service"]
    incident_group = st.sidebar.selectbox("Select Incident Group:", incident_group_list)
    return incident_group


# 3c: Define function to collect user input for borough name
def display_borough_filter(data):
    borough_list = ["All Boroughs"] + list(data["IncGeo_BoroughName"].unique())
    borough_list.sort()
    borough_name = st.sidebar.selectbox("Select Borough:", borough_list)
    return borough_name



# Step 4: Define function to display incident facts -------------------------------------------------------------------------------------------------------------------
def display_incident_facts(unfiltered_data, filtered_data):
    # Display number of filtered incidents
    filtered_total = filtered_data.shape[0]
    first_metric_title = "Number of Displayed Incidents"
    formatted_filtered_total = '{:,}'.format(filtered_total)

    # Display percentage of total incidents
    total = unfiltered_data.shape[0]
    share_total = filtered_total / total * 100
    second_metric_title = "Percentage of All Incidents"
    if share_total == 100:
        formatted_share_total = "100%"
    else:
        formatted_share_total = f'{share_total:.1f}%'

    # Create two columns for side-by-side display
    with st.container():
        st.markdown("#### Incident Facts")
        col1, col2 = st.columns(2)
        with col1:
            st.metric(first_metric_title, formatted_filtered_total)
        with col2:
            st.metric(second_metric_title, formatted_share_total)



# Step 5: Define function to display development by incident group ----------------------------------------------------------------------------------------------------
def display_development_incident_group(filtered_data, start_year, end_year, incident_group, borough_name):
    # Customize chart based on user selection
    if incident_group == "All Incidents":
        name = "Incident"
        title = "Group"
        group_by_col = "IncidentGroup"
    else:
        name = f"{incident_group}"
        title = "Type"
        if incident_group == "Special Service":
            group_by_col = "Grouped_SpecialServiceType"
        else:
            group_by_col = "StopCodeDescription"

    # Group records by the relevant columns
    grouped_data = filtered_data.groupby(["CalYear", group_by_col]).size().reset_index(name="Count")
    
    # Pivot data for Plotly
    pivot_table = grouped_data.pivot(index="CalYear", columns=group_by_col, values="Count").fillna(0)
    
    # Create bar chart and dropdown menu for selection of chart type
    fig = go.Figure()
    with st.container():
        st.markdown(f"#### Split by {name} {title}")

        # Add dropdown menu to select chart type
        chart_type = st.selectbox("Select chart type:", ["Absolute", "Percentage"])

        # Customize chart based on selected chart type
        if chart_type == "Percentage":
            pivot_table = pivot_table.div(pivot_table.sum(axis=1), axis=0) * 100
            hovertemplate = "%{data.name}<br>%{y:.1f}%<extra></extra>"
            if borough_name != "All Boroughs":
                title_prefix = f"Percentage of {name}s in {borough_name}"
            else:
                title_prefix = f"Percentage of {name}s by {name} {title}"
        else:
            hovertemplate = "%{data.name}<br>%{y:,}<extra></extra>"
            if borough_name != "All Boroughs":
                title_prefix = f"Number of {name}s in {borough_name}"
            else:
                title_prefix = f"Number of {name}s by {name} {title}"

        # Separate "Other" category if it exists
        if "Other" in pivot_table.columns:
            columns_without_other = pivot_table.drop(columns=["Other"])
        else:
            columns_without_other = pivot_table

        # Sort columns except "Other"
        column_totals = columns_without_other.sum(axis=0)
        sorted_columns = column_totals.sort_values(ascending=False).index

        # Reconstruct pivot_table with sorted columns and "Other" last
        sorted_columns = sorted_columns.tolist()
        if "Other" in pivot_table.columns:
            sorted_columns.append("Other")
        pivot_table = pivot_table[sorted_columns]

        # Define color palette
        palette = ["#7891AA", "#83AC9A", "#BA749F", "#C6AA3D", "#9999FF", "#B6B6B6"]
        
        # Add traces to figure with specified colors
        for i, col in enumerate(pivot_table.columns):
            fig.add_trace(
                go.Bar(
                    x=pivot_table.index,
                    y=pivot_table[col],
                    name=col,
                    marker_color=palette[i % len(palette)],
                    opacity=0.75,
                    hovertemplate=hovertemplate
                )
            )

        # Add dynamic title
        dynamic_title = f"{title_prefix} ({start_year})" if start_year == end_year else f"{title_prefix} ({start_year}-{end_year})"

        # Define chart layout
        fig.update_layout(
            barmode="stack",
            title=dynamic_title,
            xaxis_title="Year",
            xaxis_tickvals=pivot_table.index,
            legend=dict( orientation="h", yanchor="top", y=-0.2, xanchor="center", x=0.5),
            height=500
        )

        st.plotly_chart(fig)



# Step 6: Define functions to display map and facts based on user selection -------------------------------------------------------------------------------------------
# 6a: Define function to display choropleth map - adapted based on Chowdhury (2022)
def display_map(unfiltered_data, filtered_data, start_year, end_year, incident_group, borough_name):
    # Filter data based on selected years and incident group
    filtered_without_borough = unfiltered_data[(unfiltered_data["CalYear"] >= start_year) & (unfiltered_data["CalYear"] <= end_year)]
    if incident_group != "All Incidents":
        filtered_without_borough = filtered_without_borough[filtered_without_borough["IncidentGroup"] == incident_group]
    
    # Initialize map with focus on London
    map = folium.Map(location=[51.50, -0.10], scrollWheelZoom=False, tiles="CartoDB positron")
    with st.container():
        st.markdown("#### Split by Borough")

        # Add dropdown menu to select map metric
        map_metric = st.selectbox("Select metric:", ["Number of Incidents", "Percentage of Delays", "Average Attendance Times (in seconds)", "Average Pump Minutes Rounded"])

        # Group data by selected metric per borough
        incidents_by_borough = filtered_without_borough.groupby("IncGeo_BoroughName").size()
        filtered_delays = filtered_without_borough[filtered_without_borough["Grouped_DelayType"] == "Delayed"]
        delays_by_borough = filtered_delays.groupby("IncGeo_BoroughName").size()
        avg_attendance_times_by_borough = filtered_without_borough.groupby("IncGeo_BoroughName")["FirstPumpArriving_AttendanceTime"].mean()
        pump_minutes_by_borough = filtered_without_borough.groupby("IncGeo_BoroughName")["PumpMinutesRounded"].mean()

        # Prepare data based on selected metric
        if map_metric == "Number of Incidents":
            data_to_plot = incidents_by_borough.reset_index(name="Data")
            if incident_group != "All Incidents":
                title_prefix = f"Number of {incident_group}s per Borough"
            else:
                title_prefix = "Total Number of Incidents per Borough"
        elif map_metric == "Percentage of Delays":
            share_delays_by_borough = (delays_by_borough / incidents_by_borough * 100).fillna(0)
            data_to_plot = share_delays_by_borough.reset_index(name="Data")
            if incident_group != "All Incidents":
                title_prefix = f"Percentage of Delays for {incident_group}s per Borough"
            else:
                title_prefix = f"Percentage of Delays of Incidents per Borough"
        elif map_metric == "Average Attendance Times (in seconds)":
            data_to_plot = avg_attendance_times_by_borough.reset_index(name="Data")
            if incident_group != "All Incidents":
                title_prefix = f"Average Attendance Time for {incident_group}s per Borough"
            else:
                title_prefix = "Average Attendance Time per Borough"
        else:
            data_to_plot = pump_minutes_by_borough.reset_index(name="Data")
            if incident_group != "All Incidents":
                title_prefix = f"Average Pump Minutes Rounded for {incident_group}s per Borough"
            else:
                title_prefix = "Average Pump Minutes Rounded per Borough"

        # Highlight selected borough
        if borough_name != "All Boroughs":
            for feature in folium.GeoJson("input/london-boroughs.geojson").data["features"]:
                if feature["properties"]["name"] == borough_name:
                    folium.GeoJson(
                        feature,
                        style_function=lambda x: {"color": "red", "weight": 8, "fillOpacity": 0}
                    ).add_to(map)
                    break

        # Create choropleth map
        choropleth = folium.Choropleth(
            geo_data="input/london-boroughs.geojson",
            data=data_to_plot,
            columns=["IncGeo_BoroughName", "Data"],
            key_on="feature.properties.name",
            line_opacity=0.8,
            highlight=True
        ).add_to(map)

        # Add tooltip for each borough
        data_indexed = data_to_plot.set_index("IncGeo_BoroughName")

        for feature in choropleth.geojson.data["features"]:
            borough_name_tooltip = feature["properties"]["name"]
            if borough_name_tooltip in data_indexed.index:
                value = data_indexed.loc[borough_name_tooltip, "Data"]
                if map_metric == "Number of Incidents":
                    feature["properties"]["data"] = '{:,}'.format(value)
                elif map_metric == "Percentage of Delays":
                    feature["properties"]["data"] = '{:.1f}%'.format(value)
                elif map_metric == "Average Attendance Times (in seconds)":
                    feature["properties"]["data"] = '{:.1f} sec'.format(value)
                else:
                    feature["properties"]["data"] = '{:.1f} min'.format(value)

        choropleth.geojson.add_child(
            folium.features.GeoJsonTooltip(["name", "data"], labels=False)
        )

        # Add dynamic title
        dynamic_title = f"{title_prefix} ({start_year})" if start_year == end_year else f"{title_prefix} ({start_year}-{end_year} aggregated)"
        st.markdown(f"###### {dynamic_title}")

        # Display choropleth map in Streamlit
        st_map = st_folium(map, width=700, height=540)
        display_stats_map(unfiltered_data, filtered_data, start_year, end_year, incident_group, borough_name, map_metric)



# 6b: Define function to display stats of map that match the user selection
def display_stats_map(unfiltered_data, filtered_data, start_year, end_year, incident_group, borough_name, map_metric):
    # Filter data only based on selected years and incident group
    filtered_without_borough = unfiltered_data[(unfiltered_data["CalYear"] >= start_year) & (unfiltered_data["CalYear"] <= end_year)]
    if incident_group != "All Incidents":
        filtered_without_borough = filtered_without_borough[filtered_without_borough["IncidentGroup"] == incident_group]

    if map_metric == "Number of Incidents":
        average_all_boroughs = filtered_without_borough.groupby("IncGeo_BoroughName").size().mean()
        if borough_name == "All Boroughs":
            statistic = round(average_all_boroughs)
            if incident_group != "All Incidents":
                prefix = f"Average Number of {incident_group}s per Borough"
            else:
                prefix = "Average Number of Incidents per Borough"
        else:
            statistic = round(filtered_data.groupby("IncGeo_BoroughName").size().mean() - average_all_boroughs)
            prefix = f"Deviation of <strong>{borough_name}</strong> from Average across Boroughs"
        dynamic_text = f"{prefix} ({start_year}): <strong>{statistic:,}</strong>" if start_year == end_year else f"{prefix} ({start_year}-{end_year}): <strong>{statistic:,}</strong>"

    elif map_metric == "Percentage of Delays":
        filtered_delays = filtered_data[filtered_data["Grouped_DelayType"] == "Delayed"]
        statistic = round(len(filtered_delays) / len(filtered_data) * 100, 1)
        if borough_name == "All Boroughs":
            prefix = "Average Percentage of Delays per Borough"
        else:
            prefix = f"Average Percentage of Delays for <strong>{borough_name}</strong>"
        dynamic_text = f"{prefix} ({start_year}): <strong>{statistic}%</strong>" if start_year == end_year else f"{prefix} ({start_year}-{end_year}): <strong>{statistic}%</strong>"

    elif map_metric == "Average Attendance Times (in seconds)":
        statistic = round(filtered_data["FirstPumpArriving_AttendanceTime"].mean(), 1)
        if borough_name == "All Boroughs":
            prefix = "Average Attendance Time per Borough"
        else:
            prefix = f"Average Attendance Time for <strong>{borough_name}</strong>"
        dynamic_text = f"{prefix} ({start_year}): <strong>{statistic} sec</strong>" if start_year == end_year else f"{prefix} ({start_year}-{end_year}): <strong>{statistic} sec</strong>"

    else:
        statistic = round(filtered_data["PumpMinutesRounded"].mean(), 1)
        if borough_name == "All Boroughs":
            prefix = "Average Pump Minutes Rounded per Borough"
        else:
            prefix = f"Average Pump Minutes Rounded for <strong>{borough_name}</strong>"
        dynamic_text = f"{prefix} ({start_year}): <strong>{statistic} min</strong>" if start_year == end_year else f"{prefix} ({start_year}-{end_year}): <strong>{statistic} min</strong>"

    st.markdown(f"<div style='text-align: center; font-style: italic;'>{dynamic_text}</div>", unsafe_allow_html=True)



# Step 7: Define function to display incidents by time period ----------------------------------------------------------------------------------------------------------
def display_incidents_by_time(filtered_data, start_year, end_year, incident_group, borough_name):
    # Customize chart based on user selection
    if incident_group == "All Incidents":
        name = "Incident"
        group_by_col = "IncidentGroup"
    else:
        name = f"{incident_group}"
        if incident_group == "Special Service":
            group_by_col = "Grouped_SpecialServiceType"
        else:
            group_by_col = "StopCodeDescription"

    # Group records by the relevant columns
    grouped_data_by_month = filtered_data.groupby(["Month", group_by_col]).size().reset_index(name="Count")
    grouped_data_by_weekday = filtered_data.groupby(["DayOfWeek", group_by_col]).size().reset_index(name="Count")
    grouped_data_by_hour = filtered_data.groupby(["HourOfCall", group_by_col]).size().reset_index(name="Count")

    # Define order to display time periods
    month_order = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    day_of_week_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

    # Create bar chart and dropdown menu for selection of time period
    fig = go.Figure()
    with st.container():
        st.markdown("#### Split by Time Period")

        # Add dropdown menu to select time period
        time_period = st.selectbox("Select time period:", ["Month", "Day of Week", "Hour of Day"])

        # Customize chart based on selected time period
        if time_period == "Month":
            pivot_table = grouped_data_by_month.pivot(index="Month", columns=group_by_col, values="Count").fillna(0)
            pivot_table.index = pd.Categorical(pivot_table.index, categories=month_order, ordered=True)
            pivot_table = pivot_table.sort_index()
            xaxis_title = "Month"
            if borough_name != "All Boroughs":
                title_prefix = f"Number of {name}s per Month in {borough_name}"
            else:
                title_prefix = f"Number of {name}s per Month"

        elif time_period == "Day of Week":
            pivot_table = grouped_data_by_weekday.pivot(index="DayOfWeek", columns=group_by_col, values="Count").fillna(0)
            pivot_table.index = pd.Categorical(pivot_table.index, categories=day_of_week_order, ordered=True)
            pivot_table = pivot_table.sort_index()
            xaxis_title = "Day of Week"
            if borough_name != "All Boroughs":
                title_prefix = f"Number of {name}s per Weekday in {borough_name}"
            else:
                title_prefix = f"Number of {name}s per Weekday"

        else:
            pivot_table = grouped_data_by_hour.pivot(index="HourOfCall", columns=group_by_col, values="Count").fillna(0)     
            xaxis_title = "Hour of Day"
            if borough_name != "All Boroughs":
                title_prefix = f"Number of {name}s per Hour in {borough_name}"
            else:
                title_prefix = f"Number of {name}s per Hour"

        # Separate "Other" category if it exists
        if "Other" in pivot_table.columns:
            columns_without_other = pivot_table.drop(columns=["Other"])
        else:
            columns_without_other = pivot_table

        # Sort columns except "Other"
        column_totals = columns_without_other.sum(axis=0)
        sorted_columns = column_totals.sort_values(ascending=False).index

        # Reconstruct pivot_table with sorted columns and "Other" last
        sorted_columns = sorted_columns.tolist()
        if "Other" in pivot_table.columns:
            sorted_columns.append("Other")
        pivot_table = pivot_table[sorted_columns]

        # Define color palette
        palette = ["#7891AA", "#83AC9A", "#BA749F", "#C6AA3D", "#9999FF", "#B6B6B6"]

        # Add traces to figure
        for i, col in enumerate(pivot_table.columns):
                fig.add_trace(
                    go.Bar(
                        x=pivot_table.index,
                        y=pivot_table[col],
                        name=col,
                        marker_color=palette[i % len(palette)],
                        opacity=0.75,
                        hovertemplate=f"{col}<br>%{{y:,}}<extra></extra>"
                    )
                )

        # Add dynamic title
        dynamic_title = f"{title_prefix}<br>({start_year})" if start_year == end_year else f"{title_prefix}<br>({start_year}-{end_year} aggregated)"

        # Define chart layout
        fig.update_layout(
            barmode="stack",
            title=dynamic_title,
            xaxis_title=xaxis_title, 
            xaxis_tickvals=pivot_table.index,
            legend=dict( orientation="h", yanchor="top", y=-0.2, xanchor="center", x=0.5),
            height=450
        )

        st.plotly_chart(fig)



# Step 8: Define function to display comparison of average response times ----------------------------------------------------------------------------------------------
def display_average_times(unfiltered_data, filtered_data, filtered_quarters, start_year, end_year, incident_group, borough_name):
    # Define helper function to calculate aggregated average
    def calculate_aggregated_average(data, filter_column, filter_value, groupby_column, metric, rounding):
        filtered_data = data[data[filter_column] == filter_value]
        calculate_aggregated_average = filtered_data.groupby(groupby_column)[metric].mean().round(rounding)
        return calculate_aggregated_average
    
    # Filter data only based on selected years and borough
    filtered_without_incident_group = unfiltered_data[(unfiltered_data["CalYear"] >= start_year) & (unfiltered_data["CalYear"] <= end_year)]
    if borough_name != "All Boroughs":
        filtered_without_incident_group = filtered_without_incident_group[filtered_without_incident_group["IncGeo_BoroughName"] == borough_name]

    # Calculate average times
    average_times = filtered_data.groupby("Quarter_Year").agg({
        "FirstPumpArriving_AttendanceTime": "mean",
        "TravelTimeSeconds": "mean",
        "TurnoutTimeSeconds": "mean"
    }).round(2)

    # Calculate average attendance times by incident group
    times_false_alarm = calculate_aggregated_average(filtered_without_incident_group, "IncidentGroup", "False Alarm", "Quarter_Year", "FirstPumpArriving_AttendanceTime", 2)
    times_special_service = calculate_aggregated_average(filtered_without_incident_group, "IncidentGroup", "Special Service", "Quarter_Year", "FirstPumpArriving_AttendanceTime", 2)
    times_fire = calculate_aggregated_average(filtered_without_incident_group, "IncidentGroup", "Fire", "Quarter_Year", "FirstPumpArriving_AttendanceTime", 2)

    average_times_incident_group = pd.DataFrame({
        "False Alarm": times_false_alarm, 
        "Special Service": times_special_service,
        "Fire": times_fire
    })

    # Reindex data and change x-axis title if only one, two, or three years are selected
    average_times = average_times.reindex(filtered_quarters)
    average_times_incident_group = average_times_incident_group.reindex(filtered_quarters)

    # Replace underscores in x-axis labels
    average_times.index = average_times.index.str.replace("_", " ")
    average_times_incident_group.index = average_times_incident_group.index.str.replace("_", " ")

    # Create line chart
    fig = go.Figure()
    with st.container():
        st.markdown("#### Response Times of First Pump")

        # Add dropdown menu to select metric for comparison
        comparison_metric = st.selectbox("Select comparison metric:", ["Average Attendance Time by Component", "Average Attendance Time by Incident Group"])

         # Define common chart settings
        name = f"{incident_group}s" if incident_group != "All Incidents" else incident_group

        # Customize chart based on user selection
        if comparison_metric == "Average Attendance Time by Component":
            data = average_times
            title_prefix = f"Response Times for {name} in {borough_name}" if borough_name != "All Boroughs" else f"Response Times for {name}"
            legend_names = {"FirstPumpArriving_AttendanceTime": "Attendance Time", "TravelTimeSeconds": "Travel Time", "TurnoutTimeSeconds": "Turnout Time"}
            y_min = 0
            palette = ["#BA749F", "#83AC9A", "#7891AA"]
        else:
            data = average_times_incident_group
            title_prefix = f"Attendance Times for {name} in {borough_name}" if borough_name != "All Boroughs" else f"Attendance Times for {name}"
            legend_names = {"False Alarm": "False Alarm", "Special Service": "Special Service", "Fire": "Fire"}
            y_min = np.floor(data.min().min() / 50) * 50
            if incident_group == "False Alarm":
                palette = ["#7891AA", "#A9A9A9", "#D3D3D3"]
            elif incident_group == "Fire":
                palette = ["#A9A9A9", "#D3D3D3", "#BA749F"]
            elif incident_group == "Special Service":
                palette = ["#A9A9A9", "#83AC9A", "#D3D3D3"]
            else:
                palette = ["#7891AA", "#83AC9A", "#BA749F"]

        # Add traces to figure
        for i, col in enumerate(data.columns):
            fig.add_trace(go.Scatter(
                x=data.index,
                y=data[col],
                mode="lines",
                name=legend_names.get(col, col),
                line=dict(width=2.5, color=palette[i % len(palette)]),
                hovertemplate=f"{legend_names.get(col, col)}<br>%{{x}}<br>%{{y:.1f}} sec<extra></extra>"
            ))

        # Add dynamic title
        dynamic_title = f"{title_prefix}<br>({start_year}, average in seconds)" if start_year == end_year else f"{title_prefix}<br>({start_year}-{end_year}, average in seconds)"

        # Calculate max y value and round up to nearest multiple of 50
        y_max = data.max().max()
        y_max_rounded = np.ceil(y_max / 50) * 50

        # Define chart layout
        fig.update_layout(
            title=dynamic_title,
            xaxis_title="Quarter",
            yaxis=dict(dtick=50, range=[y_min, y_max_rounded]),
            legend=dict( orientation="h", yanchor="top", y=-0.4, xanchor="center", x=0.5),
            height=450
        )

        st.plotly_chart(fig)



# Step 9: Define function to display split by property category -------------------------------------------------------------------------------------------------------
def display_split_by_property(filtered_data, start_year, end_year, incident_group, borough_name):
    # Group records by "Grouped_PropertyCategory", calculate percentage share, and sort in descending order
    property_categories = filtered_data.groupby("Grouped_PropertyCategory").size().reset_index(name="Count")
    total_count = property_categories["Count"].sum()
    property_categories["Percentage"] = (property_categories["Count"] / total_count) * 100
    property_categories = property_categories.sort_values(by="Percentage", ascending=False)

    # Group by "PropertyType", identify 5 largest property types, and aggregate data
    property_types = filtered_data.groupby("PropertyType").size().reset_index(name="Count").sort_values(by="Count", ascending=False)
    property_types_top_5 = property_types.head(5)
    property_types_others = property_types.iloc[5:]
    other_count = property_types_others["Count"].sum()
    other_df = pd.DataFrame({"PropertyType": ["Other"], "Count": [other_count]})
    property_types_aggregated = pd.concat([property_types_top_5, other_df], ignore_index=True)

    # Create vertical bar chart
    fig = go.Figure()
    with st.container():
        # Define placeholder for markdown title
        title_placeholder = st.empty()
        
        # Add dropdown menu to select property metric with default value "Property Category"
        property_metric = st.selectbox("Select property metric:", ["Property Category", "Property Type"], index=0)

        # Update markdown title based on user selection
        title_placeholder.markdown(f"#### Split by {property_metric}")

        # Select appropriate data
        if property_metric == "Property Category":
            data = property_categories
            name_column = "Grouped_PropertyCategory"
            color_mapping = {name: color for name, color in zip(data[name_column].unique(), ["#7891AA", "#83AC9A", "#BA749F", "#C6AA3D", "#9999FF", "#C4A484", "#B6B6B6"])}
            chart_height = 500
        else:
            data = property_types_aggregated
            name_column = "PropertyType"
            color_mapping = {name: color for name, color in zip(data[name_column].unique(), ["#7891AA", "#83AC9A", "#BA749F", "#C6AA3D", "#9999FF", "#B6B6B6"])}
            chart_height = 538

        # Add traces to the figure
        for i, row in data.iterrows():
            percentage = (row["Count"] / data["Count"].sum()) * 100
            fig.add_trace(
                go.Bar(
                    x=[property_metric],
                    y=[percentage],
                    name=row[name_column],
                    marker_color=color_mapping.get(row[name_column], "#B6B6B6"),
                    opacity=0.75,
                    hovertemplate=(
                        f"{row[name_column]}<br>"
                        f"Count: {row['Count']:,.0f}<br>"
                        f"Share: {percentage:.1f}%<extra></extra>"
                    ), 
                    width=0.4
                )
            )

        # Add dynamic title
        name = "Incident" if incident_group == "All Incidents" else incident_group
        title_prefix = f"{name}s in {borough_name}" if borough_name != "All Boroughs" else f"{name}s"
        dynamic_title = f"{title_prefix}<br>({start_year}, in %)" if start_year == end_year else f"{title_prefix}<br>({start_year}-{end_year} aggregated, in %)"

        # Define chart layout
        fig.update_layout(
            barmode="stack",
            title=dynamic_title,
            legend=dict( orientation="h", yanchor="top", y=-0.1, xanchor="center", x=0.5), 
            height=chart_height
        )

        st.plotly_chart(fig)



# Step 10: Define and excute "main" function --------------------------------------------------------------------------------------------------------------------------
# 10a: Define function to display web application
def main():
    # Set configurations
    st.set_page_config(
        page_title="LFB Dashboard",
        page_icon="🚒",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # Set title
    st.title("LFB Incident and Mobilization Records")

    # Add custom CSS
    add_custom_css()

    # Load LFB data using caching
    @st.cache_data
    def load_data():
        df = pd.read_csv("input/reduced_records.csv")
        return df
    all_records = load_data()

    # Create sidebar and add filter options
    st.sidebar.header("Filter Options")
    start_year, end_year = display_year_filters(all_records)
    incident_group = display_incident_group_filter(all_records)
    borough_name = display_borough_filter(all_records)

    # Add reset button to sidebar - taken from Blackwood (2023)
    if st.sidebar.button("Reset All Filters"):
        streamlit_js_eval(js_expressions="parent.window.location.reload()")

    # Add info box to sidebar
    with st.sidebar.expander("About this Dashboard 💡", expanded=True):
        st.write("""
        Welcome to the LFB Dashboard!

        Here you can explore historical incident and mobilization records of the London Fire Brigade (LFB):
        - Filter all charts by selecting specific year ranges, incident groups, or boroughs from above
        - Customize individual charts by using different dropdown options   

        ---

        Data published via London Datastore:
        - [LFB Incident Records](https://data.london.gov.uk/dataset/london-fire-brigade-incident-records)
        - [LFB Mobilization Records](https://data.london.gov.uk/dataset/london-fire-brigade-mobilisation-records)
        """)

    # Filter data based on user selections
    filtered_records = all_records[(all_records["CalYear"] >= start_year) & (all_records["CalYear"] <= end_year)]
    if incident_group != "All Incidents":
        filtered_records = filtered_records[(filtered_records["IncidentGroup"] == incident_group)]
    if borough_name != "All Boroughs":
        filtered_records = filtered_records[(filtered_records["IncGeo_BoroughName"] == borough_name)]

    # Generate list of quarters for selected years
    quarters_range = [f"Q{i}_{year}" for year in range(start_year, end_year + 1) for i in range(1, 5)]
    filtered_quarters = [q for q in quarters_range if q in filtered_records["Quarter_Year"].unique()]

    # Create first row in grid
    row1_col1, row_col2 = st.columns([1, 1])
    with row1_col1:
        display_incident_facts(all_records, filtered_records)
        display_development_incident_group(filtered_records, start_year, end_year, incident_group, borough_name)
    with row_col2:
        display_map(all_records, filtered_records, start_year, end_year, incident_group, borough_name)
    
    # Create second row in grid
    row2_col1, row2_col2, row2_col3 = st.columns([1.5, 1.5, 1])
    with row2_col1:
        st.write("")
        st.write("")
        display_incidents_by_time(filtered_records, start_year, end_year, incident_group, borough_name)
    with row2_col2:
        st.write("")
        st.write("")
        display_average_times(all_records, filtered_records, filtered_quarters, start_year, end_year, incident_group, borough_name)
    with row2_col3:
        st.write("")
        st.write("")
        display_split_by_property(filtered_records, start_year, end_year, incident_group, borough_name)


# 10b: Run "main" function
if __name__ == "__main__":
    main()