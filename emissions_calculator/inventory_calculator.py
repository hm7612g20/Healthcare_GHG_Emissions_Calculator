#### IMPORTS ####
import csv
import os
import shutil

from datetime import datetime

import pandas as pd
import numpy as np
import math
import pkg_resources

import searoute as sr
from geopy.geocoders import Nominatim

import streamlit as st


#### READ STORED DATA ####
def get_filepath(filename):
    '''Returns filepath in package given filename.'''
    filepath = pkg_resources.resource_filename('emissions_calculator',
                                               filename)
    
    return filepath

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


#### USED FOR EXTRACTING CORRECT DATA ####
def find_closest_year(data, year, need_cc=False):
    '''
    Finds closest year in factors file to when the product was made if there
    is not an exact match so most accurate estimate can be made.

    Parameters:
    -----------
    data: pd.Series or pd.DataFrame
        Extract of factors dataframe containing relevant emissions factors for
        given component.
    year: str
        Year to use for factor.
    need_cc: bool, optional (default=False)
        False if you want to extract the factor in kg CO2e, True if want to
        extract the carbon content.

    Returns:
    --------
    val: float
        Either carbon factor in kg CO2e or carbon content.
    '''
    smallest = 1000
    closest_yr = 1000
    # Used to find all years stored in database
    for yr, vals in data.iterrows():
        year = int(year)
        yr = int(yr)
        # Finds difference between that year and the year the product was made
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

def extract_best_factor(factors, comp, loc, year, need_cc, country,
                        prod, searched_all):
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
    country: str
        Name of country where component made.
    prod: str
        Name of product.
    searched_all: bool
        If country is selected but specific factor not available, it then
        searches based on whether it is made in Europe or the rest of the
        world so tries again. Then it tries world. If cannot find information,
        it prints out an error message.
    
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
                rer_countries, row_countries = read_countries_continents()
                if country.lower() in rer_countries:
                    region = 'europe'
                elif country.lower() in row_countries:
                    region = 'rest of world'
                if not need_cc:
                    st.error(f'''{prod.title()}: No factor available for
                             **{comp.title()}** in {country.title()},
                             {region.title()} or World. 0.0 will be used.''')

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
def manufacture_calc(products, factors, no_comp, dest_city):
    '''
    Calculates emissions for manufacturing the product, given the
    components it is made from.

    Parameters:
    -----------
    products: pd.DataFrame
        Inventory containing products - made up of components, mass, where they 
        are made and where they are transported to, reprocessing if required and
        disposal information.
    factors: pd.DataFrame
        Contains component name, year and location corresponding to carbon factor
        in kg CO2e and carbon content.
    no_comp: int
        Maximum number of components contained in the products file.
    dest_city: str
        Destination of product.

    Returns:
    --------
    manu_emissions: list of lists
        Each nested list contains individual GHG emissions for each component
        the product is made from.
    total_manu_emissions: list
        Sum of all individual components to give total GHG emissions for each
        product in the inventory.
    '''
    rer_countries, row_countries = read_countries_continents()

    # Calculates emissions corresponding to making specific products
    manu_emissions = []
    total_manu_emissions = []
    
    # Loops through all items in the products data frame
    for index, row in products.iterrows():
        prod_em = [] # Stores per use emissions for each component
        prod = str(row['product'])

        for i in range(no_comp): # Loops through components of product
            comp = str(row['component_' + str(i+1)]) # Finds name of component
            # Finds year and location of manufacture
            year = row['manu_year_' + str(i+1)]
            manu_loc = str(row['manu_loc_' + str(i+1)])
    
            #found = False # Used to check if relevant information found
            if comp != '0':
                if manu_loc == '0':
                    manu_loc = dest_city + '(united kingdom)'
                # Finds country where component made
                loc = manu_loc[manu_loc.find('(')+1:manu_loc.find(')')]
                country = manu_loc[manu_loc.find('(')+1:manu_loc.find(')')]
                
                # Tries to find the best factor for provided information
                need_cc = False
                fact, found = extract_best_factor(factors, comp, loc, year,
                                                  need_cc, country, prod,
                                                  searched_all=False)

                if fact is None:
                    # If not found, loc not listed in file but can change
                    # specific country to Europe or Rest of World
                    if loc.lower() in rer_countries:
                        loc = 'rer'
                    elif loc.lower() in row_countries:
                        loc = 'row'
                    else:
                        st.error(f'Error: **{loc.capitalize()}** not a valid '
                                 f'country.')
                        break
                    fact, found = extract_best_factor(factors, comp, loc,
                                                      year, need_cc, country,
                                                      prod,
                                                      searched_all=False)
                    if fact is None:
                        # If still not found, tries world
                        loc = 'world'
                        fact, found = extract_best_factor(factors, comp, loc,
                                                          year, need_cc,
                                                          country, prod,
                                                          searched_all=True)

            # Stops calculation if no component listed
            else:
                break
    
            # Stops calculation if relevant factor not found in file
            if not found:
                break
    
            mass = row['mass_kg_' + str(i+1)] # Finds mass of material
            no_uses = row['no_uses_' + str(i+1)] # Finds number of uses

            # Per use emission = factor x (mass / no. uses)
            em = fact * (float(mass) / float(no_uses))
    
            # Adds emissions to list for specific item
            prod_em.append(em)
    
        # Adds emission lists to list containing emissions for all products
        manu_emissions.append(prod_em)
        # Adds total emission for making that product to list
        total_manu_emissions.append(sum(prod_em))

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
            # If not in data frame, it is not in travel file so calculate
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
            st.error(f'*Could not find ports: {start_port} and/or '
                     f'{end_port}.*')

    return sea_dist_km

def calc_travel_emissions(travel_dist, start, end, sea, no_uses, mass,
                          travel_fact, prod):
    '''
    Calculates emissions for section of journey to end destination.
    Corresponds to either: travel from start location to port, travel
    between ports, or travel from port to destination.

    Parameters:
    -----------
    travel_dist: pd.DataFrame
        Containing distance (km) between 2 locations.
    start: str
        Start location of journey.
    end: str
        End location of journey.
    sea: int, 0 or 1.
        0 if land travel, 1 if sea travel.
    no_uses: int
        Number of uses of component.
    mass: float
        Mass of component.
    travel_fact: float
        Emissions factor for travel (land or sea).
    prod: str
        Name of product.

    Returns:
    --------
    ghg_em_pu: float
        Greenhouse gas emissions per use for that journey if available.
    '''
    if start != '0':
        # Calculates or extracts sea travel distance
        if sea == 1:
            dist_km = calc_sea_distance(travel_dist, start, end)

        elif sea == 0:
            try: # Extracts distance travelled if in dataframe
                #dist_df = travel_dist.at[(start, end), 'distance_km']
                dist_df = travel_dist.loc[(start, end), 'distance_km']
                try:
                    dist_km = dist_df.to_list()[0]
                except AttributeError:
                    dist_km = dist_df
            except KeyError:
                # If not in data frame, not in travel file - prints out name
                st.error(f'''Journey from {start} to {end} not listed in file
                             - product: {prod}.''')
                dist_km = 0.0

        # Uses this to calculate travel emissions
        ghg_em = (mass * dist_km * travel_fact) / 1000 # Factor is in tonne km
        ghg_em_pu = ghg_em / no_uses
    else:
        ghg_em_pu = 0.0

    return ghg_em_pu

def travel_calc(products, no_comp, additional_factors, dest_city,
                land_travel_dist, sea_travel_dist):
    '''
    Calculates emissions for transporting the components of the product, from
    the start location to port (land travel), then port to port (sea travel),
    the port to end location (land travel).

    Parameters:
    -----------
    products: pd.DataFrame
        Inventory containing products - made up of components, mass, where 
        they are made and where they are transported to, reprocessing if
        required and disposal information.
    no_comp: int
        Maximum number of components contained in the products file.
    additional_factors: pd.DataFrame
        Contains water, electricity and gas emissions factors.
    dest_city: str
        Location of hospital to transport to.

    Returns:
    --------
    travel_emissions: list of lists
        Each nested list contains individual GHG emissions for each component
        the product is made from.
    total_travel_emissions: list
        Sum of all individual components to give total GHG emissions for each
        product in the inventory.
    '''
    #land_travel_dist, sea_travel_dist = read_travel_dist()
    # Calculates emissions corresponding to travel
    travel_emissions = []
    total_travel_emissions = []
    count = 0
    # Loops through all items in the products data frame
    for index, row in products.iterrows():
        travel_em = [] # Travel emissions
        count += 1

        prod_name = row['product']
        for i in range(no_comp): # Loops through components
            obj_travel_em = 0

            # Start at manufacture location
            manu_loc = str(row['manu_loc_' + str(i+1)])
            dest_loc = str(dest_city) + ' (united kingdom)'
            comp = str(row['component_' + str(i+1)]) # Finds name of component

            if comp != '0':
                # If process, then no travel needed
                if manu_loc != '0' and manu_loc != dest_loc:
                    # Start of sea travel
                    debark_port = str(row['debark_port_' + str(i+1)])
                    # Start of travel in UK
                    depart_loc_uk = str(row['depart_loc_uk_' + str(i+1)])
        
                    mass = row['mass_kg_' + str(i+1)] # Mass of component
                    no_uses = row['no_uses_' + str(i+1)] # Number of uses
                    year = row['manu_year_' + str(i+1)] # Year of manufacture
    
                    (land_travel_fact,
                        sea_travel_fact) = read_travel_fact(
                            additional_factors, year)
    
                    # Emissions from land travel to start port if required
                    if manu_loc != debark_port and debark_port != '0':
                        ghg_em = calc_travel_emissions(land_travel_dist,
                                                       manu_loc, debark_port,
                                                       0, no_uses,
                                                       mass, land_travel_fact,
                                                       prod_name)
                        obj_travel_em += ghg_em
        
                    # Emissions from sea travel between ports
                    if debark_port != depart_loc_uk and debark_port != '0' \
                        and depart_loc_uk != '0':
                            city2 = depart_loc_uk + ' (united kingdom)'
                            ghg_em = calc_travel_emissions(sea_travel_dist,
                                                           debark_port, city2,
                                                           1, no_uses, mass,
                                                           sea_travel_fact,
                                                           prod_name)
                            obj_travel_em += ghg_em
    
                    # Emissions to make point if no sea travel
                    if debark_port == '0' and manu_loc != depart_loc_uk and \
                        depart_loc_uk != '0':
                        city2 = depart_loc_uk + ' (united kingdom)'
                        ghg_em = calc_travel_emissions(land_travel_dist,
                                                       manu_loc, city2, 0,
                                                       no_uses, mass,
                                                       land_travel_fact,
                                                       prod_name)
                        obj_travel_em += ghg_em
                
            travel_em.append(obj_travel_em)
    
        # Adds emissions to list for specific 
        travel_emissions.append(travel_em)
        total_travel_emissions.append(sum(travel_em))

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

def product_use_calc(products, no_comp, additional_factors, product_year):
    '''
    Calculates emissions corresponding to water, gas and electricity
    use during product lifetime.

    Parameters:
    -----------
    products: pd.DataFrame
        Inventory containing products - made up of components, mass, where 
        they are made and where they are transported to, reprocessing if
        required and disposal information.
    no_comp: int
        Maximum number of components contained in the products file.
    additional_factors: pd.DataFrame
        Contains water, electricity and gas emissions factors.
    product_year: int
        Year to use to extract factors from.

    Returns:
    --------
    use_emissions: list
        Kg CO2e corresponding to water/electricity/gas use over
        the products lifetimes.
    '''
    # Extracts emissions factors for use
    # Water = treatment and supply
    # Electricity = generation, transmission & distribution (incl. WTT)
    # Gas = gas as fuel (incl. WTT)
    (wt_fact, ws_fact, eg_fact, etd_fact, eg_wtt_fact, etd_wtt_fact,
     gas_fact, gas_wtt_fact) = read_use_fact(additional_factors,
                                             product_year)
    
    use_emissions = []

    # Loops through all items in the products data frame
    for index, row in products.iterrows():
        elec = row['electricity']
        water = row['water']
        gas = row['gas']
        name = row['product']
    
        use_em = 0.0
        # Calculates emissions from water use
        if water != 0 and water != '0':
            water = str(water)
            try:
                vol = float(water[water.find('(')+1:water.find(')')])
                use_em += wt_fact * (vol / 1000)
                use_em += ws_fact * (vol / 1000)
            except ValueError:
                st.error(f'Incorrect format for water use for product '
                         f'{name}.')
        # Calculates emissions from electricity use
        if elec != 0 and elec != '0':
            elec = str(elec)
            try:
                power = float(elec[elec.find('(')+1:elec.find(' ')])
                time = float(elec[elec.find(' ')+1:elec.find(')')])
                kwh = (power * time) / 1000
                use_em += eg_fact * kwh
                use_em += etd_fact * kwh
                use_em += eg_wtt_fact * kwh
                use_em += etd_wtt_fact * kwh
            except ValueError:
                st.error(f'Incorrect format for electricity use for '
                         f'product {name}.')
        # Calculates emissions from gas use
        if gas != 0 and gas != '0':
            gas = str(gas)
            try:
                vol = float(gas[gas.find('(')+1:gas.find(')')])
                use_em += gas_fact * vol
                use_em += gas_wtt_fact * vol
            except ValueError:
                st.error(f'Incorrect format for gas use for product {name}.')
    
        use_emissions.append(use_em)

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
    # Extracts emissions factors for use
    # Water = treatment and supply
    # Electricity = generation, transmission & distribution (incl. WTT)
    # Gas = gas as fuel (incl. WTT)
    (wt_fact, ws_fact, eg_fact, etd_fact, eg_wtt_fact, etd_wtt_fact,
     gas_fact, gas_wtt_fact) = read_use_fact(additional_factors, product_year)
    
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

def reprocessing_calc(products, no_comp, additional_factors, product_year,
                      decon_name, decon_units):
    '''
    Calculates emissions for reprocessing the product.

    Parameters:
    -----------
    products: pd.DataFrame
        Inventory containing products - made up of components, mass, where
        they are made and where they are transported to, reprocessing if
        required and disposal information.
    no_comp: int
        Maximum number of components contained in the products file.
    additonal_fact: pd.DataFrame
        Contains emissions factor for laundry reprocessing.
    product_year: int
        Year to use to extract factors from.
    decon_name: str
        Name of type of decontamination unit to use.
    decon_units: dict
        Contains information about water, electricity and gas use of
        each decontamination unit.

    Returns:
    --------
    reprocess_emissions: list
        Reprocessing GHG emissions for each product in the inventory.
    '''
    laundry_fact = read_laundry_fact(additional_factors, product_year)
    decon_fact = decon_emission_calc(decon_name, decon_units,
                                     additional_factors, product_year)
    
    # Calculates emissions corresponding to reprocessing products
    reprocess_emissions = []
    
    # Loops through all items in the products in the data frame
    for index, row in products.iterrows():
        repro_em = 0
        autoclave_req = False
        year = 0
        
        for i in range(no_comp): # Loops through components
            comp = row['component_' + str(i+1)] # Finds name of component
            mass = row['mass_kg_' + str(i+1)] # Finds mass of product/process
            # Finds reprocessing type if applicable
            repro = row['reprocessing_' + str(i+1)]
            
            if repro != 0:
                if repro == 'laundry':
                    repro_em += mass * laundry_fact
                elif 'hsdu' in repro:
                    percent_fill = float(repro[repro.find('(')+1:repro.\
                                         find(')')])
                    autoclave_req = True

        if autoclave_req:
            repro_em += decon_fact * percent_fill
    
        reprocess_emissions.append(repro_em)

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

def disposal_calc(products, factors, no_comp, additional_factors,
                  product_year):
    '''
    Calculates emissions for manufacturing the product, given the
    components it is made from.

    Parameters:
    -----------
    products: pd.DataFrame
        Inventory containing products - made up of components, mass, where 
        they are made and where they are transported to, reprocessing if
        required and disposal information.
    factors: pd.DataFrame
        Contains component name, year and location corresponding to emissions
        factor in kg CO2e and carbon content.
    no_comp: int
        Maximum number of components contained in the products file.
    additonal_factors: pd.DataFrame
        Contains emissions factors for transporting waste and landfill.
    product_year: int
        Year used for disposal factors.

    Returns:
    --------
    incinerate_emissions: list
        Incineration emissions for products.
    recycle_emissions: list
        Recycling emissions for products.
    landfill_emissions: list
        Landfill emissions for products.
    biogenic_carbon: list
        Biogenic carbon component for products.
    net_waste_emissions: list
        Sum of all individual disposal emissions for each component to give
        total GHG emissions for each product in the inventory.
        Calculated as sum of incineration emissions, recycling emissions,
        landfill emissions and biogenic component.
    '''
    # Creates list of all countries in Europe so correct factor used
    rer_countries, row_countries = read_countries_continents()

    # Reads landfill emissions factor
    landfill_fact = read_landfill_fact(additional_factors, product_year)
    # Reads waste transport emissions factor
    transport_fact = read_disposal_fact(additional_factors, product_year)
    
    # Calculates emissions corresponding to disposing of specific products
    incinerate_emissions = []
    recycle_emissions = []
    landfill_emissions = []
    biogenic_carbon = []
    net_waste_emissions = []
    
    # Loops through all items in the products in the data frame
    for index, row in products.iterrows():
        incinerate_c_mass = 0
        mass_for_incinerate = 0
        mass_for_recycle = 0
        mass_for_landfill = 0
        bio = 0

        prod = str(row['product'])
    
        for i in range(no_comp): # Loops through components
            comp = str(row['component_' + str(i+1)]) # Finds name of component
            # Finds year and location of production
            year = row['manu_year_' + str(i+1)]
            manu_loc = str(row['manu_loc_' + str(i+1)])

            # If incinerated or not - 1 if it is or 0 if not
            incinerate = float(row['incinerate_' + str(i+1)])
            # If recycled or not - 1 if it is or 0 if not
            recycle = float(row['recycle_' + str(i+1)])
            # If landfill disposal or not - 1 if it is, 0 if not
            landfill = float(row['landfill_' + str(i+1)])
    
            if (incinerate + recycle + landfill) > 1:
                st.error(f'Error: {comp} disposed of in multiple ways.')
                break

            # Stops calculation if no disposal listed (e.g. process)
            if incinerate == 0 and recycle == 0 and landfill == 0:
                break

            if comp != '0':
                if manu_loc == '0':
                    break
                
                loc = manu_loc[manu_loc.find('(')+1:manu_loc.find(')')]
                country = manu_loc[manu_loc.find('(')+1:manu_loc.find(')')]
                
                # Tries to find best carbon content for provided information
                need_cc = True
                cc, found = extract_best_factor(factors, comp, loc, year,
                                                need_cc, country, prod,
                                                searched_all=False)
    
                if cc is None:
                    # If not found, location may not be listed in file but may
                    # change specific country to Europe or Rest of World
                    if loc.lower() in rer_countries:
                        loc = 'rer'
                    elif loc.lower() in row_countries:
                        loc = 'row'
                    else:
                        st.error(f'Error: {loc} not a valid country.')
                        break
                    cc, found = extract_best_factor(factors, comp, loc, year,
                                                    need_cc, country, prod,
                                                    searched_all=False)

                    if cc is None:
                        # If still not found, tries world
                        loc = 'world'
                        cc, found = extract_best_factor(factors, comp, loc,
                                                        year, need_cc,
                                                        country, prod,
                                                        searched_all=True)
            # Stops calculation if no component listed
            else:
                break

            # Stops calculation if factor not found in file
            if not found:
                break
    
            mass = row['mass_kg_' + str(i+1)] # Mass of product/process
            no_uses = row['no_uses_' + str(i+1)] # Number of uses
    
            # Per use mass = mass / number of uses
            pu_mass = float(mass) / float(no_uses)
    
            # If biogenic component - 0 if not, 1 if it is
            is_biogen = row['biogenic_' + str(i+1)]
    
            # Calculates biogenic = carbon content x mass x (if biogenic)
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
        total_incinerate = incinerate_em + incinerate_transport
    
        # Calculates total recycling emissions = transport emissions
        total_recycle = mass_for_recycle * transport_fact
    
        # Calculates emissions for travel to landfill
        landfill_transport = mass_for_landfill * transport_fact
        # Calculates emissions in landfill
        landfill_em = mass_for_landfill * landfill_fact
        # Calculates total landfill emissions
        total_landfill = landfill_transport + landfill_em
    
        # Calculates biogenic carbon
        biogenic_c = (bio / 12.01) * 44.01
    
        # Adds disposal emissions to list
        incinerate_emissions.append(total_incinerate)
        recycle_emissions.append(total_recycle)
        landfill_emissions.append(total_landfill)
    
        # Adds biogenic carbon to list
        biogenic_carbon.append(biogenic_c)
    
        total = total_incinerate + total_recycle + total_landfill - biogenic_c
        net_waste_emissions.append(total)

    return (incinerate_emissions, recycle_emissions,
            landfill_emissions, biogenic_carbon, net_waste_emissions)


#### TOTAL EMISSIONS CALCULATIONS ####
def total_calc(total_manu_emissions, total_travel_emissions,
               use_emissions, reprocess_emissions, net_waste_emissions):
    '''
    Calculates total emissions for each product.
    Sum of: manufacturing the product, travel of components to end location,
    reprocessing and waste.

    Parameters:
    -----------
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

    Returns:
    --------
    total_emissions: list
        Sum of all GHG emissions for each stage of life to give total for each
        product in the inventory.
    '''
    total_emissions = []

    # Calculates total sum of emissions from manufacture, travel, use,
    # reprocessing and waste
    for (make, transport, use,
         reprocess, disposal) in zip(total_manu_emissions,
                                     total_travel_emissions,
                                     use_emissions,
                                     reprocess_emissions,
                                     net_waste_emissions):
        total = make + transport + use + reprocess + disposal
        total_emissions.append(total)

    return total_emissions

def emissions_calculation(products, factors, no_comp, additional_factors,
                          decon_units, product_year, decon_name):
    '''
    Performs all emissions calculations and outputs the results for each 
    section.

    Parameters:
    -----------
    products: pd.DataFrame
        Inventory containing products - made up of components, mass, where
        they are made and where they are transported to, use, reprocessing if
        required and disposal information.
    factors: pd.DataFrame
        Contains component name, year and location corresponding to emissions
        factors in kg CO2e and carbon content.
    no_comp: int
        Maximum number of components contained in the products file.
    additonal_factors: pd.DataFrame
        Contains carbon factor per kg of laundry and carbon factor for
        transporting waste per kg of waste.
    decon_units: dict
        Contains information about water, electricity and gas use of
        each decontamination unit.
    product_year: int
        Year to extract correct factors from.
    decon_name: str
        Name of type of decontamination unit to use.

    Returns:
    --------
    total_emissions: list
        Sum of all GHG emissions for each stage of life to give total for each
        product in the inventory.
    total_manu_emissions: list
        Total manufacturing GHG emissions for each product in the inventory.
    total_travel_emissions: list
        Total travel GHG emissions for each product in the inventory.
    use_emissions: list
        Total GHG emissions during use for each product in the inventory.
    reprocess_emissions: list
        Total reprocessing GHG emissions for each product in the inventory.
    net_waste_emissions: list
        Total disposal GHG emissions for each product in the inventory.
        Calculated as sum of incineration emissions, recycling emissions,
        landfill emissions and biogenic component.
    '''
    # Manufacturing emissions
    manu_emissions, total_manu_emissions = manufacture_calc(products, factors,
                                                            no_comp)

    # Travel emissions
    (travel_emissions,
     total_travel_emissions) = travel_calc(products, no_comp,
                                           additional_factors)

    # Use emissions
    use_emissions = product_use_calc(products, no_comp, additional_factors,
                                     product_year)
        
    # Reprocessing emissions  
    reprocess_emissions = reprocessing_calc(products, no_comp,
                                            additional_factors,
                                            product_year, decon_name,
                                            decon_units)

    # Disposal emissions
    (incinerate_emissions, recycle_emissions,
     landfill_emissions, biogenic_carbon,
     net_waste_emissions) = disposal_calc(products, factors, no_comp,
                                          additional_factors, product_year)

    # Total emissions
    total_emissions = total_calc(total_manu_emissions,
                                 total_travel_emissions,
                                 use_emissions,
                                 reprocess_emissions,
                                 net_waste_emissions)

    return (total_emissions, total_manu_emissions,
            total_travel_emissions, use_emissions,
            reprocess_emissions, net_waste_emissions)