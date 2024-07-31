#### IMPORTS ####
import streamlit as st
import pandas as pd
import sys
from importlib import resources as impresources
import os

from datetime import datetime

import plotly.express as px
import plotly.graph_objects as go

# Local package for calculations and data access
from emissions_calculator import product_calculator as calc
from emissions_calculator import read_data
from emissions_calculator import update_files as update
from emissions_calculator import read_upload


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
    '''Checks that data has successfully been read in, else exits program.'''
    if data is None:
        exit_program()


def is_cloud():
    '''Extracts if program is running on Streamlit cloud.'''
    cloud = False
    for i in os.environ:
        if i == 'HOSTNAME':
            cloud = True

    return cloud


#### ADDITIONAL TRAVEL CALCULATIONS ####
def travel_end_loc(selected, dest_city, no_comp, additional_factors,
                   land_travel_dist, cloud, key=0, from_database=False):
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
    dest_city = str(dest_city)

    for i in range(no_comp):  # Loops through all components
        # Relevant product information selected
        if from_database:
            mass = selected['mass_kg_' + str(i+1)].iloc[0]  # Mass of comp
            no_uses = selected['no_uses_' + str(i+1)].iloc[0]  # No. of uses
            year = selected['manu_year_' + str(i+1)].iloc[0]  # Year
            # Location where component begins journey in UK
            depart_loc_uk = str(selected['depart_loc_uk_' + str(i+1)].iloc[0])
        else:
            mass = selected['mass_kg_' + str(i+1)]
            no_uses = selected['no_uses_' + str(i+1)]
            year = selected['manu_year_' + str(i+1)]
            depart_loc_uk = str(selected['depart_loc_uk_' + str(i+1)])

        if depart_loc_uk != dest_city and depart_loc_uk != '0':
            # Reads travel factors
            travel_fact, _ = calc.read_travel_fact(
                additional_factors, year)

            # Sets up format for reading file
            city1 = depart_loc_uk + ' (united kingdom)'
            city2 = dest_city + ' (united kingdom)'

            try:  # Extracts distance travelled if in dataframe
                dist_km = land_travel_dist.at[(city1, city2), 'distance_km']
            except KeyError:  # If not in df, user inputs value
                city1_name = depart_loc_uk.title()
                city2_name = dest_city.title()
                dist_km = st.number_input(
                    f'''Input travel distance between {city1_name} and
                    {city2_name}''', min_value=0.0, step=1.0,
                    format='%0.3f', key=f'end_travel_{key}')

                # Adds new info to df to prevent repeats
                if dist_km > 0.0:
                    land_travel_dist.loc[(city1, city2),
                                         ['distance_km']] = [dist_km]

                    if not cloud:  # Updates file if available
                        update.update_travel_distances(
                            city1, city2, dist_km)
                else:
                    break

            travel_emissions += calc.calc_travel_emissions(
                dist_km, no_uses, mass, travel_fact)

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
    end_travel = travel_end_loc(
        selected, dest_city, no_comp, additional_factors, land_travel_dist,
        cloud, from_database=True)
    selected['transport_emissions'] = end_travel + travel
    # Saves with transport emissions added
    original_selected_df = selected.copy(deep=True)

    selected.index.names = ['Product']
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

    # Filters emissions only
    emissions = selected.filter(items=filter_items)
    # Renames columns
    emissions.rename(columns=col_names, inplace=True)

    for i in range(no_comp):
        # Stops searching if no more components
        if str(selected['component_' + str(i+1)].iloc[0]) == '0':
            break
        # Additional filters are component names, product location and year
        filter_items.append(f'component_{i+1}')
        filter_items.append(f'no_uses_{i+1}')
        filter_items.append(f'manu_loc_{i+1}')

        # Capitalises strings in these columns
        selected['component_' + str(i+1)] = selected['component_' + str(i+1)]\
            .str.title()
        try:
            selected['manu_loc_' + str(i+1)] = selected['manu_loc_' +
                                                        str(i+1)].str.title()
        except AttributeError:
            selected['manu_loc_' + str(i+1)] = f'''{dest_city.title()}
                                                   (United Kingdom)'''

        # Used to rename columns
        col_names['component_' + str(i+1)] = 'Component/Process ' + str(i+1)
        col_names['no_uses_' + str(i+1)] = 'Number of Uses ' + str(i+1)
        col_names['manu_loc_' + str(i+1)] = 'Manufacture Location ' + str(i+1)
        col_names['manu_year_' + str(i+1)] = 'Manufacture Year ' + str(i+1)

        # Removes commas from dates
        selected = selected.map(format_integer_without_commas)
        filter_items.append(f'manu_year_{i+1}')

    # Filters to only show specific columns
    data = selected.filter(items=filter_items)
    # Renames columns
    data.rename(columns=col_names, inplace=True)

    # Adds trailing 0s to columns
    if data['Use / kg CO2e'].iloc[0] == '0':
        data['Use / kg CO2e'] = data['Use / kg CO2e'].astype(float)\
            .map('{:.1f}'.format)

    # Capitalises product names
    data.index = data.index.str.title()
    # Rounds values then converts all to strings
    data = data.round(decimals=6).astype(str)

    # Displays dataframe
    st.dataframe(data.T)

    return original_selected_df, emissions


def select_autofill(selected_prod, product_categories, available_factor,
                    dest_city, cities_list, ports_list, uk_locations):
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
    dest_city: str
        Destination of product.
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

    # Saves autofill information
    selected_auto['no_comp'] = no_comp
    cat = selected_prod['category'].iloc[0].title()
    selected_auto['cat'] = product_categories.index(cat)
    selected_auto['no_uses'] = selected_prod['no_uses_1'].iloc[0]
    selected_auto['elec'] = str(selected_prod['electricity'].iloc[0])
    selected_auto['water'] = str(selected_prod['water'].iloc[0])
    selected_auto['gas'] = str(selected_prod['gas'].iloc[0])

    for i in range(no_comp):
        comp = selected_prod['component_' + str(i+1)].iloc[0].title()
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

        dc = dest_city.title() + ' (United Kingdom)'
        loc = str(selected_prod['manu_loc_' + str(i+1)].iloc[0])
        selected_auto['loc_' + str(i+1)] = cities_list.index(dc) if \
            loc == '0' else cities_list.index(loc.title())

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
    # Creates title and x-axis labels
    if comp:
        name = ['Original Product', 'New Product']
        title = f'Emissions Comparison: {prod_name.title()}'

        # Takes dataframe and converts information to lists
        make = data['Manufacturing / kg CO2e'].to_list()
        travel = data['Transport / kg CO2e'].to_list()
        use = data['Use / kg CO2e'].to_list()
        repro = data['Reprocessing / kg CO2e'].to_list()
        waste = data['Disposal / kg CO2e'].to_list()
    else:
        name = [data.name]
        title = f'{name[0].title()} Emissions'

        make = [data['Manufacturing / kg CO2e']]
        travel = [data['Transport / kg CO2e']]
        use = [data['Use / kg CO2e']]
        repro = [data['Reprocessing / kg CO2e']]
        waste = [data['Disposal / kg CO2e']]

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
        title=title,
        yaxis_title='Emissions / kg CO2e'
    )

    return fig


def create_pie_chart(data, name='Product', w=900, h=650):
    '''
    Create a plotly pie chart.

    Parameters:
    -----------
    data: pd.Series
        Product emissions broken down into categories.
    name: str, optional (default=Product)
        Name for plot if required.
    w: int, optional (default=900)
        Width of plot.
    h: int, optional (default=650)
        Height of plot.

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
    fig = go.Figure(data=[go.Pie(
        labels=data.index, values=data.values, marker=dict(colors=colours))])

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
    if total > 0.0:
        car_comp = round((total / 0.1224), 2)
        st.markdown(f'''> 🚗 Emissions equivalent to driving **{car_comp} km**
                        in an average passenger car (EEA, 2020).''')

    return


#### DOWNLOADS ####
def create_product_df(product, manu, travel, use, reprocess, waste, total):
    '''Creates new pd.DataFrame with required information for output.'''
    product_info = product.copy(deep=True)
    no_comp = int(list(product_info.index)[-7].split('_')[-1])

    # Drops info from dataframe that will not be saved
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
    emissions_info['manufacture_emissions'] = manu
    emissions_info['transport_emissions'] = travel
    emissions_info['use_emissions'] = use
    emissions_info['reprocessing_emissions'] = reprocess
    emissions_info['disposal_emissions'] = waste
    emissions_info['total_emissions'] = total

    return product_info, emissions_info


def convert_df(df):
    '''Converts dataframe to csv file for download.'''
    return df.to_csv(index=False).encode('utf-8')


def download_example_file():
    '''Downloads example template file for users to fill in and upload.'''
    st.markdown(f'''You can download an empty file below that can be
                    populated and uploaded above.''')

    # Reads in example file
    ex_df = pd.read_excel('resources/factors_example.xlsx')
    ex = convert_df(ex_df)

    # Outputs download button
    st.download_button(
        label='Download example file',
        data=ex,
        file_name='factors.csv',
        mime='text/csv'
    )

    return


def download_database(product_info, emissions_info, extra_travel, incl_travel,
                      products, emissions):
    '''Download dataframes with new product added.'''
    # Updates dataframe in the correct format
    products = update.update_inventory(product_info, products)
    emissions, single_prod = update.update_emissions(emissions_info,
                                                     emissions)

    # Converts to format required for download
    single_prod_data_csv = convert_df(product_info.to_frame().T)

    # Outputs download button
    st.download_button(
        label='Download product information CSV',
        data=single_prod_data_csv,
        file_name='new_product_info.csv',
        mime="text/csv"
    )

    if single_prod is not None:
        # Adds extra travel emissions if required to file output
        if incl_travel:
            travel = single_prod['transport_emissions'].to_list()
            new_travel = travel + extra_travel
            single_prod['transport_emissions'] = new_travel

            total = single_prod['total_emissions'].to_list()
            new_total = total + extra_travel
            single_prod['total_emissions'] = new_total

        # Converts to format required for download
        single_prod_csv = convert_df(single_prod)

        # Outputs download button
        st.download_button(
            label='Download product emissions CSV',
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
st.set_page_config(layout='wide')  # Removes whitespace from edge of page

st.title('Calculate Emissions for Products')  # Page title
st.markdown(f'''Input product details to get an estimate of its
                carbon footprint per use.''')

cloud = is_cloud()  # Checks if running locally

#### READ IN DATA ####
today = datetime.now()
year = int(today.strftime("%Y"))  # Finds current year

with st.spinner('Loading data...'):
    if cloud:
        factors = read_data.read_factors()  # Reads in factors file
        # Reads other factors such as travel and electricity/water/gas
        additional_factors = read_data.read_additional_factors()
    
        # Inventory file and emissions
        product_data = read_data.read_products()
        product_emissions = read_data.read_emissions()
        open_emissions = read_data.read_open_source_emissions()
        check_data(open_emissions)
    
        # Reads in travel distances
        land_travel_dist, sea_travel_dist = read_data.read_travel_dist()

    else:
        factors = read_data.read_factors_local()  # Reads in factors file
        # Reads other factors such as travel and electricity/water/gas
        additional_factors = read_data.read_additional_factors_local()

        # Inventory file and emissions
        product_data = read_data.read_products_local()
        product_emissions = read_data.read_emissions_local()
        open_emissions = product_emissions.copy(deep=True)

        # Reads in travel distances
        land_travel_dist, sea_travel_dist = read_data.read_travel_dist_local()

    check_data(factors)
    check_data(additional_factors)
    check_data(product_data)
    check_data(product_emissions)
    check_data(land_travel_dist)
    check_data(sea_travel_dist)

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

    # Reads info on decontamination units
    decon_units = read_data.read_decon_units()
    check_data(decon_units)

    # Creates list of all products in file
    current_prod = product_emissions['product'].to_list()

st.divider()
st.markdown('#### Update Emissions Factors if Desired')
st.markdown(f'''Update information stored in databases to suit your
                own file requirements.''')
#### INPUT OWN FACTORS AND INFO ####
# Finds which years of Defra file have been added to files
defra_yrs = additional_factors[additional_factors['name'] == 'hgv transport']
defra_years_in_file = defra_yrs['year'].to_list()

# Options for inputting own emissions factors in some cases
with st.expander(f'''Click to add new Defra file or change reprocessing
                     factors.'''):
    st.markdown(f'''Defra used for: transport, electricity, water, gas and
                    landfill emissions factors.''')
    st.markdown(f'''**Upload Defra file if not currently in database.**
                    Database contains years: {defra_years_in_file}''')
    defra_file = st.file_uploader('Choose Defra file', type=['xlsx'])
    if defra_file is not None:
        defra_year = st.number_input(f'Enter file year', min_value=2000,
                                     max_value=year, step=1, value=year)

        additional_factors, defra_info = read_upload.new_defra(
            defra_file, str(defra_year), to_database=False)

    # User can change laundry factor
    st.markdown(f'''**Choose own emissions factors (kg CO2e) for the following
                    processes if required.** Leave as 0.0 to use factors in
                    database.''')
    laundry_fact = st.number_input(f'Laundry (per kg)', min_value=0.0,
                                   step=0.001, format='%0.6f')

    # User can input another deconcomination unit and elec/water/gas use
    st.markdown(f'**Use another decontamination unit.**')
    new_decon_name = st.text_input(f'Name of unit').lower()
    new_decon_elec = st.number_input(f'Electricity use (kWh)',
                                     min_value=0.0, step=0.0001,
                                     format='%0.4f')
    new_decon_water = st.number_input(f'Water use (L)', min_value=0.0,
                                      step=0.0001, format='%0.4f')
    new_decon_gas = st.number_input(f'Gas use (m3)', min_value=0.0,
                                    step=0.0001, format='%0.4f')

    if (not cloud and len(new_decon_name) > 0):
        if st.checkbox('Select to add unit to file'):
            calc.add_new_decon_to_file(new_decon_name, new_decon_elec,
                                       new_decon_water, new_decon_gas)


#### ADD OWN FACTORS FILE ####
need_factors = True if factors is None else False
upload_factors = st.checkbox(f'''Select if you wish to upload your own
                             emissions factors file''', value=need_factors)
if upload_factors:
    join_files = False
    own_factors_file = st.file_uploader(f'Upload own emission factors file',
                                        type=['csv'])
    with st.expander(f'''Click to view file requirements or to download
                         empty example file'''):
        download_example_file()
        st.markdown(read_file_contents('resources/own_factors.md'))

    if own_factors_file is not None:
        (own_factors_df,
         error) = read_data.check_uploaded_factors_file(
             own_factors_file, False)
        if error:
            exit_program()

        join_files = st.checkbox(f'''**Select if you wish to also include
                                 factors from the current database**''')
        # Joins with stored data if required
        if join_files and len(factors) > 0:
            factors = pd.concat([own_factors_df, factors])
        else:
            factors = own_factors_df

        if not cloud:
            if st.checkbox('Select to add new factors to file'):
                with st.spinner('Updating...'):
                    update.update_factors_file(own_factors_df)
                st.success('Done!')

if factors is not None:
    # Creates list of available factors to choose from
    available_factor = factors['component'].to_list()
    # Removes duplicates
    available_factor = list(dict.fromkeys(available_factor))
    try:
        available_factor = [word.title() for word in available_factor]
    except AttributeError:
        st.error(f'''Error: Incorrect format for component name.''')
        exit_program()
    available_factor.append('Other')  # Adds option for other
else:
    exit_program()


#### SETS UP NEW INFO ####
# Sets index and sorts additional factors
additional_factors.set_index(['name', 'unit', 'year'], inplace=True)
additional_factors = additional_factors.sort_index()

# Adds new decon units to dict
if new_decon_name != '':
    decon_units[new_decon_name + ' electricity'] = new_decon_elec
    decon_units[new_decon_name + ' water'] = new_decon_water
    decon_units[new_decon_name + ' gas'] = new_decon_gas

# Extracts name of decontamination units to select
decon_names_all = list(decon_units.keys())
decon_names = []
for ind, nm in enumerate(decon_names_all):
    if (ind % 3) == 0:
        decon_names.append(nm[:-12].title())
decon_info = False
decon_type = None


#### USER INPUT ####
st.divider()
st.markdown('#### Add New Product or Query Database')
name = st.text_input('Name of Product').lower()  # User can input name


#### USER SELECTS DATABASE PRODUCT IF AVAILABLE ####
current_store = [None]  # Lists all products currently in dataframe
for prod in current_prod:
    if name in prod and prod not in current_store:
        current_store.append(prod.title())

product_categories = []  # Lists all categories in dataframe
for cat in product_emissions['category'].to_list():
    cat = cat.title()
    if cat not in product_categories:
        product_categories.append(cat)
if len(product_categories) == 0:
    st.error('Error: Please populate required files to continue.')
    exit_program()

# User can choose to select current product in database
chosen = st.selectbox(f'''Search database for desired product''',
                      current_store)

#### USER INPUTS DESTINATION ####
# User inputs destination city for final travel distance calc
felixstowe_ind = uk_cities_list.index('Felixstowe')
dest_city = st.selectbox(f'Select end destination where product is used',
                         uk_cities_list, index=felixstowe_ind).lower()
st.markdown(f'''> *Please note: it is assumed that all products in the
                database are shipped to Felixstowe port and transported by
                land to end destination using average laden HGV (relevant
                emissions factor from Defra).*''')

#### CHOOSE DATABASE ####
# Changes which data is used depending on user choice
if cloud:
    open = st.checkbox(f'''Select to use database containing emissions values
                       calculated with freely available emissions factors''')
    st.markdown(f'''> *Please note: selecting this is recommended if changing
                product information so values are calculated using the same
                emissions factors. If this is not selected, it will access
                values calculated using emissions factors from EcoInvent
                (version 3.10). Any emissions values calculated using this
                calculator will use freely available emissions factors and so
                the final value will differ.*''')
    if open:
        product_emissions = open_emissions.copy(deep=True)

#### SETS UP VARIABLES ####
# Holds product info
index_names = ['product', 'category', 'electricity', 'water', 'gas']
change_info = False
selected_auto = None
check = None

#### USER SELECTS DATABASE PRODUCT ####
if chosen is not None:
    # If product selected, prints out information to user
    no_comp = int(list(product_emissions.columns)[-7].split('_')[-1])
    prod_df, prod_em = choose_database(
        chosen.lower(), product_emissions, no_comp, additional_factors,
        land_travel_dist, dest_city, cloud)

    comparison_emissions_graphic(prod_em['Total / kg CO2e'].iloc[0])

    # Plots pie chart of total product emissions
    pie_chart = create_pie_chart(prod_em.T.squeeze(), name=chosen)
    st.plotly_chart(pie_chart)
    st.download_button(label=f'''Download pie chart as PNG''',
                       data=pie_chart.to_image(format='png', scale=3),
                       file_name='emissions.png', mime='image/png', key='pie')

    # Plots bar chart of total product emissions
    bar_chart = create_bar_chart(prod_em.T.squeeze(), w=400, h=600)
    st.plotly_chart(bar_chart)
    st.download_button(label=f'''Download bar chart as PNG''',
                       data=bar_chart.to_image(format='png', scale=3),
                       file_name='emissions.png', mime='image/png', key='bar')

    st.divider()
    st.markdown(f'#### Change Product Information')
    change_info = st.checkbox(f'Click to change product information')
    if change_info:
        # Creates autofill options for selected product
        selected_auto = select_autofill(
            prod_df, product_categories, available_factor, dest_city,
            cities_list, ports_list, uk_locations)


#### USER CREATES OWN NEW PRODUCT ####
if chosen is None or change_info:
    if change_info and len(name) == 0:
        name = chosen.lower()

    all_info = [name]  # Stores all inputted data

    # If no product selected, user can create own
    no_comp_val = None if not change_info else selected_auto['no_comp']
    no_comp = st.number_input(
        f'Enter number of components used to make product',
        min_value=1, value=no_comp_val, step=1)

    if no_comp is not None:
        no_comp = int(no_comp)

        if not change_info:
            st.divider()
            st.markdown(f'#### Product Information')

        #### WHOLE PRODUCT INFO ####
        # User selects category
        cat_ind = 0 if not change_info else selected_auto['cat']
        cat = st.selectbox(f'Select product category', product_categories,
                           index=cat_ind).lower()
        all_info.append(cat)

        # User inputs number of uses of product
        use_ind = 1 if not change_info else selected_auto['no_uses']
        no_uses = st.number_input(
            f'Select number of times product can be used', min_value=1,
            step=10, value=use_ind)

        # User selects year of product use
        use_year = st.number_input(
            f'Select year of product use', min_value=1970, max_value=year,
            value=year, step=1)

        #### USE EMISSIONS - ELECTRICITY ####
        use_emissions = 0.0

        elec_val = False
        t_val = 0.0
        pr_val = 0.0
        if change_info:
            e_auto = selected_auto['elec']
            if e_auto != '0':
                elec_val = True
                # Extracts saved info about elec use (time and power)
                e_info = e_auto[e_auto.find('(')+1:e_auto.find(')')]
                t_val = float(e_info[:e_info.find(' ')])
                pr_val = float(e_info[e_info.find(' ')+1:])
        electricity = st.checkbox(f'''Product uses electricity
                                  during lifetime''', value=elec_val)
        pr = None
        t = None
        if electricity:  # User can specify/change time on and power rating
            t = st.number_input(f'Time on during use (hr)', value=t_val,
                                min_value=0.0, step=0.001, format='%0.5f')
            pr = st.number_input(f'Power rating (W)', value=pr_val,
                                 min_value=0.0, step=0.001, format='%0.3f')
            use_emissions += calc.use_calc(additional_factors, use_year,
                                           power_rating=pr, time_per_use=t)
        all_info.append('1 (' + str(t) + ' ' + str(pr) + ')' if electricity
                        else '0')

        #### USE EMISSIONS - WATER ####
        water_val = False
        w_val = 0.0
        if change_info:
            w_auto = selected_auto['water']
            if w_auto != '0':
                water_val = True
                w_val = float(w_auto[w_auto.find('(')+1:w_auto.find(')')])
        water = st.checkbox('Product uses water during lifetime',
                            value=water_val)
        w = None
        if water:  # User can specify/change water use
            w = st.number_input(f'Amount of water used per use (L)',
                                min_value=0.0, step=0.001, value=w_val,
                                format='%0.5f')
            use_emissions += calc.use_calc(additional_factors,
                                           use_year, water_vol_per_use=w)
        all_info.append('1 (' + str(w) + ')' if water else '0')

        #### USE EMISSIONS - GAS ####
        gas_val = False
        g_val = 0.0
        if change_info:
            g_auto = selected_auto['gas']
            if g_auto != '0':
                gas_val = True
                g_val = float(g_auto[g_auto.find('(')+1:g_auto.find(')')])
        gas = st.checkbox('Product uses gas during lifetime',
                          value=gas_val)
        g = None
        if gas:  # User can specify/change gas use
            g = st.number_input(f'Amount of gas used per use (m$^{3}$)',
                                min_value=0.0, step=0.001, value=g_val,
                                format='%0.5f')
            use_emissions += calc.use_calc(additional_factors, use_year,
                                           gas_per_use=g)
        all_info.append('1 (' + str(g) + ')' if gas else '0')

        #### INDIVIDUAL COMPONENTS OF PRODUCT ####
        for i in range(no_comp):  # User inputs info about each component
            new_index = [f'component_{i+1}', f'manu_year_{i+1}',
                         f'mass_kg_{i+1}', f'no_uses_{i+1}',
                         f'biogenic_{i+1}', f'manu_loc_{i+1}',
                         f'debark_port_{i+1}', f'depart_loc_uk_{i+1}',
                         f'land_dist_{i+1}', f'sea_dist_{i+1}',
                         f'reprocessing_{i+1}', f'recycle_{i+1}',
                         f'incinerate_{i+1}', f'landfill_{i+1}']
            index_names += new_index

            st.divider()
            st.markdown(f'##### Component {i+1}')

            # User selects if it is single use packaging
            packaging = st.checkbox(
                'Component is single-use packaging', key='pck_%d'%i)

            # Specify if need to autofill info stored in database
            if change_info and i <= (selected_auto['no_comp'] - 1):
                autofill = True
            else:
                autofill = False

            #### COMPONENT OF PRODUCT ####
            # Chooses component from available factors
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
                new_process = st.checkbox(
                    f'Select if factor describes process (e.g. weaving)',
                    key='np_%d'%i)
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
                                    for **{curr_comp.title()}**. '''
            else:
                input_own_factor = st.checkbox(
                    f'Select to input your own factor', key='of_%d'%i)
                own_fact_text = f'''Input emissions factor (kg CO$_{2}$e / kg)
                                    for **{curr_comp.title()}**.
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
                year_prod = st.number_input(
                    f'Select year of component manufacture', min_value=1970,
                    max_value=year, value=comp_val, step=1, key='yr_%d'%i)
            else:  # Autofills value of previous component
                prev_yr = all_info[6+((i-1)*14)]
                year_prod = st.number_input(
                    f'Year of component manufacture', min_value=1970,
                    max_value=year, value=prev_yr, step=1, key='yr_%d'%i)
            all_info.append(year_prod)

            #### MASS OF COMPONENT ####
            # User inputs product mass
            if i != 0 and curr_process and not change_info:
                # Autofills as prev mass for process
                prev_mass = all_info[7+((i-1)*14)]
                mass = st.number_input(
                    f'Enter component mass in kg', min_value=0.0, step=0.01,
                    value=prev_mass, format='%0.5f', key='mass_%d'%i)
            else:
                mass_val = 0.0 if not autofill else \
                               selected_auto['mass_' + str(i+1)]
                mass = st.number_input(
                    f'Enter component mass in kg', min_value=0.0, step=0.01,
                    value=mass_val, format='%0.5f', key='mass_%d'%i)
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
                if i == 0 or change_info:
                    sh_ind = cities_list.index('Shanghai (China)')
                    ml_ind = sh_ind if not autofill else \
                        selected_auto['loc_' + str(i+1)]
                    manu_loc = st.selectbox(
                        'Select component manufacture location', cities_list,
                        index=ml_ind, key='ml_%d'%i).lower().strip()
                else:  # Autofills with same location as previous component
                    prev_loc = all_info[10+((i-1)*14)]
                    prev_ind = cities_list.index(prev_loc.title())
                    manu_loc = st.selectbox(
                        'Select component manufacture location', cities_list,
                        index=prev_ind, key='ml_%d'%i).lower().strip()

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
                all_info.append(manu_loc)

                #### DEBARKATION PORT ####
                # Port where comp leaves country of manufacture
                if not uk_comp:
                    if i == 0 or change_info:
                        dp_ind = port_ind if not autofill else \
                                     selected_auto['port_' + str(i+1)]
                        debark_port = st.selectbox(
                            'Select debarkation port', ports_list,
                            index=dp_ind, key='dp_%d'%i).lower().strip()
                    else:  # Autofills with same location as previous comp
                        prev_loc = all_info[11+((i-1)*14)]
                        prev_ind = ports_list.index(prev_loc.title())
                        debark_port = st.selectbox(
                            'Select debarkation port', ports_list,
                            index=prev_ind, key='dp_%d'%i).lower().strip()
                else:
                    debark_port = '0'
                all_info.append(debark_port)

                # Distance between manufacture city and port
                land_dist_km = 0
                if manu_loc != debark_port and not uk_comp:
                    try:  # Extracts distance travelled if in dataframe
                        land_dist_km += land_travel_dist.at[(manu_loc,
                                                             debark_port),
                                                            'distance_km']
                    except KeyError:  # If not in df, user inputs value
                        city1_nm = manu_loc.title()
                        city2_nm = debark_port.title()
                        land_dist_km += st.number_input(
                            f'''Input travel distance between {city1_nm} and
                            {city2_nm}''', min_value=0.0, step=1.0,
                            format='%0.3f', key='ld1_%d'%i)

                        if not cloud and land_dist_km > 0.0:
                            update.update_travel_distances(
                                manu_loc, debark_port, land_dist_km)

                #### LOCATION IN UK ####
                # Where they travel from in UK (port if from overseas)
                if i == 0 or change_info:
                    dl_ind = uk_end_ind if not autofill else \
                                 selected_auto['loc_uk_' + str(i+1)]
                    depart_loc_uk = st.selectbox(
                        f'''Select UK location from which they travel to
                        destination city''', uk_locations, index=uk_end_ind,
                        key='dluk_%d'%i).lower().strip()
                else:  # Autofills with same location as previous component
                    prev_loc = all_info[12+((i-1)*14)]
                    prev_ind = uk_locations.index(prev_loc.title())
                    depart_loc_uk = st.selectbox(
                        f'''Select UK location from which they travel to
                        destination city''', uk_locations, index=prev_ind,
                        key='dluk_%d'%i).lower().strip()
                all_info.append(depart_loc_uk)

                # Distance between ports if sea travel involved
                if debark_port != depart_loc_uk and not uk_comp:
                    city2 = depart_loc_uk + ' (united kingdom)'
                    # Calculates or extacts sea travel dist
                    sea_dist_km = calc.calc_sea_distance(
                        sea_travel_dist, debark_port, city2)
                else:
                    sea_dist_km = 0

                # Distance between manufacture loc and place of depart for UK
                depart_uk_nm = depart_loc_uk + ' (united kingdom)'
                if manu_loc != depart_uk_nm and uk_comp:
                    try:  # Extracts distance travelled if in dataframe
                        land_dist_km += land_travel_dist.at[(manu_loc,
                                                             depart_uk_nm),
                                                            'distance_km']
                    except KeyError:  # If not in df, user inputs value
                        city1_nm = manu_loc[:manu_loc.find('(')-1].title()
                        city2_nm = depart_loc_uk.title()
                        land_dist_km += st.number_input(
                            f'''Input travel distance between {city1_nm} and
                            {city2_nm}''', min_value=0.0, step=1.0,
                            format='%0.3f', key='ld2_%d'%i)

                        if not cloud and land_dist_km > 0.0:
                            update.update_travel_distances(
                                manu_loc, city2, land_dist_km)
                all_info.append(land_dist_km)
                all_info.append(sea_dist_km)

                #### REPROCESSING ####
                # User inputs method of reprocessing
                re_ind = 0
                perc_val = 0.0
                if autofill:
                    re_auto = str(selected_auto['repro_' + str(i+1)])
                    if re_auto != '0':
                        if 'hsdu' in re_auto:
                            re_ind = 2
                            # Extracts % fill from stored format
                            perc_val = float(re_auto[re_auto.
                                             find('(')+1:re_auto.find(')')])
                        else:
                            re_ind = 1 if re_auto == 'laundry' else 0

                repro = st.selectbox(
                    'Select reprocessing type', [None, 'Laundry', 'HSDU'],
                    index=re_ind, key='rep_%d'%i)

                if repro == 'HSDU':
                    if not decon_info:
                        # User inputs decontamination unit filling
                        perc = st.number_input(
                            f'''Enter product percentage filling of
                            decontamination unit''', value=perc_val*100,
                            min_value=0.0, max_value=100.0, step=0.001,
                            format='%0.2f')
                        # Saves info in required format
                        repro = 'hsdu (' + str(perc/100) + ')'
                        decon_info = True
                    else:
                        repro = 'hsdu (' + str(perc/100) + ')'
                    if decon_type is None:
                        decon_type = st.selectbox(
                            f'Select decontamination unit',
                            decon_names).lower()
                all_info.append(repro.lower() if repro is not None else '0')

                #### DISPOSAL ####
                if not autofill:
                    disposal_ind = 0
                else:  # Sets disposal type index from autofill
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
                disposal = st.selectbox(
                    'Select disposal method',
                    ['Recycle', 'Incineration', 'Landfill', None],
                    index=disposal_ind, key='dis_%d'%i)

                if disposal == 'Recycle':
                    all_info += [1, 0, 0]
                elif disposal == 'Incineration':
                    all_info += [0, 1, 0]
                elif disposal == 'Landfill':
                    all_info += [0, 0, 1]
                else:
                    all_info += [0, 0, 0]

            # Autofills some info if it is a process (e.g. weaving cotton)
            else:
                sh_ind = cities_list.index('Shanghai (China)')
                ml_ind = sh_ind if not autofill else \
                    selected_auto['loc_' + str(i+1)]
                process_loc = st.selectbox(
                    'Select location of process', cities_list, index=ml_ind,
                    key='ml_%d'%i).lower().strip()
                manu_ctry = process_loc[process_loc.find('(')+1:
                                        process_loc.find(')')]
                all_info += [0, process_loc, '0', '0', 0, 0, '0', 0, 0, 0]

            #### ADDS OWN FACTOR TO DATAFRAME IF REQUIRED ####
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
                if (~condition.any()) & (~found_comp.any()):
                    new_cc = st.number_input(
                        f'''Input carbon content (%) for
                        **{curr_comp.title()}**''', value=0.0,
                        min_value=0.0, step=0.001, format='%0.3f',
                        key='cc_%d'%i)
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
        manu_emissions, total_manu_emissions = calc.manufacture_calc(
            product, access_factors, no_comp, dest_city)

        # Travel emissions
        travel_emissions, total_travel_emissions = calc.travel_calc(
            product, no_comp, additional_factors)

        # Read reprocessing factors
        if laundry_fact == 0.0:
            laundry_fact = calc.read_laundry_fact(
                additional_factors, use_year)

        if decon_type is not None:
            decon_fact = calc.decon_emission_calc(
                decon_type, decon_units, additional_factors, use_year)
        else:
            decon_fact = 0.0
        # Reprocessing emissions
        reprocess_emissions = calc.reprocessing_calc(
            product, no_comp, laundry_fact, decon_fact)

        # Reads disposal factors
        landfill_fact = calc.read_landfill_fact(additional_factors, use_year)

        disp_transport_fact = calc.read_disposal_fact(
            additional_factors, year)
        # Disposal emissions
        (incinerate_emissions, recycle_emissions, landfill_emissions,
         biogenic_carbon, net_waste_emissions) = calc.disposal_calc(
             product, access_factors, no_comp, landfill_fact,
             disp_transport_fact, use_year)

        # Calculates total
        total_emissions = total_manu_emissions \
                        + total_travel_emissions \
                        + use_emissions \
                        + reprocess_emissions \
                        + net_waste_emissions

        #### CREATE OUTPUT ####
        # Additional travel to end location
        extra_travel = travel_end_loc(
            product, dest_city, no_comp, additional_factors, land_travel_dist,
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
            series_name = f'{name.title()}'
        elif change_info:
            series_name = f'{chosen.title()}'
            product['product'] = series_name.lower()
        else:
            series_name = 'Product'
            product['product'] = 'new_product'
        col_dict = {series_name: st.column_config.NumberColumn(format='%.6f')}
        total_series = pd.Series(total_data, index=index_names,
                                 name=series_name)

        st.divider()
        st.markdown(f'#### Results')
        # Outputs dataframe
        st.dataframe(total_series, column_config=col_dict)

        comparison_emissions_graphic(total_series['Total / kg CO2e'])

        # Outputs pie chart
        if total_series.iloc[0] > 0.0:
            # Plots pie chart of total product emissions
            new_pie_chart = create_pie_chart(total_series, name=series_name)
            st.plotly_chart(new_pie_chart)
            # Download image as PNG
            st.download_button(
                label=f'Download pie chart as PNG',
                data=new_pie_chart.to_image(format='png', scale=3),
                file_name='emissions.png', mime='image/png', key='new_pie')

            # Plots bar chart of total product emissions
            new_bar_chart = create_bar_chart(total_series, w=400, h=600)
            st.plotly_chart(new_bar_chart)
            # Download image as PNG
            st.download_button(
                label=f'Download bar chart as PNG',
                data=new_bar_chart.to_image(format='png', scale=3),
                file_name='emissions.png', mime='image/png', key='new_bar')

        # Outputs comparison bar chart to original product if changes made
        if change_info:
            # Total data = new emissions, prod_em = original product
            comp_df = compare_changes(
                prod_em, total_data, chosen.title(), index_names)

            # Plots comparison bar chart between new and original product
            comp_bar_chart = create_bar_chart(
                comp_df, comp=True, prod_name=chosen.title(), g=0.5)
            st.plotly_chart(comp_bar_chart)
            # Download image as PNG
            st.download_button(
                label=f'Download bar chart as PNG',
                data=comp_bar_chart.to_image(format='png', scale=3),
                file_name='emissions_comparison.png', mime='image/png',
                key='comp_bar')

        #### DOWNLOAD DATA ####
        st.divider()
        st.markdown(f'#### Download Results')
        if st.checkbox('Select for options to download results files'):
            prod_info, emissions_info = create_product_df(
                product, total_manu_emissions, total_travel_emissions,
                use_emissions, reprocess_emissions, net_waste_emissions,
                total_emissions)

            st.markdown(f'''> *Please note: all emissions values in downloaded
                            files are calculated using freely available emissions
                            factors.*''')

            incl_travel = st.checkbox(
                f'''Select if you wish to include travel to end location
                in single product emissions file''')

            if not cloud:
                to_database = st.checkbox(f'Save product to database')
                if to_database:
                    with st.spinner('Updating...'):
                        update.update_local_emissions(prod_info)
                        update.update_local_inventory(prod_info)
                    st.success('Done!')

            download_database(
                prod_info, emissions_info, extra_travel, incl_travel,
                product_data, open_emissions)
