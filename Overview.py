#### IMPORTS ####
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


#### PAGE CONFIGURE ####
st.set_page_config(
    layout='wide',
    initial_sidebar_state='expanded'
)


#### MAIN ####
# Page title
st.title(f'Healthcare Greenhouse Gas Emissions Calculator and Database')

intro_file = 'resources/overview.md'
# Show introductory markdown
st.markdown(read_file_contents(intro_file))
