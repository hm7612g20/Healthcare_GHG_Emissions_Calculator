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


#### UPDATE DATABASE FROM INVENTORY CALCULATOR ####
def archive_local_emissions(products, total_manu_emissions,
                            total_travel_emissions, use_emissions,
                            reprocess_emissions, net_waste_emissions,
                            total_emissions, own_file):
    '''
    Updates emissions file given new calculations and archives the old one.

    Parameters:
    -----------
    products: pd.DataFrame
        Inventory containing products - made up of components, mass, where
        they are made and where they are transported to, reprocessing if
        required and disposal information.
    total_manu_emissions: list
        Total manufacturing GHG emissions for each product in the inventory.
    total_travel_emissions: list
        Total travel GHG emissions for each product in the inventory.
    use_emissions: list
        Total GHG emissions during use for each product in the inventory.
    reprocess_emissions: list
        Total reprocessing GHG emissions for each product in the inventory.
    net_waste_emissions: list
        Net waste GHG emissions for each product in the inventory.
    total_emissions: list
        Sum of all GHG emissions for each stage of life to give total for each
        product in the inventory.
    own_file: bool
        If it is a new file that should be added to end of other file.

    Returns:
    --------
    None.
    '''
    # Creates new df containing this info to be output to emissions csv file
    product_emissions = products.copy()

    product_emissions['manufacture_emissions'] = total_manu_emissions
    product_emissions['transport_emissions'] = total_travel_emissions
    product_emissions['use_emissions'] = use_emissions
    product_emissions['reprocessing_emissions'] = reprocess_emissions
    product_emissions['disposal_emissions'] = net_waste_emissions
    product_emissions['total_emissions'] = total_emissions

    now = datetime.now()  # Current date and time
    date_time = now.strftime("%Y-%m-%d_%H-%M-%S")  # Formatted string

    filepath = get_filepath('inventory/emissions.csv')

    # Archives current emissions file using date and time
    if os.path.isfile(filepath):
        # Exports as new csv file to archive folder
        filename = 'emissions_' + date_time + '.csv'
        filepath_arch = get_filepath(
            'inventory/emissions_archive/' + filename)
        shutil.copyfile(filepath, filepath_arch)

    if own_file:
        # Joins old and new database if it is a new file
        old_emissions = pd.read_csv(filepath)
        product_emissions = pd.concat([old_emissions, product_emissions])

    # Creates new .csv file with emissions
    product_emissions.to_csv(filepath, index=False)

    return


#### ADD NEW DECONTAMINATION UNIT ####
def add_new_decon_to_file(name, elec, water, gas):
    filepath = get_filepath(f'data/decon_units.csv')

    if os.path.isfile(filepath):
        with open(filepath, 'r') as f:
            rows = []
            for ind, line in enumerate(f):
                ln = line.rstrip('\n')
                wd = ln.split(',')
                if ind == 0:
                    header = wd
                elif ind > 0:
                    rows.append(wd)

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


#### SAVE PRODUCT TO DATABASE FROM PRODUCT CALCULATOR ####
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


def update_local_database(data, name):
    '''Updates saved database file and archives previous version.'''
    now = datetime.now()  # Current date and time
    date_time = now.strftime("%Y-%m-%d_%H-%M-%S")  # Formatted string

    filepath = get_filepath(f'inventory/{name}.csv')

    # Archives current file using date and time
    if os.path.isfile(filepath):
        # Exports as new csv file to archive folder
        filename = f'{name}_' + date_time + '.csv'
        filepath_arch = get_filepath(
            f'inventory/{name}_archive/' + filename)
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
            product_comp.extend(to_add)  # Extends new row to match
        product = product_info + product_comp
        data.append(product)

    # If old data shorter, need to extend original file to fit new
    elif new_no_comp > large_no_comp:
        new_data = []
        for ind, d in enumerate(data):
            # Finds number of comps not contained so can be replaced with 0s
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


def update_local_inventory(product_info):
    '''
    Updates emissions file given new calculations and archieves the old one.

    Parameters:
    -----------
    product_info: pd.Series
        Contains product information - made up of components, mass, where they
        are made and where they are transported to, reprocessing if required
        and disposal information.

    Returns:
    --------
    None.
    '''
    filepath = get_filepath(f'inventory/products.csv')

    if os.path.isfile(filepath):
        header, data = read_csv_file(filepath)
        new_data, new_header = lengthen_shorten_inventory_data(
            product_info, data, header)
        products = pd.DataFrame(new_data, columns=new_header)

        # Creates new .csv file with emissions
        update_local_database(products, 'products')
    else:
        products = None
        st.error('Cannot update product database.')

    return


def update_inventory(product_info, products):
    '''
    Updates emissions file given new calculations and archieves the old one.

    Parameters:
    -----------
    product_info: pd.Series
        Contains product information - made up of components, mass, where they
        are made and where they are transported to, reprocessing if required
        and disposal information.
    products: pd.DataFrame
        Current product database

    Returns:
    --------
    None.
    '''
    header = products.columns.to_list()
    data = products.values.tolist()

    new_data, new_header = lengthen_shorten_inventory_data(
        product_info, data, header)
    products = pd.DataFrame(new_data, columns=new_header)

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
            product_comp.extend(to_add)  # Extends new row to match
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
            # Finds number of comps not contained so can be replaced with 0s
            for i in range(new_no_comp - large_no_comp):
                # Extends all current lists in file to match size of new data
                to_add = ['0' for j in range(12)]
                other.extend(to_add)
                if ind == 0:
                    # Creates new headers corresponding to new information
                    comp_header = write_new_header(
                        comp_header, large_no_comp, i)

            other.extend(emissions_data)
            new_data.append(other)

        header = comp_header + emissions_header
        data = new_data
        product = product_info + product_comp + emissions_product
        data.append(product)

    return data, header, product_data


def update_local_emissions(product_info):
    '''
    Updates emissions file given new calculations and archieves the old one.

    Parameters:
    -----------
    product_info: pd.Series
        Contains product information - made up of components, mass, where they
        are made and where they are transported to, reprocessing if required
        and disposal information.

    Returns:
    --------
    None.
    '''
    filepath = get_filepath(f'inventory/emissions.csv')

    if os.path.isfile(filepath):
        header, data = read_csv_file(filepath)
        (new_data, new_header,
         product_data) = lengthen_shorten_emissions_data(
             product_info, data, header)
        emissions = pd.DataFrame(new_data, columns=new_header)

        # Creates new .csv file with emissions
        update_local_database(emissions, 'emissions')
    else:
        emissions = None
        st.error('Cannot update emissions database.')

    return


def update_emissions(product_info, emissions):
    '''
    Updates emissions file given new calculations and archieves the old one.

    Parameters:
    -----------
    product_info: pd.Series
        Contains product information - made up of components, mass, where they
        are made and where they are transported to, reprocessing if required
        and disposal information.
    emissions: pd.DataFrame
        Current product emissions database.

    Returns:
    --------
    None.
    '''
    header = emissions.columns.to_list()
    data = emissions.values.tolist()
    (new_data, new_header,
     product_data) = lengthen_shorten_emissions_data(
         product_info, data, header)

    emissions = pd.DataFrame(new_data, columns=new_header)
    product = pd.DataFrame([product_data], columns=new_header)

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
    # Factors data filepath
    factors_filepath = get_filepath(f'factors/factors.csv')

    # Checks that file exists in location
    if os.path.isfile(factors_filepath):
        old_factors = pd.read_csv(factors_filepath)
        new_factors = pd.concat([old_factors, factors])
        new_factors.to_csv(factors_filepath, index=False)

    return


#### UPDATES TRAVEL DISTANCES WITH INPUT ####
def update_travel_distances(start, end, distance, sea=False):
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

def update_travel_distances_from_df(df, sea=False):
    '''
    Adds new travel distance file to csv.

    Parameters:
    -----------
    df: pd.DataFrame
        Contains new travel distances as a df.
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

    # Checks that file exists in location
    if os.path.isfile(filepath):
        old_dist = pd.read_csv(filepath)
        new_dist = pd.concat([old_dist, df])
        new_dist.to_csv(filepath, index=False)

    return
