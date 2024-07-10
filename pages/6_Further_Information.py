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
st.title(f'Calculator Information')

intro_file = 'resources/further_info.md'
# Show explanatory markdown
st.markdown(read_file_contents(intro_file))