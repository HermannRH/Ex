import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go

# Load the data
data_file = 'data.csv'
data = pd.read_csv(data_file)

# Ensure 'Collection Days' is numeric
data['Collection Days'] = pd.to_numeric(data['Collection Days'], errors='coerce')

# Sidebar Filters
st.sidebar.header("Filters")

# Dropdown for excluding countries
countries = data['Country'].dropna().unique()
selected_countries = st.sidebar.multiselect("Exclude Countries:", countries, default=[])

# Range slider for minimum revenue
min_revenue = st.sidebar.slider("Minimum Revenue:", 
                              min_value=float(data['Revenue'].min()), 
                              max_value=float(data['Revenue'].max()), 
                              value=float(data['Revenue'].min()))

# Date filter for Year-Month
year_months = data['[Year-Month]'].dropna().unique()
selected_dates = st.sidebar.multiselect("Filter by Year-Month:", year_months, default=year_months)

# Filter the dataset
filtered_data = data[(~data['Country'].isin(selected_countries)) &
                    (data['Revenue'] >= min_revenue) &
                    (data['[Year-Month]'].isin(selected_dates))]

# Main Dashboard Title
st.title("Business Performance Dashboard")

# Analysis Section
st.header("Analysis")

# Lost Clients Analysis
st.subheader("Lost Clients")
filtered_data['Quarter'] = pd.to_datetime(filtered_data['[Year-Month]']).dt.to_period('Q')
quarters = ['2023Q4', '2024Q1']
client_revenue = pd.DataFrame()

for quarter in quarters:
    quarter_data = filtered_data[filtered_data['Quarter'] == quarter].groupby('Client name')['Revenue'].sum()
    client_revenue[quarter] = quarter_data

client_revenue = client_revenue.fillna(0)
client_revenue['Change'] = client_revenue['2024Q1'] - client_revenue['2023Q4']
lost_clients = client_revenue[client_revenue['2024Q1'] == 0].reset_index()

# Style the lost clients dataframe with color gradients
def color_scale(val):
    if val < 0:
        return f'background-color: rgba(255, 0, 0, {abs(val/lost_clients["Change"].min())})'
    return ''

st.dataframe(
    lost_clients.style.apply(lambda x: [color_scale(v) if i > 0 else '' for i, v in enumerate(x)], axis=1),
    column_config={
        "Client name": "Client Name",
        "2023Q4": st.column_config.NumberColumn(
            "Q4 2023 Revenue",
            help="Revenue in Q4 2023",
            format="$%d"
        ),
        "Change": st.column_config.NumberColumn(
            "Revenue Change",
            help="Change in revenue",
            format="$%d"
        )
    },
    hide_index=True
)


# Lost Clients Visualization - Top 10 clients with the most revenue change loss
top_lost_clients = lost_clients.nsmallest(10, 'Change')

fig_lost_clients = px.bar(top_lost_clients, 
                          x='Client name', 
                          y='Change',
                          title='Top 10 Clients with Most Revenue Change Loss',
                          labels={'Change': 'Revenue Change', 'Client name': 'Client Name'},
                          text='Change')
fig_lost_clients.update_traces(texttemplate='%{text:.2s}', textposition='outside')
fig_lost_clients.update_layout(uniformtext_minsize=8, uniformtext_mode='hide')

st.plotly_chart(fig_lost_clients)

# Service Lines Analysis
st.subheader("Service Lines Trends")
service_line_quarterly = filtered_data.groupby(['Service Lines', 'Quarter'])['Revenue'].sum().unstack(fill_value=0)
service_line_quarterly = service_line_quarterly.reindex(columns=quarters)
service_line_quarterly['Change'] = service_line_quarterly['2024Q1'] - service_line_quarterly['2023Q4']
service_line_quarterly = service_line_quarterly.sort_values('Change')

# Style with color gradients
def color_gradient(s):
    # Convert series to numeric, coercing errors to NaN
    s = pd.to_numeric(s, errors='coerce')
    
    if s.max() == 0 or pd.isna(s.max()):
        return [''] * len(s)
    
    return ['background-color: #{:02x}ff{:02x}'.format(
        int(255*(1-float(v)/float(s.max()) if not pd.isna(v) else 0)), 
        int(255*(float(v)/float(s.max()) if not pd.isna(v) else 0))) 
        for v in s]

st.dataframe(
    service_line_quarterly.style.apply(color_gradient),
    column_config={
        col: st.column_config.NumberColumn(
            col,
            help=f"Revenue in {col}",
            format="$%d"
        ) for col in service_line_quarterly.columns
    }
)

# Service Lines Visualization
fig_service_lines = px.line(service_line_quarterly.reset_index(), 
                           x='Service Lines',
                           y=quarters,
                           title='Service Lines Revenue Trends')
st.plotly_chart(fig_service_lines)

# Service Offerings Analysis (New)
st.subheader("Service Offerings Analysis")

# Create a more manageable dataframe structure
service_offerings_data = filtered_data.groupby('Service Offerings').agg({
    'Revenue': 'sum',
    'Total Cost': 'sum',
    'Gross Profit': 'sum',
    'Direct Profit': 'sum'
}).reset_index()

# Create a melted dataframe for visualization
service_offerings_melted = pd.melt(
    service_offerings_data,
    id_vars=['Service Offerings'],
    value_vars=['Revenue', 'Total Cost', 'Gross Profit', 'Direct Profit'],
    var_name='Metric',
    value_name='Value'
)

# Visualization for Service Offerings
fig_service_offerings = px.bar(
    service_offerings_melted,
    x='Service Offerings',
    y='Value',
    color='Metric',
    title='Service Offerings Performance',
    barmode='group'
)

# Customize the layout
fig_service_offerings.update_layout(
    xaxis_title="Service Offerings",
    yaxis_title="Amount ($)",
    legend_title="Metrics",
    xaxis={'tickangle': 45}
)

st.plotly_chart(fig_service_offerings)

# Display the tabular data as well
st.dataframe(
    service_offerings_data.style.apply(color_gradient),
    column_config={
        col: st.column_config.NumberColumn(
            col,
            help=f"{col}",
            format="$%d"
        ) for col in service_offerings_data.columns if col != 'Service Offerings'
    }
)
# Client Profitability Analysis
st.subheader("Client Profitability Analysis")
client_profitability = filtered_data.groupby('Client name').agg({
    'Revenue': 'sum',
    'Gross Profit': 'sum',
    'Direct Profit': 'sum',
    'Total Cost': 'sum'
}).sort_values('Revenue', ascending=False)

# Create a size column that's always positive for the scatter plot
client_profitability['Marker_Size'] = (client_profitability['Direct Profit'] - 
                                     client_profitability['Direct Profit'].min() + 1)  # Add 1 to avoid zero sizes

# Client Profitability Visualization
fig_client_profit = px.scatter(
    client_profitability.reset_index(),
    x='Revenue',
    y='Gross Profit',
    size='Marker_Size',  # Use the new positive size column
    hover_data={
        'Client name': True,
        'Direct Profit': ':,.0f',  # Show actual Direct Profit in hover
        'Marker_Size': False  # Hide the size column in hover
    },
    title='Client Profitability Analysis'
)

# Update the layout for better readability
fig_client_profit.update_layout(
    xaxis_title="Revenue ($)",
    yaxis_title="Gross Profit ($)",
    xaxis=dict(tickformat="$,.0f"),
    yaxis=dict(tickformat="$,.0f")
)

# Add color based on Direct Profit
fig_client_profit.update_traces(
    marker=dict(
        color=client_profitability['Direct Profit'],
        colorscale='RdYlBu',  # Red for negative, yellow for neutral, blue for positive
        showscale=True,
        colorbar=dict(title="Direct Profit ($)")
    )
)

st.plotly_chart(fig_client_profit)

# Geographic Revenue Impact
st.subheader("Country Revenue Trends")
country_quarterly = filtered_data.groupby(['Country', 'Quarter'])['Revenue'].sum().unstack(fill_value=0)
country_quarterly = country_quarterly.reindex(columns=quarters)
country_quarterly['Change'] = country_quarterly['2024Q1'] - country_quarterly['2023Q4']
country_quarterly = country_quarterly.sort_values('Change', ascending=False)

st.dataframe(
    country_quarterly.style.apply(color_gradient),
    column_config={
        col: st.column_config.NumberColumn(
            col,
            help=f"Revenue in {col}",
            format="$%d"
        ) for col in country_quarterly.columns
    }
)

# Geographic Revenue Visualization
fig_geo = px.line(country_quarterly.reset_index(),
                  x='Country',
                  y=quarters,
                  title='Country Revenue Trends')
st.plotly_chart(fig_geo)

# Revenue Trends Visualization
st.subheader("Revenue Trends")
monthly_revenue = filtered_data.groupby(['[Year-Month]'])['Revenue'].sum().reset_index()
monthly_revenue['views_history'] = monthly_revenue['Revenue'].rolling(window=3).mean()

st.dataframe(
    monthly_revenue,
    column_config={
        "[Year-Month]": "Period",
        "Revenue": st.column_config.NumberColumn(
            "Monthly Revenue",
            help="Total revenue for the month",
            format="$%d"
        ),
        "views_history": st.column_config.LineChartColumn(
            "Revenue Trend (3-month rolling average)",
            y_min=0,
            y_max=float(monthly_revenue['Revenue'].max() * 1.1)
        ),
    },
    hide_index=True
)

# Overall Revenue Visualization
fig_revenue = px.line(monthly_revenue,
                     x='[Year-Month]',
                     y=['Revenue', 'views_history'],
                     title='Monthly Revenue Trends')
st.plotly_chart(fig_revenue)

# Revenue Peaks and Lows
st.subheader("Revenue Peaks and Lows")
peak_revenue = monthly_revenue['Revenue'].max()
low_revenue = monthly_revenue['Revenue'].min()
st.write(f"**Peak Monthly Revenue:** ${peak_revenue:,.0f}")
st.write(f"**Lowest Monthly Revenue:** ${low_revenue:,.0f}")

