#### IMPORTS ####
import streamlit as st
import pandas as pd
import sys
from importlib import resources as impresources
import os

from datetime import datetime

import plotly.express as px
import plotly.graph_objects as go

from emissions_calculator import product_calculator as calc
from emissions_calculator import read_data
from emissions_calculator import update_files as update
from emissions_calculator import read_upload

import searoute as sr
from geopy.geocoders import Nominatim


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
    '''Checks that data has successfully been read in, else exits program.'''
    if data is None:
        exit_program()

def is_local():
    '''Extracts if program is running locally.'''
    cloud = False
    for i in os.environ:
        if i == 'HOSTNAME':
            cloud = True

    return cloud

#### ADDITIONAL TRAVEL CALCULATIONS ####
def travel_end_loc(selected, dest_city, no_comp, additional_factors,
                   land_travel_dist, cloud, key=0,
                   from_database=False):
    '''
    Calculates GHG emissions corresponding to travel to end city from point
    where it begins journey in UK.

    Parameters:
    -----------
    selected: pd.DataFrame
        Contains product information.
    dest_city: str
        City where product will be used.
    no_comp: int
        Number of components in product.
    additional_factors: pd.DataFrame
        Contains travel emissions factors.
    land_travel_dist: pd.DataFrame
        Contains distances between relevant cities.
    cloud: bool
        If travel distance can be saved to file.
    key: optional
        Needed for st.number_input if used multiple times.
    from_database: bool, optional (default=False)
        If it is read from database or created by user input.
    
    Returns:
    --------
    travel_emissions: float
        Additional emissions for travel.
    '''
    travel_emissions = 0.0

    for i in range(no_comp):
        if from_database:
            mass = selected['mass_kg_' + str(i+1)].iloc[0] # Mass of component
            no_uses = selected['no_uses_' + str(i+1)].iloc[0] # Number of uses
            year = selected['manu_year_' + str(i+1)].iloc[0] # Year
            # Location where component begins journey in UK
            depart_loc_uk = selected['depart_loc_uk_' + str(i+1)].iloc[0]
        else:
            mass = selected['mass_kg_' + str(i+1)] # Mass of component
            no_uses = selected['no_uses_' + str(i+1)] # Number of uses
            year = selected['manu_year_' + str(i+1)] # Year
            # Location where component begins journey in UK
            depart_loc_uk = selected['depart_loc_uk_' + str(i+1)]

        if depart_loc_uk != dest_city and depart_loc_uk != '0' \
            and depart_loc_uk != 0:
                # Reads travel factors
                travel_fact, _ = calc.read_travel_fact(additional_factors,
                                                       year)

                city1 = depart_loc_uk + ' (united kingdom)'
                city2 = dest_city + ' (united kingdom)'
                try: # Extracts distance travelled if in dataframe
                    dist_km = land_travel_dist.at[(city1, city2), \
                                                  'distance_km']
                except KeyError: # If not, user inputs value
                    city1_name = depart_loc_uk.title()
                    city2_name = dest_city.title()
                    dist_km = st.number_input(f'''Input travel distance 
                                              between {city1_name} and 
                                              {city2_name}''',
                                              min_value=0.0,
                                              step=1.0,
                                              format='%0.3f',
                                              key='ld_%d'%key)

                    # Adds new info to df to prevent repeats
                    if dist_km > 0.0:
                        land_travel_dist.loc[(city1, city2), 
                                             ['distance_km']] = [dist_km]
                        if not cloud: # Updates file if available
                            update.update_travel_distances(city1,
                                                           city2,
                                                           dist_km)

                travel_emissions += calc.calc_travel_emissions(dist_km,
                                                               no_uses,
                                                               mass,
                                                               travel_fact)

    return travel_emissions

#### FORMATTING ####
def format_integer_without_commas(x):
    '''Ensures years are printed without a comma.'''
    if isinstance(x, int):
        return f'{x}'
    return x

def choose_database(chosen, product_emissions, no_comp, additional_factors,
                    land_travel_dist, dest_city, cloud):
    '''
    Selects relevant part of emissions database if certain product
    is selected from list.

    Parameters:
    -----------
    chosen: str
        Name of product
    product_emissions: pd.DataFrame
        Contains current products inventory.
    no_comp: int
        Maximum number of components in data.
    additional_factors: pd.DataFrame
        Contains travel emissions factors.
    land_travel_dist: pd.DataFrame
        Contains distances between relevant cities.
    dest_city: str
        City where product will be used.
    cloud: bool
        Determines if travel distance can be saved to file.

    Returns:
    -------
    original_selected_df: pd.DataFrame
        Extract from original database containing chosen products.
    product_emissions: pd.DataFrame
        Contains emissions values only.
    '''
    # Finds information in database on the selected product
    selected = product_emissions[product_emissions['product'] == chosen]\
               .copy(deep=True)
    selected.set_index('product', inplace=True)

    # Works out additional travel emissions to end city
    travel = selected['transport_emissions'].iloc[0]
    end_travel = travel_end_loc(selected, dest_city, no_comp,
                                additional_factors, land_travel_dist,
                                cloud, from_database=True)
    selected['transport_emissions'] = end_travel + travel
    original_selected_df = selected.copy(deep=True)

    # Sets index name
    selected.index.names = ['Product']
    
    filter_items = ['total_emissions', 'manufacture_emissions',
                    'transport_emissions', 'use_emissions',
                    'reprocessing_emissions', 'disposal_emissions']
    col_names = {'total_emissions': 'Total / kg CO2e',
                 'manufacture_emissions': 'Manufacturing / kg CO2e',
                 'transport_emissions': 'Transport / kg CO2e',
                 'use_emissions': 'Use / kg CO2e',
                 'reprocessing_emissions': 'Reprocessing / kg CO2e',
                 'disposal_emissions': 'Disposal / kg CO2e'}

    product_emissions = selected.filter(items=filter_items)
    # Renames columns
    product_emissions.rename(columns=col_names, inplace=True)
    
    for i in range(no_comp):
        # Stops searching if no more components
        if selected['component_' + str(i+1)].iloc[0] == '0':
            break
         # Additional filters are component names, product location and year
        filter_items.append(f'component_{i+1}')
        filter_items.append(f'manu_loc_{i+1}')
        # Capitalises strings in these columns
        selected['component_' + str(i+1)] = selected['component_' + str(i+1)]\
                                            .str.title()
        selected['manu_loc_' + str(i+1)] = selected['manu_loc_' + str(i+1)]\
                                           .str.title()

        # Used to rename columns
        col_names['component_' + str(i+1)] = 'Component ' + str(i+1)
        col_names['manu_loc_' + str(i+1)] = 'Manufacture Location ' + str(i+1)
        col_names['manu_year_' + str(i+1)] = 'Manufacture Year ' + str(i+1)

        # Removes commas from dates
        selected = selected.map(format_integer_without_commas)
        filter_items.append(f'manu_year_{i+1}')

    # Filters to only show specific columns
    data = selected.filter(items=filter_items)
    # Renames columns
    data.rename(columns=col_names, inplace=True)
    # Capitalises product names
    data.index = data.index.str.capitalize()
    # Rounds values then converts all to strings
    data = data.round(decimals=6).astype(str)
    # Displays dataframe
    st.dataframe(data.T)

    return original_selected_df, product_emissions

def select_autofill(selected_prod, product_categories, available_factor,
                    cities_list, ports_list, uk_locations):
    '''
    Creates dictionary of values to autofill the options for if user is
    changing a pre-exisiting product in the file.

    Parameters:
    -----------
    selected_prod: pd.DataFrame
        Contains current information on product.
    product_categories: list
        Categories of product.
    available_factor: pd.DataFrame
        Contains emissions factors.
    cities_list, ports_list, uk_locations: list
        List of cities, ports and places in UK to use as autofill.

    Returns:
    --------
    selected_auto: dict
        Autofill options corresponding to current product.
    '''
    selected_auto = {}
    
    count = 1
    # Finds number of components up to where 0's appear
    total_comp = int(list(selected_prod.columns)[-7].split('_')[-1])
    for i in range(total_comp):
        c_name = selected_prod['component_' + str(count)].iloc[0]
        if c_name == '0' or c_name == 0:
            no_comp = count - 1
            break
        elif i == (total_comp - 1):
            no_comp = total_comp
        count += 1

    selected_auto['no_comp'] = no_comp
    cat = selected_prod['category'].iloc[0].capitalize()
    selected_auto['cat'] = product_categories.index(cat)
    selected_auto['no_uses'] = selected_prod['no_uses_1'].iloc[0]
    selected_auto['elec'] = str(selected_prod['electricity'].iloc[0])
    selected_auto['water'] = str(selected_prod['water'].iloc[0])
    selected_auto['gas'] = str(selected_prod['gas'].iloc[0])

    for i in range(no_comp):
        comp = selected_prod['component_' + str(i+1)].iloc[0].capitalize()
        try:
            selected_auto['comp_' + str(i+1)] = available_factor.index(comp)
        except ValueError:
            st.error(f'''{comp} not listed in factors file. Please 'Input own 
                         factor' or select 'Include factors from current 
                         database'.''')
            available_factor.insert(-2, comp)
            selected_auto['comp_' + str(i+1)] = available_factor.index(comp)
        
        yr = selected_prod['manu_year_' + str(i+1)].iloc[0]
        selected_auto['yr_' + str(i+1)] = int(yr)
        
        mass = selected_prod['mass_kg_' + str(i+1)].iloc[0]
        selected_auto['mass_' + str(i+1)] = float(mass)
        
        bio = selected_prod['biogenic_' + str(i+1)].iloc[0]
        selected_auto['bio_' + str(i+1)] = True if bio == 1 else False

        loc = str(selected_prod['manu_loc_' + str(i+1)].iloc[0])
        selected_auto['loc_' + str(i+1)] = 0 if loc == '0' \
            else cities_list.index(loc.title())
        
        port = str(selected_prod['debark_port_' + str(i+1)].iloc[0])
        selected_auto['port_' + str(i+1)] = 0 if port == '0' \
            else ports_list.index(port.title())
        
        uk_loc = str(selected_prod['depart_loc_uk_' + str(i+1)].iloc[0])
        selected_auto['loc_uk_' + str(i+1)] = 0 if uk_loc == '0' \
            else uk_locations.index(uk_loc.title())
        
        repro = selected_prod['reprocessing_' + str(i+1)].iloc[0]
        selected_auto['repro_' + str(i+1)] = repro
        
        recycle = selected_prod['recycle_' + str(i+1)].iloc[0]
        incinerate = selected_prod['incinerate_' + str(i+1)].iloc[0]
        landfill = selected_prod['landfill_' + str(i+1)].iloc[0]
        if recycle == 1:
            disposal = 'recycle'
        elif incinerate == 1:
            disposal = 'incinerate'
        elif landfill == 1:
            disposal = 'landfill'
        else:
            disposal = None
        selected_auto['disposal_' + str(i+1)] = disposal

    return selected_auto

def compare_changes(original, changed, name, index_names):
    '''Creates new dataframe to compare original product and changes made.'''
    # Creates df using name of product and emissions list
    new_df = pd.DataFrame([name] + changed).T
    
    # Renames columns with required emission type
    new_df.columns = ['Product'] + index_names
    
    # Sets index as product name
    new_df.set_index('Product', inplace=True)
    
    # Combines old and new emissions into df
    comb_df = pd.concat([original, new_df], ignore_index=True)

    return comb_df

#### PLOTS ####
def create_bar_chart(data, comp=False, prod_name=None, w=1000, h=700, g=0.2):
    '''
    Create a plotly stacked bar chart.
    
    Parameters:
    -----------
    data: pd.Dataframe
        rows = products, columns = emissions broken down into categories.
    comp: bool, optional (default=False)
        If comparison plot required.
    prod_name: str, optional (default=None)
        Name for plot if required.
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
    # Creates title
    if comp:
        name = ['Original Product', 'New Product']
        title = f'Emissions Comparison: {prod_name.title()}'
    else:
        name = data['Product'].to_list()
        title = 'Emissions Comparison'
    
    # Takes dataframe and converts information to lists
    make = data['Manufacturing / kg CO2e'].to_list()
    travel = data['Transport / kg CO2e'].to_list()
    use = data['Use / kg CO2e'].to_list()
    repro = data['Reprocessing / kg CO2e'].to_list()
    waste = data['Disposal / kg CO2e'].to_list()

    # Prevents error if < 0
    for ind, val in enumerate(waste):
        if val < 0.0:
            waste[ind] = 0.0

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
    fig.update_layout(barmode='stack',
                      autosize=False,
                      bargap=g, 
                      width=w,
                      height=h,
                      title=title,
                      yaxis_title='Emissions / kg CO2e')

    return fig

def create_pie_chart(data, name='Product', h=650, w=900):
    '''
    Create a plotly pie chart.
    
    Parameters:
    -----------
    data: pd.Series
        Product emissions broken down into categories.
    name: str, optional (default=Product)
        Name for plot if required.
    h: int, optional (default=650)
        Height of plot.
    w: int, optional (default=900)
        Width of plot.

    Returns:
    -------
    plotly.figure
    '''
    # Removes total (sum of components)
    data = data.drop('Total / kg CO2e')
    # Doesn't include disposal if it is less than 0
    if data['Disposal / kg CO2e'] < 0.0:
        data = data.drop('Disposal / kg CO2e')
        colours = ['orange', 'blue', 'purple', 'green']
    else:
        colours = ['orange', 'blue', 'purple', 'green', 'crimson']

    # Create pie chart
    fig = go.Figure(data=[go.Pie(labels=data.index,
                                 values=data.values,
                                 marker=dict(colors=colours))])

    # Figure layout
    fig.update_layout(
        autosize=False,
        width=w,
        height=h,
        title=f'Total Emissions: {name.title()}',
        title_x=0.5
    )

    return fig

def comparison_emissions_graphic(total):
    '''Displays emissions in terms of comparison values.'''
    # CO2e emissions per km driven by average car
    car_comp = round((total / 0.1224), 2)
    st.markdown(f'''> 🚗 Emissions equivalent to driving **{car_comp} km** in
                    an average passenger car (EEA, 2020).''')

    return

#### DOWNLOADS ####
def create_product_df(product, total_manu_emissions, total_travel_emissions,
                      use_emissions, reprocess_emissions,
                      net_waste_emissions, total_emissions):
    '''Creates new pd.DataFrame with required information for output.'''
    product_info = product.copy(deep=True)
    no_comp = int(list(product_info.index)[-7].split('_')[-1])
            
    # Drops info not to save
    indices_to_drop = []
    for i in range(no_comp):
        col1 = 'land_dist_' + str(i+1)
        col2 = 'sea_dist_' + str(i+1)
        indices_to_drop.append(col1)
        indices_to_drop.append(col2)
    for idx in indices_to_drop:
        if idx in product_info.index:
            product_info.drop(idx, inplace=True)

    emissions_info = product_info.copy(deep=True)
    emissions_info['manufacture_emissions'] = total_manu_emissions
    emissions_info['transport_emissions'] = total_travel_emissions
    emissions_info['use_emissions'] = use_emissions
    emissions_info['reprocessing_emissions'] = reprocess_emissions
    emissions_info['disposal_emissions'] = net_waste_emissions
    emissions_info['total_emissions'] = total_emissions

    return product_info, emissions_info

def convert_df(df):
    '''Converts dataframe to csv file for download.'''
    return df.to_csv(index=False).encode('utf-8')

def download_example_file():
    '''Download example file for users to fill in.'''
    ex_df = pd.read_excel('resources/factors_example.xlsx')
    ex = convert_df(ex_df)
    
    st.download_button(
        label='Download empty file',
        data=ex,
        file_name='factors.csv',
        mime='text/csv'
    )

    return

def download_databases_new_product(product_info, emissions_info,
                                   extra_travel, incl_travel,
                                   to_database=False):
    '''Download dataframes with new product added.'''
    products = update.update_inventory(product_info, to_database)
    emissions, single_prod = update.update_emissions(emissions_info,
                                                     to_database)

    if single_prod is not None:
        # Adds extra travel emissions if required to file output
        if incl_travel:
            travel = single_prod['transport_emissions'].to_list()
            new_travel = travel + extra_travel
            single_prod['transport_emissions'] = new_travel

            total = single_prod['total_emissions'].to_list()
            new_total = total + extra_travel
            single_prod['total_emissions'] = new_total
        single_prod_csv = convert_df(single_prod)

        st.download_button(
            label='Download single product CSV',
            data=single_prod_csv,
            file_name='new_product.csv',
            mime="text/csv",
        )

    if products is not None:
        prod_csv = convert_df(products)

        st.download_button(
            label='Download product database CSV',
            data=prod_csv,
            file_name='products.csv',
            mime="text/csv",
        )

    if emissions is not None:
        emissions_csv = convert_df(emissions)
    
        st.download_button(
            label='Download emissions database CSV',
            data=emissions_csv,
            file_name='emissions.csv',
            mime="text/csv",
        )


#### MAIN ####
# Removes whitespace from edge of page
st.set_page_config(layout='wide')

# Page title
st.title('Calculate Emissions for Products')
st.markdown(f'''Input product details to get an estimate of its
                carbon footprint per use.''')

# Checks if running locally
cloud = is_local()

#### READ IN DATA ####
# Finds current year
today = datetime.now()
year = int(today.strftime("%Y"))

with st.spinner('Loading data...'):
    # Reads in factors file
    factors = read_data.read_factors()
    
    # Reads other factors such as travel and electricity/water/gas
    additional_factors = read_data.read_additional_factors()
    check_data(additional_factors)
    
    # Read list of processes in factors file
    process_list = read_data.read_processes()
    check_data(process_list)
    
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
    
    # Inventory file
    product_emissions = read_data.read_emissions()
    check_data(product_emissions)
    current_prod = product_emissions['product'].to_list()


#### INPUT OWN FACTORS AND INFO ####
# Finds which years of Defra file have been added to files
defra_years_in_file = []
for index, row in additional_factors.iterrows():
    if row['name'] == 'hgv transport':
        defra_years_in_file.append(row['year'])

# Options for inputting own emissions factors in some cases
with st.expander('Update Information'):
    st.markdown(f'''Defra used for: transport, electricity, water, gas and
                    landfill emissions factors.''')
    st.markdown(f'''**Upload Defra file if not currently in database.**
                    Database contains years: {defra_years_in_file}''')
    defra_file = st.file_uploader('Choose Defra file', type=['xlsx'])
    if defra_file is not None:
        defra_year = st.number_input(f'Enter file year', min_value=2000,
                                     max_value=year, step=1, value=year)
        if not cloud:
            defra_to_database = True
        else:
            defra_to_database = False
        additional_factors = read_upload.new_defra(
            defra_file, str(defra_year), to_database=defra_to_database)

    st.markdown(f'''**Choose own emissions factors (kg CO2e) for the following
                    processes if required.** Leave as 0 to use factors in
                    database.''')
    laundry_fact = st.number_input(f'Laundry (per kg)', min_value=0.0,
                                   step=0.001, format='%0.6f')

    st.markdown(f'**Use another decontamination unit.**')
    new_decon_name = st.text_input(f'Name of unit').lower()
    new_decon_elec = st.number_input(f'Electricity use (kWh)',
                                     min_value = 0.0, step=0.0001,
                                     format='%0.4f')
    new_decon_water = st.number_input(f'Water use (L)', min_value = 0.0,
                                      step=0.0001, format='%0.4f')
    new_decon_gas = st.number_input(f'Gas use (m3)', min_value = 0.0,
                                    step=0.0001, format='%0.4f')

    if (not cloud and len(new_decon_name) > 0):
        if st.checkbox('Add to file'):
            calc.add_new_decon_to_file(new_decon_name, new_decon_elec,
                                       new_decon_water, new_decon_gas)


#### ADD OWN FACTORS FILE ####
need_factors = True if factors is None else False
upload_factors = st.checkbox(f'Upload own emissions factors file',
                             value=need_factors)
if upload_factors:
    join_files = False
    own_factors_file = st.file_uploader(f'Upload own emission factors file',
                                        type=['csv'])
    with st.expander(f'File requirements and example'):
        download_example_file()
        st.markdown(read_file_contents('resources/own_factors.md'))
    if own_factors_file is not None:
        own_factors_df = pd.read_csv(own_factors_file)
        join_files = st.checkbox(f'Include factors from current database')
        
        # Joins with stored data if required
        if join_files and factors is not None:
            factors = pd.concat([own_factors_df, factors])
        else:
            factors = own_factors_df

if factors is not None:
    try:
        # Creates list of available factors to choose from
        available_factor = factors['component'].to_list()
        available_factor = list(dict.fromkeys(available_factor))
        # Capitalises names
        available_factor = [word.capitalize() for word in available_factor]
        # Adds option for other
        available_factor.append('Other')
    except KeyError:
        st.error('Error: Incorrect factors file format.')
        exit_program()
else:
    exit_program()


#### SETS UP NEW INFO ####
# Sets index and sorts additional factors
additional_factors.set_index(['name', 'unit', 'year'], inplace=True)
additional_factors = additional_factors.sort_index()

# Reads info on decontamination units
decon_units = read_data.read_decon_units()
if new_decon_name != '':
    decon_units[new_decon_name + ' electricity'] = ['kwh', new_decon_elec]
    decon_units[new_decon_name + ' water'] = ['l', new_decon_water]
    decon_units[new_decon_name + ' gas'] = ['m3', new_decon_gas]

# Extracts name of decontamination units to select
decon_names_all = list(decon_units.keys())
decon_names = []
for ind, nm in enumerate(decon_names_all):
    if ind%3 == 0:
        decon_names.append(nm[:-12].capitalize())
decon_info = False
decon_type = None


#### USER INPUT ####
# User can input name of product
name = st.text_input('Name of Product').lower()


#### USER SELECTS DATABASE PRODUCT IF AVAILABLE ####
# Shows list of all products currently in dataframe
current_store = [None]
for prod in current_prod:
    if name in prod and prod not in current_store:
        current_store.append(prod.capitalize())

# Lists all categories in dataframe
product_categories = []
for cat in product_emissions['category'].to_list():
    cat = cat.capitalize()
    if cat not in product_categories:
        product_categories.append(cat)

# User can choose to get info about a current product
chosen = st.selectbox('Select required product if available',
                      current_store)

#### USER INPUTS DESTINATION ####
# User inputs destination city for final travel distance calc
felixstowe_ind = uk_cities_list.index('Felixstowe')
dest_city = st.selectbox(f'Select approximate destination for product',
                         uk_cities_list, index=felixstowe_ind).lower()

#### SETS UP VARIABLES ####
# Holds product info
index_names = ['product', 'category', 'electricity',
               'water', 'gas']

change_info = False
selected_auto = None
check = None

#### USER SELECTS DATABASE PRODUCT ####
if chosen is not None:
    # If product selected, prints out information to user
    no_comp = int(list(product_emissions.columns)[-7].split('_')[-1])
    prod_df, prod_em = choose_database(chosen.lower(), product_emissions,
                                       no_comp, additional_factors,
                                       land_travel_dist, dest_city,
                                       cloud)
    comparison_emissions_graphic(prod_em['Total / kg CO2e'].iloc[0])

    pie_chart = create_pie_chart(prod_em.T.squeeze(), name=chosen)
    st.plotly_chart(pie_chart)

    # Download image as PNG
    st.download_button(label='Download pie chart as PNG',
                       data=pie_chart.to_image(format='png', scale=3),
                       file_name='emissions.png', mime='image/png', key=0)
    
    change_info = st.checkbox(f'Change product information')
    if change_info:
        selected_auto = select_autofill(prod_df, product_categories,
                                        available_factor, cities_list,
                                        ports_list, uk_locations)

#### USER CREATES OWN NEW PRODUCT ####
if chosen is None or change_info:
    if change_info and len(name) == 0:
        name = chosen.lower()
    
    # List to store all inputted data
    all_info = [name]

    # If no product selected, user can create own
    no_comp_val = None if not change_info else selected_auto['no_comp']
    no_comp = st.number_input(f'''Enter number of components used to make
                              product''', min_value=1, value=no_comp_val,
                              step=1)
    if no_comp is not None:
        no_comp = int(no_comp)

        #### WHOLE PRODUCT INFO ####
        st.markdown(f'##### **Product Information**')
        # User selects category
        cat_ind = 0 if not change_info else selected_auto['cat']
        cat = st.selectbox(f'Select category', product_categories,
                           index=cat_ind).lower()
        all_info.append(cat)

        # User inputs number of uses of product
        use_ind = 1 if not change_info else selected_auto['no_uses']
        no_uses = st.number_input(f'''Select number of times product can be
                                  used''', min_value=1, step=10,
                                  value=use_ind)

        # User selects year of product year
        use_year = st.number_input(f'Year of product use', min_value=1970,
                                   max_value=year, value=year, step=1)

        #### USE EMISSIONS - ELECTRICITY ####
        use_emissions = 0.0
        elec_val = False
        if change_info:
            e_auto = selected_auto['elec']
            if e_auto != '0':
                elec_val = True
                e_info = e_auto[e_auto.find('(')+1:e_auto.find(')')]
                t_val = float(e_info[:e_info.find(' ')])
                pr_val = float(e_info[e_info.find(' ')+1:])
            else:
                t_val = 0.0
                pr_val = 0.0
        else:
            t_val = 0.0
            pr_val = 0.0
        electricity = st.checkbox('Product uses electricity during lifetime',
                                  value=elec_val)
        pr = None
        t = None
        if electricity:
            t = st.number_input(f'Time on during use (hr)', value=t_val,
                                min_value=0.0, step=0.001, format='%0.5f')
            pr = st.number_input(f'Power rating (W)', value=pr_val,
                                 min_value=0.0, step=0.001, format='%0.3f')
            use_emissions += calc.use_calc(additional_factors, use_year,
                                           power_rating=pr, time_per_use=t)
        all_info.append('1 (' + str(t) + ' ' + str(pr) + ')' if electricity \
                        else '0')

        #### USE EMISSIONS - WATER ####
        water_val = False
        if change_info:
            w_auto = selected_auto['water']
            if w_auto != '0':
                water_val = True
                w_val = float(w_auto[w_auto.find('(')+1:w_auto.find(')')])
            else:
                w_val = 0.0
        else:
            w_val = 0.0
        water = st.checkbox('Product uses water during lifetime',
                            value=water_val)
        w = None
        if water:
            w = st.number_input(f'Amount of water used per use (L)',
                                min_value=0.0, step=0.001, value=w_val,
                                format='%0.5f')
            use_emissions += calc.use_calc(additional_factors,
                                           use_year, water_vol_per_use=w)
        all_info.append('1 (' + str(w) + ')' if water else '0')

        #### USE EMISSIONS - GAS ####
        gas_val = False
        if change_info:
            g_auto = selected_auto['gas']
            if g_auto != '0':
                gas_val = True
                g_val = float(g_auto[g_auto.find('(')+1:g_auto.find(')')])
            else:
                g_val = 0.0  
        else:
            g_val = 0.0
        gas = st.checkbox('Product uses gas during lifetime', value=gas_val)
        g = None
        if gas:
            g = st.number_input(f'Amount of gas used per use (m$^{3}$)',
                                min_value=0.0, step=0.001, value=g_val,
                                format='%0.5f')
            use_emissions += calc.use_calc(additional_factors, use_year,
                                           gas_per_use=g)
        all_info.append('1 (' + str(g) + ')' if gas else '0')

        #### INDIVIDUAL COMPONENTS OF PRODUCT ####
        # User inputs information about each component
        for i in range(no_comp):
            new_index = [f'component_{i+1}', f'manu_year_{i+1}',
                         f'mass_kg_{i+1}', f'no_uses_{i+1}',
                         f'biogenic_{i+1}', f'manu_loc_{i+1}',
                         f'debark_port_{i+1}', f'depart_loc_uk_{i+1}',
                         f'land_dist_{i+1}', f'sea_dist_{i+1}',
                         f'reprocessing_{i+1}', f'recycle_{i+1}',
                         f'incinerate_{i+1}', f'landfill_{i+1}']
            index_names += new_index
            
            st.markdown(f'###### **Component {i+1} Information**')

            # User selects if it is single use packaging
            packaging = st.checkbox('Single-use packaging', key='pack_%d'%i)

            if change_info and i <= (selected_auto['no_comp'] - 1):
                autofill = True
            else:
                autofill = False

            #### COMPONENT OF PRODUCT ####
            # Chooses component from list in factors
            comp_ind = 0 if not autofill else \
                           selected_auto['comp_' + str(i+1)]
            curr_comp = st.selectbox(f'Select component {i+1}',
                                     available_factor, index=comp_ind,
                                     key='comp_%d'%i).lower()
            curr_process = False
            own_comp = False
            # If other, user inputs name
            if curr_comp == 'other':
                own_comp = True
                curr_comp = st.text_input('Name of component',
                                          key='name_%d'%i).lower().strip()
                # User describes if it is a process (e.g. weaving cotton)
                new_process = st.checkbox(f'''Factor describes process
                                          (e.g. weaving)''', key='np_%d'%i)
                if new_process:
                    processes_list.append(curr_comp)
            # Not all info required if it is a process
            if curr_comp in process_list:
                curr_process = True
            all_info.append(curr_comp)

            #### INPUT OWN INDIVIDUAL FACTORS ####
            # Can input your own factors if desired
            new_fact = 0.0
            if own_comp:
                input_own_factor = True
                own_fact_text = f'''Input emissions factor (kg CO$_{2}$e / kg) 
                                    for **{curr_comp.capitalize()}**. '''
            else:
                input_own_factor = st.checkbox(f'Input own factor',
                                               key='of_%d'%i)
                own_fact_text = f'''Input emissions factor (kg CO$_{2}$e / kg)
                                    for **{curr_comp.capitalize()}**. 
                                    Leave as 0.0 to use value in database.'''
                
            if len(curr_comp) > 0 and input_own_factor:
                new_fact = st.number_input(own_fact_text, value=0.0,
                                           min_value=0.0, step=0.001,
                                           format='%0.5f', key='fact_%d'%i)

            #### YEAR OF MANUFACTURE ####
            # User selects year of product manufacture
            if i == 0 or change_info:
                comp_val = year if not autofill else \
                               selected_auto['yr_' + str(i+1)]
                year_prod = st.number_input(f'Year of component manufacture',
                                            min_value=1970, max_value=year,
                                            value=comp_val,
                                            step=1, key='yr_%d'%i)
            # Autofills value of previous component
            else:
                prev_yr = all_info[6+((i-1)*14)]
                year_prod = st.number_input(f'Year of component manufacture',
                                            min_value=1970, max_value=year,
                                            value=prev_yr,
                                            step=1, key='yr_%d'%i)
            all_info.append(year_prod)

            #### MASS OF COMPONENT ####
            # User inputs product mass
            # Autofills as prev mass for process
            if i != 0 and curr_process and not change_info:
                prev_mass = all_info[7+((i-1)*14)]
                mass = st.number_input(f'Give component mass in kg',
                                       min_value=0.0, step=0.01,
                                       value=prev_mass, format='%0.5f',
                                       key='mass_%d'%i)
            else:
                mass_val = 0.0 if not autofill else \
                               selected_auto['mass_' + str(i+1)]
                mass = st.number_input(f'Give component mass in kg',
                                       min_value=0.0, step=0.01,
                                       value=mass_val, format='%0.5f',
                                       key='mass_%d'%i)
            all_info.append(mass)

            #### NUMBER OF USES ####
            # Saves number of uses depending if it is single-use packaging
            if packaging:
                all_info.append(1)
            else:
                all_info.append(no_uses)

            # Info only required if it is not a process (e.g. weaving cotton)
            if not curr_process:
                #### BIOGENIC COMPONENT ####
                # User can select if it has a biogenic component
                bio_val = False if not autofill else \
                              selected_auto['bio_' + str(i+1)]
                biogenic = st.checkbox('Biogenic component', value=bio_val,
                                       key='bio_%d'%i)
                all_info.append(1 if biogenic else 0)

                #### TRAVEL INFO ####
                #### LOCATION OF MANUFACTURE ####
                # User selects travel information for component
                # Location where component manufactured
                if i == 0 or change_info:
                    sh_ind = cities_list.index('Shanghai (China)')
                    ml_ind = sh_ind if not autofill else \
                                 selected_auto['loc_' + str(i+1)]
                    manu_loc = st.selectbox('Component manufacture location',
                                            cities_list, index=ml_ind,
                                            key='ml_%d'%i).lower().strip()
                # Autofills with same location as previous component
                else:
                    prev_loc = all_info[10+((i-1)*14)]
                    prev_ind = cities_list.index(prev_loc.title())
                    manu_loc = st.selectbox('Component manufacture location',
                                            cities_list,
                                            index=prev_ind,
                                            key='ml_%d'%i).lower().strip()

                # Extracts city and country from city (country)
                manu_ctry = manu_loc[manu_loc.find('(')+1:manu_loc.find(')')]
                manu_cty = manu_loc[:manu_loc.find('(')-1]

                # Autofills options depending on whether comp is UK-made
                if manu_ctry == 'united kingdom':
                    uk_comp = True
                    port_ind = None
                    uk_end_ind = uk_locations.index(manu_cty.title())
                else:
                    uk_comp = False
                    port_ind = ports_list.index('Shanghai (China)') # 232 # Shanghai
                    uk_end_ind = uk_locations.index('Felixstowe') # 289 # Felixstowe
                all_info.append(manu_loc)

                #### DEBARKATION PORT ####
                # Port where comp leaves country of manufacture
                if not uk_comp:
                    if i == 0 or change_info:
                        dp_ind = port_ind if not autofill else \
                                     selected_auto['port_' + str(i+1)]
                        debark_port = st.selectbox('Debarkation port',
                                                   ports_list, index=dp_ind,
                                                   key='dp_%d'%i).\
                                                   lower().strip()
                    else:
                        prev_loc = all_info[11+((i-1)*14)]
                        prev_ind = ports_list.index(prev_loc.title())
                        debark_port = st.selectbox('Debarkation port',
                                                   ports_list, index=prev_ind,
                                                   key='dp_%d'%i)\
                                                   .lower().strip()
                else:
                    debark_port = '0'
                all_info.append(debark_port)

                # Distance between manufacture city and port
                land_dist_km = 0
                if manu_loc != debark_port and not uk_comp:
                    try: # Extracts distance travelled if in dataframe
                        land_dist_km += land_travel_dist.at[(manu_loc,
                                                             debark_port),\
                                                            'distance_km']
                    except KeyError: # If not, user inputs value
                        city1_nm = manu_loc.title()
                        city2_nm = debark_port.title()
                        land_dist_km += st.number_input(f'''Input travel
                                                        distance between
                                                        {city1_nm} and
                                                        {city2_nm}''',
                                                        min_value=0.0,
                                                        step=1.0,
                                                        format='%0.3f',
                                                        key='ld1_%d'%i)
                        if not cloud and land_dist_km > 0.0:
                            update.update_travel_distances(manu_loc,
                                                           debark_port,
                                                           land_dist_km)

                #### LOCATION IN UK ####
                # Where they travel from in UK (port if from overseas)
                if i == 0 or change_info:
                    dl_ind = uk_end_ind if not autofill else \
                                 selected_auto['loc_uk_' + str(i+1)]
                    depart_loc_uk = st.selectbox(f'''UK location from which
                                                 they travel to destination
                                                 city''', uk_locations,
                                                 index=uk_end_ind,
                                                 key='dluk_%d'%i)\
                                                 .lower().strip()
                else:
                    prev_loc = all_info[12+((i-1)*14)]
                    prev_ind = uk_locations.index(prev_loc.title())
                    depart_loc_uk = st.selectbox(f'''UK location from which
                                                 they travel to destination
                                                 city''', uk_locations,
                                                 index=prev_ind,
                                                 key='dluk_%d'%i).\
                                                      lower().strip()
                all_info.append(depart_loc_uk)

                # Distance between ports if sea travel involved
                if debark_port!= depart_loc_uk and not uk_comp:
                    city2 = depart_loc_uk + ' (united kingdom)'
                    # Calculates or extacts sea travel dist
                    sea_dist_km = calc.calc_sea_distance(sea_travel_dist,
                                                         debark_port,
                                                         city2)
                else:
                    sea_dist_km = 0

                # Distance between manufacture loc and place of depart for UK
                if manu_loc != depart_loc_uk and uk_comp:
                    try: # Extracts distance travelled if in dataframe
                        city2 = depart_loc_uk + ' (united kingdom)'
                        land_dist_km += land_travel_dist.at[(manu_loc,
                                                             city2),\
                                                            'distance_km']
                    except KeyError: # If not, user inputs value
                        city1_nm = manu_loc[:manu_loc.find('(')-1].title()
                        city2_nm = depart_loc_uk.title()
                        land_dist_km += st.number_input(f'''Input travel
                                                        distance between
                                                        {city1_nm} and 
                                                        {city2_nm}''',
                                                        min_value=0.0,
                                                        step=1.0,
                                                        format='%0.3f',
                                                        key='ld2_%d'%i)
                        if not cloud and land_dist_km > 0.0:
                            update.update_travel_distances(manu_loc,
                                                           city2,
                                                           land_dist_km)
                
                all_info.append(land_dist_km)
                all_info.append(sea_dist_km)

                #### REPROCESSING ####
                # User inputs method of reprocessing
                re_ind = 0
                perc_val = 0.0
                if autofill:
                    re_auto = selected_auto['repro_' + str(i+1)]
                    if re_auto != '0':
                        re_ind = 1 if re_auto == 'laundry' else 2
                        if re_auto != 'laundry':
                            perc_val = float(re_auto[re_auto.\
                                             find('(')+1:re_auto.find(')')])
                
                repro = st.selectbox('Component reprocessing',
                                     [None, 'Laundry', 'HSDU'], index=re_ind,
                                     key='rep_%d'%i)
                if repro == 'HSDU':
                    if not decon_info:
                        # User inputs decontamination unit filling
                        perc = st.number_input(f'''Enter product percentage
                                               filling of decontamination
                                               unit''', value=perc_val*100,
                                               min_value=0.0, max_value=100.0,
                                               step=0.001, format='%0.2f')
                        repro = 'hsdu (' + str(perc/100) + ')'
                        decon_info = True
                    else:
                        repro = 'hsdu (' + str(perc/100) + ')'
                    if decon_type is None:
                        decon_type = st.selectbox(f'''Select decontamination
                                                  unit''',
                                                  decon_names).lower()
                all_info.append(repro.lower() if repro is not None else '0')

                #### DISPOSAL ####
                if not autofill:
                    disposal_ind = 0
                else:
                    d_type = selected_auto['disposal_' + str(i+1)]
                    if d_type == 'recycle':
                        disposal_ind = 0
                    elif d_type == 'incinerate':
                        disposal_ind = 1
                    elif d_type == 'landfill':
                        disposal_ind = 2
                    else:
                        disposal_ind = 3
                # User selects method of disposal
                disposal = st.selectbox('Component disposal method',
                                        ['Recycle', 'Incineration',
                                         'Landfill', None],
                                        index=disposal_ind,
                                        key='dis_%d'%i)

                if disposal == 'Recycle':
                    all_info += [1,0,0]
                elif disposal == 'Incineration':
                    all_info += [0,1,0]
                elif disposal == 'Landfill':
                    all_info += [0,0,1]
                else:
                    all_info += [0,0,0]

            # Autofills some info if it is a process (e.g. weaving cotton)
            else:
                sh_ind = cities_list.index('Shanghai (China)')
                ml_ind = sh_ind if not autofill else \
                             selected_auto['loc_' + str(i+1)]
                process_loc = st.selectbox('Process location',
                                        cities_list, index=ml_ind,
                                        key='ml_%d'%i).lower().strip()
                manu_ctry = process_loc[process_loc.find('(')+1:\
                                        process_loc.find(')')]
                all_info += [0, process_loc, '0', '0', 0, 0, '0', 0, 0, 0]

            #### ADDS OWN FACTOR TO DF IF REQUIRED ####
            if new_fact != 0.0:
                # Checks if same information exists in database
                condition = (factors['component'] == curr_comp) \
                            & (factors['loc'] == manu_ctry) & \
                            (factors['year'] == year_prod)
                # If it does, will replace current value with user-specified
                factors.loc[condition, 'factor_kgCO2eq_unit'] = new_fact

                # Checks if component already in database
                found_comp = (factors['component'] == curr_comp)

                # If not in database, user must specify carbon content
                if  (~condition.any()) & (~found_comp.any()):
                    new_cc = st.number_input(f'''Input carbon content
                                             (kg per kg) for
                                             **{curr_comp.capitalize()}**''',
                                             value=0.0, min_value=0.0,
                                             step=0.001,
                                             format='%0.3f', key='cc_%d'%i)
                    # Creates new row in factors dataframe with info
                    new_row = {'component': curr_comp, 'loc': manu_ctry,
                               'year': year_prod,
                               'factor_kgCO2eq_unit': new_fact,
                               'carbon_content': new_cc}
                    factors.loc[len(factors)] = new_row

                # If component already in database, it extracts carbon content
                elif found_comp.any():
                    curr_cc = factors.loc[found_comp,
                                          'carbon_content'].iloc[0]
                    # Creates new row in factors dataframe with info
                    new_row = {'component': curr_comp, 'loc': manu_ctry,
                               'year': year_prod,
                               'factor_kgCO2eq_unit': new_fact,
                               'carbon_content': curr_cc}
                    factors.loc[len(factors)] = new_row

            # Sets multi-index and sorts
            access_factors = factors.set_index(['component', 'loc', 'year'])
            access_factors = access_factors.sort_index()

        #### EMISSIONS CALCULATIONS ####
        # Adds all user-input information to pd.Series
        product = pd.Series(all_info, index=index_names)

        # Uses user-input data to calculate emissions
        # Manufacturing emissions
        manu_emissions,\
            total_manu_emissions = calc.manufacture_calc(product,
                                                         access_factors,
                                                         no_comp, dest_city)

        # Travel emissions
        travel_emissions,\
            total_travel_emissions = calc.travel_calc(product, no_comp,
                                                      additional_factors)

        # Read reprocessing factors
        if laundry_fact == 0.0:
            laundry_fact = calc.read_laundry_fact(additional_factors,
                                                  use_year)

        if decon_type is not None:
            decon_fact = calc.decon_emission_calc(decon_type, decon_units,
                                                  additional_factors,
                                                  use_year)
        else:
            decon_fact = 0.0
        # Reprocessing emissions
        reprocess_emissions = calc.reprocessing_calc(product, no_comp,
                                                     laundry_fact, decon_fact)

        # Reads disposal factors
        landfill_fact = calc.read_landfill_fact(additional_factors, use_year)
        #if disp_transport_fact == 0.0:
        disp_transport_fact = calc.read_disposal_fact(additional_factors,
                                                      year)
        # Disposal emissions
        (incinerate_emissions, recycle_emissions, 
         landfill_emissions, biogenic_carbon,
         net_waste_emissions) = calc.disposal_calc(product, access_factors,
                                                   no_comp, landfill_fact,
                                                   disp_transport_fact,
                                                   use_year)

        # Calculates total
        total_emissions = total_manu_emissions \
                          + total_travel_emissions \
                          + use_emissions \
                          + reprocess_emissions \
                          + net_waste_emissions

        #### CREATE OUTPUT ####
        # Additional travel to end location
        extra_travel = travel_end_loc(product, dest_city, no_comp,
                                      additional_factors, land_travel_dist,
                                      cloud, key=1)
        # Creates pd.Series containing emissions for product
        index_names = ['Total / kg CO2e', 'Manufacturing / kg CO2e', 
                       'Transport / kg CO2e', 'Use / kg CO2e',
                       'Reprocessing / kg CO2e', 'Disposal / kg CO2e']
        total_data = [(total_emissions + extra_travel),
                      total_manu_emissions,
                      (total_travel_emissions + extra_travel),
                      use_emissions, reprocess_emissions,
                      net_waste_emissions]
        if len(name) > 0:
            series_name = f'{name.capitalize()}'
        elif change_info:
            series_name = f'{chosen.capitalize()}'
        else:
            series_name = f'Product'
        col_dict = {series_name: st.column_config.NumberColumn(format='%.6f')}
        total_series = pd.Series(total_data, index=index_names,
                                 name=series_name)

        # Outputs dataframe
        st.dataframe(total_series, column_config=col_dict)

        comparison_emissions_graphic(total_series['Total / kg CO2e'])

        # Outputs pie chart
        if total_series.iloc[0] > 0.0:
            pie_chart_new = create_pie_chart(total_series, name=series_name)
            st.plotly_chart(pie_chart_new)
            
            # Download image as PNG
            st.download_button(label='Download pie chart as PNG',
                               data=pie_chart_new.to_image(format='png',
                                                           scale=3),
                               file_name='emissions.png',
                               mime='image/png', key=1)

        # Outputs comparison bar chart to original product if changes made
        if change_info:
            # Total data = new emissions, prod_em = original product
            comp_df = compare_changes(prod_em, total_data, chosen.title(),
                                      index_names)
            bar_chart = create_bar_chart(comp_df, comp=True,
                                         prod_name=chosen.title(), g=0.5)
            st.plotly_chart(bar_chart)
                
            # Download image as PNG
            st.download_button(label='Download bar chart as PNG',
                               data=bar_chart.to_image(format='png', scale=3),
                               file_name='emissions_comparison.png',
                               mime='image/png', key=2)

        #### DOWNLOAD DATA ####
        if st.checkbox('Download files'):
            (prod_info,
             emissions_info) = create_product_df(product,
                                                 total_manu_emissions,
                                                 total_travel_emissions,
                                                 use_emissions,
                                                 reprocess_emissions,
                                                 net_waste_emissions,
                                                 total_emissions)

            incl_travel = st.checkbox(f'''Include travel to end location
                                          in single product file''')
            to_database = False
            #if not cloud:
            #    to_database = st.checkbox(f'Save product to database')
            download_databases_new_product(prod_info, emissions_info,
                                           extra_travel, incl_travel,
                                           to_database=to_database)