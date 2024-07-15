#### IMPORTS ####
import streamlit as st
import pandas as pd
import sys
from importlib import resources as impresources
import os

import plotly.express as px
import plotly.graph_objects as go

from emissions_calculator import read_data

#### FUNCTIONS ####
def exit_program():
    '''Exits programme.'''
    sys.exit(0)

def check_data(data):
    '''Checks that data has successfully been read in, else exits program.'''
    if data is None:
        exit_program()

#### PLOTS ####
def create_bar_chart(open_data, exclude=0, num_plot=15, w=1000, h=700, a=False,
                     open=True, data=None):
    '''
    Create a plotly stacked bar chart.
    
    Parameters:
    -----------
    data: pd.Dataframe
        rows = products, columns = emissions broken down into
        categories.

        
    Returns:
    -------
    plotly.figure
    '''
    open_data = open_data.sort_values(by=['total_emissions'], ascending=a)
    
    if open:
        # Plots breakdown of emissions for first n components
        data = open_data.iloc[exclude:(num_plot+exclude)]
    else:
        names = open_data.iloc[exclude:(num_plot+exclude)]\
            ['product'].to_list()
        data = data[data['product'].isin(names)]

    # Sorts so highest total appears first
    sorted_data = data.sort_values(by=['total_emissions'], ascending=a)

    sorted_data['use_emissions'] = sorted_data['use_emissions'].astype(float)
    sorted_data['reprocessing_emissions'] = \
        sorted_data['reprocessing_emissions'].astype(float)

    # Takes dataframe and converts information to lists
    name = sorted_data['product'].to_list()
    make = sorted_data['manufacture_emissions'].to_list()
    travel = sorted_data['transport_emissions'].to_list()
    use = sorted_data['use_emissions'].to_list()
    repro = sorted_data['reprocessing_emissions'].to_list()
    waste = sorted_data['disposal_emissions'].to_list()

    # Plots stacked bar chart broken down by emission type
    fig = go.Figure(go.Bar(x=name, y=make, marker_color='orange',
                           name='Manufacture'))
    fig.add_bar(x=name, y=travel, marker_color='blue',
                name='Transport')
    fig.add_bar(x=name, y=use, marker_color='purple',
                name='Use')
    fig.add_bar(x=name, y=repro, marker_color='green',
                name='Reprocessing')
    fig.add_bar(x=name, y=waste, marker_color='crimson',
                name='Disposal')

    # Figure set-up
    fig.update_layout(
        barmode='relative',
        autosize=False,
        width=w,
        height=h,
        yaxis_title='Emissions / kg CO2e'
    )

    return fig

def create_spec_bar_chart(open, eco, prod_name, w=800, h=600, g=0.3):
    '''
    Create a plotly stacked bar chart.
    
    Parameters:
    -----------
    data: pd.Dataframe
        rows = products, columns = emissions broken down into
        categories.
        
    Returns:
    -------
    plotly.figure
    '''   
    name = ['Open-Source', 'EcoInvent']

    # Takes dataframe and converts information to lists
    make = open['manufacture_emissions']
    travel = open['transport_emissions']
    use = open['use_emissions']
    repro = open['reprocessing_emissions']
    waste = open['disposal_emissions']

    make_eco = eco['manufacture_emissions']
    travel_eco = eco['transport_emissions']
    use_eco = eco['use_emissions']
    repro_eco = eco['reprocessing_emissions']
    waste_eco = eco['disposal_emissions']

    # Plots stacked bar chart broken down by emission type
    fig = go.Figure(go.Bar(x=name, y=[make_eco, make],
                           marker_color='orange', name='Manufacture'))
    fig.add_bar(x=name, y=[travel_eco, travel], marker_color='blue',
                name='Travel')
    fig.add_bar(x=name, y=[use_eco, use], marker_color='purple',
                name='Use')
    fig.add_bar(x=name, y=[repro_eco, repro], marker_color='green',
                name='Reprocessing')
    fig.add_bar(x=name, y=[waste_eco, waste], marker_color='crimson',
                name='Disposal')

    # Figure set-up
    fig.update_layout(
        barmode='relative',
        autosize=False,
        bargap=g,
        width=w,
        height=h,
        title=f'Emissions Comparison: {prod_name.title()}',
        yaxis_title='Emissions / kg CO2e'
    )

    return fig


#### MAIN ####
# Removes whitespace from edge of page
st.set_page_config(layout='wide')

# Page title
st.title('Comparison Emissions Plots')
st.markdown(f'''Compare GHG emissions for products contained in the database
                calculated using EcoInvent data and open-source data.''')


with st.spinner('Loading data...'):
    # Reads in factors file
    factors = read_data.read_factors()
    
    # Emissions file using open-source data
    open_product_emissions = read_data.read_open_source_emissions()
    check_data(open_product_emissions)
    current_prod = open_product_emissions['product'].to_list()

    # Emissions file using EcoInvent data
    product_emissions = read_data.read_emissions()
    check_data(product_emissions)

open_emissions = open_product_emissions.filter(
    items=['product', 'category', 'manufacture_emissions',
           'transport_emissions', 'use_emissions', 'reprocessing_emissions',
           'disposal_emissions', 'total_emissions'])

emissions = product_emissions.filter(
    items=['product', 'category', 'manufacture_emissions',
           'transport_emissions', 'use_emissions', 'reprocessing_emissions',
           'disposal_emissions', 'total_emissions'])

cat_list = emissions['category'].unique().tolist()
cat_list = [c.title() for c in cat_list]

#### SELECT PRODUCTS ####
to_compare = st.multiselect(f'###### **Select products to compare**',
                                current_prod, key=1)
# Return to lower case so can access data in dataframe
to_compare = [p.lower() for p in to_compare]

open_chosen = open_emissions[open_emissions['product'].isin(to_compare)]\
    .copy(deep=True)
chosen = emissions[emissions['product'].isin(to_compare)].copy(deep=True)

# Create comparison plots
for ind, open_row in open_chosen.iterrows():
    name = open_row['product']
    row = chosen.set_index('product').loc[name]
    fig = create_spec_bar_chart(open_row, row, name)
    st.plotly_chart(fig)


#### SELECT BASED ON DATA ####
num_to_plot = st.number_input('Number of products to plot', min_value=1,
                              max_value=len(emissions), value=10) 

#### HIGHEST EMISSIONS ####
st.markdown('**Highest Emissions in Open-Source Data:**')
num_start_highest = st.number_input('Number of product to begin plot at',
                                    min_value=0, max_value=len(emissions),
                                    value=0, key='high') 

st.markdown('**Open-Source:**')
open_highest_fig = create_bar_chart(open_emissions, exclude=num_start_highest,
                                    num_plot=num_to_plot)
st.plotly_chart(open_highest_fig)

st.markdown('**EcoInvent:**')
highest_fig = create_bar_chart(open_emissions, exclude=num_start_highest,
                               num_plot=num_to_plot, open=False,
                               data=emissions)
st.plotly_chart(highest_fig)

#### LOWEST EMISSIONS ####
st.markdown('**Lowest Emissions in Open-Source Data:**')
num_start_lowest = st.number_input('Number of product to begin plot at',
                                   min_value=0, max_value=len(emissions),
                                   value=0, key='low')

st.markdown('**Open-Source:**')
open_lowest_fig = create_bar_chart(open_emissions, exclude=num_start_lowest,
                                   num_plot=num_to_plot, a=True)
st.plotly_chart(open_lowest_fig)

st.markdown('**EcoInvent:**')
lowest_fig = create_bar_chart(open_emissions, exclude=num_start_lowest,
                              num_plot=num_to_plot, a=True, open=False,
                              data=emissions)
st.plotly_chart(lowest_fig)