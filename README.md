# 🌍 Greenhouse Gas Emissions Calculator for Healthcare

> Developed as part of MSc Health Data Science (University of Exeter) research project in association with NHS GIRFT (Getting It Right First Time) programme.

## Overview

The materials in this repository are designed to support the calculations of greenhouse gas (GHG) emissions for products and processes used in healthcare. The model code represents GHG emissions calculations made for individual products from cradle-to-grave.

* The code builds a `Streamlit` web application that can be used to run the calculator via a web app.
* Python dependencies are managed through `conda`.

## Model

This model is based on calculations performed by GIRFT of the carbon footprint of healthcare pathways.

## Streamlit community cloud deployment

* https://healthcare-ghg-emissions-calculator.streamlit.app/

> Please note that the calculator has been deployed to a free tier service.  If the app has not been used recently then you will need to wake up the app and wait while it reboots.

## Create local calculator interface

The following information describes an alternate method of running the calculator by creating a local copy.

### Download Code

Either clone the repository using git or click on the green "Code" button and select "Download Zip".

```bash
git clone https://github.com/hm7612g20/Healthcare_GHG_Emissions_Calculator.git
```

### Installing dependencies

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/release/python-3100+/)

All dependencies can be found in [`binder/environment.yml`]().  

Navigate to the directory containing the repo using your terminal/cmd prompt and use the command:

```bash
conda env create -f binder/environment.yml
```

To activate the environment, use:

```bash
conda activate ghg_emissions_calc
```

### Running the interface to the model

In the directory (folder) containing the code, issue the following command via the terminal/cmd prompt:

```bash
streamlit run Overview.py
```

This should launch the Streamlit interface automatically in an internet browser. Alternatively, you can navigate to the following URL.

```bash
http://localhost:8501
```

#### Required Files
> Please note that running this locally requires data to be uploaded into the model files. File templates are located in the directory /emissions_calculator.

Populate/add the following files to the emissions_calculator/factors folder:
- factors.csv
- additional_factors.csv

Populate/add the following files to the emissions_calculator/inventory folder:
- products.csv
- emissions.csv

Populate/add the following files to the emissions_calculator/data folder:
- land_travel_dist.csv
- sea_travel_dist.csv

Products.csv and emissions.csv can be downloaded from the Streamlit interface as required.

## License
This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Contact
For any queries, please reach out to:
* hm7612g20@gmail.com