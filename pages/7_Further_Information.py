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
st.title(f'Calculator Information')

# Show explanatory markdowns
st.markdown(read_file_contents('resources/further_info.md'))

st.divider()
st.markdown('#### Calculator Details')
st.markdown(read_file_contents('resources/calc_details.md'))

st.divider()
st.markdown('#### Assumptions')
st.markdown(read_file_contents('resources/assumptions.md'))
