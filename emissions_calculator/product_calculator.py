#### IMPORTS ####
import csv
import os
import shutil

from datetime import datetime

import pandas as pd
import numpy as np
import math

import pkg_resources
from importlib import resources as impresources

import searoute as sr
from geopy.geocoders import Nominatim

import streamlit as st

from google.oauth2 import service_account
from gspread_pandas import Spread, Client


#### READ STORED DATA ####
def get_filepath(filename):
    '''Returns filepath in package given filename.'''
    filepath = pkg_resources.resource_filename('emissions_calculator',
                                               filename)
    
    return filepath

def read_gsheets(name):
    '''Reads data in from Google Sheets.'''
    scope = ['https://spreadsheets.google.com/feeds',
             'https://www.googleapis.com/auth/drive']

    try:
        credentials = service_account.Credentials.from_service_account_info(
            st.secrets['gcp_service_account'], scopes = scope)
        client = Client(scope=scope, creds=credentials)
        spread = Spread(name, client = client)
        sh = client.open(name)
    except (FileNotFoundError, KeyError, Error, MalformedError) as e:
        sh = None
        spread = None

    return sh, spread

@st.cache_data(show_spinner=False)
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

@st.cache_data(show_spinner=False)
def read_factors():
    '''
    Reads factors file into a pd.DataFrame.

    Parameters:
    -----------
    None.

    Returns:
    --------
    factors: pd.DataFrame
        Contains component name, year and location corresponding to carbon
        factor in kg CO2e and carbon content.
    '''
    sh, spread = read_gsheets('factors')

    if sh is not None:
        worksheet = sh.worksheet('factors.csv')
        factors = pd.DataFrame(worksheet.get_all_records())
    else:
        st.error('No factors file found.')
        factors = None

    return factors

def read_factors_local():
    '''
    Reads factors file into a pd.DataFrame.

    Parameters:
    -----------
    None.

    Returns:
    --------
    factors: pd.DataFrame
        Contains component name, year and location corresponding to carbon
        factor in kg CO2e and carbon content.
    '''
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

@st.cache_data(show_spinner=False)
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

def read_decon_units():
    '''Reads information on decontamination units into a dictionary.'''
    filepath = get_filepath(f'data/decon_units.csv')

    if os.path.isfile(filepath):
        with open(filepath, 'r') as f:
            decon_units = {}
            for ind, line in enumerate(f):
                # Header is at index 0 so ignore
                if ind > 0:
                    l = line.rstrip('\n')
                    d = l.split(',')
                    d[2] = float(d[2])
                    # Dictionary containing value
                    decon_units[d[0]] = d[2]
    else:
        st.error('No decontamination units file found.')
        decon_units = None

    return decon_units

@st.cache_data(show_spinner=False)
def read_travel_dist():
    '''Reads list of land and sea travel distances into a DataFrame.'''
    sh, spread = read_gsheets('land_travel_distance')
    if sh is not None:
        worksheet = sh.worksheet('land_travel_distance')
        land_travel_dist = pd.DataFrame(worksheet.get_all_records())
    else:
        st.error('No land travel distance file found.')
        land_travel_dist = None

    sh, spread = read_gsheets('sea_travel_distance')
    if sh is not None:
        worksheet = sh.worksheet('sea_travel_distance')
        sea_travel_dist = pd.DataFrame(worksheet.get_all_records())
    else:
        st.error('No sea travel distance file found.')
        sea_travel_dist = None

    return land_travel_dist, sea_travel_dist

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


#### UPDATE FILE WITH NEW DEFRA FACTORS ####
@st.cache_data
def read_defra_travel_factors(filename, year):
    '''
    Extracts travel emissions factors from Defra excel file to use in
    calculation.

    Parameters:
    -----------
    filename: str
        Filepath of Defra excel file.
    year: str
        Year to use for factor.

    Returns:
    --------
    land, wtt_land: float
        Emissions factors of HGV land travel.
    sea, wtt_sea: float
        Emissions factors of container ship sea travel.
    '''
    travel_sheetname = 'Freighting goods'
    travel_factors = pd.read_excel(filename,
                                   sheet_name=travel_sheetname,
                                   skiprows=range(0, 24))

    wtt_travel_sheetname = 'WTT- delivery vehs & freight'
    wtt_travel_factors = pd.read_excel(filename,
                                       sheet_name=wtt_travel_sheetname,
                                       skiprows=range(0, 18))

    # Fills N/A values with the values in cells above
    travel_factors[['Activity', 'Type']] \
        = travel_factors[['Activity', 'Type']].ffill()

    wtt_travel_factors[['Activity', 'Type']] \
        = wtt_travel_factors[['Activity', 'Type']].ffill()

    # Reflects change in reporting name
    if int(year) > 2022:
        fact_name = 'kg CO2e'
    else:
        fact_name = 'Total kg CO2e per unit'
    land_name = fact_name + '.3'
    sea_name = fact_name + '.1'

    # Locates the correct land travel factor
    land = pd.to_numeric(travel_factors.\
                         loc[(travel_factors['Activity'] == \
                              'HGV (all diesel)') &
                             (travel_factors['Type'] == \
                              'Rigid (>7.5 tonnes-17 tonnes)') &
                             (travel_factors['Unit'] == 'tonne.km'),
                             land_name])
    land = land.iloc[0]

    # Locates the correct sea travel factor
    sea = pd.to_numeric(travel_factors.\
                        loc[(travel_factors['Activity'] == 'Cargo ship') &
                            (travel_factors['Type'] == 'Container ship') &
                            (travel_factors['Unit'] == 'Average'), sea_name])
    sea = sea.iloc[0]

    # Locates the correct well-to-tank land travel factor
    wtt_land = pd.to_numeric(wtt_travel_factors.\
                            loc[(wtt_travel_factors['Activity'] == \
                                 'WTT- HGV (all diesel)') &
                                (wtt_travel_factors['Type'] == \
                                 'Rigid (>7.5 tonnes-17 tonnes)') &
                                (wtt_travel_factors['Unit'] == 'tonne.km'),
                                land_name])
    wtt_land = wtt_land.iloc[0]

    # Locates the correct well-to-tank sea travel factor
    wtt_sea = pd.to_numeric(wtt_travel_factors.\
                            loc[(wtt_travel_factors['Activity'] == \
                                 'WTT- cargo ship') &
                                (wtt_travel_factors['Type'] == \
                                 'Container ship') &
                                (wtt_travel_factors['Unit'] == 'Average'),
                                sea_name])
    wtt_sea = wtt_sea.iloc[0]

    return land, wtt_land, sea, wtt_sea

@st.cache_data
def read_defra_water_gas_elec_factors(filename, year):
    '''
    Extracts water, gas and electricity emissions factors from
    Defra excel file to use in calculations.

    Parameters:
    -----------
    filename: str
        Filepath of Defra excel file.
    year: str
        Year to use for factor.

    Returns:
    --------
    (water_treat, water_supply, elec_gen, elec_td wtt_elec_gen,
     wtt_elec_td, gas, wtt_gas): float
         Emissions factors for electricity, water and gas.
    '''
    # Reflects change in reporting name
    if int(year) > 2022:
        fact_name = 'kg CO2e'
    else:
        fact_name = 'Total kg CO2e per unit'

    water_supply_sheetname = 'Water supply'
    water_supply_factors = pd.read_excel(filename,
                                         sheet_name=water_supply_sheetname,
                                         skiprows=range(0, 16))
    
    water_treat_sheetname = 'Water treatment'
    water_treat_factors = pd.read_excel(filename,
                                        sheet_name=water_treat_sheetname,
                                        skiprows=range(0, 15))

    water_supply = pd.to_numeric(water_supply_factors.\
                                 loc[(water_supply_factors['Unit'] == \
                                      'cubic metres'), fact_name])
    water_supply = water_supply.iloc[0]

    water_treat = pd.to_numeric(water_treat_factors.\
                                loc[(water_treat_factors['Unit'] == \
                                     'cubic metres'), fact_name])
    water_treat = water_treat.iloc[0]

    elec_sheetname = 'UK electricity'
    elec_factors = pd.read_excel(filename, sheet_name=elec_sheetname,
                                 skiprows=range(0, 22))

    elec_td_sheetname = 'Transmission and distribution'
    elec_td_factors = pd.read_excel(filename, sheet_name=elec_td_sheetname,
                                    skiprows=range(0, 19))
    
    wtt_elec_sheetname = 'WTT- UK electricity'
    wtt_elec_factors_defra = pd.read_excel(filename,
                                           sheet_name=wtt_elec_sheetname,
                                           skiprows=range(0, 17))

    elec_gen = pd.to_numeric(elec_factors.loc[(elec_factors['Activity'] == \
                                  'Electricity generated') &
                                  (elec_factors['Unit'] == 'kWh'), fact_name])
    elec_gen = elec_gen.iloc[0]

    elec_td = pd.to_numeric(elec_td_factors.\
                            loc[(elec_td_factors['Activity'] == \
                                 'T&D- UK electricity') &
                                (elec_td_factors['Unit'] == 'kWh'), fact_name])
    elec_td = elec_td.iloc[0]

    wtt_elec_gen = pd.to_numeric(wtt_elec_factors.\
                                 loc[(wtt_elec_factors['Activity'] == \
                                      'WTT- UK electricity (generation)') &
                                     (wtt_elec_factors['Unit'] == 'kWh'),
                                     fact_name])
    wtt_elec_gen = wtt_elec_gen.iloc[0]

    wtt_elec_td = pd.to_numeric(wtt_elec_factors.\
                                loc[(wtt_elec_factors['Activity'] == \
                                     'WTT- UK electricity (T&D)') &
                                    (wtt_elec_factors_defra['Unit'] == 'kWh'),
                                    fact_name])
    wtt_elec_td = wtt_elec_td.iloc[0]

    fuel_sheetname = 'Fuels'
    fuel_factors = pd.read_excel(filename, sheet_name=fuel_sheetname,
                                 skiprows=range(0, 21))
    
    wtt_fuel_sheetname = 'WTT- fuels'
    wtt_fuel_factors = pd.read_excel(filename,
                                     sheet_name=wtt_fuel_sheetname,
                                     skiprows=range(0, 20))

    fuel_factors[['Activity', 'Fuel']] \
        = fuel_factors[['Activity', 'Fuel']].ffill()
    
    wtt_fuel_factors[['Activity', 'Fuel']] \
        = wtt_fuel[['Activity', 'Fuel']].ffill()

    gas = pd.to_numeric(fuel_factors.\
                        loc[(fuel_factors['Activity'] == 'Gaseous fuels') &
                            (fuel_factors['Fuel'] == 'Natural gas') &
                            (fuel_factors['Unit'] == 'cubic metres'),
                            fact_name])
    gas = gas.iloc[0]

    wtt_gas = pd.to_numeric(wtt_fuel_factors.\
                            loc[(wtt_fuel_factors['Activity'] == \
                                 'Gaseous fuels') &
                                (wtt_fuel_factors['Fuel'] == 'Natural gas') &
                                (wtt_fuel_factors['Unit'] == 'cubic metres'),
                                fact_name])
    wtt_gas = wtt_gas.iloc[0]

    return (water_treat, water_supply, elec_gen, elec_td, wtt_elec_gen,
            wtt_elec_td, gas, wtt_gas)

@st.cache_data
def read_defra_disposal_factors(filename, year):
    '''
    Reads landfill carbon factor from Defra excel file.

    Parameters:
    -----------
    filename: str
        Name of Defra excel file.
    year: str
        Year to use for factor.

    Returns:
    --------
    landfill_fact: float
        Carbon factor per kg of landfill waste.
    '''
    waste_sheetname = 'Waste disposal'
    waste_factors = pd.read_excel(filename, sheet_name=waste_sheetname,
                                  skiprows=range(0, 23))

    waste_factors[['Activity']] = waste_factors[['Activity']].ffill()

    # Reflects change in reporting name
    if int(year) > 2022:
        fact_name = 'kg CO2e.5'
    else:
        fact_name = 'Total kg CO2e per unit'

    landfill_fact = pd.to_numeric(waste_factors.\
                                  loc[(waste_factors['Activity'] == \
                                       'Refuse') & \
                                      (waste_factors['Waste type'] == \
                                       'Commercial and industrial waste'),
                                      fact_name])
    landfill_fact = landfill_fact.iloc[0] / 1000

    return landfill_fact

def new_defra(file, year, to_database=False):
    '''
    Extracts info using new Defra file. If file cannot be
    read, user can input values manually.
    
    Parameters:
    -----------
    file: Excel file
        New Defra file to extract factors from.
    year: str
        Year of new Defra file.
    to_database: bool, optional (default=False)
        If new factors should be saved to file.

    Returns:
    --------
    None
    '''
    # Reads current factors
    filepath = get_filepath('factors/additional_factors.csv')
    df = pd.read_csv(filepath)

    try:
        # Extracts new factors from file
        land, wtt_land, sea, wtt_sea = read_defra_travel_factors(file, year)
    
        water_treat, water_supply, elec_gen, elec_td, wtt_elec_gen,\
            wtt_elec_td, gas,\
            wtt_gas = read_defra_water_gas_elec_factors(file, year)
    
        landfill = read_defra_disposal_factors(file, year)

        success = True
    except (ValueError, KeyError) as e:
        success = False
        st.error(f'Unable to read file. '
                 f'Values may be entered manually if required.')
        st.write(f'**Error message:** ')
        st.write(e)

        land = st.number_input(f'HGV travel in km. Recommend: '
                               f'Rigid (>7.5 tonnes-17 tonnes), '
                               f'average laden.', min_value=0.0)
        wtt_land = st.number_input(f'WTT-HGV travel in km '
                                   f'(ensure same type as previous).',
                                   min_value=0.0)
        sea = st.number_input(f'Cargo ship travel in tonne/km. '
                              f'Recommend: Container ship, average size.',
                              min_value=0.0)
        wtt_sea = st.number_input(f'WTT-Cargo ship travel in tonne/km '
                                  f'(ensure same type as previous).',
                                  min_value=0.0)
        water_treat = st.number_input(f'Water treatment in cubic metres.',
                                      min_value=0.0)
        water_supply = st.number_input(f'Water supply in cubic metres.',
                                       min_value=0.0)
        elec_gen = st.number_input(f'Electricity generation in kWh.',
                                   min_value=0.0)
        elec_td = st.number_input(f'Electricity transmission and '
                                  f'distribution in kWh.', min_value=0.0)
        wtt_elec_gen = st.number_input(f'WTT-Electricity generation in kWh.',
                                       min_value=0.0)
        wtt_elec_td = st.number_input(f'WTT-Electricity transmission and '
                                      f'distribution in kWh.',
                                       min_value=0.0)
        gas = st.number_input(f'Natural gas (fuel) in cubic metres.',
                              min_value=0.0)
        wtt_gas = st.number_input(f'WTT- Natural gas (fuel) in cubic metres.',
                                  min_value=0.0)
        landfill = st.number_input(f'Waste disposal in tonnes (refuse - '
                                   f'commercial and industrial waste).',
                                   min_value=0.0)/1000

    # Only combines old and new when all values filled in or file read in
    if (land > 0.0 and wtt_land > 0.0 and sea > 0.0 and wtt_sea > 0.0 and
        water_treat > 0.0 and water_supply > 0.0 and elec_gen > 0.0 and
        elec_td and wtt_elec_gen > 0.0 and wtt_elec_td > 0.0 and gas > 0.0 and
        wtt_gas > 0.0 and landfill > 0.0 and not success):
        combine = True
    elif success:
        combine = True
    else:
        combine = False

    if combine:
        # Creates new df with new factors
        new = [['hgv transport', 'km', year, land],
               ['hgv transport wtt', 'km', year, wtt_land],
               ['container ship transport', 'km', year, sea],
               ['container ship transport wtt', 'km', year, wtt_sea],
               ['water treatment', 'm3', year, water_treat],
               ['water supply', 'm3', year, water_supply],
               ['electricity generation', 'kwh', year, elec_gen],
               ['electricity t&d', 'kwh', year, elec_td],
               ['electricity generation wtt', 'kwh', year, wtt_elec_gen],
               ['electricity t&d wtt', 'kwh', year, wtt_elec_td],
               ['gas', 'm3', year, gas],
               ['gas wtt', 'm3', year, wtt_gas],
               ['landfill', 'kg', year, landfill]]
        new_df = pd.DataFrame(new, columns=['name', 'unit', 'year',
                                            'factor_kgCO2eq_unit'])
    
        # Combines data
        combined_df = pd.concat([df, new_df])
        if to_database:
            combined_df.to_csv(filepath, index=False)
    else:
        combined_df = df.copy(deep=True)

    return combined_df


#### USED FOR EXTRACTING CORRECT DATA ####
def find_closest_year(data, year, need_cc=False):
    '''
    Finds closest year in factors file to when the product was made if there
    is not an exact match so most accurate estimate can be made.

    Parameters:
    -----------
    data: pd.Series or pd.DataFrame
        Extract of factors dataframe containing relevant emissions factors
        for given component.
    year: str
        Year to use for factor.
    need_cc: bool, optional (default=False)
        False if you want to extract the factor in kg CO2e, True if want to
        extract the carbon content.

    Returns:
    --------
    val: float
        Carbon factor in kg CO2e or carbon content.
    '''
    smallest = 1000
    closest_yr = 1000
    # Used to find all years stored in database
    for yr, vals in data.iterrows():
        # Finds difference between that year and year the product was made
        year = int(year)
        yr = int(yr)
        diff = abs(yr - year)
        # Finds the smallest difference
        if diff < smallest:
            if closest_yr == 1000:
                smallest = diff
                closest_yr = yr
            else:
                if yr <= year:
                    smallest = diff
                    closest_yr = yr

    # Extracts factor from the closest year found
    best = data.loc[(data.index.get_level_values('year') == closest_yr)]

    if need_cc:
        val = float(best['carbon_content'].to_list()[0])
    else:
        val = float(best['factor_kgCO2eq_unit'].to_list()[0])

    return val

def extract_best_factor(factors, comp, loc, year, need_cc, searched_all):
    '''
    Extracts the best factor in the factors file if available.

    Parameters:
    -----------
    factors: pd.DataFrame
        Contains component name, year and location corresponding to carbon
        factor in kg CO2e and carbon content.
    comp: str
        Name of component.
    loc: str
        Name of location where component made.
    year: str
        Year to use for factor.
    need_cc: bool
        True if carbon content should be extracted, False if emissions factor
        should be extracted.
    searched_all: bool
        If country is selected but specific factor not available, it then
        searches based on whether it is made in Europe or the rest of the
        world so tries again. If cannot find information, it prints out an
        error message.
    
    Returns:
    --------
    fact: float or None
        Emissions factor in kg CO2e or carbon content if available,
        None if not.
    found: bool
        If required emissions factor or carbon content was found.
    '''
    # Whether to extract carbon content or emissions factor
    if need_cc:
        fact_name = 'carbon_content'
    else:
        fact_name = 'factor_kgCO2eq_unit'
                
    found = False # Used to check if relevant information found
    
    try: # Extracts factor if component in factors dataframe given the
         # exact year and location
        fact_df = factors.loc[(comp, loc, year)][fact_name]
        try:
            fact = fact_df.to_list()[0]
        except AttributeError:
            fact = fact_df
        found = True
    # If exact data not listed in dataframe, stops crash
    except KeyError:
        # Extracts part of dataframe with same component and location
        # if available
        fact_df = factors.loc[(factors.index.get_level_values('component') \
                               == comp) & (factors.index.\
                                           get_level_values('loc') == loc)]
            
        # If not exact year listed, finds closest given years available
        if len(fact_df) > 0:
            fact_df.index = fact_df.index.get_level_values('year')
            fact = find_closest_year(fact_df, year, need_cc=need_cc)
            found = True
        # Returns None if factor not found given information
        else:
            fact = None
            # Prints out error message if location not available
            if searched_all:
                if loc == 'rer':
                    loc = 'europe'
                elif loc == 'row':
                    loc = 'rest of world'
                if need_cc:
                    st.error(f'No carbon content available for '
                             f'**{comp.capitalize()}** in '
                             f'{loc.capitalize()}.')
                else:
                    st.error(f'No factor available for '
                             f'**{comp.capitalize()}** in '
                             f'{loc.capitalize()}.')

    return fact, found

def extract_best_factor_ex(additional_factors, name, unit, year):
    '''
    Extracts the best factor in the additional factors file if available.

    Parameters:
    -----------
    additional_factors: pd.DataFrame
        Contains name, unit, and year corresponding to carbon factor
        in kg CO2e.
    name: str
        Name of factor to extract.
    unit: str
        Unit to which factor corresponds.
    year: str
        Year to use for factor.
    
    Returns:
    --------
    fact: float or None
        Emissions factor in kg CO2e or carbon content if available,
        None if not.
    found: bool
        If required emissions factor or carbon content was found.
    '''
    # Uses closest year in file if file not available
    try:
        fact = additional_factors.loc[(name, unit,
                                       year)]['factor_kgCO2eq_unit']
    except KeyError:
        fact_df = additional_factors.loc[(additional_factors.index.\
                                          get_level_values('name') == name)]
        fact_df.index = fact_df.index.get_level_values('year')
        fact = find_closest_year(fact_df, year)

    return fact


#### MANUFACTURING EMISSIONS CALCULATION ####
def manufacture_calc(product, factors, no_comp, dest_city):
    '''
    Calculates emissions for manufacturing the product, given the
    components it is made from.

    Parameters:
    -----------
    product: pd.Series
        Contains product information - made up of components, mass, where they 
        are made and where they are transported to, reprocessing if required
        and disposal information.
    factors: pd.DataFrame
        Contains component name, year and location corresponding to carbon
        factor in kg CO2e and carbon content.
    no_comp: int
        Maximum number of components contained in the products file.
    dest_city: str
        Destination of product.

    Returns:
    --------
    mamu_emissions: list
        List contains individual GHG emissions for each component
        the product is made from.
    total_manu_emission: float
        Sum of manufacture emissions for all components.
    '''
    # List of countries in Europe and Rest of World
    rer_countries, row_countries = read_countries_continents()

    # Calculates emissions corresponding to making specific products
    manu_emissions = []
    
    for i in range(no_comp): # Loops through components of product
        comp = product['component_' + str(i+1)] # Finds name of component
        # Finds year and location of production
        year = product['manu_year_' + str(i+1)]
        manu_loc = product['manu_loc_' + str(i+1)]

        need_cc = False
        
        if manu_loc == '0':
            manu_loc = dest_city + '(united kingdom)'
        loc = manu_loc[manu_loc.find('(')+1:manu_loc.find(')')]

        # Tries to find the best factor for provided information
        fact, found = extract_best_factor(factors, comp, loc, year,
                                          need_cc, searched_all=False)

        if fact is None:
            # If not found, location may not be listed in file but may be able
            # to change specific country to Europe or Rest of World
            if loc.lower() in rer_countries:
                loc = 'rer'
            elif loc.lower() in row_countries:
                loc = 'row'
            else:
                st.error(f'Error: **{loc.capitalize()}** not a valid '
                         f'country.')
                break
            fact, found = extract_best_factor(factors, comp, loc, year,
                                              need_cc, searched_all=True)

        # Stops calculation if relevant factor not found in file
        if not found:
            break

        # Finds mass of material
        mass = product['mass_kg_' + str(i+1)] # Finds mass of material
        no_uses = product['no_uses_' + str(i+1)] # Finds number of uses

        # Per use emission = factor x (mass / no. uses)
        em = fact * (float(mass) / float(no_uses))
    
        # Adds emissions to list for specific item
        manu_emissions.append(em)

    total_manu_emissions = float(sum(manu_emissions))

    return manu_emissions, total_manu_emissions


#### TRVAEL EMISSIONS CALCULATION ####
def read_travel_fact(additional_factors, year):
    '''Reads travel emissions factors from file.'''
    unit = 'km'
    land_fact = extract_best_factor_ex(additional_factors,
                                       'hgv transport',
                                       unit, year)
    wtt_land_fact = extract_best_factor_ex(additional_factors,
                                           'hgv transport wtt',
                                            unit, year)
    sea_fact = extract_best_factor_ex(additional_factors,
                                      'container ship transport',
                                      unit, year)
    wtt_sea_fact = extract_best_factor_ex(additional_factors,
                                          'container ship transport wtt',
                                          unit, year)

    # Calculates total factor for land and sea travel
    land_travel_fact = land_fact + wtt_land_fact
    sea_travel_fact = sea_fact + wtt_sea_fact

    return land_travel_fact, sea_travel_fact

def calc_sea_distance(sea_travel_dist, start_port, end_port):
    '''
    Extracts sea travel distance if input in file or calculates
    distance of sea travel if not.

    Parameters:
    -----------
    sea_travel_dist: pd.DataFrame
        Contains information about known sea travel distances.
    start_port: str
        Start of sea travel.
    end_port: str
        End of sea travel.

    Returns:
    -------
    sea_dist_km: float
        Distance travelled in km.
    '''
    try:
        # Extracts distance travelled if in dataframe
        #sea_dist_df = sea_travel_dist.at[(start_port, end_port),
        #                                 'distance_km']
        sea_dist_df = sea_travel_dist.loc[(start_port, end_port),
                                          'distance_km']
        try:
            sea_dist_km = sea_dist_df.to_list()[0]
        except AttributeError:
            sea_dist_km = sea_dist_df
    except KeyError:
        try:
            # If not in data frame, calculate value using Nominatim
            # Uses GeoPy to calculate sea travel distances
            loc = Nominatim(user_agent='Geopy_Library')
            start_loc = loc.geocode(start_port)
            end_loc = loc.geocode(end_port)
            # Define origin and destination points as [long, lat]
            origin = [start_loc.longitude, start_loc.latitude]
            destination = [end_loc.longitude, end_loc.latitude]
            # Returns a GeoJSON LineString Feature
            route = sr.searoute(origin, destination)
            # Returns distance in km
            sea_dist_km = route.properties['length']
            # Updates file with new calculation
            update_travel_distances(start_port, end_port, sea_dist_km,
                                    sea=True)
        except (ValueError, AttributeError) as e:
            sea_dist_km = 0
            st.error(f'*Select a valid port.*')

    return sea_dist_km

def calc_travel_emissions(dist_km, no_uses, mass, travel_fact):
    '''
    Calculates emissions for section of journey to end destination.
    Corresponds to either: travel from start location to port, travel
    between ports, or travel from port to destination.

    Parameters:
    -----------
    dist_km: float
        Distance travelled in km
    no_uses: int
        Number of uses of component.
    mass: float
        Mass of component.
    travel_fact: float
        Emissions factor for land or sea travel.

    Returns:
    --------
    ghg_em_pu: float
        Greenhouse gas emissions per use for that journey if available.
    '''
    # Calculate travel emissions
    ghg_em = (mass * dist_km * travel_fact) / 1000 # Factor is in tonne km
    ghg_em_pu = ghg_em / no_uses
            
    return ghg_em_pu

def travel_calc(product, no_comp, additional_factors):
    '''
    Calculates emissions for transporting the components of the product, from
    the start location to port (land travel), then port to port (sea travel),
    the port to end location (land travel).

    Parameters:
    -----------
    product: pd.Series
        Contains product information - made up of components, mass, where they 
        and are made and where they are transported to, reprocessing if required
        disposal information.
    no_comp: int
        Maximum number of components contained in the products file.
    additional_factors: pd.DataFrame
        Contains emissions factors for goods transport.

    Returns:
    --------
    travel_emissions: list
        List contains individual GHG emissions for each component
        the product is made from.
    total_travel_emissions: float
        Sum of travel emissions for all components.
    '''
    # Calculates emissions corresponding to travel
    travel_emissions = []
    
    for i in range(no_comp): # Loops through components
        travel_em = 0.0

        start = product['manu_loc_' + str(i+1)] # Start at manufacture loc
    
        if start != '0' and start != None: # Stops calc if process
            comp = product['component_' + str(i+1)] # Finds name of component
            mass = product['mass_kg_' + str(i+1)] # Mass of component
            no_uses = product['no_uses_' + str(i+1)] # Number of uses
            year = product['manu_year_' + str(i+1)] # Year of manufacture

            land_travel_fact, \
                sea_travel_fact = read_travel_fact(additional_factors, year)

            land_dist_km = product['land_dist_' + str(i+1)] # Land distance
            sea_dist_km = product['sea_dist_' + str(i+1)] # Sea distance
    
            # Emissions from land travel
            if land_dist_km > 0.0:
                ghg_em = calc_travel_emissions(land_dist_km, no_uses,
                                               mass, land_travel_fact)
                travel_em += ghg_em
    
            # Emissions from sea travel
            if sea_dist_km > 0.0:
                ghg_em = calc_travel_emissions(sea_dist_km, no_uses,
                                               mass, sea_travel_fact)
                travel_em += ghg_em
    
        # Adds emissions to list for specific 
        travel_emissions.append(travel_em)
    
    total_travel_emissions = sum(travel_emissions)

    return travel_emissions, total_travel_emissions


#### USE EMISSIONS CALCULATION ####
def read_use_fact(additional_factors, year):
    '''Reads electricity/water/gas emissions factors from file.'''    
    water_unit = 'm3'
    wt_fact = extract_best_factor_ex(additional_factors,
                                     'water treatment',
                                     water_unit, year)
    ws_fact = extract_best_factor_ex(additional_factors,
                                     'water supply',
                                      water_unit, year)

    elec_unit = 'kwh'
    eg_fact = extract_best_factor_ex(additional_factors,
                                     'electricity generation',
                                     elec_unit, year)
    etd_fact = extract_best_factor_ex(additional_factors,
                                      'electricity t&d',
                                      elec_unit, year)
    eg_wtt_fact = extract_best_factor_ex(additional_factors,
                                         'electricity generation wtt',
                                         elec_unit, year)
    etd_wtt_fact = extract_best_factor_ex(additional_factors,
                                          'electricity t&d wtt',
                                          elec_unit, year)

    gas_unit = 'm3'
    gas_fact = extract_best_factor_ex(additional_factors,
                                      'gas', gas_unit, year)
    gas_wtt_fact = extract_best_factor_ex(additional_factors,
                                          'gas wtt', gas_unit, year)

    return (wt_fact, ws_fact, eg_fact, etd_fact, eg_wtt_fact, etd_wtt_fact,
            gas_fact, gas_wtt_fact)

def use_calc(additional_factors, year, water_vol_per_use=None,
             power_rating=None, time_per_use=None, gas_per_use=None):
    '''
    Calculates emissions corresponding to water, gas and electricity
    use during product lifetime.

    Parameters:
    -----------
    filename: str
        Filepath of Defra excel file to extract electricity,
        water and gas factors.
    water_vol_per_use: float, optional (default=None)
        Volume of water used during use (litres) or None if water
        not used.
    power_rating: float, optional (default=None)
        Power rating of applicance (W) or None if electricity
        not used.
    time_per_use: float, optional (default=None)
        Time applicance is on for (hours) or None if electricity
        not used.
    gas_per_use: float, optional (default=None)
        Volume of gas used during use (m^3) or None if gas
        not used.

    Returns:
    --------
    use_emissions: float
        Kg CO2e corresponding to water/electricity/gas use over
        the product's lifetime.
    '''
    # Extracts emissions factors for use
    # Water = treatment and supply
    # Electricity = generation, transmission & distribution (incl. WTT)
    # Gas = gas as fuel (incl. WTT)
    (wt_fact, ws_fact, eg_fact, etd_fact, eg_wtt_fact, etd_wtt_fact,
     gas_fact, gas_wtt_fact) = read_use_fact(additional_factors, year)

    use_emissions = 0
    # Calculates emissions from water use
    if water_vol_per_use is not None:
        use_emissions += wt_fact * (water_vol_per_use / 1000)
        use_emissions += ws_fact * (water_vol_per_use / 1000)
    # Calculates emissions from electricity use
    elif power_rating is not None and time_per_use is not None:
        kwh = (power_rating * time_per_use) / 1000
        use_emissions += eg_fact * kwh
        use_emissions += etd_fact * kwh
        use_emissions += eg_wtt_fact * kwh
        use_emissions += etd_wtt_fact * kwh
    # Calculates emissions from gas use
    elif gas_per_use is not None:
        use_emissions += gas_fact * gas_per_use
        use_emissions += gas_wtt_fact * gas_per_use

    return use_emissions


#### REPROCESSING EMISSIONS CALCULATION ####
def decon_emission_calc(name, decon_units, additional_factors, product_year):
    '''
    Calculates emissions factors for decontamination unit chosen.

    Parameters:
    -----------
    name: str
        Name of decontamination unit.
    decon_units: dict
        Contains unit and corresponding values for water, electricity and
        gas use.
    additional_factors: pd.DataFrame
        Contains water/gas/electricity emissions factors.
    product_year: int
        Year to use to extract factors from.

    Returns:
    --------
    decon_fact: float
         Emissions factors for decontamination.
    '''
    # Extracts emissions factors
    # Water = treatment and supply
    # Electricity = generation, transmission & distribution (incl. WTT)
    # Gas = gas as fuel (incl. WTT)
    (wt_fact, ws_fact, eg_fact, etd_fact, eg_wtt_fact, etd_wtt_fact,
     gas_fact, gas_wtt_fact) = read_use_fact(additional_factors,
                                             product_year)
    
    water_kg_co2e = (wt_fact + ws_fact) * \
                    0.001 * decon_units[name + ' water']

    elec_kg_co2e = (eg_fact + etd_fact + eg_wtt_fact + etd_wtt_fact) * \
                   decon_units[name + ' electricity']

    gas_kg_co2e = (gas_fact + gas_wtt_fact) * \
                  decon_units[name + ' gas']

    decon_fact = water_kg_co2e + elec_kg_co2e + gas_kg_co2e

    return decon_fact

def read_laundry_fact(additional_factors, year):
    '''Reads laundry emissions factors from file.'''
    laundry_fact = extract_best_factor_ex(additional_factors,
                                          'laundry', 'kg', year)

    return laundry_fact

def reprocessing_calc(product, no_comp, laundry_fact, decon_fact):
    '''
    Calculates emissions for reprocessing the product.

    Parameters:
    -----------
    product: pd.Series
        Contains product information - made up of components, mass, where they 
        are made and where they are transported to, reprocessing if required
        and disposal information.
    no_comp: int
        Maximum number of components contained in the products file.
    laundry_fact: float
        Emissions factor per kg of laundry.
    decon_fact: float
        Emissions factor for decontamination unit.

    Returns:
    --------
    reprocess_emissions: float
        Reprocessing GHG emissions for product.
    '''
    # Calculates emissions corresponding to reprocessing product
    reprocess_emissions = 0.0
    autoclave_req = False
    found_percent_fill = False
        
    for i in range(no_comp): # Loops through components
        comp = product['component_' + str(i+1)] # Finds name of component
        mass = product['mass_kg_' + str(i+1)] # Finds mass of product/process
        # Finds reprocessing type if applicable
        repro = product['reprocessing_' + str(i+1)]
            
        if repro is not None:
            if repro == 'laundry':
                reprocess_emissions += mass * laundry_fact
            elif 'hsdu' in repro:
                if not found_percent_fill:
                    percent_fill = float(repro[repro.find('(')+1:repro.find(')')])
                    found_percent_fill = True
                autoclave_req = True

    if autoclave_req:
        reprocess_emissions += decon_fact * (percent_fill / 100)

    return reprocess_emissions


#### DISPOSAL EMISSIONS CALCULATION ####
def read_landfill_fact(additional_factors, year):
    '''Reads landfill emissions factors from file.'''
    landfill_fact = extract_best_factor_ex(additional_factors,
                                           'landfill', 'kg', year)

    return landfill_fact

def read_disposal_fact(additional_factors, year):
    '''Reads disposal travel emissions factors from file.'''
    disposal_fact = extract_best_factor_ex(additional_factors,
                                           'disposal transport',
                                           'km', year)

    return disposal_fact

def disposal_calc(product, factors, no_comp, landfill_fact, transport_fact,
                  year):
    '''
    Calculates emissions for manufacturing the product, given the
    components it is made from.

    Parameters:
    -----------
    product: pd.Series
        Contains product information - made up of components, mass, where they 
        are made and where they are transported to, reprocessing if required
        and disposal information.
    factors: pd.DataFrame
        Contains component name, year and location corresponding to carbon
        factor in kg CO2e and carbon content.
    no_comp: int
        Maximum number of components contained in the products file.
    landfill_fact: float
        Emissions factor per kg of landfill waste.
    transport_fact: float
        Emissions factor for transporting waste.
    year: int
        Year of component manufacture.

    Returns:
    --------
    incinerate_emissions: float
        Incineration emissions for product.
    recycle_emissions: float
        Recycling emissions for product.
    landfill_emissions: float
        Landfill emissions for product.
    biogenic_carbon: float
        Biogenic carbon component for product.
    net_waste_emissions: float
        Sum of all individual disposal emissions for each component to give
        total GHG emissions for each product in the inventory.
        Calculated as sum of incineration emissions, recycling emissions,
        landfill emissions and biogenic component.
    '''
    rer_countries, row_countries = read_countries_continents()

    bio = 0.0
    incinerate_c_mass = 0.0
    mass_for_incinerate = 0.0
    mass_for_recycle = 0.0
    mass_for_landfill = 0.0
    
    # Calculates emissions corresponding to disposing of specific products
    for i in range(no_comp): # Loops through components
        comp = product['component_' + str(i+1)] # Finds name of component
    
        # Finds year and location of production
        year = product['manu_year_' + str(i+1)]
        manu_loc = product['manu_loc_' + str(i+1)]

        # If incinerated or not - 1 if it is or 0 if not
        incinerate = float(product['incinerate_' + str(i+1)])
        # If recycled or not - 1 if it is or 0 if not
        recycle = float(product['recycle_' + str(i+1)])
        # If landfill disposal or not - 1 if it is, 0 if not
        landfill = float(product['landfill_' + str(i+1)])
    
        if (incinerate + recycle + landfill) > 1:
            st.error(f'Error: {comp} disposed of in multiple ways.')
            break

        # Stops calculation if no disposal listed (e.g. process)
        if incinerate == '0' and recycle == '0' and landfill == '0':
            break

        if comp != '0' and manu_loc != '0':
            loc = manu_loc[manu_loc.find('(')+1:manu_loc.find(')')]
            # Tries to find the best carbon content for provided information
            need_cc = True
            cc, found = extract_best_factor(factors, comp, loc, year, need_cc,
                                            searched_all=False)
    
            if cc is None:
                # If not found, location not be in file but may be able
                # to change specific country to Europe or Rest of World
                if loc.lower() in rer_countries:
                    loc = 'rer'
                elif loc.lower() in row_countries:
                    loc = 'row'
                else:
                    st.error(f'Error: {loc} not a valid country.')
                    break
                cc, found = extract_best_factor(factors, comp, loc, year,
                                                need_cc, searched_all=True)
        # Stops calculation if no component listed
        else:
            break
        
        # Stops calculation if relevant factor not found in file
        if not found:
            break
    
        mass = product['mass_kg_' + str(i+1)] # Mass of product/process
        no_uses = product['no_uses_' + str(i+1)] # Number of uses
    
        # Per use mass = mass / number of uses
        pu_mass = float(mass) / float(no_uses)
    
        # If biogenic component - 0 if not, 1 if it is
        is_biogen = product['biogenic_' + str(i+1)]
    
        # Calculates biogenic = carbon content x per use mass x (if biogenic)
        bio += cc * is_biogen * pu_mass
    
        # Calculates incineration carbon mass
        incinerate_c_mass += pu_mass * incinerate * cc
    
        # Calculates mass for incineration
        mass_for_incinerate += pu_mass * incinerate
    
        # Calculates recycling mass
        mass_for_recycle += pu_mass * recycle
    
        # Calculates landfill mass
        mass_for_landfill += pu_mass * landfill
    
    # Calculates CO2e emissions from incineration
    # C Mass / C Mr = Mol * CO2 Mr = Mass CO2
    incinerate_em = (incinerate_c_mass / 12.01) * 44.01
    # Calculates incineration transport emissions    
    incinerate_transport = mass_for_incinerate * transport_fact
    # Calculates total incineration emissions
    incinerate_emissions = incinerate_em + incinerate_transport
    
    # Calculates total recycling emissions = transport emissions
    recycle_emissions = mass_for_recycle * transport_fact
    
    # Calculates emissions for travel to landfill
    landfill_transport = mass_for_landfill * transport_fact
    # Calculates emissions in landfill
    landfill_em = mass_for_landfill * landfill_fact
    # Calculates total landfill emissions
    landfill_emissions = landfill_transport + landfill_em
    
    # Calculates biogenic carbon
    biogenic_carbon = (bio / 12.01) * 44.01
    
    net_waste_emissions = incinerate_emissions + recycle_emissions + \
                          landfill_emissions - biogenic_carbon

    return (incinerate_emissions, recycle_emissions, landfill_emissions,
            biogenic_carbon, net_waste_emissions)


#### ADD NEW DECONTAMINATION UNIT ####
def add_new_decon_to_file(name, elec, water, gas):
    filepath = get_filepath(f'data/decon_units.csv')

    if os.path.isfile(filepath):
        with open(filepath, 'r') as f:
            rows = []
            for ind, line in enumerate(f):
                l = line.rstrip('\n')
                d = l.split(',')
                if ind == 0:
                    header = d
                elif ind > 0:
                    rows.append(d)

        elec_name = name + ' electricity'
        water_name = name + ' water'
        gas_name = name + ' water'
        rows += [[elec_name, 'kwh', elec],
                 [water_name, 'l', water],
                 [gas_name, 'm3', gas]]
    
        with open(filepath, 'w') as f:
            csvwriter = csv.writer(f)
            csvwriter.writerow(header)
            csvwriter.writerows(rows)
    
    return


#### SAVE PRODUCT TO DATABASE ####
def read_csv_file(file):
    '''Reads CSV file and extracts header and data.'''
    with open(file, 'r') as f:
        # Reader object will iterate over lines in csv file 
        csv_reader = csv.reader(f)
  
        # Convert to list 
        file_contents = list(csv_reader) 

        # Extracts data
        header = file_contents[0]
        data = file_contents[1:]

    return header, data

def update_database(data, name):
    '''Updates saved database file and archives previous version.'''
    now = datetime.now() # Current date and time
    date_time = now.strftime("%Y-%m-%d_%H-%M-%S") # Formatted string

    filepath = get_filepath(f'inventory/{name}.csv')

    # Archives current file using date and time
    if os.path.isfile(filepath):
        # Exports as new csv file to archive folder
        filename = f'{name}_' + date_time + '.csv'
        filepath_arch = get_filepath(f'inventory/{name}_archive/' \
                                     + filename)
        shutil.copyfile(filepath, filepath_arch)
    
    # Creates new .csv file
    data.to_csv(filepath, index=False)

    return
    
def write_new_header(header, large_no_comp, i):
    '''Creates new header for updated file length.'''
    new_num = str(large_no_comp+i+1)
    header.append('component_' + new_num)
    header.append('manu_year_' + new_num)
    header.append('mass_kg_' + new_num)
    header.append('no_uses_' + new_num)
    header.append('biogenic_' + new_num)
    header.append('manu_loc_' + new_num)
    header.append('debark_port_' + new_num)
    header.append('depart_loc_uk_' + new_num)
    header.append('reprocess_' + new_num)
    header.append('recycle_' + new_num)
    header.append('incinerate_' + new_num)
    header.append('landfill_' + new_num)

    return header
    
def lengthen_shorten_inventory_data(product, data, header):
    '''Updates product file or new product data to ensure matching formats.'''
    # Finds the greatest number of components that are currently in the
    # inventory file so can be updated if necessary
    final_data = header[-1]
    ind = final_data.rindex('_')
    large_no_comp = int(final_data[ind+1:])

    # Separates emissions so they appear at the end
    product_data = product.to_list()
    product_info = product_data[:5]
    product_comp = product_data[5:]

    # Lengths used to see if changes have to be made to current data or new
    # data to be compatible with the file
    new_no_comp = int(list(product.index)[-1].split('_')[-1])

    # If they are the same length, it can be added on without changes
    if new_no_comp == large_no_comp:
        data.append(product_data)
    
    # If new data is shorter, need to add additional 0s for remaining columns
    elif new_no_comp < large_no_comp:
        # Finds number of components not contained so can be replaced with 0s
        for i in range(large_no_comp - new_no_comp):
            to_add = ['0' for j in range(12)]
            product_comp.extend(to_add) # Extends new row to match
        product = product_info + product_comp
        data.append(product)
    
    # If old data shorter, need to extend original file to fit new
    elif new_no_comp > large_no_comp:
        new_data = []
        for ind, d in enumerate(data):
            # Finds number of components not contained so can be replaced with 0s
            for i in range(new_no_comp - large_no_comp):
            # Extends all current lists in file to match size of new data
                to_add = ['0' for j in range(12)]
                d.extend(to_add)
                if ind == 0:
                    # Creates new headers corresponding to new information
                    header = write_new_header(header, large_no_comp, i)
            
            new_data.append(d)
        
        data = new_data
        product = product_info + product_comp
        data.append(product)

    return data, header

def update_inventory(product_info, to_database):
    '''
    Updates emissions file given new calculations and archieves the old one.

    Parameters:
    -----------
    product_info: pd.Series
        Contains product information - made up of components, mass, where they 
        are made and where they are transported to, reprocessing if required
        and disposal information.
    to_database: bool
        If changes should be pushed to database. Only works locally.

    Returns:
    --------
    None.
    '''
    filepath = get_filepath(f'inventory/products.csv')

    if os.path.isfile(filepath):
        header, data = read_csv_file(filepath)
        new_data, new_header = lengthen_shorten_inventory_data(product_info,
                                                               data,
                                                               header)
        products = pd.DataFrame(new_data, columns=new_header)

        if to_database:
            # Creates new .csv file with emissions
            update_database(products, 'products')
            #products.to_csv(filepath, index=False)
    else:
        products = None
        st.error('Cannot update product database.')

    return products

def lengthen_shorten_emissions_data(product, data, header):
    '''Updates product file or new product data to ensure matching formats.'''
    # Finds the greatest number of components that are currently in the
    # emissions file so can be updated if necessary
    final_data = header[-7]
    ind = final_data.rindex('_')
    large_no_comp = int(final_data[ind+1:])

    # Separates emissions so they appear at the end
    product_data = product.to_list()
    emissions_product = product_data[-6:]
    product_info = product_data[:5]
    product_comp = product_data[5:-6]

    # Lengths used to see if changes have to be made to current data or new
    # data to be compatible with the file
    new_no_comp = int(list(product.index)[-7].split('_')[-1])

    # If they are the same length, it can be added on without changes
    if new_no_comp == large_no_comp:
        data.append(product_data)

    # If new data is shorter, need to add additional 0s for remaining columns
    elif new_no_comp < large_no_comp:
        # Finds number of components not contained so can be replaced with 0s
        for i in range(large_no_comp - new_no_comp):
            to_add = ['0' for j in range(12)]
            product_comp.extend(to_add) # Extends new row to match
        product = product_info + product_comp + emissions_product
        data.append(product)
        product_data = product

    # If old data shorter, need to extend original file to fit new
    elif new_no_comp > large_no_comp:
        new_data = []
        # Removes emissions part of header so can be added at the end
        emissions_header = header[-6:]
        comp_header = header[:len(header)-6]

        for ind, d in enumerate(data):
            emissions_data = d[-6:]
            other = d[:-6]
            # Finds number of components not contained so can be replaced with 0s
            for i in range(new_no_comp - large_no_comp):
            # Extends all current lists in file to match size of new data
                to_add = ['0' for j in range(12)]
                other.extend(to_add)
                other.extend(emissions_data)
                if ind == 0:
                    # Creates new headers corresponding to new information
                    comp_header = write_new_header(comp_header,
                                                   large_no_comp, i)
            
            new_data.append(other)
        
        header = comp_header + emissions_header
        data = new_data
        product = product_info + product_comp + emissions_product
        data.append(product)

    return data, header, product_data

def update_emissions(product, to_database):
    '''
    Updates emissions file given new calculations and archieves the old one.

    Parameters:
    -----------
    product: pd.Series
        Contains product information - made up of components, mass, where they 
        are made and where they are transported to, reprocessing if required
        and disposal information.
    to_database: bool
        If changes should be pushed to database. Only works locally.

    Returns:
    --------
    None.
    '''
    filepath = get_filepath(f'inventory/emissions.csv')

    if os.path.isfile(filepath):
        header, data = read_csv_file(filepath)
        (new_data, new_header,
         product_data) = lengthen_shorten_emissions_data(product, data,
                                                         header)
        emissions = pd.DataFrame(new_data, columns=new_header)
        product = pd.DataFrame([product_data], columns=new_header)

        if to_database:
            # Creates new .csv file with emissions
            update_database(emissions, 'emissions')
    else:
        emissions = None
        product = None
        st.error('Cannot update emissions database.')

    return emissions, product


#### UPDATE FACTORS FILE ####
def update_factors_file(factors):
    '''
    Adds new factors file to csv.

    Parameters:
    -----------
    factors: pd.DataFrame
        Contains component name, year and location corresponding to carbon
        factor in kg CO2e and carbon content.

    Returns:
    --------
    None.
    '''
    sh, spread = read_gsheets('factors')

    col = ['component', 'loc', 'year', 'unit', 'factor_kgCO2eq_unit',
           'carbon_content']
    spread.df_to_sheet(factors[col], sheet='factors.csv', index=False)

    return

def update_factors_file_local(factors):
    '''
    Adds new factors file to csv.

    Parameters:
    -----------
    factors: pd.DataFrame
        Contains component name, year and location corresponding to carbon
        factor in kg CO2e and carbon content.

    Returns:
    --------
    None.
    '''
    # Factors data filepath
    factors_filepath = get_filepath(f'factors/factors.csv')

    # Checks that file exists in location
    if os.path.isfile(factors_filepath):
        old_factors = pd.read_csv(factors_filepath)
        new_factors = pd.concat([old_factors, factors])
        new_factors.to_csv(factors_filepath, index=False)

    return


#### UPDATES TRAVEL DISTANCES WITH INPUT ####
def update_travel_distances_local(start, end, distance, sea=False):
    '''
    Updates travel distances file given new information.

    Parameters:
    -----------
    start: str
        Start location name.
    end: str
        End location name.
    distance: float
        Distance between start and end.
    sea: bool, optional (default=False)
        If sea travel file or land travel file should be updated.

    Returns:
    --------
    None.
    '''
    if sea:
        filepath = get_filepath(f'data/sea_travel_distance.csv')
    else:
        filepath = get_filepath(f'data/land_travel_distance.csv')

    if os.path.isfile(filepath):
        header, data = read_csv_file(filepath)

        new_info = [start.lower(), end.lower(), distance]
        data.append(new_info)

        travel_distance = pd.DataFrame(data, columns=header)
        travel_distance.to_csv(filepath, index=False)

    return