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


#### FORMATTING ####
def choose_database(data):
    '''
    Selects relevant part of emissions database if certain product
    is selected from list.

    Parameters:
    -----------
    data: pd.DataFrame
        Contains chosen products from the product inventory.

    Returns:
    -------
    sorted_data: pd.DataFrame
        Formatted dataframe of selected products.
    original_df: pd.DataFrame
        Dataframe of selected products in original format without additional
        travel emissions to end location.
    original_df_inc_travel: pd.DataFrame
        Dataframe of selected products in original format with additional
        travel emissions to end location.
    '''
    data = data.set_index(['product'])
    data.index.names = ['Product']

    # Used to filter and rename required columns
    filter_items = ['total_emissions', 'manufacture_emissions',
                    'transport_emissions', 'use_emissions',
                    'reprocessing_emissions', 'disposal_emissions']

    col_names = {'total_emissions': 'Total / kg CO2e',
                 'manufacture_emissions': 'Manufacturing / kg CO2e',
                 'transport_emissions': 'Transport / kg CO2e',
                 'use_emissions': 'Use / kg CO2e',
                 'reprocessing_emissions': 'Reprocessing / kg CO2e',
                 'disposal_emissions': 'Disposal / kg CO2e'}

    # Filters to only show specific columns
    data = data.filter(items=filter_items)
    # Renames columns
    data.rename(columns=col_names, inplace=True)

    # Capitalises product names
    data.index = data.index.str.capitalize()
    # Sets indexes
    data = data.reset_index()
    data.index += 1

    # Displays dataframe and rounds values
    st.dataframe(data.round(decimals=6).astype(str))

    return


#### PLOTS ####
def comp2_bar_chart(data, prod1, prod2, w=700, h=700, g=0.2):
    '''
    Create a plotly stacked bar chart.

    Parameters:
    -----------
    data: pd.Dataframe
        rows = products, columns = emissions broken down into
        categories.
    prod1, prod2: str
        Name of products.
    w: int, optional (default=1000)
        Width of plot.
    h: int, optional (default=650)
        Height of plot.
    g: float, optional (default=0.2)
        Separation of bars.

    Returns:
    -------
    plotly.figure
    '''
    # Changes data type
    data['use_emissions'] = data['use_emissions'].astype(float)
    data['reprocessing_emissions'] = \
        data['reprocessing_emissions'].astype(float)
    # Set index
    data = data.set_index('product')

    prod1_data = data.loc[prod1.lower()]
    prod2_data = data.loc[prod2.lower()]

    name = [prod1, prod2]
    make = [prod1_data['manufacture_emissions'],
            prod2_data['manufacture_emissions']]
    travel = [prod1_data['transport_emissions'],
              prod2_data['transport_emissions']]
    use = [prod1_data['use_emissions'],
           prod2_data['use_emissions']]
    repro = [prod1_data['reprocessing_emissions'],
             prod2_data['reprocessing_emissions']]
    waste = [prod1_data['disposal_emissions'],
             prod2_data['disposal_emissions']]

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
        bargap=g,
        width=w,
        height=h,
        yaxis_title='Emissions / kg CO2e'
    )

    return fig


def create_bar_chart(data, exclude=0, num_plot=15, w=1000, h=650, a=False,
                     sort_name='total_emissions'):
    '''
    Create a plotly stacked bar chart.

    Parameters:
    -----------
    data: pd.Dataframe
        rows = products, columns = emissions broken down into
        categories.
    exclude: int, optional (default=0)
        Index of dataframe where first prouct extracted from.
    num_plot: int, optional (default=15)
        Number of products to plot.
    w: int, optional (default=1000)
        Width of plot.
    h: int, optional (default=650)
        Height of plot.
    a: bool, optional (default=False)
        If values should be sorted in ascending order.
    sort_name: str, optional (default='total_emissions')
        Column by which values should be sorted.

    Returns:
    -------
    plotly.figure
    '''
    # Plots breakdown of emissions for first n components
    data = data.iloc[exclude:(num_plot+exclude)]

    # Sorts so highest/lowest total appears first
    sorted_data = data.sort_values(by=[sort_name], ascending=a)
    # Changes data type
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
st.set_page_config(layout='wide')  # Removes whitespace from edge of page

st.title('Comparison Emissions Plots')  # Page title
st.markdown(f'''Create informative plots of GHG emissions for products
                contained in the database.''')


with st.spinner('Loading data...'):
    factors = read_data.read_factors()  # Reads in factors file

    # Inventory emissions file
    product_emissions = read_data.read_emissions()
    check_data(product_emissions)
    open_emissions = read_data.read_open_source_emissions()
    check_data(open_emissions)

    # List of products in dataframe
    current_prod = product_emissions['product'].to_list()

#### CHOOSE DATABASE ####
# Changes which data is used depending on user choice
open = st.checkbox(f'''Select to use database containing emissions values
                       calculated with freely available emissions factors''')
st.markdown(f'''> *Please note: if this is not selected, it will access
                values calculated using emissions factors from EcoInvent
                (version 3.10).*''')
if open:
    product_emissions = open_emissions.copy(deep=True)

# Extracts columns needed for plot
emissions = product_emissions.filter(
    items=['product', 'category', 'manufacture_emissions',
           'transport_emissions', 'use_emissions', 'reprocessing_emissions',
           'disposal_emissions', 'total_emissions'])

# Extracts category list
cat_list = emissions['category'].unique().tolist()
cat_list = [c.title() for c in cat_list]

#### COMPARE PRODUCTS ####
st.divider()
st.markdown('#### Compare Products')
prod_list = [p.title() for p in current_prod]
prod1 = st.selectbox(f'Select first product', prod_list)
prod2 = st.selectbox(f'Select second product', prod_list)
if prod1 != prod2:
    comp_fig = comp2_bar_chart(emissions, prod1, prod2)
    st.plotly_chart(comp_fig)
    # Download image as PNG
    st.download_button(
        label=f'Download bar chart as PNG',
        data=comp_fig.to_image(format='png', scale=3),
        file_name='comp_emissions.png', mime='image/png', key='f_comp')

st.divider()
st.markdown('#### Select Number of Products to Plot')
num_to_plot = st.number_input(
    'Choose number of products to plot', min_value=1,
    max_value=len(emissions), value=15)

#### HIGHEST EMISSIONS ####
st.divider()
st.markdown('#### Plot Highest Emissions in Database')
num_start_highest = st.number_input(
    f'Choose index of product to begin plot at', min_value=0,
    max_value=len(emissions), value=0, key='high')
highest = emissions.sort_values(by=['total_emissions'], ascending=False)
highest_fig = create_bar_chart(highest, exclude=num_start_highest,
                               num_plot=num_to_plot)
st.plotly_chart(highest_fig)
# Download image as PNG
st.download_button(
    label=f'Download bar chart as PNG',
    data=highest_fig.to_image(format='png', scale=3),
    file_name='highest_emissions.png', mime='image/png', key='f_high')

#### LOWEST EMISSIONS ####
st.divider()
st.markdown('#### Plot Lowest Emissions in Database')
num_start_lowest = st.number_input(
    'Choose index of product to begin plot at', min_value=0,
    max_value=len(emissions), value=0, key='low')
lowest = emissions.sort_values(by=['total_emissions'], ascending=True)
lowest_fig = create_bar_chart(lowest, exclude=num_start_lowest,
                              num_plot=num_to_plot, a=True)
st.plotly_chart(lowest_fig)
# Download image as PNG
st.download_button(
    label=f'Download bar chart as PNG',
    data=lowest_fig.to_image(format='png', scale=3),
    file_name='lowest_emissions.png', mime='image/png', key='f_low')

#### SORT BY CATEGORY ####
st.divider()
st.markdown('#### Plot Emissions by Category')
cat = st.selectbox('Select product category', cat_list).lower()
num_start_cat = st.number_input(
    'Choose index of product to begin plot at', min_value=0,
    max_value=len(emissions), value=0, key='cat')
emissions_cat = emissions[emissions['category'] == cat]
ch = emissions_cat[emissions_cat['product'] == 'disposable cup']

st.markdown('**Highest Emissions by Category:**')
cat_h = emissions_cat.sort_values(by=['total_emissions'], ascending=False)
cat_h_fig = create_bar_chart(cat_h, exclude=num_start_cat,
                             num_plot=num_to_plot)
st.plotly_chart(cat_h_fig)
# Download image as PNG
st.download_button(
    label=f'Download bar chart as PNG',
    data=cat_h_fig.to_image(format='png', scale=3),
    file_name='highest_cat_emissions.png', mime='image/png', key='f_high_cat')

st.markdown('**Lowest Emissions by Category:**')
cat_l = emissions_cat.sort_values(by=['total_emissions'], ascending=True)
cat_l_fig = create_bar_chart(cat_l, exclude=num_start_cat,
                             num_plot=num_to_plot, a=True)
st.plotly_chart(cat_l_fig)
# Download image as PNG
st.download_button(
    label=f'Download bar chart as PNG',
    data=cat_l_fig.to_image(format='png', scale=3),
    file_name='lowest_cat_emissions.png', mime='image/png', key='f_low_cat')

#### SORT BY INDIVIDUAL EMISSION TYPE ####
st.divider()
st.markdown('#### Plot Emissions by Type')
types_lst = ['Manufacture', 'Transport', 'Use', 'Reprocessing', 'Disposal']
type = st.selectbox('Select emission type', types_lst)
if type == 'Manufacture':
    sort_name = 'manufacture_emissions'
elif type == 'Transport':
    sort_name = 'transport_emissions'
elif type == 'Use':
    sort_name = 'use_emissions'
elif type == 'Reprocessing':
    sort_name = 'reprocessing_emissions'
elif type == 'Disposal':
    sort_name = 'disposal_emissions'
num_start_sep = st.number_input(
    f'Choose index of product to begin plot at', min_value=0,
    max_value=len(emissions), value=0, key='sep')

st.markdown('**Highest Emissions by Type:**')
highest_sep = emissions.sort_values(by=[sort_name], ascending=False)
highest_sep_fig = create_bar_chart(highest_sep, exclude=num_start_sep,
                                   num_plot=num_to_plot, sort_name=sort_name)
st.plotly_chart(highest_sep_fig)
# Download image as PNG
st.download_button(
    label=f'Download bar chart as PNG',
    data=highest_sep_fig.to_image(format='png', scale=3),
    file_name='highest_type_emissions.png', mime='image/png', key='f_high_tp')

st.markdown('**Lowest Emissions by Type:**')
lowest_sep = emissions.sort_values(by=[sort_name], ascending=True)
lowest_sep_fig = create_bar_chart(lowest_sep, exclude=num_start_sep,
                                  num_plot=num_to_plot, a=True,
                                  sort_name=sort_name)
st.plotly_chart(lowest_sep_fig)
# Download image as PNG
st.download_button(
    label=f'Download bar chart as PNG',
    data=lowest_sep_fig.to_image(format='png', scale=3),
    file_name='lowest_type_emissions.png', mime='image/png', key='f_low_tp')
