**File should be a .csv file (can be saved from an Excel spreadsheet) in the following format:**

*Please ensure there are no spaces after the comma separating the data columns!*

product, category, electricity, water, gas, component_1, manu_year_1, mass_kg_1, no_uses_1, biogenic_1, manu_loc_1, debark_port_1, depart_loc_uk_1, reprocessing_1, recycle_1, incinerate_1, landfill_1

Number of components per product can be changed by adding new columns (i.e. component_2, manu_year_2, mass_kg_2, no_uses_2, biogenic_2, manu_loc_2, debark_port_2, depart_loc_uk_2, reprocessing_2, recycle_2, incinerate_2, landfill_2)

The columns should be filled as follows:
- product: name of the product
- category: type of product
- electricity: 1 (p t) if electricity used during its lifetime, where p = power rating of product (W) and t = time per use (hr), 0 if not
- water: 1 (w) if water used during its lifetime, where w = water used per use (L), 0 if not
- gas: 1 (g) if gas used during its lifetime, where g = gas used by product (m$^{3}$), 0 if not
- component_{number}: name of component material/process (e.g. injection moulding) used to make product
- manu_year_{number}: year of manufacture
- mass_kg_{number}: mass in kg of component
- no_uses_{number}: number of uses of component
- biogenic_{number}: 1 if has a biogenic component, 0 if not
- manu_loc_{number}: manufacture location of componen using the format: city (country)
- debark_port_{number}: debarkation port of component if required, using the format: city (country), 0 if not required
- depart_loc_uk_{number}: where component begins journey in UK, using the format: city
- reprocessing_{number}: reprocessing type if applicable, 0 if not. Reprocessing options are: laundry or hsdu (% fill), where % fill = percentage filling of autoclave and is given inside brakets
- recycle_{number}: 1 if component recycled at the end of its lifetime, 0 if not
- incinerate_{number}: 1 if component incinerated at the end of its lifetime, 0 if not
- landfill_{number}: 1 if component disposed of in landfill at the end of its lifetime, 0 if not
