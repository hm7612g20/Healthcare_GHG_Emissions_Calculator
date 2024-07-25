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


#### UPDATE FILE WITH NEW DEFRA FACTORS ####
@st.cache_data(show_spinner=False)
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
    travel_factors = pd.read_excel(
        filename, sheet_name=travel_sheetname, skiprows=range(0, 24))

    wtt_travel_sheetname = 'WTT- delivery vehs & freight'
    wtt_travel_factors = pd.read_excel(
        filename, sheet_name=wtt_travel_sheetname, skiprows=range(0, 18))

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
    land = pd.to_numeric(
        travel_factors.loc[(
            travel_factors['Activity'] == 'HGV (all diesel)') &
            (travel_factors['Type'] == 'Rigid (>7.5 tonnes-17 tonnes)') &
            (travel_factors['Unit'] == 'tonne.km'), land_name])
    land = land.iloc[0]

    # Locates the correct sea travel factor
    sea = pd.to_numeric(
        travel_factors.loc[(travel_factors['Activity'] == 'Cargo ship') &
                           (travel_factors['Type'] == 'Container ship') &
                           (travel_factors['Unit'] == 'Average'), sea_name])
    sea = sea.iloc[0]

    # Locates the correct well-to-tank land travel factor
    wtt_land = pd.to_numeric(
        wtt_travel_factors.loc[(
            wtt_travel_factors['Activity'] == 'WTT- HGV (all diesel)') &
           (wtt_travel_factors['Type'] == 'Rigid (>7.5 tonnes-17 tonnes)') &
           (wtt_travel_factors['Unit'] == 'tonne.km'), land_name])
    wtt_land = wtt_land.iloc[0]

    # Locates the correct well-to-tank sea travel factor
    wtt_sea = pd.to_numeric(
        wtt_travel_factors.loc[(
            wtt_travel_factors['Activity'] == 'WTT- cargo ship') &
            (wtt_travel_factors['Type'] == 'Container ship') &
            (wtt_travel_factors['Unit'] == 'Average'), sea_name])
    wtt_sea = wtt_sea.iloc[0]

    return land, wtt_land, sea, wtt_sea


@st.cache_data(show_spinner=False)
def read_defra_water_gas_elec_factors(filename, year):
    '''
    Extracts water, gas and electricity emissions factors from Defra excel
    file to use in calculations.

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

    water_supply_factors = pd.read_excel(
        filename, sheet_name='Water supply',  skiprows=range(0, 16))

    water_treat_sheetname = 'Water treatment'
    water_treat_factors = pd.read_excel(
        filename, sheet_name='Water treatment', skiprows=range(0, 15))

    water_supply = pd.to_numeric(
        water_supply_factors.loc[(
            water_supply_factors['Unit'] == 'cubic metres'), fact_name])
    water_supply = water_supply.iloc[0]

    water_treat = pd.to_numeric(
        water_treat_factors.loc[(
            water_treat_factors['Unit'] == 'cubic metres'), fact_name])
    water_treat = water_treat.iloc[0]

    elec_factors = pd.read_excel(
        filename, sheet_name='UK electricity', skiprows=range(0, 22))

    elec_td_factors = pd.read_excel(
        filename, sheet_name='Transmission and distribution',
        skiprows=range(0, 19))

    wtt_elec_factors = pd.read_excel(
        filename, sheet_name='WTT- UK electricity', skiprows=range(0, 17))

    elec_gen = pd.to_numeric(
        elec_factors.loc[(
            elec_factors['Activity'] == 'Electricity generated') &
            (elec_factors['Unit'] == 'kWh'), fact_name])
    elec_gen = elec_gen.iloc[0]

    elec_td = pd.to_numeric(
        elec_td_factors.loc[(
            elec_td_factors['Activity'] == 'T&D- UK electricity') &
            (elec_td_factors['Unit'] == 'kWh'), fact_name])
    elec_td = elec_td.iloc[0]

    wtt_elec_gen = pd.to_numeric(
        wtt_elec_factors.loc[(wtt_elec_factors['Activity'] ==
                              'WTT- UK electricity (generation)') &
                             (wtt_elec_factors['Unit'] == 'kWh'), fact_name])
    wtt_elec_gen = wtt_elec_gen.iloc[0]

    wtt_elec_td = pd.to_numeric(
        wtt_elec_factors.loc[(
            wtt_elec_factors['Activity'] == 'WTT- UK electricity (T&D)') &
            (wtt_elec_factors['Unit'] == 'kWh'), fact_name])
    wtt_elec_td = wtt_elec_td.iloc[0]

    fuel_factors = pd.read_excel(
        filename, sheet_name='Fuels', skiprows=range(0, 21))

    wtt_fuel_factors = pd.read_excel(
        filename, sheet_name='WTT- fuels', skiprows=range(0, 20))

    fuel_factors[['Activity', 'Fuel']] \
        = fuel_factors[['Activity', 'Fuel']].ffill()

    wtt_fuel_factors[['Activity', 'Fuel']] \
        = wtt_fuel_factors[['Activity', 'Fuel']].ffill()

    gas = pd.to_numeric(
        fuel_factors.loc[(fuel_factors['Activity'] == 'Gaseous fuels') &
                         (fuel_factors['Fuel'] == 'Natural gas') &
                         (fuel_factors['Unit'] == 'cubic metres'), fact_name])
    gas = gas.iloc[0]

    wtt_gas = pd.to_numeric(
        wtt_fuel_factors.loc[(
            wtt_fuel_factors['Activity'] == 'Gaseous fuels') &
            (wtt_fuel_factors['Fuel'] == 'Natural gas') &
            (wtt_fuel_factors['Unit'] == 'cubic metres'), fact_name])
    wtt_gas = wtt_gas.iloc[0]

    return (water_treat, water_supply, elec_gen, elec_td, wtt_elec_gen,
            wtt_elec_td, gas, wtt_gas)


@st.cache_data(show_spinner=False)
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
    waste_factors = pd.read_excel(
        filename, sheet_name=waste_sheetname, skiprows=range(0, 23))

    waste_factors[['Activity']] = waste_factors[['Activity']].ffill()

    # Reflects change in reporting name
    if int(year) > 2022:
        fact_name = 'kg CO2e.5'
    else:
        fact_name = 'Total kg CO2e per unit'

    landfill_fact = pd.to_numeric(
        waste_factors.loc[(
            waste_factors['Activity'] == 'Refuse') &
            (waste_factors['Waste type'] == 'Commercial and industrial waste'),
            fact_name])
    landfill_fact = landfill_fact.iloc[0] / 1000

    return landfill_fact


def new_defra(file, year, to_database=False):
    '''
    Extracts info using new Defra file. If file cannot be read, user can input
    values manually.

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
    df = read_additional_factors()

    try:  # Extracts new factors from file
        land, wtt_land, sea, wtt_sea = read_defra_travel_factors(file, year)

        (water_treat, water_supply, elec_gen, elec_td, wtt_elec_gen,
         wtt_elec_td, gas, wtt_gas) = read_defra_water_gas_elec_factors(
             file, year)

        landfill = read_defra_disposal_factors(file, year)

        success = True
    except (ValueError, KeyError) as e:
        success = False
        st.error(f'''Unable to read file.
                     Values may be entered manually if required.''')
        st.write(f'**Error message:** ')
        st.write(e)

        land = st.number_input(
            f'''HGV travel in km. Recommend: Rigid (>7.5 tonnes-17 tonnes),
            average laden.''', min_value=0.0)
        wtt_land = st.number_input(
            f'WTT-HGV travel in km (ensure same type as previous).',
            min_value=0.0)
        sea = st.number_input(
            f'''Cargo ship travel in tonne/km. Recommend: Container ship,
            average size.''', min_value=0.0)
        wtt_sea = st.number_input(
            f'''WTT-Cargo ship travel in tonne/km (ensure same type as
            previous).''', min_value=0.0)

        water_treat = st.number_input(
            f'Water treatment in cubic metres.', min_value=0.0)
        water_supply = st.number_input(
            f'Water supply in cubic metres.', min_value=0.0)

        elec_gen = st.number_input(
            f'Electricity generation in kWh.', min_value=0.0)
        elec_td = st.number_input(
            f'Electricity transmission and distribution in kWh.',
            min_value=0.0)
        wtt_elec_gen = st.number_input(
            f'WTT-Electricity generation in kWh.', min_value=0.0)
        wtt_elec_td = st.number_input(
            f'WTT-Electricity transmission and distribution in kWh.',
            min_value=0.0)

        gas = st.number_input(
            f'Natural gas (fuel) in cubic metres.', min_value=0.0)
        wtt_gas = st.number_input(
            f'WTT- Natural gas (fuel) in cubic metres.', min_value=0.0)

        landfill = st.number_input(
            f'''Waste disposal in tonnes (refuse - commercial and
            industrial waste).''', min_value=0.0)/1000

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
        new_df = pd.DataFrame(
            new, columns=['name', 'unit', 'year', 'factor_kgCO2eq_unit'])

        # Combines data
        combined_df = pd.concat([df, new_df])
        if to_database:
            filepath = get_filepath('factors/additional_factors.csv')
            combined_df.to_csv(filepath, index=False)
    else:
        combined_df = df.copy(deep=True)
        new_df = None

    return combined_df, new_df
