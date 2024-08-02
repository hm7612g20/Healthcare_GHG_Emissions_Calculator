#### IMPORTS ####
import csv
import os
import shutil

from datetime import datetime

import pandas as pd
import numpy as np
import pkg_resources

import streamlit as st

from google.oauth2 import service_account
from gspread_pandas import Spread, Client


#### READ STORED DATA FUNCTIONS ####
def get_filepath(filename):
    '''Returns filepath in package given filename.'''
    filepath = pkg_resources.resource_filename(
        'emissions_calculator', filename)

    return filepath


def read_gsheets(name):
    '''Reads data in from Google Sheets.'''
    scope = ['https://spreadsheets.google.com/feeds',
             'https://www.googleapis.com/auth/drive']

    try:  # Tries to connect using streamlit secrets
        credentials = service_account.Credentials.from_service_account_info(
            st.secrets['gcp_service_account'], scopes=scope)
        client = Client(scope=scope, creds=credentials)
        spread = Spread(name, client=client)
        sh = client.open(name)
    except (FileNotFoundError, KeyError) as e:
        sh = None
        spread = None

    return sh, spread


#### READ INVENTORY FILES ####
@st.cache_data(show_spinner=False, ttl='1d')
def read_products():
    '''Reads inventory of products into a pd.DataFrame.'''
    sh, spread = read_gsheets('products')

    if sh is not None:
        worksheet = sh.worksheet('products')
        products = pd.DataFrame(worksheet.get_all_records())
    else:
        st.error('No products file found.')
        products = None

    return products


@st.cache_data(show_spinner=False, ttl='1d')
def read_products_local():
    '''Reads inventory of products into a pd.DataFrame.'''
    # Read in products data
    products_filepath = get_filepath(f'inventory/products.csv')

    # Checks that file exists in location
    if os.path.isfile(products_filepath):
        # Read in products data
        products = pd.read_csv(products_filepath)
    else:
        st.error('No products file found.')
        products = None

    return products


@st.cache_data(show_spinner=False, ttl='1d')
def read_emissions():
    '''Reads inventory of products and their emissions into a pd.DataFrame.'''
    sh, spread = read_gsheets('emissions')

    if sh is not None:
        worksheet = sh.worksheet('emissions')
        emissions = pd.DataFrame(worksheet.get_all_records())
    else:
        st.error('No emissions file found.')
        emissions = None

    return emissions


@st.cache_data(show_spinner=False, ttl='1d')
def read_open_source_emissions():
    '''Reads inventory of products and their emissions into a pd.DataFrame.'''
    sh, spread = read_gsheets('open_source_emissions')

    if sh is not None:
        worksheet = sh.worksheet('open_source_emissions')
        emissions = pd.DataFrame(worksheet.get_all_records())
    else:
        st.error('No emissions file found.')
        emissions = None

    return emissions


@st.cache_data(show_spinner=False, ttl='1d')
def read_emissions_local():
    '''Reads inventory of products and their emissions into a pd.DataFrame.'''
    # Emissions data filepath
    emissions_filepath = get_filepath(f'inventory/emissions.csv')

    # Checks that file exists in location
    if os.path.isfile(emissions_filepath):
        # Read in products data
        emissions = pd.read_csv(emissions_filepath)
    else:
        st.error('No emissions file found.')
        emissions = None

    return emissions


#### READ FACTORS ####
@st.cache_data(show_spinner=False, ttl='1d')
def read_factors():
    '''Reads factors file into a pd.DataFrame.'''
    sh, spread = read_gsheets('open_source_factors')

    if sh is not None:
        worksheet = sh.worksheet('open_source_factors')
        factors = pd.DataFrame(worksheet.get_all_records())
    else:
        st.error('No factors file found.')
        factors = None

    return factors


@st.cache_data(show_spinner=False, ttl='1d')
def read_factors_local():
    '''Reads factors file into a pd.DataFrame.'''
    # Factors data filepath
    factors_filepath = get_filepath(f'factors/factors.csv')

    # Checks that file exists in location
    if os.path.isfile(factors_filepath):
        # Read in factors data
        factors = pd.read_csv(factors_filepath)
    else:
        st.error('No factors file found.')
        factors = None

    return factors


@st.cache_data(show_spinner=False, ttl='1d')
def read_factors_inv():
    '''Reads factors file into a pd.DataFrame for use in inventory calc.'''
    sh, spread = read_gsheets('open_source_factors')

    if sh is not None:
        worksheet = sh.worksheet('open_source_factors')
        factors = pd.DataFrame(worksheet.get_all_records())
        # Sets multi-index and sorts
        factors = factors.set_index(['component', 'loc', 'year'])
        factors = factors.sort_index()
    else:
        st.error('No factors file found.')
        factors = None

    return factors


def read_factors_inv_local():
    '''Reads factors file into a pd.DataFrame for use in inventory calc.'''
    # Factors data filepath
    factors_filepath = get_filepath(f'factors/factors.csv')

    # Checks that file exists in location
    if os.path.isfile(factors_filepath):
        # Read in factors data
        factors = pd.read_csv(factors_filepath)
        # Sets multi-index and sorts
        factors = factors.set_index(['component', 'loc', 'year'])
        factors = factors.sort_index()
    else:
        st.error('No factors file found.')
        factors = None

    return factors


#### READ ADDITIONAL FACTORS ####
@st.cache_data(show_spinner=False, ttl='1d')
def read_additional_factors():
    '''
    Reads factors file for laundry, disposal, transport, electricity, water
    and gas into a pd.DataFrame.

    Parameters:
    -----------
    None.

    Returns:
    --------
    additional_factors: pd.DataFrame
        Contains name and year corresponding to carbon factor in kg CO2e.
    '''
    sh, spread = read_gsheets('additional_factors')

    if sh is not None:
        worksheet = sh.worksheet('additional_factors')
        factors = pd.DataFrame(worksheet.get_all_records())
    else:
        st.error('No additonal factors file found.')
        factors = None

    return factors


@st.cache_data(show_spinner=False, ttl='1d')
def read_additional_factors_local():
    '''
    Reads factors file for laundry, disposal, transport, electricity, water
    and gas into a pd.DataFrame.

    Parameters:
    -----------
    None.

    Returns:
    --------
    additional_factors: pd.DataFrame
        Contains name and year corresponding to carbon factor in kg CO2e.
    '''
    # Additonal factors data filepath
    factors_filepath = get_filepath(f'factors/additional_factors.csv')

    # Checks that file exists in location
    if os.path.isfile(factors_filepath):
        # Read in additional factors data
        factors = pd.read_csv(factors_filepath)
    else:
        st.error('No additonal factors file found.')
        factors = None

    return factors


@st.cache_data(show_spinner=False, ttl='1d')
def read_additional_factors_inv():
    '''
    Reads factors file for laundry, disposal, transport, electricity, water
    and gas into a pd.DataFrame for use in inventory calc.

    Parameters:
    -----------
    None.

    Returns:
    --------
    additional_factors: pd.DataFrame
        Contains name and year corresponding to carbon factor in kg CO2e.
    '''
    sh, spread = read_gsheets('additional_factors')

    if sh is not None:
        worksheet = sh.worksheet('additional_factors')
        factors = pd.DataFrame(worksheet.get_all_records())
        # Sets index and sorts additional factors
        factors.set_index(['name', 'unit', 'year'], inplace=True)
        factors = factors.sort_index()
    else:
        st.error('No additonal factors file found.')
        factors = None

    return factors


@st.cache_data(show_spinner=False, ttl='1d')
def read_additional_factors_inv_local():
    '''
    Reads factors file for laundry, disposal, transport, electricity, water
    and gas into a pd.DataFrame for use in inventory calc.

    Parameters:
    -----------
    None.

    Returns:
    --------
    additional_factors: pd.DataFrame
        Contains name and year corresponding to carbon factor in kg CO2e.
    '''
    # Additonal factors data filepath
    factors_filepath = get_filepath(f'factors/additional_factors.csv')

    # Checks that file exists in location
    if os.path.isfile(factors_filepath):
        # Read in additional factors data
        factors = pd.read_csv(factors_filepath)
        # Sets index and sorts additional factors
        factors.set_index(['name', 'unit', 'year'], inplace=True)
        factors = factors.sort_index()
    else:
        st.error('No additonal factors file found.')
        factors = None

    return factors


#### READ TRAVEL DISTANCES ####
@st.cache_data(show_spinner=False, ttl='1d')
def read_travel_dist():
    '''Reads list of land and sea travel distances into a DataFrame.'''
    sh, spread = read_gsheets('land_travel_distance')
    if sh is not None:
        worksheet = sh.worksheet('land_travel_distance')
        land_travel_dist = pd.DataFrame(worksheet.get_all_records())

        # Make all names lower case
        land_travel_dist['start_loc'] = land_travel_dist['start_loc'].str\
            .lower()
        land_travel_dist['end_loc'] = land_travel_dist['end_loc'].str\
            .lower()
        # Sets index as start and end location
        land_travel_dist = land_travel_dist.set_index(['start_loc',
                                                       'end_loc'])
        land_travel_dist = land_travel_dist.sort_index()
    else:
        st.error('No land travel distance file found.')
        land_travel_dist = None

    sh, spread = read_gsheets('sea_travel_distance')
    if sh is not None:
        worksheet = sh.worksheet('sea_travel_distance')
        sea_travel_dist = pd.DataFrame(worksheet.get_all_records())

        # Makes all names lower case
        sea_travel_dist['start_loc'] = sea_travel_dist['start_loc'].str\
            .lower()
        sea_travel_dist['end_loc'] = sea_travel_dist['end_loc'].str.lower()
        # Sets index as start and end location
        sea_travel_dist = sea_travel_dist.set_index(['start_loc',
                                                     'end_loc'])
        sea_travel_dist = sea_travel_dist.sort_index()
    else:
        st.error('No sea travel distance file found.')
        sea_travel_dist = None

    return land_travel_dist, sea_travel_dist


@st.cache_data(show_spinner=False, ttl='1d')
def read_travel_dist_local():
    '''Reads list of land and sea travel distances into a DataFrame.'''
    # Land travel distances filepath
    land_filepath = get_filepath(f'data/land_travel_distance.csv')

    # Checks that file exists in location
    if os.path.isfile(land_filepath):
        # Reads in land travel distances
        land_travel_dist = pd.read_csv(land_filepath)

        # Make all names lower case
        land_travel_dist['start_loc'] = land_travel_dist['start_loc'].str\
            .lower()
        land_travel_dist['end_loc'] = land_travel_dist['end_loc'].str\
            .lower()
        # Sets index as start and end location
        land_travel_dist = land_travel_dist.set_index(['start_loc',
                                                       'end_loc'])
        land_travel_dist = land_travel_dist.sort_index()
    else:
        st.error('No land travel distance file found.')
        land_travel_dist = None

    # Sea travel distances filepath
    sea_filepath = get_filepath(f'data/sea_travel_distance.csv')

    # Checks that file exists in location
    if os.path.isfile(sea_filepath):
        # Reads in sea travel distances
        sea_travel_dist = pd.read_csv(sea_filepath)

        # Makes all names lower case
        sea_travel_dist['start_loc'] = sea_travel_dist['start_loc'].str\
            .lower()
        sea_travel_dist['end_loc'] = sea_travel_dist['end_loc'].str.lower()
        # Sets index as start and end location
        sea_travel_dist = sea_travel_dist.set_index(['start_loc',
                                                     'end_loc'])
        sea_travel_dist = sea_travel_dist.sort_index()
    else:
        st.error('No sea travel distance file found.')
        sea_travel_dist = None

    return land_travel_dist, sea_travel_dist


#### READ USEFUL INFO ####
def read_processes():
    '''Reads list of processes in factors file.'''
    # Processes filepath
    filepath = get_filepath(f'data/processes.csv')

    # Checks that file exists in location
    if os.path.isfile(filepath):
        # Read in processes data
        processes = pd.read_csv(filepath)
        # Creates list of processes
        processes = processes['process'].to_list()
    else:
        st.error('No processes file found.')
        processes = None

    return processes


@st.cache_data(show_spinner=False, ttl='1d')
def read_decon_units_cloud():
    '''Reads information on decontamination units into a dictionary.'''
    sh, spread = read_gsheets('decon_units')
    if sh is not None:
        worksheet = sh.worksheet('decon_units')
        decon_df = pd.DataFrame(worksheet.get_all_records())

        decon_units = {}
        for ind, row in decon_df.iterrows():
            name = str(row['name'])
            unit = row['value']
            val = float(row['value'])
            # Dictionary containing value
            decon_units[name] = val
    else:
        st.error('No decontamination units file found.')
        decon_units = None

    return decon_units


def read_decon_units():
    '''Reads information on decontamination units into a dictionary.'''
    filepath = get_filepath(f'data/decon_units.csv')

    if os.path.isfile(filepath):
        with open(filepath, 'r') as f:
            decon_units = {}
            for ind, line in enumerate(f):
                # Header is at index 0 so ignore
                if ind > 0:
                    ln = line.rstrip('\n')
                    wd = ln.split(',')
                    wd[2] = float(wd[2])
                    # Dictionary containing value
                    decon_units[wd[0]] = wd[2]
    else:
        st.error('No decontamination units file found.')
        decon_units = None

    return decon_units


#### READ COUNTRIES, CITIES AND PORTS DATA ####
@st.cache_data(show_spinner=False)
def read_countries():
    '''Reads country names into a list.'''
    # Country filepath
    country_filepath = get_filepath(f'data/countries_all.csv')

    # Checks that file exists in location
    if os.path.isfile(country_filepath):
        # Read in country data
        country = pd.read_csv(country_filepath)
        # Creates list of countries
        country = country['country'].to_list()
        country = [c.capitalize() for c in country]
    else:
        st.error('No country file found.')
        country = None

    return country


@st.cache_data(show_spinner=False)
def read_countries_continents():
    '''Reads countries in Europe and Rest of World into a list.'''
    # Creates list of all countries in Europe so correct factor used
    euro_filepath = get_filepath(f'data/countries_europe.csv')
    if os.path.isfile(euro_filepath):
        rer_df = pd.read_csv(euro_filepath)
        rer = rer_df['country'].str.lower().to_list()
    else:
        st.error('No country file found.')
        rer = None

    country_filepath = get_filepath(f'data/countries_other.csv')
    if os.path.isfile(country_filepath):
        row_df = pd.read_csv(country_filepath)
        row = row_df['country'].str.lower().to_list()
    else:
        st.error('No country file found.')
        row = None

    return rer, row


@st.cache_data(show_spinner=False)
def read_cities():
    '''Reads world cities and UK cities into a list.'''
    filepath = get_filepath(f'data/world_cities.csv')

    if os.path.isfile(filepath):
        cities_df = pd.read_csv(filepath)
        cities_list = []
        uk_cities_list = []
        for ind, row in cities_df.iterrows():
            city = row['name']
            ctry = row['country']
            # Saves city as city (country)
            city_name = f'{city} ({ctry})'
            if city_name not in cities_list:
                cities_list.append(city_name)
            # Creates separate list for UK with not country
            if ctry == 'United Kingdom':
                if city not in uk_cities_list:
                    uk_cities_list.append(city)
        uk_cities_list = sorted(uk_cities_list)
    else:
        st.error('No cities file found.')
        cities_list = None
        uk_cities_list = None

    return cities_list, uk_cities_list


@st.cache_data(show_spinner=False)
def read_ports():
    '''Reads names of main ports into a list.'''
    filepath = get_filepath(f'data/ports.csv')

    if os.path.isfile(filepath):
        ports_df = pd.read_csv(filepath)
        uk_ports_list = []
        ports_list = []
        for ind, row in ports_df.iterrows():
            name = row['name']
            ctry = row['country']
            if ctry == 'united kingdom':
                uk_ports_list.append(name)
            else:
                if ctry is not np.nan:
                    ports_list.append(f'{name} ({ctry})')
                else:
                    ports_list.append(name)
    else:
        st.error('No ports file found.')
        ports_list = None
        uk_ports_list = None

    return ports_list, uk_ports_list

#### CHECK FILES UPLOADED BY USER ####
def check_uploaded_product_file(file):
    '''Checks that the uploaded products file is in a suitable format.'''
    error = False

    try:  # Reads in uploaded file
        df = pd.read_csv(file)
    except pd.errors.ParserError:  # Stops if wrong type of file used
        st.error('Error: Cannot read file.')
        error = True
        df = None

    header = df.columns.to_list()
    head_a = ['product', 'category', 'electricity', 'water', 'gas']

    try:
        no_comp = int(list(df.columns)[-1].split('_')[-1])
    except ValueError:  # Stops if wrong type of file used
        st.error(f'''Error: Header formatted incorrectly for numbered
                     components.''')
        error = True

    if header[0:5] != head_a:
        st.error(f'''Error: Header should contain product, category,
                     electricity, water and gas.''')
        error = True

    for i in range(no_comp):
        head_b = ['component_' + str(i+1), 'manu_year_' + str(i+1),
                  'mass_kg_' + str(i+1), 'no_uses_' + str(i+1),
                  'biogenic_' + str(i+1), 'manu_loc_' + str(i+1),
                  'debark_port_' + str(i+1), 'depart_loc_uk_' + str(i+1),
                  'reprocessing_' + str(i+1), 'recycle_' + str(i+1),
                  'incinerate_' + str(i+1), 'landfill_' + str(i+1)]
        to_check = header[(5+(12*i)):(5+(12*i)+12)]
        if to_check != head_b:
            st.error(f'''Error: Header does not contain required information
                         for each component.''')
            error = True

    if not error:
        # Removes any extra rows with no listed product to prevent errors
        df.dropna(subset=['product'], inplace=True)

    check_for = ['0', '0.0', '1', '1.0', 0, 0.0, 1, 1.0]
    if not error:
        for ind, row in df.iterrows():
            for i in range(no_comp):
                # Prevents empty component columns
                if str(row['manu_year_' + str(i+1)]) == 'nan':
                    no_comp = no_comp - 1
                    df = df[df.columns[:((no_comp*12)+5)]]
                    break
                try:
                    int(row['manu_year_' + str(i+1)])
                except ValueError:
                    st.error(f'''Error: Incorrect format for manu_year_{i+1}
                                 on line {ind+1}.''')
                    error = True

                try:
                    float(row['mass_kg_' + str(i+1)])
                except ValueError:
                    st.error(f'''Error: Incorrect format for mass_kg_{i+1}
                                 on line {ind+1}.''')
                    error = True

                try:
                    int(row['no_uses_' + str(i+1)])
                except ValueError:
                    st.error(f'''Error: Incorrect format for no_uses_{i+1} on
                                 line {ind+1}.''')
                    error = True

                if row['biogenic_' + str(i+1)] not in check_for:
                    st.error(f'''Error: Incorrect format for biogenic_{i+1} on
                                 line {ind+1}.''')
                    error = True

                if row['manu_loc_' + str(i+1)] not in check_for:
                    if '(' not in str(row['manu_loc_' + str(i+1)]) or ')' \
                        not in str(row['manu_loc_' + str(i+1)]):
                        st.error(f'''Error: Incorrect format for
                                     manu_loc_{i+1} on line {ind+1}.''')
                        error = True

                if row['debark_port_' + str(i+1)] not in check_for:
                    if '(' not in str(row['debark_port_' + str(i+1)]) or ')' \
                        not in str(row['debark_port_' + str(i+1)]):
                        st.error(f'''Error: Incorrect format for
                                     debark_port_{i+1} on line {ind+1}.''')
                        error = True

                if row['recycle_' + str(i+1)] not in check_for:
                    st.error(f'''Error: Incorrect format for recycle_{i+1}
                                 on line {ind+1}.''')
                    error = True

                if row['incinerate_' + str(i+1)] not in check_for:
                    st.error(f'''Error: Incorrect format for incinerate_{i+1}
                                 on line {ind+1}.''')
                    error = True

                if row['landfill_' + str(i+1)] not in check_for:
                    st.error(f'''Error: Incorrect format for landfill_{i+1} on
                                 line {ind+1}.''')
                    error = True

    return df, no_comp, error


def check_uploaded_emissions_file(file):
    '''Checks that the uploaded emissions file is in a suitable format.'''
    error = False

    try:  # Reads in uploaded file
        df = pd.read_csv(file)
    except pd.errors.ParserError:  # Stops if wrong type of file used
        st.error('Error: Cannot read file.')
        error = True
        df = None

    header = df.columns.to_list()

    try:
        no_comp = int(list(df.columns)[-7].split('_')[-1])
    except ValueError:  # Stops if wrong type of file used
        st.error(f'''Error: Header formatted incorrectly for numbered
                     components.''')
        error = True

    head_a = ['product', 'category', 'electricity', 'water', 'gas']
    if header[0:5] != head_a:
        st.error(f'''Error: Header should contain product, category,
                     electricity, water and gas.''')
        error = True

    for i in range(no_comp):
        head_b = ['component_' + str(i+1), 'manu_year_' + str(i+1),
                  'mass_kg_' + str(i+1), 'no_uses_' + str(i+1),
                  'biogenic_' + str(i+1), 'manu_loc_' + str(i+1),
                  'debark_port_' + str(i+1), 'depart_loc_uk_' + str(i+1),
                  'reprocessing_' + str(i+1), 'recycle_' + str(i+1),
                  'incinerate_' + str(i+1), 'landfill_' + str(i+1)]
        to_check = header[(5+(12*i)):(5+(12*i)+12)]
        if to_check != head_b:
            st.error(f'''Error: Header does not contain required information
                         for each component.''')
            error = True

    head_c = ['manufacture_emissions', 'transport_emissions', 'use_emissions',
              'reprocessing_emissions', 'disposal_emissions',
              'total_emissions']
    if header[-6:] != head_c:
        st.error(f'''Error: Header should contain manufacture_emissions,
                 transport_emissions, use_emissions, reprocessing_emissions,
                 disposal_emissions and total_emissions.''')
        error = True

    if not error:
        # Removes any extra rows with no listed product to prevent errors
        df.dropna(subset=['product'], inplace=True)

    check_for = ['0', '0.0', '1', '1.0', 0, 0.0, 1, 1.0]
    if not error:
        for ind, row in df.iterrows():
            try:
                float(row['manufacture_emissions'])
            except ValueError:
                st.error(f'''Error: Incorrect format for manufacture_emissions
                             on line {ind+1}.''')
                error = True

            try:
                float(row['transport_emissions'])
            except ValueError:
                st.error(f'''Error: Incorrect format for transport_emissions
                             on line {ind+1}.''')
                error = True

            try:
                float(row['use_emissions'])
            except ValueError:
                st.error(f'''Error: Incorrect format for use_emissions
                             on line {ind+1}.''')
                error = True

            try:
                float(row['reprocessing_emissions'])
            except ValueError:
                st.error(f'''Error: Incorrect format for
                             reprocessing_emissions on line {ind+1}.''')
                error = True

            try:
                float(row['disposal_emissions'])
            except ValueError:
                st.error(f'''Error: Incorrect format for disposal_emissions
                             on line {ind+1}.''')
                error = True

            try:
                float(row['total_emissions'])
            except ValueError:
                st.error(f'''Error: Incorrect format for total_emissions
                             on line {ind+1}.''')
                error = True

            for i in range(no_comp):
                try:
                    int(row['manu_year_' + str(i+1)])
                except ValueError:
                    st.error(f'''Error: Incorrect format for manu_year_{i+1}
                                 on line {ind+1}.''')
                    error = True

                try:
                    float(row['mass_kg_' + str(i+1)])
                except ValueError:
                    st.error(f'''Error: Incorrect format for mass_kg_{i+1}
                                 on line {ind+1}.''')
                    error = True

                try:
                    int(row['no_uses_' + str(i+1)])
                except ValueError:
                    st.error(f'''Error: Incorrect format for no_uses_{i+1} on
                                 line {ind+1}.''')
                    error = True

                if row['biogenic_' + str(i+1)] not in check_for:
                    st.error(f'''Error: Incorrect format for biogenic_{i+1} on
                                 line {ind+1}.''')
                    error = True

                if row['manu_loc_' + str(i+1)] not in check_for:
                    if '(' not in str(row['manu_loc_' + str(i+1)]) or ')' \
                        not in str(row['manu_loc_' + str(i+1)]):
                        st.error(f'''Error: Incorrect format for
                                     manu_loc_{i+1} on line {ind+1}.''')
                        error = True

                if row['debark_port_' + str(i+1)] not in check_for:
                    if '(' not in str(row['debark_port_' + str(i+1)]) or ')' \
                        not in str(row['debark_port_' + str(i+1)]):
                        st.error(f'''Error: Incorrect format for
                                     debark_port_{i+1} on line {ind+1}.''')
                        error = True

                if row['recycle_' + str(i+1)] not in check_for:
                    st.error(f'''Error: Incorrect format for recycle_{i+1}
                                 on line {ind+1}.''')
                    error = True

                if row['incinerate_' + str(i+1)] not in check_for:
                    st.error(f'''Error: Incorrect format for incinerate_{i+1}
                                 on line {ind+1}.''')
                    error = True

                if row['landfill_' + str(i+1)] not in check_for:
                    st.error(f'''Error: Incorrect format for landfill_{i+1} on
                                 line {ind+1}.''')
                    error = True

    return df, error


def check_uploaded_factors_file(file, change_ind):
    '''Checks that the uploaded factors file is in a suitable format.'''
    error = False

    try:  # Reads in uploaded file
        df = pd.read_csv(file)
    except pd.errors.ParserError:  # Stops if wrong type of file used
        st.error('Error: Cannot read file.')
        error = True
        df = None

    header = df.columns.to_list()
    head_a = ['component', 'loc', 'year', 'unit', 'factor_kgCO2eq_unit',
              'carbon_content', 'source']

    if header != head_a:
        st.error(f'''Error: Header should contain component, loc, year, unit,
                     factor_kgCO2eq_unit, carbon_content and source.''')
        error = True

    if not error:
        # Removes any extra rows with no listed component to prevent errors
        df.dropna(subset=['component'], inplace=True)

    if not error:
        for ind, row in df.iterrows():
            try:
                int(row['year'])
            except ValueError:
                st.error(f'Error: Incorrect format for year on line {ind+1}.')
                error = True

            try:
                float(row['factor_kgCO2eq_unit'])
            except ValueError:
                st.error(f'''Error: Incorrect format for factor_kgCO2eq_unit
                             on line {ind+1}.''')
                error = True

            try:
                cc = float(row['carbon_content'])
                if cc < 0.0 or cc > 1.0:
                    st.error(f'''Error: Carbon content not between 0 and 1 on
                                 line {ind+1}.''')
                    error = True
            except ValueError:
                st.error(f'''Error: Incorrect format for carbon_content
                             on line {ind+1}.''')
                error = True

    if not error and change_ind:
        df = df.set_index(['component', 'loc', 'year'])
        df = df.sort_index()

    return df, error


def check_uploaded_distance_file(file, travel_dist):
    '''Checks that the uploaded distance file is in a suitable format.'''
    error = False

    try:  # Reads in uploaded file
        df = pd.read_csv(file)
    except pd.errors.ParserError:  # Stops if wrong type of file used
        st.error('Error: Cannot read file.')
        error = True
        df = None

    header = df.columns.to_list()
    head_a = ['start_loc', 'end_loc', 'distance_km']

    if header != head_a:
        st.error(f'''Error: Header should contain start_loc, end_loc and
                     distance_km.''')
        error = True

    if not error:
        # Removes any extra rows with no listed start loc to prevent errors
        df.dropna(subset=['start_loc'], inplace=True)

    if not error:
        for ind, row in df.iterrows():
            if '(' not in row['start_loc'] or ')' not in row['start_loc']:
                st.error(f'''Error: Incorrect format for start loc on line
                             {ind+1}.''')
                error = True

            if '(' not in row['end_loc'] or ')' not in row['end_loc']:
                st.error(f'''Error: Incorrect format for end loc on line
                             {ind+1}.''')
                error = True

            try:
                float(row['distance_km'])
            except ValueError:
                st.error(f'''Error: Incorrect format for distance_km
                             on line {ind+1}.''')
                error = True

    if not error:
        # Sets file up in the same format
        df = df.set_index(['start_loc', 'end_loc'])
        own_df = df.sort_index()
        travel_dist = pd.concat([travel_dist, df])
        travel_dist = travel_dist.sort_index()

    return travel_dist, own_df, error
