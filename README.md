# 🌍 Greenhouse Gas Emissions Calculator for Healthcare

> Developed with NHS GIRFT (Getting It Right First Time) programme.

## Overview

The materials in this repository are designed to support the calculations of greenhouse gas (GHG) emissions for products and processes used in healthcare. The model code represents emissions calculations made for individual products from cradle-to-grave.

* Model code is made available under the MIT license.
* Python dependencies are managed through `conda`.
* The code builds a `Streamlit` web application that can be used to run the calculator via a web app.

## Model

This model is based on calculations performed by GIRFT of the carbon footprint of the TUBRT pathway.

## Streamlit community cloud deployment

* https://ghg-emissions-calculator.streamlit.app/

> Please note that the calculator has been deployed to a free tier service.  If the app has not been used recently then you will need to wake up the app and wait while it reboots.

## Create local calculator interface

The following information describes an alternate method of running the calculator by creating a local copy.

### Download Code

Either clone the repository using git or click on the green "Code" button and select "Download Zip".

```bash
git clone https://github.com/hm7612g20/GHG_Emissions_Calculator.git
```

### Installing dependencies

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/release/python-3100+/)

All dependencies can be found in [`binder/environment.yml`]() and are pulled from conda-forge.  

Navigate to the directory containing the repo using your terminal/cmd prompt and issuing the command:

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

