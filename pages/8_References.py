#### IMPORTS ####
import pandas as pd
import streamlit as st


#### FUNCTIONS ####
def read_file_contents(file_name):
    ''''
    Read the contents of a file.

    Parameters:
    -----------
    file_name: str
        Path to file.

    Returns:
    -------
    str
    '''
    with open(file_name) as f:
        return f.read()


def convert_df(df):
    '''Converts dataframe to csv file for download.'''
    return df.to_csv(index=False).encode('utf-8')


def download_factors_info_file():
    '''Downloads file containing details on EcoInvent factors used.'''
    st.markdown(f'''Download file below to view information on EcoInvent
                    factors used.''')

    # Reads in example file
    ex_df = pd.read_excel('resources/ecoinvent_factors.xlsx')
    ex = convert_df(ex_df)

    # Outputs download button
    st.download_button(
        label='Download information file',
        data=ex,
        file_name='ecoinvent_factors.csv',
        mime='text/csv'
    )

    return


def download_defra_info_file():
    '''Downloads file containing details on DEFRA factors used.'''
    st.markdown(f'''Download file below to view information on DEFRA
                    factors used.''')

    # Reads in example file
    ex_df = pd.read_excel('resources/defra_factors.xlsx')
    ex = convert_df(ex_df)

    # Outputs download button
    st.download_button(
        label='Download information file',
        data=ex,
        file_name='defra_factors.csv',
        mime='text/csv'
    )

    return


#### PAGE CONFIGURE ####
st.set_page_config(
    layout='wide',
    initial_sidebar_state='expanded'
)


#### MAIN ####
st.title(f'References')
file = 'resources/citation.md'
st.markdown(read_file_contents(file))

st.divider()
download_factors_info_file()
download_defra_info_file()
