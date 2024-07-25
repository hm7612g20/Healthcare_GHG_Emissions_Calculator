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


#### READ STORED DATA ####
def get_filepath(filename):
    '''Returns filepath in package given filename.'''
    filepath = pkg_resources.resource_filename(
        'emissions_calculator', filename)

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

    # Creates list of all other countries
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
        if diff < smallest:  # Finds the smallest difference
            if closest_yr == 1000:
                smallest = diff
                closest_yr = yr
            else:  # Only extracts up to and including year of manufacture
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
                        searched_all):
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
    if need_cc:  # Whether to extract carbon content or emissions factor
        fact_name = 'carbon_content'
    else:
        fact_name = 'factor_kgCO2eq_unit'

    found = False  # Used to check if relevant information found

    try:  # Extracts factor if comp in factors df given exact year and loc
        fact_df = factors.loc[(comp, loc, year)][fact_name]
        try:
            fact = fact_df.to_list()[0]
        except AttributeError:
            fact = fact_df
        found = True
    except KeyError:  # If exact data not listed in dataframe, stops crash
        # Extracts part of df with same component and loc if available
        fact_df = factors.loc[(factors.index.get_level_values('component')
                               == comp) & (factors.index.
                                           get_level_values('loc') == loc)]

        # If not exact year listed, finds closest given years available
        if len(fact_df) > 0:
            fact_df.index = fact_df.index.get_level_values('year')
            fact = find_closest_year(fact_df, year, need_cc=need_cc)
            found = True
        else:  # Returns None if factor not found given information
            fact = None
            # Prints out error message if location not available
            if searched_all:
                rer_countries, row_countries = read_countries_continents()
                if country.lower() in rer_countries:
                    region = 'europe'
                elif country.lower() in row_countries:
                    region = 'rest of world'
                if not need_cc:
                    st.error(f'''No factor available for
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
    try:  # Uses closest year in file if file not available
        fact = additional_factors.loc[(name, unit,
                                       year)]['factor_kgCO2eq_unit']
    except KeyError:  # Uses closest year in file if exact not available
        fact_df = additional_factors.loc[(additional_factors.index.
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

    for i in range(no_comp):  # Loops through components of product
        comp = product['component_' + str(i+1)]  # Name of component
        year = product['manu_year_' + str(i+1)]  # Year of manufacture
        manu_loc = str(product['manu_loc_' + str(i+1)])  # Loc of manufacture

        need_cc = False

        if manu_loc == '0':  # Assumes made in destination city
            manu_loc = dest_city + '(united kingdom)'
        # Finds country and city where component made
        loc = manu_loc[manu_loc.find('(')+1:manu_loc.find(')')]
        country = manu_loc[manu_loc.find('(')+1:manu_loc.find(')')]

        # Tries to find the best factor for provided information
        fact, found = extract_best_factor(
            factors, comp, loc, year, need_cc, country, searched_all=False)

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
            fact, found = extract_best_factor(
                factors, comp, loc, year, need_cc, country,
                searched_all=False)

            if fact is None:
                # If still not found, tries world
                loc = 'world'
                fact, found = extract_best_factor(
                    factors, comp, loc, year, need_cc, country,
                    searched_all=True)

        if not found:  # Stops calculation if relevant factor not found
            break

        # Finds mass of material
        mass = product['mass_kg_' + str(i+1)]  # Mass of material
        no_uses = product['no_uses_' + str(i+1)]  # Number of uses

        # Per use emission = factor x (mass / no. uses)
        em = fact * (float(mass) / float(no_uses))

        # Adds emissions to list for specific item
        manu_emissions.append(em)

    total_manu_emissions = float(sum(manu_emissions))

    return manu_emissions, total_manu_emissions


#### TRVAEL EMISSIONS CALCULATION ####
def read_travel_fact(additional_factors, year):
    '''Reads travel emissions factors from file.'''
    land_fact = extract_best_factor_ex(
        additional_factors, 'hgv transport', 'km', year)
    wtt_land_fact = extract_best_factor_ex(
        additional_factors, 'hgv transport wtt', 'km', year)
    sea_fact = extract_best_factor_ex(
        additional_factors, 'container ship transport', 'km', year)
    wtt_sea_fact = extract_best_factor_ex(
        additional_factors, 'container ship transport wtt', 'km', year)

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
    try:  # Extracts distance travelled if in dataframe
        sea_dist_df = sea_travel_dist.loc[(start_port, end_port),
                                          'distance_km']
        try:
            sea_dist_km = sea_dist_df.to_list()[0]
        except AttributeError:
            sea_dist_km = sea_dist_df
    except KeyError:  # If not in df, not in travel file so value calculated
        try:
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
        Distance travelled in km.
    no_uses: int
        Number of uses of component.
    mass: float
        Mass of component.
    travel_fact: float
        Emissions factor for land or sea travel.

    Returns:
    --------
    ghg_em: float
        Greenhouse gas emissions per use for that journey if available.
    '''
    # Travel emissions = mass * km * (kg CO2 per km) / no. uses
    # /1000 as factor is in tonne km
    ghg_em = (mass * dist_km * (travel_fact / 1000)) / no_uses

    return ghg_em


def travel_calc(product, no_comp, additional_factors):
    '''
    Calculates emissions for transporting the components of the product, from
    the start location to port (land travel), then port to port (sea travel),
    the port to end location (land travel).

    Parameters:
    -----------
    product: pd.Series
        Contains product information - made up of components, mass, where they
        and are made and where they are transported to, reprocessing if
        required disposal information.
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

    for i in range(no_comp):  # Loops through components
        travel_em = 0.0

        start = product['manu_loc_' + str(i+1)]  # Start at manufacture loc

        if start != '0' and start is not None:  # Stops calc if process
            comp = product['component_' + str(i+1)]  # Name of component
            mass = product['mass_kg_' + str(i+1)]  # Mass of component
            no_uses = product['no_uses_' + str(i+1)]  # Number of uses
            year = product['manu_year_' + str(i+1)]  # Year of manufacture

            land_travel_fact, \
                sea_travel_fact = read_travel_fact(additional_factors, year)

            land_dist_km = product['land_dist_' + str(i+1)]  # Land distance
            sea_dist_km = product['sea_dist_' + str(i+1)]  # Sea distance

            # Emissions from land travel
            if land_dist_km > 0.0:
                ghg_em = calc_travel_emissions(
                    land_dist_km, no_uses, mass, land_travel_fact)
                travel_em += ghg_em

            # Emissions from sea travel
            if sea_dist_km > 0.0:
                ghg_em = calc_travel_emissions(
                    sea_dist_km, no_uses, mass, sea_travel_fact)
                travel_em += ghg_em

        # Adds emissions to list for specific comp
        travel_emissions.append(travel_em)

    total_travel_emissions = sum(travel_emissions)  # Finds total

    return travel_emissions, total_travel_emissions


#### USE EMISSIONS CALCULATION ####
def read_use_fact(additional_factors, year):
    '''Reads electricity/water/gas emissions factors from file.'''
    wt_fact = extract_best_factor_ex(
        additional_factors, 'water treatment', 'm3', year)
    ws_fact = extract_best_factor_ex(
        additional_factors, 'water supply', 'm3', year)

    eg_fact = extract_best_factor_ex(
        additional_factors, 'electricity generation', 'kwh', year)
    etd_fact = extract_best_factor_ex(
        additional_factors, 'electricity t&d', 'kwh', year)
    eg_wtt_fact = extract_best_factor_ex(
        additional_factors, 'electricity generation wtt', 'kwh', year)
    etd_wtt_fact = extract_best_factor_ex(
        additional_factors, 'electricity t&d wtt', 'kwh', year)

    gas_fact = extract_best_factor_ex(
        additional_factors, 'gas', 'm3', year)
    gas_wtt_fact = extract_best_factor_ex(
        additional_factors, 'gas wtt', 'm3', year)

    water_factor = wt_fact + ws_fact
    elec_factor = eg_fact + etd_fact + eg_wtt_fact + etd_wtt_fact
    gas_factor = gas_fact + gas_wtt_fact

    return water_factor, elec_factor, gas_factor


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
    water_factor, elec_factor, gas_factor = read_use_fact(
        additional_factors, year)

    use_emissions = 0.0
    # Calculates emissions from water use
    if water_vol_per_use is not None:
        use_emissions += water_factor * (water_vol_per_use / 1000)
    # Calculates emissions from electricity use
    elif power_rating is not None and time_per_use is not None:
        kwh = (power_rating * time_per_use) / 1000
        use_emissions += elec_factor * kwh
    # Calculates emissions from gas use
    elif gas_per_use is not None:
        use_emissions += gas_factor * gas_per_use

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
    water_factor, elec_factor, gas_factor = read_use_fact(
        additional_factors, product_year)

    water_kg_co2e = water_factor * 0.001 * decon_units[name + ' water']
    elec_kg_co2e = elec_factor * decon_units[name + ' electricity']
    gas_kg_co2e = gas_factor * decon_units[name + ' gas']

    decon_fact = water_kg_co2e + elec_kg_co2e + gas_kg_co2e

    return decon_fact


def read_laundry_fact(additional_factors, year):
    '''Reads laundry emissions factors from file.'''
    laundry_fact = extract_best_factor_ex(
        additional_factors, 'laundry', 'kg', year)

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

    for i in range(no_comp):  # Loops through components
        comp = product['component_' + str(i+1)]  # Name of component
        mass = product['mass_kg_' + str(i+1)]  # Mass of product/process
        repro = product['reprocessing_' + str(i+1)]  # Repro type

        if repro is not None:
            if repro == 'laundry':
                reprocess_emissions += mass * laundry_fact
            elif 'hsdu' in repro:
                if not found_percent_fill:
                    # Extracts % fill from repro info
                    percent_fill = float(repro[repro.find('(')+1:
                                         repro.find(')')])
                    found_percent_fill = True
                autoclave_req = True

    if autoclave_req:  # Calculates emissions from HSDU
        reprocess_emissions += decon_fact * (percent_fill / 100)

    return reprocess_emissions


#### DISPOSAL EMISSIONS CALCULATION ####
def read_landfill_fact(additional_factors, year):
    '''Reads landfill emissions factors from file.'''
    landfill_fact = extract_best_factor_ex(
        additional_factors, 'landfill', 'kg', year)

    return landfill_fact


def read_disposal_fact(additional_factors, year):
    '''Reads disposal travel emissions factors from file.'''
    disposal_fact = extract_best_factor_ex(
        additional_factors, 'disposal transport', 'km', year)

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
    # Creates list of all countries in Europe so correct factor used
    rer_countries, row_countries = read_countries_continents()

    bio = 0.0
    incinerate_c_mass = 0.0
    mass_for_incinerate = 0.0
    mass_for_recycle = 0.0
    mass_for_landfill = 0.0

    # Calculates emissions corresponding to disposing of specific products
    for i in range(no_comp):  # Loops through components
        comp = str(product['component_' + str(i+1)])  # Name of component
        year = product['manu_year_' + str(i+1)]  # Year of manufacture
        manu_loc = str(product['manu_loc_' + str(i+1)])  # Loc of manufacture

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
            # Extracts name of location and country
            loc = manu_loc[manu_loc.find('(')+1:manu_loc.find(')')]
            country = manu_loc[manu_loc.find('(')+1:manu_loc.find(')')]

            # Tries to find the best carbon content for provided information
            need_cc = True
            cc, found = extract_best_factor(factors, comp, loc, year, need_cc,
                                            country, searched_all=False)

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
                cc, found = extract_best_factor(
                    factors, comp, loc, year, need_cc, country,
                    searched_all=False)

                if cc is None:
                    # If still not found, tries world
                    loc = 'world'
                    cc, found = extract_best_factor(
                        factors, comp, loc, year, need_cc, country,
                        searched_all=True)

        else:  # Stops calculation if no component listed
            break

        if not found:  # Stops calculation if relevant factor not found
            break

        mass = product['mass_kg_' + str(i+1)]  # Mass of product
        no_uses = product['no_uses_' + str(i+1)]  # Number of uses

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

    # Calculates CO2e emissions from incineration = CO2 generated
    # C Mass / C Mr = Mol * CO2 Mr = Mass CO2
    incinerate_em = (incinerate_c_mass / 12.01) * 44.01
    # Transport emissions = mass * transport factor
    incinerate_transport = mass_for_incinerate * transport_fact
    # Calculates total incineration emissions
    incinerate_emissions = incinerate_em + incinerate_transport

    # Calculates total recycling emissions = transport emissions
    # Transport emissions = mass * transport factor
    recycle_emissions = mass_for_recycle * transport_fact

    # Transport emissions = mass * transport factor
    landfill_transport = mass_for_landfill * transport_fact
    # Landfill emissions = mass * landfill emissions factor
    landfill_em = mass_for_landfill * landfill_fact
    # Calculates total landfill emissions
    landfill_emissions = landfill_transport + landfill_em

    # Calculates biogenic carbon = contained carbon
    biogenic_carbon = (bio / 12.01) * 44.01

    net_waste_emissions = incinerate_emissions + recycle_emissions + \
                          landfill_emissions - biogenic_carbon

    return (incinerate_emissions, recycle_emissions, landfill_emissions,
            biogenic_carbon, net_waste_emissions)
