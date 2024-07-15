#### IMPORTS ####
import streamlit as st
import pandas as pd
import sys
import os

import re
from fpdf import FPDF
import base64

from datetime import datetime

import kaleido
from PIL import Image
import plotly.express as px
import plotly.graph_objects as go

from emissions_calculator import product_calculator as calc
from emissions_calculator import read_data
from emissions_calculator import update_files as update

#### FUNCTIONS ####
def read_file_contents(file_name):
    '''Read the contents of a file.'''
    with open(file_name) as f:
        return f.read()

def exit_program():
    '''Exits programme.'''
    sys.exit(0)

def check_data(data):
    '''Checks that data has successfully been read in, else exits program.'''
    if data is None:
        exit_program()

#### ADDITIONAL CALCULATIONS ####
def travel_end_loc(df, dest_city, no_comp):
    '''
    Calculates GHG emissions corresponding to travel to end city from point
    where it begins journey in UK.

    Parameters:
    -----------
    df: pd.DataFrame
        Contains product information.
    dest_city: str
        City where product will be used.
    no_comp: int
        Number of components in product

    Returns:
    --------
    travel_emissions: float
        Additional emissions for travel.
    '''
    # Reads other factors such as travel and electricity/water/gas
    additional_factors = read_data.read_additional_factors()
    check_data(additional_factors)
    # Sets index and sorts additional factors
    additional_factors.set_index(['name', 'unit', 'year'], inplace=True)
    additional_factors = additional_factors.sort_index()

    # Reads in travel distances
    land_travel_dist, sea_travel_dist = read_data.read_travel_dist()

    count = 0
    travel_emissions = []
    for ind, row in df.iterrows():
        ghg_em = 0.0
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

                    ghg_em += calc.calc_travel_emissions(dist_km, no_uses,
                                                         mass, travel_fact)

        count += 1
        travel_emissions.append(ghg_em)

    return travel_emissions
                
def calculate_total_emissions(df):
    '''
    Calculates total emissions of all chosen products.

    Parameters:
    -----------
    df: pd.DataFrame
        Contains emissions of selected products.

    Returns:
    -------
    total: float
        Sum of all total emissions of chosen products.
    make: float
        Sum of all manufacturing emissions of chosen products.
    travel: float
        Sum of all travel emissions of chosen products.
    use: float
        Sum of all use emissions of chosen products.
    repro: float
        Sum of all reprocessing emissions of chosen products.
    disposal: float
        Sum of all disposal emissions of chosen products.
    '''
    total_list = df['Total / kg CO2e'].to_list()
    total = sum([float(i) for i in total_list])
    make_list = df['Manufacturing / kg CO2e'].to_list()
    make = sum([float(i) for i in make_list])
    travel_list = df['Transport / kg CO2e'].to_list()
    travel = sum([float(i) for i in travel_list])
    use_list = df['Use / kg CO2e'].to_list()
    use = sum([float(i) for i in use_list])
    repro_list = df['Reprocessing / kg CO2e'].to_list()
    repro = sum([float(i) for i in repro_list])
    disposal_list = df['Disposal / kg CO2e'].to_list()
    disposal = sum([float(i) for i in disposal_list])

    return total, make, travel, use, repro, disposal

#### FORMATTING ####
def format_integer_without_commas(x):
    '''Ensures years are printed without a comma.'''
    if isinstance(x, int):
        return f'{x}'
    return x

def choose_database(chosen_products, product_emissions, no_comp,
                    dest_city):
    '''
    Selects relevant part of emissions database if certain product
    is selected from list.

    Parameters:
    -----------
    chosen_products: str
        Name of products
    product_emissions: pd.DataFrame
        Contains current products inventory.
    no_comp: int
        Maximum number of components in data.
    dest_city: str
        City where products are transported to.

    Returns:
    -------
    sorted_data: pd.DataFrame
        Formatted dataframe of selected products.
    original_df: pd.DataFrame
        Dataframe of selected products in original format without additional
        travel emissions to end location.
    original_df_inc_travel: pd.DataFrame
        Dataframe of selected products in original format with additional
        travel emissions to end location.
    '''
    # Finds information in database on the selected products
    selected = product_emissions[product_emissions['product']\
                                 .isin(chosen_products)].copy(deep=True)
    selected.set_index('product', inplace=True)
    #product_emissions.set_index('product', inplace=True)
    #selected = product_emissions.loc[chosen_products].copy(deep=True)

    # Keeps copy of data in original form without additional travel
    original_df = selected.reset_index().copy(deep=True)

    # Works out additional travel emissions to end city
    end_travel = travel_end_loc(selected, dest_city, no_comp)
    new_travel = []
    for old, new in zip(selected['transport_emissions'].to_list(),
                        end_travel):
        new_travel.append(old + new)
    selected['transport_emissions'] = new_travel

    # Keeps copy of data in original form with additional travel
    original_df_inc_travel = selected.reset_index().copy(deep=True)

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

    for i in range(no_comp):
        # Additional filters are component names, product location and year
        filter_items.append(f'component_{i+1}')
        filter_items.append(f'manu_loc_{i+1}')
        # Capitalises strings in these columns
        selected['component_' + str(i+1)] = selected['component_' + str(i+1)]\
                                            .str.capitalize()
        selected['manu_loc_' + str(i+1)] = selected['manu_loc_' + str(i+1)]\
                                           .str.capitalize()

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
    # Sorts so highest total appears first
    sorted_data = data.sort_values(by=['Total / kg CO2e'], ascending=False)
    # Capitalises product names
    sorted_data.index = sorted_data.index.str.capitalize()
    # Displays dataframe and rounds values
    st.dataframe(sorted_data.round(decimals=6).astype(str))

    return sorted_data, original_df, original_df_inc_travel

#### PLOTS ####
def create_bar_chart(data, process_name):
    '''
    Create a plotly stacked bar chart.
    
    Parameters:
    -----------
    data: pd.Dataframe
        rows = products, columns = emissions broken down into
        categories.
    process_name: str
        Name of process.
        
    Returns:
    -------
    plotly.figure
    '''
    # Sorts so highest total appears first
    sorted_data = data.sort_values(by=['Total / kg CO2e'], ascending=False)
    
    # Takes dataframe and converts information to lists
    name = sorted_data.index.to_list()
    make = sorted_data['Manufacturing / kg CO2e'].to_list()
    travel = sorted_data['Transport / kg CO2e'].to_list()
    use = sorted_data['Use / kg CO2e'].to_list()
    repro = sorted_data['Reprocessing / kg CO2e'].to_list()
    waste = sorted_data['Disposal / kg CO2e'].to_list()

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
        width=1000,
        height=700,
        title=f'Product Emissions: {process_name.title()}',
        yaxis_title='Emissions / kg CO2e'
    )

    return fig

def create_pie_chart(data, process_name):
    '''
    Create a plotly pie chart.
    
    Parameters:
    -----------
    data: pd.Series
        Contains sum of emissions from all chosen products.
    process_name: str
        Name of process.
        
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
    
    fig = go.Figure(data=[go.Pie(labels=data.index,
                                 values=data.values,
                                 marker=dict(colors=colours))])

    fig.update_layout(
        autosize=False,
        width=1000,
        height=700,
        title=f'Total Emissions: {process_name.title()}',
        title_x=0.5
    )

    return fig

def comparison_emissions_graphic(total):
    '''Displays emissions in terms of comparison values.'''
    comp = round((total / 0.1224), 2)

    st.markdown(f'''> 🚗 Emissions equivalent to driving **{comp} km** in 
                    an average passenger car (EEA, 2020).''')

    return

#### DOWNLOADS ####
def convert_df(df):
    '''Converts dataframe to csv file for download.'''
    return df.to_csv(index=False).encode('utf-8')

def download_example_file():

    ex_df = pd.read_excel('resources/emissions_example.xlsx')
    ex = convert_df(ex_df)
    
    st.download_button(
        label='Download empty file',
        data=ex,
        file_name='emissions.csv',
        mime='text/csv'
    )

    return

def download_button(df):
    '''
    Combines products with the total dataframe and produces a download
    button to download the results as a csv.

    Parameters:
    -----------
    df: pd.DataFrame
        Product dataframe

    Returns:
    -------
    Button to download data as csv.
    '''
    results_csv = convert_df(df)

    st.download_button(
        label='Download Product CSV',
        data=results_csv,
        file_name='process_emissions.csv',
        mime="text/csv",
    )

def create_download_link(val, filename):
    '''Creates PDF file download link.'''
    b64 = base64.b64encode(val)
    return f'<a href="data:application/octet-stream;base64,{b64.decode()}" \
             download="{filename}.pdf">Download file</a>'

def clean_data(data):
    '''Fixes issues with outputting PDF if it cannot encode character.'''
    pattern = re.compile(r'[^\x00-\x7F]+')  # Matches any non-ASCII character
    # Replace characters with a space
    cleaned_data = pattern.sub(' ', data)
    return cleaned_data

def create_pdf_report(process_name, chosen_df, total_series,
                      bar_chart, pie_chart):
    '''Creates PDF report of process.'''
    pdf = FPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.set_font('Arial', 'BU', 12)

    title_text = f'Greenhouse Gas Emissions for {process_name.title()}'
    pdf.cell(0, 8, title_text, ln=True)
    
    index_names = ['Product', 'Total / kg CO2e', 'Manufacturing / kg CO2e', 
                   'Transport / kg CO2e', 'Use / kg CO2e',
                   'Reprocessing / kg CO2e', 'Disposal / kg CO2e']
    product_names = chosen_df.index.to_list()
    cleaned_product_names = [clean_data(n) for n in product_names]
    pdf_df = chosen_df.filter(items=index_names)
    pdf_df.insert(loc=0, column='Product', value=cleaned_product_names)
    
    try:
        error = False
        # Adding DataFrame content to the PDF
        for ind, row in pdf_df.iterrows():
            count = 0
            for col, val in row.items():
                if count == 0:
                    pdf.cell(0, 2, '', ln=True)
                    pdf.set_font('Arial', 'BI', 10)
                    pdf.cell(0, 8, f'{col}: {val}', ln=True)
                else:
                    pdf.set_font('Arial', '', 9)
                    pdf.cell(0, 8, f'{col}: {round(float(val), 6)}', ln=True)
                count += 1

        pdf.cell(0, 8, '', ln=True)
        pdf.set_font('Arial', 'B', 10)
        pdf.cell(0, 8, f'Sum of Products', ln=True)
        pdf.set_font('Arial', '', 9)
        # Adding series content to the PDF
        for index, value in total_series.items():
            pdf.cell(0, 8, f'{index}: {round(float(value), 6)}', ln=True)
                
        figures = [bar_chart, pie_chart]
        pdf.add_page()
        for index, fig in enumerate(figures, 1):
            # Save Plotly figure as PNG
            fig.write_image(f'figure_{index}.png', scale=2)
            # Open the saved PNG
            img = Image.open(f'figure_{index}.png')
            # Get the dimensions of the saved PNG
            img_width, img_height = img.size
            # Calculate the scaling factor to fit the image within the page width
            scale_factor = 180 / img_width  # 180 = width of the page - margins
            # Resize the image
            img = img.resize((int(img_width * scale_factor),
                              int(img_height * scale_factor)))
            # Get the new dimensions after resizing
            img_width, img_height = img.size
            # Add the saved PNG to the PDF
            pdf.image(f'figure_{index}.png', x=10, y=pdf.get_y() + 10,
                      w=img_width, h=img_height)
            pdf.set_y(pdf.get_y() + img_height + 20)
            # Removes file once it has been written on
            os.remove(f'figure_{index}.png')
    
        # Output PDF to byte array
        pdf_output = pdf.output(dest='S').encode('latin-1')

        # Generate download link
        html = create_download_link(pdf_output, 'process_calculator')
        st.markdown(html, unsafe_allow_html=True)
            
    # Catches errors if unable to generate
    except Exception as e:
        error = True
        if 'latin-1' in str(e):
            st.error(f'Failed to generate PDF due to encoding error: {e}')
        else:
            st.error(f'An unexpected error occurred: {e}')
    
    return error


#### MAIN ####
# Removes whitespace from edge of page
st.set_page_config(layout='wide')

# Page title
st.title('Calculate Total Emissions for Process')

# Show introductory markdown
st.markdown(f'''Select different products contained in the current database to
                calculate the total emissions for a given process.''')
st.markdown(f'''If a new product is required, calculations can be made using
                **Product Calculator** or input your own file.''')

join_files = False
own_file = st.file_uploader(f'Upload own file if desired.',
                            type=['csv'])
# Additional information stored under a read more option
with st.expander(f'File requirements and example'):
    download_example_file()
    st.markdown(read_file_contents('resources/process_own_emissions.md'))
if own_file is not None:
    own_df = pd.read_csv(own_file)
    join_files = st.checkbox(f'Include products from current database')


#### READS IN DATA ####
with st.spinner('Loading data...'):
    # Reads in cities and ports
    cities_list, uk_cities_list = read_data.read_cities()
    check_data(cities_list)
    check_data(uk_cities_list)
    
    # Inventory file
    product_emissions = read_data.read_emissions()
    check_data(product_emissions)
    open_emissions = read_data.read_open_source_emissions()
    check_data(open_emissions)

# Joins with current database if required
if join_files:
    product_emissions = pd.concat([own_df, product_emissions])
elif own_file is not None:
    product_emissions = own_df

try:
    # Creates list of products in inventory
    current_prod = product_emissions['product'].to_list()
    # Capitalises all names
    current_prod = [p.capitalize() for p in current_prod]
except (AttributeError, KeyError) as e:
    st.error('Error: incorrect file format.')
    exit_program()

process_name = st.text_input(f'Enter name of process')

# User inputs destination city for final travel distance calc
felixstowe_ind = uk_cities_list.index('Felixstowe')
dest_city = st.selectbox(f'Select approximate destination for product',
                         uk_cities_list, index=felixstowe_ind).lower()

# Changes which data is used depending on user choice
open = st.checkbox(f'''Use emissions calculated with open-source emissions
                       factors''')
if open:
    product_emissions = open_emissions.copy(deep=True)

# Selects any number of products from the current inventory
chosen = st.multiselect('Select products in process', current_prod)

# Reverts names to lower case
chosen = [c.lower() for c in chosen]

if len(chosen) > 0:
    try:
        # Finds maximum number of components for the products
        no_comp = int(list(product_emissions.columns)[-7].split('_')[-1])
        # Creates dataframe containing only chosen items
        chosen_df, orig_df, orig_df_trv = choose_database(chosen,
                                                          product_emissions,
                                                          no_comp, dest_city)
    except (KeyError, IndexError) as e:
        st.error('Error: incorrect file format.')
        exit_program()

    # Calculates sum of their emissions
    total, make, travel, use, \
        repro, disposal = calculate_total_emissions(chosen_df)
    
    # Creates pd.Series containing sum of chosen products
    index_names = ['Total / kg CO2e', 'Manufacturing / kg CO2e', 
                   'Transport / kg CO2e', 'Use / kg CO2e',
                   'Reprocessing / kg CO2e', 'Disposal / kg CO2e']
    total_data = [total, make, travel, use, repro, disposal]
    series_name = 'Sum of Products'
    col_dict = {series_name: st.column_config.NumberColumn(format='%.6f')}
    total_series = pd.Series(total_data, index=index_names,
                             name=series_name)
    st.dataframe(total_series, column_config=col_dict)
    comparison_emissions_graphic(total)

    if len(process_name) == 0:
        process_name = 'Process'
    # Plots bar chart of emissions
    bar_chart = create_bar_chart(chosen_df, process_name)
    st.plotly_chart(bar_chart)
    # Download image as PNG
    st.download_button(label='Download bar chart as PNG',
                       data=bar_chart.to_image(format='png', scale=3),
                       file_name='emissions_comparison.png',
                       mime='image/png', key=0)

    pie_chart = create_pie_chart(total_series, process_name)
    st.plotly_chart(pie_chart)
    # Download image as PNG
    st.download_button(label='Download pie chart as PNG',
                       data=pie_chart.to_image(format='png', scale=3),
                       file_name='emissions.png',
                       mime='image/png', key=1)

    if st.checkbox('Download results'):
        if st.checkbox(f'Include travel to end location in CSV file'):
            download_button(orig_df_trv)
        else:
            download_button(orig_df)


        #### EXPORT PDF REPORT ####
        export_as_pdf = st.button('Export PDF report')
        if export_as_pdf:
            with st.spinner('Creating PDF...'):
                error = create_pdf_report(process_name, chosen_df,
                                          total_series,
                                          bar_chart, pie_chart)
    
            if not error:
                st.success('Done!')