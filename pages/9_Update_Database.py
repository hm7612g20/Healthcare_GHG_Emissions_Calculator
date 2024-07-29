#### IMPORTS ####
import streamlit as st
import pandas as pd
import hmac

from datetime import datetime

from google.oauth2 import service_account
from gspread_pandas import Spread, Client

# Local package for updates and data access
from emissions_calculator import update_files as update
from emissions_calculator import read_data
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


#### PASSWORD ####
def password_entered():
    '''Checks whether a password entered by the user is correct.'''
    if hmac.compare_digest(st.session_state['password'],
                           st.secrets['password']):
        st.session_state['password_correct'] = True
        del st.session_state['password']  # Don't store password
    else:
        st.session_state['password_correct'] = False


def check_password():
    '''Returns `True` if the user had the correct password.'''

    # Return True if the password is validated.
    if st.session_state.get('password_correct', False):
        return True

    # Show input for password.
    st.text_input(
        'Enter password', type='password', on_change=password_entered,
        key='password')

    if "password_correct" in st.session_state:
        st.error('Incorrect password')
    return False


#### UPDATE ####
def update_gsheets(name, new_data):
    '''Updates data in from Google Sheets.'''
    scope = ['https://spreadsheets.google.com/feeds',
             'https://www.googleapis.com/auth/drive']

    try:  # Tries to connect using streamlit secrets
        credentials = service_account.Credentials.from_service_account_info(
            st.secrets['gcp_service_account'], scopes=scope)
        client = Client(scope=scope, creds=credentials)
        spread = Spread(name, client=client)
        sh = client.open(name)

        worksheet = sh.worksheet(name)
        client.set_timeout(9999)

        for i in range(len(new_data)):
            row = new_data.iloc[i].to_list()
            row_str = [str(d) for d in row]

            worksheet.append_row(row_str)

    except (FileNotFoundError, KeyError) as e:
        st.error('Error: Data not found.')


def edit_gsheets(name, df, update_cols, year):
    '''Updates data in from Google Sheets.'''
    scope = ['https://spreadsheets.google.com/feeds',
             'https://www.googleapis.com/auth/drive']

    try:  # Tries to connect using streamlit secrets
        credentials = service_account.Credentials.from_service_account_info(
            st.secrets['gcp_service_account'], scopes=scope)
        client = Client(scope=scope, creds=credentials)
        spread = Spread(name, client=client)
        sh = client.open(name)

        worksheet = sh.worksheet(name)
        client.set_timeout(9999)

        for col in update_cols:
            for ind, row in df.iterrows():
                sheet.update_cell(row, col, year)

    except (FileNotFoundError, KeyError) as e:
        st.error('Error: Data not found.')


#### DOWNLOADS ####
def convert_df(df):
    '''Converts dataframe to csv file for download.'''
    return df.to_csv(index=False).encode('utf-8')


def download_example_file(name='products'):
    '''Downloads example template file for users to fill in and upload.'''
    st.markdown(f'''You can download an empty file below that can be
                    populated and uploaded above.''')

    # Reads in example file
    ex_df = pd.read_excel(f'resources/{name}_example.xlsx')
    ex = convert_df(ex_df)

    # Outputs download button
    st.download_button(
        label='Download example file',
        data=ex,
        file_name=name+'.csv',
        mime='text/csv'
    )

    return


if not check_password():
    st.markdown(f'''If you do not have access: to request an update, please
                email revelant files to <email>''')
    st.stop()  # Do not continue if check_password is not True


#### MAIN ####
st.session_state.update_year = None

st.set_page_config(layout='wide')  # Removes whitespace from edge of page

st.title('Update Databases')  # Page title
st.markdown(f'''Input product and emissions factor files to update the stored
                databases.''')

today = datetime.now()
year = int(today.strftime("%Y"))  # Finds current year

with st.spinner('Loading data...'):
    # Reads other factors such as travel and electricity/water/gas
    additional_factors = read_data.read_additional_factors()
    check_data(additional_factors)

    # Inventory file
    product_data = read_data.read_products()
    check_data(product_data)
    product_emissions = read_data.read_emissions()
    check_data(product_emissions)

no_comp = int(list(product_emissions.columns)[-7].split('_')[-1])

#### CHOOSE DATABASE ####
# Changes which data is used depending on user choice
opens = st.checkbox(f'''Select to use update database containing emissions
                        values calculated with freely available emissions
                        factors''')
st.markdown(f'''> *Please note: if this is not selected, it will update the
                file containing values calculated using emissions factors from
                EcoInvent (version 3.10). Any emissions values calculated
                using this calculator will use freely available emissions
                factors unless own factors were used.*''')
if opens:
    e_name = 'open_source_emissions'
    f_name = 'open_source_factors'
else:
    e_name = 'emissions'
    f_name = 'factors'

#### ADD TO PRODUCT DATABASE ####
st.divider()
st.markdown('#### Add New Product')
st.markdown(f'''These files can be downloaded in **Product Calculator** as
            *product information* and *product emissions*, respectively.''')
st.markdown(f'''Alternatively, you can create your own file using the guidance
            below.''')
new_prod = st.file_uploader(f'Upload new product information file.',
                            type=['csv'])
with st.expander(f'''Click to view file requirements or to download
                     empty example file'''):
    download_example_file()
    st.markdown(read_file_contents('resources/inventory_own_products.md'))

new_prod_emissions = st.file_uploader(f'Upload new product emissions file.',
                                      type=['csv'])
with st.expander(f'''Click to view file requirements or to download
                     empty example file'''):
    download_example_file(name='emissions')
    st.markdown(f'''Please note: the file should include the number of
                components equal to that contained in the current database
                (number of components: {no_comp}.''')
    st.markdown(read_file_contents('resources/process_own_emissions.md'))

if new_prod is not None and new_prod_emissions is not None:
    prod_header = product_data.columns.values.tolist()

    new_prod_df = pd.read_csv(new_prod, names=prod_header)
    new_prod_df.drop([0], inplace=True)
    new_prod_df = new_prod_df.fillna(0)
    new_em_df = pd.read_csv(new_prod_emissions)

    new_no_comp = int(list(new_em_df.columns)[-7].split('_')[-1])
    if no_comp != new_no_comp:
        st.error(f'''Error: New file must have data with the same number of
                   components per product.''')
        exit_program()

    if st.button('Click to update product database'):
        with st.spinner('Updating...'):
            done = False
            try:
                update_gsheets('products', new_prod_df)
                update_gsheets(e_name, new_em_df)
                done = True
            except (TypeError) as e:
                st.error('Error: Could not update')
        if done:
            st.success('Done!')


#### ADD TO FACTORS DATABASE ####
st.divider()
st.markdown('#### Add New Emissions Factors')
new_factors = st.file_uploader(f'Upload new emissions factors file.',
                               type=['csv'])
with st.expander(f'''Click to view file requirements or to download
                     empty example file'''):
    download_example_file(name='factors')
    st.markdown(read_file_contents('resources/own_factors.md'))

if new_factors is not None:
    new_fact_df = pd.read_csv(new_factors)
    new_fact_df = new_fact_df.fillna(0)

    if st.button('Click to update factors database'):
        with st.spinner('Updating...'):
            done = False
            try:
                update_gsheets(f_name, new_fact_df)
                done = True
            except (TypeError) as e:
                st.error('Error: Could not update')
        if done:
            st.success('Done!')


#### ADD TO LAND TRAVEL DISTANCES DATABASE ####
st.divider()
st.markdown('#### Add New Land Travel Distances')
new_dist = st.file_uploader(f'Upload new land travel distances file.',
                            type=['csv'])
with st.expander(f'''Click to view file requirements or to download
                     empty example file'''):
    download_example_file(name='distance', key='ld')
    st.markdown(read_file_contents('resources/own_distance.md'))

if new_dist is not None:
    new_dist_df = pd.read_csv(new_dist)
    new_dist_df = new_dist_df.fillna(0)

    if st.button('Click to update land travel distance database'):
        with st.spinner('Updating...'):
            done = False
            try:
                update_gsheets('land_travel_distance', new_dist_df)
                done = True
            except (TypeError) as e:
                st.error('Error: Could not update')
        if done:
            st.success('Done!')


#### ADD TO SEA TRAVEL DISTANCES DATABASE ####
st.divider()
st.markdown('#### Add New Sea Travel Distances')
new_sea_dist = st.file_uploader(f'Upload new sea travel distances file.',
                                type=['csv'])
with st.expander(f'''Click to view file requirements or to download
                     empty example file'''):
    download_example_file(name='distance', key='sd')
    st.markdown(read_file_contents('resources/own_distance.md'))

if new_sea_dist is not None:
    new_sea_dist_df = pd.read_csv(new_sea_dist)
    new_sea_dist_df = new_sea_dist_df.fillna(0)

    if st.button('Click to update sea travel distance database'):
        with st.spinner('Updating...'):
            done = False
            try:
                update_gsheets('sea_travel_distance', new_sea_dist_df)
                done = True
            except (TypeError) as e:
                st.error('Error: Could not update')
        if done:
            st.success('Done!')


#### ADD TO ADDITIONAL FACTORS DATABASE ####
st.divider()
st.markdown('#### Add New DEFRA Emissions Factors')
# Finds which years of Defra file have been added to files
defra_yrs = additional_factors[additional_factors['name'] == 'hgv transport']
defra_years_in_file = defra_yrs['year'].to_list()

st.markdown(f'''**Upload Defra file if not currently in database.**
                Database contains years: {defra_years_in_file}''')
defra_file = st.file_uploader('Choose Defra file', type=['xlsx'])
defra_info = None

if defra_file is not None:
    defra_year = st.number_input(f'Enter file year', min_value=2000,
                                 max_value=year, step=1, value=year)

    comb_additional, defra_info = read_upload.new_defra(
        defra_file, str(defra_year), to_database=False)

if defra_info is not None:
    if st.button('Click to update factors database'):
        with st.spinner('Updating...'):
            done = False
            try:
                defra_info['source'] = [
                    'DEFRA, delivery vehicles', 'DEFRA, delivery vehicles',
                    'DEFRA, delivery vehicles', 'DEFRA, delivery vehicles',
                    'DEFRA, water treatment', 'DEFRA, water supply',
                    'DEFRA, UK electricity',
                    'DEFRA, transmission and distribution',
                    'DEFRA, UK electricity', 'DEFRA, UK electricity',
                    'DEFRA, fuels', 'DEFRA, fuels', 'DEFRA, waste disposal']
                update_gsheets('additional_factors', defra_info)
                done = True
            except (TypeError) as e:
                st.error('Error: Could not update')
        if done:
            st.success('Done!')
