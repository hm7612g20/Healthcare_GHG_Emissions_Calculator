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
def create_bar_chart(data, exclude=0, num_plot=15, w=1000, h=700, a=False):
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
    # Plots breakdown of emissions for first n components
    data = data.iloc[exclude:(num_plot+exclude)]

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


#### MAIN ####
# Removes whitespace from edge of page
st.set_page_config(layout='wide')

# Page title
st.title('Comparison Emissions Plots')
st.markdown(f'''Create informative plots of GHG emissions for products
                contained in the database.''')


with st.spinner('Loading data...'):
    # Reads in factors file
    factors = read_data.read_factors()
    
    # Inventory file
    product_emissions = read_data.read_emissions()
    check_data(product_emissions)
    current_prod = product_emissions['product'].to_list()

emissions = product_emissions.filter(items=['product',
                                            'category',
                                            'manufacture_emissions',
                                            'transport_emissions',
                                            'use_emissions',
                                            'reprocessing_emissions',
                                            'disposal_emissions',
                                            'total_emissions'])

cat_list = emissions['category'].unique().tolist()
cat_list = [c.title() for c in cat_list]

num_to_plot = st.number_input('Number of products to plot', min_value=1,
                              max_value=len(emissions), value=15) 

#### HIGHEST EMISSIONS ####
st.markdown('**Highest Emissions in Database:**')
num_start_highest = st.number_input('Number of product to begin plot at',
                                    min_value=0, max_value=len(emissions),
                                    value=0, key='high') 
highest = emissions.sort_values(by=['total_emissions'], ascending=False)
highest_fig = create_bar_chart(highest, exclude=num_start_highest,
                               num_plot=num_to_plot)
st.plotly_chart(highest_fig)

#### LOWEST EMISSIONS ####
st.markdown('**Lowest Emissions in Database:**')
num_start_lowest = st.number_input('Number of product to begin plot at',
                                   min_value=0, max_value=len(emissions),
                                   value=0, key='low') 
lowest = emissions.sort_values(by=['total_emissions'], ascending=True)
lowest_fig = create_bar_chart(lowest, exclude=num_start_lowest,
                              num_plot=num_to_plot, a=True)
st.plotly_chart(lowest_fig)

#### SORT BY CATEGORY ####
st.markdown('**Select by Category:**')
cat = st.selectbox('Select category', cat_list).lower()
num_start_cat = st.number_input('Number of product to begin plot at',
                                min_value=0, max_value=len(emissions),
                                value=0, key='cat')
emissions_cat = emissions[emissions['category'] == cat]
ch = emissions_cat[emissions_cat['product'] == 'disposable cup']

st.markdown('**Highest Emissions by Category:**')
cat_h = emissions_cat.sort_values(by=['total_emissions'], ascending=False)
cat_h_fig = create_bar_chart(cat_h, exclude=num_start_cat,
                             num_plot=num_to_plot)
st.plotly_chart(cat_h_fig)

st.markdown('**Lowest Emissions by Category:**')
cat_l = emissions_cat.sort_values(by=['total_emissions'], ascending=True)
cat_l_fig = create_bar_chart(cat_l, exclude=num_start_cat,
                             num_plot=num_to_plot, a=True)
st.plotly_chart(cat_l_fig)