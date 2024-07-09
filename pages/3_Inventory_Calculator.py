#### IMPORTS ####
import streamlit as st
import pandas as pd

import sys
from importlib import resources as impresources
import os
from io import BytesIO

from datetime import datetime

import plotly.express as px
import plotly.graph_objects as go

from emissions_calculator import inventory_calculator as calc
from emissions_calculator import read_data
from emissions_calculator import update_files as update

#### FUNCTIONS ####
@st.cache_data # Cache the conversion to prevent computation on every rerun
def read_file_contents(file_name):
    '''Reads the contents of a file.'''
    with open(file_name) as f:
        return f.read()

def exit_program():
    '''Exits programme.'''
    sys.exit(0)

def check_data(data):
    '''Checks that data has successfully been read in.'''
    if data is None:
        exit_program()

def is_local():
    '''Extracts if program is running locally and if can save to database.'''
    cloud = False
    for i in os.environ:
        if i == 'HOSTNAME':
            cloud = True

    return cloud

#### ADDITIONAL TRAVEL CALC ####
def travel_end_loc(df, dest_city, no_comp):
    '''Calculates emissions to end city.'''
    # Reads other factors such as travel and electricity/water/gas
    additional_factors = read_data.read_additional_factors_inv()
    check_data(additional_factors)

    # Reads in travel distances
    land_travel_dist, sea_travel_dist = read_data.read_travel_dist()

    count = 0
    travel_emissions = []
    for ind, row in df.iterrows():
        ghg_em_pu = 0.0
        for i in range(no_comp):
            mass = row['mass_kg_' + str(i+1)] # Mass of component
            no_uses = row['no_uses_' + str(i+1)] # Number of uses
            year = row['manu_year_' + str(i+1)] # Year of manufacture

            # Locations where component begins journey in UK
            depart_loc_uk = row['depart_loc_uk_' + str(i+1)]

            if depart_loc_uk != dest_city and depart_loc_uk != '0' \
                and depart_loc_uk != 0:
                    # Reads travel factors
                    travel_fact, _ = calc.read_travel_fact(additional_factors,
                                                           year)

                    city1 = depart_loc_uk + ' (united kingdom)'
                    city2 = dest_city + ' (united kingdom)'
                    try: # Extracts distance travelled if in dataframe
                        dist_km = land_travel_dist.at[(city1,
                                                       city2), \
                                                       'distance_km']
                    except KeyError: # If not, user inputs value
                        city1_name = depart_loc_uk.title()
                        city2_name = dest_city.title()
                        num = (count+1) * (i+100)
                        dist_km = st.number_input(f'''Input travel distance
                                                  between {city1_name} and
                                                  {city2_name}''',
                                                  min_value=0.0, step=1.0,
                                                  format='%0.3f',
                                                  key='ld_%d'%num)

                        # Adds new info to df to prevent repeats
                        if dist_km > 0.0:
                            land_travel_dist.loc[(city1, city2), 
                                                 ['distance_km']] = [dist_km]

                    # Calculate travel emissions
                    # Factor is in tonne km so / 1000
                    ghg_em = (mass * dist_km * travel_fact) / 1000
                    ghg_em_pu += ghg_em / no_uses

        count += 1
        travel_emissions.append(ghg_em_pu)

    return travel_emissions

#### DOWNLOADS ####
def convert_df(df):
    '''Converts dataframe to csv file for download.'''
    return df.to_csv(index=False).encode('utf-8')

def download_example_file(key='products'):

    ex_df = pd.read_excel('resources/products_example.xlsx')
    ex = convert_df(ex_df)
    
    st.download_button(
        label='Download empty file',
        data=ex,
        file_name='products.csv',
        mime='text/csv',
        key=key
    )

    return

def download_button(results, products):
    '''
    Combines results and products dataframe and produces a download
    button to download the results as a csv.

    Parameters:
    -----------
    results: pd.DataFrame
        Calculated emissions values.
    products: pd.DataFrame
        Product information.

    Returns:
    -------
    Button to download data as csv.
    '''
    # Renames columns
    col_names = {'Product': 'product',
                 'Total / kg CO2e': 'total_emissions',
                 'Manufacturing / kg CO2e': 'manufacture_emissions',
                 'Transport / kg CO2e': 'transport_emissions',
                 'Use / kg CO2e': 'use_emissions',
                 'Reprocessing / kg CO2e':'reprocessing_emissions',
                 'Disposal / kg CO2e':'disposal_emissions'}
    results.rename(columns=col_names, inplace=True)
    # Reorders columns
    column_titles = ['product', 'manufacture_emissions', 'transport_emissions',
                     'use_emissions', 'reprocessing_emissions',
                     'disposal_emissions', 'total_emissions']
    results = results.reindex(columns=column_titles)

    # Merges results and product dataframes
    output = pd.merge(products, results, on='product',  how='left')

    # Converts to suitable format for button
    results_csv = convert_df(output)

    st.download_button(
        label='Download results as CSV',
        data=results_csv,
        file_name='inventory_emissions.csv',
        mime='text/csv'
    )

    return

#### FORMATTING ####
def format_dataframe(df):
    '''
    Formats dataframe for output.
    
    Parameters:
    -----------
    df: pd.Dataframe
        Product information
        
    Returns:
    -------
    df_formatted: pd.Dataframe
        Sets index as product and capitalises first letters
    '''
    # Sets index as name of product
    df_formatted = df.set_index(['Product'])
    # Capitalises product names
    df_formatted.index = df_formatted.index.str.capitalize()

    return df_formatted

#### PLOTS ####
def create_bar_chart(data):
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
    # Sorts so highest total appears first
    sorted_data = data.sort_values(by=['Total / kg CO2e'], ascending=False)
    
    # Takes dataframe and converts information to lists
    name = sorted_data['Product'].to_list()
    make = sorted_data['Manufacturing / kg CO2e'].to_list()
    travel = sorted_data['Transport / kg CO2e'].to_list()
    use = sorted_data['Use / kg CO2e'].to_list()
    repro = sorted_data['Reprocessing / kg CO2e'].to_list()
    waste = sorted_data['Disposal / kg CO2e'].to_list()

    for ind, val in enumerate(waste):
        if val < 0.0:
            waste[ind] = 0.0

    # Plots stacked bar chart broken down by emission type
    fig = go.Figure(go.Bar(x=name, y=make, marker_color='orange',
                           name='Manufacture'))
    fig.add_bar(x=name, y=travel, marker_color='blue',
                name='Travel')
    fig.add_bar(x=name, y=use, marker_color='purple',
                name='Use')
    fig.add_bar(x=name, y=repro, marker_color='green',
                name='Reprocessing')
    fig.add_bar(x=name, y=waste, marker_color='crimson',
                name='Disposal')

    # Figure set-up
    fig.update_layout(barmode='stack',
                      autosize=False,
                      width=1000,
                      height=800,
                      title='Emissions',
                      yaxis_title='Emissions / kg CO2e')

    return fig

#### MAIN ####
# Initialise session state to store variables
st.session_state.calculation = None
st.session_state.additional_calculation = None
st.session_state.multiselect = None
st.session_state.additional_csv = None

# Removes whitespace from edge of page
st.set_page_config(layout='wide')

# Page title
st.title('Calculate Emissions from Inventory File')

# Show introductory markdown
st.markdown(f'''You can either upload your own file or update and download
                the current emissions database.''')

cloud = is_local()

# Finds current year
today = datetime.now()
year = int(today.strftime("%Y"))

#### OPTION TO UPLAOD OWN FILE ####
uploaded_file = st.file_uploader('Upload own file if desired.',
                                 type=['csv'])
# Additional information stored under a read more option
with st.expander('File requirements and example'):
    download_example_file()
    st.markdown(read_file_contents('resources/inventory_own_products.md'))


#### READS IN DATA ####
with st.spinner('Loading data...'):
    if uploaded_file is not None:
        try: # Reads in uploaded file
            products = pd.read_csv(uploaded_file)
        except pd.errors.ParserError: # Stops if wrong type of file used
            st.error('Error: Incorrect file format.')
            exit_program()
        own_file = True
    else: # Otherwise uses current database
        products = read_data.read_products()
        check_data(products)
        own_file = False
    
    try:
        # Finds number of components given the data
        no_comp = int(list(products.columns)[-1].split('_')[-1])
    except ValueError: # Stops if wrong type of file used
        st.error('Error: Incorrect file format.')
        exit_program()

    factors = read_data.read_factors_inv() # Reads in factors file
    check_data(factors)
    
    additional_factors = read_data.read_additional_factors_inv()
    check_data(additional_factors)
    
    # Reads in cities and ports
    cities_list, uk_cities_list = read_data.read_cities()
    check_data(cities_list)
    check_data(uk_cities_list)
    ports_list, uk_ports_list = read_data.read_ports()
    check_data(ports_list)
    check_data(uk_ports_list)
    
    # Reads in travel distances
    land_travel_dist, sea_travel_dist = read_data.read_travel_dist()
    
    # Reads info on decontamination units
    decon_units = read_data.read_decon_units()
    check_data(decon_units)

# Extracts name of decontamination units to select
decon_names_all = list(decon_units.keys())
decon_names = []
for ind, nm in enumerate(decon_names_all):
    if ind%3 == 0:
        decon_names.append(nm[:-12].capitalize())


#### UPLOAD OWN EMISSIONS FACTORS ####
own_factors_file = None
if st.checkbox('Upload own emissions factors file'):
    join_files = False
    own_factors_file = st.file_uploader('Upload own emission factors file',
                                        type=['csv'])
    with st.expander('File requirements and example'):
        download_example_file(key='factors')
        st.markdown(read_file_contents('resources/own_factors.md'))
    if own_factors_file is not None:
        own_factors_df = pd.read_csv(own_factors_file)
        try:
            own_factors_df = own_factors_df.set_index(['component', 'loc',
                                                       'year'])
            own_factors_df = own_factors_df.sort_index()
        except KeyError:
            st.error('Error: Incorrect factors file format.')
            exit_program()
        join_files = st.checkbox('Include factors from current database')
    
    # Joins with stored data if required
    if join_files:
        factors = pd.concat([own_factors_df, factors])
    elif own_factors_file is not None:
        factors = own_factors_df


#### SELECT RELEVANT INFO ####
# User inputs destination city for final travel distance calc
felixstowe_ind = uk_cities_list.index('Felixstowe')
dest_city = st.selectbox('Select approximate destination for product',
                         uk_cities_list, index=felixstowe_ind).lower()

# User selects year 
product_year = st.number_input('Year of use/disposal emissions factors',
                               min_value=1970, max_value=year,
                               value=year, step=1)

decon_type = st.selectbox('Select decontamination unit', decon_names).lower()


##### SELECT PRODUCTS TO PLOT #####
st.write('\n')
current_prods = products['product'].to_list()
# Capitalizes first letter
current_prods = [p.capitalize() for p in current_prods]
to_plot = st.multiselect(f'###### **Select products to appear in bar chart.**',
                         current_prods)
# Return to lower case so can access data in dataframe
to_plot = [p.lower() for p in to_plot]
if len(to_plot) > 0:
    st.session_state.multiselect = to_plot


#### OPTION TO INCLUDE EXTRA TRAVEL EMISSIONS ####
inc_additional = st.checkbox(f'''Include travel to end location in CSV
                                 file''', key='travel_csv')
st.session_state.additional_csv = inc_additional

#update = False
#if not cloud:
#    update = st.checkbox('Update emissions file following calculation',
#                         key='update')


#### PERFORM CALCULATIONS ####
if st.button('Calculate Emissions'): # If clicked, performs calculation
    with st.spinner('Running Calculations...'):
        try:
            # Manufacturing emissions
            make, total_make = calc.manufacture_calc(products, factors,
                                                     no_comp, dest_city)
            st.success('Manufacturing calculations complete.')

            # Travel emissions
            travel, total_travel = calc.travel_calc(products, no_comp,
                                                    additional_factors,
                                                    dest_city,
                                                    land_travel_dist,
                                                    sea_travel_dist)
            st.success('Travel calculations complete.')

            # Use emissions
            use = calc.product_use_calc(products, no_comp, additional_factors,
                                        product_year)
            st.success('Use calculations complete.')
        
            # Reprocessing emissions  
            total_repro = calc.reprocessing_calc(products, no_comp,
                                                 additional_factors,
                                                 product_year, decon_type,
                                                 decon_units)
            st.success('Reprocessing calculations complete.')

            # Disposal emissions
            (incinerate, recycle, landfill, biogenic,
             net_waste) = calc.disposal_calc(products, factors, no_comp,
                                             additional_factors, product_year)
            st.success('Disposal calculations complete.')

            # Total emissions
            total = calc.total_calc(total_make, total_travel, use, total_repro,
                                    net_waste)

            # Additional travel to end location
            additional_travel = travel_end_loc(products, dest_city, no_comp)

        except (KeyError, AttributeError) as e: # Stops if wrong type of file used
            st.error('Error: Incorrect file format.')
            st.markdown('**Error Message:**')
            st.write(e)
            exit_program()

        total_inc_end_travel = []
        total_travel_inc_end = []
        for ttl, trl, atrl in zip(total, total_travel, additional_travel):
            total_inc_end_travel.append(ttl + atrl)
            total_travel_inc_end.append(trl + atrl)
        # Creates dataframe containing the results
        obj = products['product'].to_list()
        results = pd.DataFrame(obj, columns=['Product'])
        results['Total / kg CO2e'] = total
        results['Manufacturing / kg CO2e'] = total_make
        results['Transport / kg CO2e'] = total_travel
        results['Use / kg CO2e'] = use
        results['Reprocessing / kg CO2e'] = total_repro
        results['Disposal / kg CO2e'] = net_waste
        results.reset_index(drop=True, inplace=True)

        results_inc_additional = results.copy(deep=True)
        results_inc_additional['Total / kg CO2e'] = total_inc_end_travel
        results_inc_additional['Transport / kg CO2e'] =total_travel_inc_end

    st.success(f'**Done!**')
    st.session_state.calculation = results
    st.session_state.additional_calculation = results_inc_additional

    #if update and not cloud:
    #    own = False
    #    if uploaded_file is not None:
    #        own = True
    #    update.update_emissions(products, total_make, total_travel, use,
    #                            total_repro, net_waste, total, own)

#### PLOT AND DISPLAY RESULTS ####
# Plots results if required and prints dataframe of results
if st.session_state.calculation is not None and \
    st.session_state.multiselect is not None:
    results = st.session_state.calculation
    results_inc_additional = st.session_state.additional_calculation
    to_plot = st.session_state.multiselect
    inc_additional = st.session_state.additional_csv
    
    names = list(to_plot)
    results_plot = results[results['Product'].isin(names)]
    fig = create_bar_chart(results_plot)

    formatted_results = format_dataframe(results)
    st.dataframe(formatted_results)
    st.plotly_chart(fig)
    # Download image as PNG
    st.download_button(label='Download bar chart as PNG',
                       data=fig.to_image(format='png', scale=3),
                       file_name='emissions_comparison.png',
                       mime='image/png', key=0)

    if inc_additional:
        download_button(results_inc_additional, products)
    else:
        download_button(results, products)

# Prints dataframe of results if no plot items asked for
elif st.session_state.calculation is not None:
    results = st.session_state.calculation
    results_inc_additional = st.session_state.additional_calculation
    inc_additional = st.session_state.additional_csv
    
    formatted_results = format_dataframe(results)
    st.dataframe(formatted_results)

    if inc_additional:
        download_button(results_inc_additional, products)
    else:
        download_button(results, products)