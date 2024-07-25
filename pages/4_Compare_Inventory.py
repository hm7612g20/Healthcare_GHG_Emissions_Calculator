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

# Local package for calculations and data access
from emissions_calculator import inventory_calculator as calc
from emissions_calculator import read_data
from emissions_calculator import update_files as update


#### FUNCTIONS ####
@st.cache_data  # Cache the conversion to prevent computation on every rerun
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


#### DOWNLOADS ####
def convert_df(df):
    '''Converts dataframe to csv file for download.'''
    return df.to_csv(index=False).encode('utf-8')


def download_example_file(key='products'):
    '''Downloads example template file for users to fill in and upload.'''
    st.markdown(f'''You can download an empty file below that can be
                    populated and uploaded above.''')

    # Reads in example file
    ex_df = pd.read_excel('resources/products_example.xlsx')
    ex = convert_df(ex_df)

    # Outputs download button
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
    col_names = {'Product': 'product',
                 'Total / kg CO2e': 'total_emissions',
                 'Manufacturing / kg CO2e': 'manufacture_emissions',
                 'Transport / kg CO2e': 'transport_emissions',
                 'Use / kg CO2e': 'use_emissions',
                 'Reprocessing / kg CO2e': 'reprocessing_emissions',
                 'Disposal / kg CO2e': 'disposal_emissions'}
    results.rename(columns=col_names, inplace=True)  # Renames columns

    column_titles = ['product', 'manufacture_emissions', 'transport_emissions',
                     'use_emissions', 'reprocessing_emissions',
                     'disposal_emissions', 'total_emissions']
    results = results.reindex(columns=column_titles)  # Reorders columns

    # Merges results and product dataframes
    output = pd.merge(products, results, on='product',  how='left')
    # Converts to suitable format for button
    products_csv = convert_df(products)
    results_csv = convert_df(output)

    st.divider()
    st.markdown('#### Download Results')

    # Outputs download button
    st.download_button(
        label='Download product data as CSV',
        data=products_csv,
        file_name='changed_products.csv',
        mime='text/csv'
    )

    # Outputs download button
    st.download_button(
        label='Download emissions results as CSV',
        data=results_csv,
        file_name='changed_emissions.csv',
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
    # Changes data type
    df['Use / kg CO2e'] = df['Use / kg CO2e'].astype(float)
    df['Reprocessing / kg CO2e'] = df['Reprocessing / kg CO2e'].astype(float)

    sorted = df.sort_values(by=['Total / kg CO2e'], ascending=False)
    # Sets index as name of product
    df_formatted = sorted.set_index(['Product'])
    # Capitalises product names
    df_formatted.index = df_formatted.index.str.capitalize()
    df_formatted = df_formatted.round(decimals=8).astype(str)

    return df_formatted


#### PLOTS ####
def create_bar_chart(data, orig, prod_name, w=700, h=550, g=0.3):
    '''
    Create a plotly stacked bar chart for comparing change in emissions.

    Parameters:
    -----------
    data: pd.Dataframe
        rows = products, columns = emissions broken down into
        categories.
    orig: pd.Dataframe
        rows = products, columns = emissions broken down into
        categories, for original product.
    prod_name: str
        Name of product.
    w: int, optional (default=1000)
        Width of plot.
    h: int, optional (default=700)
        Height of plot.
    g: float, optional (default=0.2)
        Separation of bars.

    Returns:
    -------
    plotly.figure
    '''
    name = ['Original Product', 'New Product']

    # Takes dataframe and converts information to lists
    make = data['Manufacturing / kg CO2e']
    travel = data['Transport / kg CO2e']
    use = data['Use / kg CO2e']
    repro = data['Reprocessing / kg CO2e']
    waste = data['Disposal / kg CO2e']

    make_orig = orig['Manufacturing / kg CO2e']
    travel_orig = orig['Transport / kg CO2e']
    use_orig = orig['Use / kg CO2e']
    repro_orig = orig['Reprocessing / kg CO2e']
    waste_orig = orig['Disposal / kg CO2e']

    # Plots stacked bar chart broken down by emission type
    fig = go.Figure(go.Bar(x=name, y=[make_orig, make],
                           marker_color='orange', name='Manufacture'))
    fig.add_bar(x=name, y=[travel_orig, travel], marker_color='blue',
                name='Travel')
    fig.add_bar(x=name, y=[use_orig, use], marker_color='purple',
                name='Use')
    fig.add_bar(x=name, y=[repro_orig, repro], marker_color='green',
                name='Reprocessing')
    fig.add_bar(x=name, y=[waste_orig, waste], marker_color='crimson',
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
# Initialise session state to store variables
st.session_state.compare = None
st.session_state.chnaged_info = None
st.session_state.calculation = None
st.session_state.original_calc = None
st.session_state.original_info = None
st.session_state.plots = None

st.set_page_config(layout='wide')  # Removes whitespace from edge of page

st.title('Change Characterstics and Compare Emissions')  # Page title
st.markdown(f'''Use this page to change product characteristics in the current
                product database for multiple products and compare their GHG
                emissions.''')

today = datetime.now()
year = int(today.strftime("%Y"))  # Finds current year

#### READS IN DATA ####
with st.spinner('Loading data...'):
    # Reads in product database
    products = read_data.read_products()
    check_data(products)

    # Finds number of components given the data
    no_comp = int(list(products.columns)[-1].split('_')[-1])

    # Inventory emissions file
    emissions = read_data.read_open_source_emissions()
    check_data(emissions)

    factors = read_data.read_factors_inv()  # Reads in factors file
    check_data(factors)
    # Reads other factors such as travel and electricity/water/gas
    additional_factors = read_data.read_additional_factors_inv()
    check_data(additional_factors)

    # Reads in cities and ports
    cities_list, uk_cities_list = read_data.read_cities()
    check_data(cities_list)
    check_data(uk_cities_list)
    ports_list, uk_ports_list = read_data.read_ports()
    check_data(ports_list)
    check_data(uk_ports_list)

    # List of places in UK, including ports
    uk_locations = uk_ports_list + uk_cities_list
    uk_locations = sorted(list(set(uk_locations)))

    # Reads in travel distances
    land_travel_dist, sea_travel_dist = read_data.read_travel_dist()

    # Reads info on decontamination units
    decon_units = read_data.read_decon_units()
    check_data(decon_units)

# Extracts name of decontamination units to select
decon_names_all = list(decon_units.keys())
decon_names = []
for ind, nm in enumerate(decon_names_all):
    if (ind % 3) == 0:
        decon_names.append(nm[:-12].capitalize())

st.divider()
st.markdown('#### Update Emissions Factors if Desired')
#### UPLOAD OWN EMISSIONS FACTORS ####
own_factors_file = None
if st.checkbox(f'''Select if you wish to upload your own emissions factors
               file'''):
    join_files = False
    own_factors_file = st.file_uploader(
        f'Upload your own emissions factors file if required', type=['csv'])
    with st.expander(f'''Click to view file requirements or to download
                         empty example file'''):
        download_example_file(key='factors')
        st.markdown(read_file_contents('resources/own_factors.md'))

    if own_factors_file is not None:  # Reads uploaded file into pd.DataFrame
        own_factors_df = pd.read_csv(own_factors_file)
        try:  # Sets file up in the same format
            own_factors_df = own_factors_df.set_index(['component', 'loc',
                                                       'year'])
            own_factors_df = own_factors_df.sort_index()
        except KeyError:  # Stops if wrong type of file used
            st.error('Error: Incorrect factors file format.')
            exit_program()
        join_files = st.checkbox(f'''Select if you wish to also include
                                 factors from the current database''')

    if join_files:  # Joins with stored data if requested
        factors = pd.concat([own_factors_df, factors])
    elif own_factors_file is not None:
        factors = own_factors_df

st.divider()
st.markdown('#### Select Products to Compare')
##### SELECT PRODUCTS TO COMPARE #####
current_prods = products['product'].to_list()
current_prods = [p.capitalize() for p in current_prods]
all_compare = st.checkbox(f'''Select to change charcteristics of all
                          products in database''')

if not all_compare:  # Select which products to calculate new emissions for
    to_compare = st.multiselect(f'**Select products to compare**',
                                current_prods, key=1)
    to_compare = [p.lower() for p in to_compare]  # Needed to access data
    if len(to_compare) > 0:  # Saves to variable store
        st.session_state.compare = to_compare

    # Selects database containing chosen products
    original = products[products['product'].isin(to_compare)].copy(deep=True)
    original_emissions = emissions[emissions['product'].isin(to_compare)]\
        .copy(deep=True)
else:  # Selects entire database
    to_compare = [p.lower() for p in current_prods]  # Needed to access data
    st.session_state.compare = to_compare
    original = products.copy(deep=True)
    original_emissions = emissions.copy(deep=True)

# Used to rename and filter dataframe
original_emissions.rename(columns={'product': 'Product'}, inplace=True)
filter_items = ['Product', 'total_emissions', 'manufacture_emissions',
                'transport_emissions', 'use_emissions',
                'reprocessing_emissions', 'disposal_emissions']
col_names = {'total_emissions': 'Total / kg CO2e',
             'manufacture_emissions': 'Manufacturing / kg CO2e',
             'transport_emissions': 'Transport / kg CO2e',
             'use_emissions': 'Use / kg CO2e',
             'reprocessing_emissions': 'Reprocessing / kg CO2e',
             'disposal_emissions': 'Disposal / kg CO2e'}
orig_filt = original_emissions.filter(items=filter_items)
orig_filt.rename(columns=col_names, inplace=True)
st.session_state.original_calc = orig_filt

filter_items = []
for i in range(no_comp):
    filter_items.append('manu_loc_' + str(i+1))
    filter_items.append('depart_loc_' + str(i+1))
    filter_items.append('depart_loc_uk_' + str(i+1))
    filter_items.append('manu_year_' + str(i+1))
# Stores relevant information in variable store
st.session_state.original_info = original_emissions.filter(items=filter_items)

st.divider()
st.markdown('#### Select Information to Change')
#### SELECT INFORMATION TO CHANGE ####
change_location = st.checkbox('Select to change manufacture location')
change_yr = st.checkbox('Select to change year of manufacture')
change_decon = st.checkbox('Select to change sterilisation unit')

changed = original.copy(deep=True)  # Sets up new df for new values

st.divider()
st.markdown('#### Select Required Information For Calculation')
#### SELECT RELEVANT INFO ####
# User inputs destination city for final travel distance calc
felixstowe_ind = uk_cities_list.index('Felixstowe')
dest_city = st.selectbox('Select end destination where product is used',
                         uk_cities_list, index=felixstowe_ind).lower()
st.markdown(f'''> *Please note: this calculation does not take into account
                travel emissions from point they are transported to the UK
                to the end location as it is assumed they are unchanged.*''')

# User selects year
product_year = st.number_input(
    f'Select year for use/disposal emissions factors',
    min_value=1970, max_value=year, value=year, step=1)

decon_type = 'bmm weston steam steriliser'

if change_location or change_yr or change_decon:
    st.divider()
    st.markdown('#### Make Changes')

#### CHANGE LOCATION ####
if change_location:
    sh_ind = cities_list.index('Shanghai (China)')
    manu_loc = st.selectbox(
        'Select new manufacture location', cities_list, index=sh_ind,
        key='ml_%d').lower().strip()

    # Extracts city and country from format city (country)
    manu_ctry = manu_loc[manu_loc.find('(')+1:manu_loc.find(')')]
    manu_cty = manu_loc[:manu_loc.find('(')-1]

    # Autofills options depending on whether comp is UK-made
    if manu_ctry == 'united kingdom':
        uk_comp = True
        port_ind = None
        uk_end_ind = uk_locations.index(manu_cty.title())
    else:
        uk_comp = False
        port_ind = ports_list.index('Shanghai (China)')
        uk_end_ind = uk_locations.index('Felixstowe')

    if port_ind is not None:
        debark_port = st.selectbox(
            'Select new debarkation port', ports_list, index=port_ind,
            key='dp').lower().strip()
    else:
        debark_port = '0'

    if manu_loc != debark_port and not uk_comp:
        try:  # Extracts distance travelled if in dataframe
            land_dist = land_travel_dist.at[(manu_loc, debark_port),
                                            'distance_km']
        except KeyError:  # If not in df, user inputs value
            city1_nm = manu_loc.title()
            city2_nm = debark_port.title()
            land_dist = st.number_input(
                f'Input travel distance between {city1_nm} and {city2_nm}',
                min_value=0.0, step=1.0, format='%0.3f', key='ld1_%d')
            if land_dist > 0.0:
                # Adds new info to df to prevent repeats
                travel_info = [manu_loc, debark_port, land_dist]
                travel_cols = ['start_loc', 'end_loc', 'distance_km']
                new_land_dist = pd.DataFrame([travel_info],
                                             columns=travel_cols)
                new_land_dist = new_land_dist.set_index(['start_loc',
                                                         'end_loc'])
                land_travel_dist = pd.concat([land_travel_dist,
                                              new_land_dist])
        land_travel_dist = land_travel_dist.sort_index()

    depart_loc_uk = st.selectbox(
        f'Select new UK location from which they travel to destination city',
        uk_locations, index=uk_end_ind, key='dluk').lower().strip()

    # Distance between ports if sea travel involved
    if debark_port != depart_loc_uk and not uk_comp:
        city2 = depart_loc_uk + ' (united kingdom)'
        # Calculates or extacts sea travel dist
        sea_dist = calc.calc_sea_distance(sea_travel_dist, debark_port, city2)

        # Adds new info to df to prevent repeats
        sea_travel_info = [debark_port, depart_loc_uk + ' (united kingdom)',
                           sea_dist]
        sea_travel_cols = ['start_loc', 'end_loc', 'distance_km']
        new_sea_dist = pd.DataFrame([sea_travel_info],
                                    columns=sea_travel_cols)
        new_sea_dist = new_sea_dist.set_index(['start_loc', 'end_loc'])
        sea_travel_dist = pd.concat([sea_travel_dist, new_sea_dist])

        sea_travel_dist = sea_travel_dist.sort_index()

    # Distance between manufacture loc and transport loc for UK component
    depart_uk_nm = depart_loc_uk + ' (united kingdom)'
    if manu_loc != depart_uk_nm and uk_comp:
        try:  # Extracts distance travelled if in dataframe
            land_dist = land_travel_dist.at[(manu_loc, depart_uk_nm),
                                            'distance_km']
        except KeyError:  # If not in df, user inputs value
            city1_nm = manu_loc.replace(' (united kingdom)', '').title()
            city2_nm = depart_loc_uk.title()
            land_dist = st.number_input(
                f'Input travel distance between {city1_nm} and {city2_nm}',
                min_value=0.0, step=1.0, format='%0.3f', key='ld')
            if land_dist > 0.0:
                # Adds new info to df to prevent repeats
                travel_info = [manu_loc, depart_uk_nm, land_dist]
                travel_cols = ['start_loc', 'end_loc', 'distance_km']
                new_land_dist = pd.DataFrame([travel_info],
                                             columns=travel_cols)
                new_land_dist = new_land_dist.set_index(['start_loc',
                                                         'end_loc'])
                land_travel_dist = pd.concat([land_travel_dist,
                                              new_land_dist])
        land_travel_dist = land_travel_dist.sort_index()

    # Adds updated info to the dataframe containing product information
    for index, row in changed.iterrows():
        for i in range(no_comp):
            comp = row['component_' + str(i+1)]
            if comp != '0':
                changed.at[index, 'manu_loc_' + str(i+1)] = manu_loc
                if row['debark_port_' + str(i+1)] != '0':
                    changed.at[index, 'debark_port_' + str(i+1)] = debark_port
                if row['depart_loc_uk_' + str(i+1)] != '0':
                    changed.at[index, 'depart_loc_uk_' + str(i+1)] \
                        = depart_loc_uk

#### CHANGE YEAR ####
if change_yr:
    year_prod = st.number_input(
        f'Select new year of component manufacture', min_value=1970,
        max_value=year, value=year, step=1, key='yr_%d')

    # Adds updated info to the dataframe containing product information
    for index, row in changed.iterrows():
        for i in range(no_comp):
            comp = row['component_' + str(i+1)]
            if comp != '0':
                changed.at[index, 'manu_year_' + str(i+1)] = year_prod

#### CHANGE DECON ####
if change_decon:
    decon_type = st.selectbox('Choose different decontamination unit',
                              decon_names, index=1).lower()

st.divider()
st.markdown('#### Perform Calculation')
if not all_compare:  # Options for plotting
    st.session_state.plots = st.checkbox(f'''Select to show comparison
                                             plots following calculation''')
st.session_state.changed_info = changed


#### PERFORM CALCULATIONS ####
# If clicked, performs calculation
perform_calc = st.button('Click to Calculate Emissions')
if perform_calc and len(original) > 0:
    with st.spinner('Running Calculations...'):
        # Manufacturing emissions
        make, total_make = calc.manufacture_calc(
            changed, factors, no_comp, dest_city)
        st.success('Manufacturing calculations complete.')

        # Travel emissions
        travel, total_travel = calc.travel_calc(
            changed, no_comp, additional_factors, dest_city,
            land_travel_dist, sea_travel_dist)
        st.success('Travel calculations complete.')

        # Use emissions
        use = calc.product_use_calc(
            changed, no_comp, additional_factors, product_year)
        st.success('Use calculations complete.')

        # Reprocessing emissions
        total_repro = calc.reprocessing_calc(
            changed, no_comp, additional_factors, product_year, decon_type,
            decon_units)
        st.success('Reprocessing calculations complete.')

        # Disposal emissions
        (incinerate, recycle, landfill, biogenic,
         net_waste) = calc.disposal_calc(
             changed, factors, no_comp, additional_factors, product_year)
        st.success('Disposal calculations complete.')

        # Total emissions
        total = calc.total_calc(
            total_make, total_travel, use, total_repro, net_waste)

        # Creates dataframe containing the results
        results = pd.DataFrame(changed['product'].to_list(),
                               columns=['Product'])
        results['Total / kg CO2e'] = total
        results['Manufacturing / kg CO2e'] = total_make
        results['Transport / kg CO2e'] = total_travel
        results['Use / kg CO2e'] = use
        results['Reprocessing / kg CO2e'] = total_repro
        results['Disposal / kg CO2e'] = net_waste
        results.reset_index(drop=True, inplace=True)

    st.success(f'**Done!**')
    st.session_state.calculation = results  # Saves results to variable store
elif perform_calc and len(original) == 0:
    st.markdown(f'*Please select products first.*')

#### PLOT AND DISPLAY RESULTS ####
# Plots results if required and prints dataframe of results
if st.session_state.calculation is not None:
    results = st.session_state.calculation
    original = st.session_state.original_calc
    info = st.session_state.original_info
    comp_plots = st.session_state.plots
    changed_info = st.session_state.changed_info

    st.divider()
    st.markdown('#### Results')

    # Show results dataframes
    st.markdown('**New**')
    formatted_new = format_dataframe(results)
    st.dataframe(formatted_new)
    st.markdown('\n**Original**')
    formatted_orig = format_dataframe(original)
    st.dataframe(formatted_orig)

    if comp_plots:
        # Create comparison plots
        for ind, row in results.iterrows():
            name = row['Product']
            row_orig = original.set_index('Product').loc[name]
            fig = create_bar_chart(row, row_orig, name)
            st.plotly_chart(fig)

    # Option to download results as df
    download_button(results, changed_info)
