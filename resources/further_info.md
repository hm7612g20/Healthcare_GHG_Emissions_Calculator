**GHG emissions calculated as sum of:**
- GHG emissions from manufacture of product given its raw components.
- Travel GHG emissions of raw materials from source to end location.
- GHG emissions of product during use if it requires electricity, water or gas.
- Reprocessing GHG emissions of product, if applicable.
- GHG emissions from disposal of product, either by landfill, incineration or recycling.

#### Calculation details
Each product is made up of components, where each component specifies manufacture year, mass, no. uses (may change if packaging is included), manufacture location, port where it departs country of manufacture (if applicable), location in UK where it travels to end location

Emissions are calculated per use, where emissions value is divided by the number of times the product can be used.

**Manufacture:**
- Component emissions = emissions factor * (mass / no. uses)
- Product emissions = sum of component emissions

**Travel:**
- Component emissions = (mass * distance travelled * travel factor) / no. uses
- Product emissions = sum of component emissions

**Use:**
- Electricity use emissions = (electricity generation factor + generation well-to-tank (WTT) factor + electricity transmission & distribution factor + T&D WTT factor) * electricity use (kwh)
- Water use emissions = (water treatment factor + water supply factor) * water volume (L)
- Gas use emissions = (gas fuel factor + WTT factor) * gas use (m$^{3}$)

**Reprocessing:**
- Laundry emissions = mass * laundry factor per kg laundry
- HSDU emissions = percentage fill of decontamination unit * decontamination factor
	- Decontamination factor = [(electricity generation factor + generation well-to-tank (WTT) factor + electricity transmission & distribution factor + T&D WTT factor) * electricity use of decontamination unit (kwh)] + [(water treatment factor + water supply factor) * water use of decontamination unit (L)] + [(gas fuel factor + WTT factor) * gas use of decontamination unit (m$^{3}$)]

**Disposal:**
- Incineration emissions = [(mass / 12.01) * 44.01 (mass of CO$_{2}$)] + (mass * disposal transport factor per kg)
- Recycling emissions = mass * disposal transport factor per kg
- Landfill emissions = (mass * landfill factor per kg landfill) + (mass * disposal transport factor per kg)
- Biogenic emissions = (mass / 12.01) * 44.01 for biogenic components
- Net waste = incineration + recycling + landfill - biogenic

#### Assumptions
- Travel is split into stages:
	- Manufacture location of components to port where components leaves country of manufacture (if applicable)
	- Departure port to UK port (if applicable) or manufacture location to point in UK where it travels to end location for UK based product.
	- Users can additionally add calculations of emissions corresponding to the travel between the point in UK where it dpearts from and the approximate end location of the product.
	 - It is assumed that the product is made somewhere along this route and it does not need to be transported elsewhere for manufacture.
- HSDU reprocessing is calculated using percentage filling of decontamination unit. It is assumed the autoclave is full to capacity based on this value.
- Biogenic emissions are subtracted from other disposal emissions as this accounts for the CO$_{2}$ that was originally absorbed by plants during their growth to produce the component. Therefore, the emissions are considered to be part of the natural cycle and so do not contribute to increasing atmospheric CO$_{2}$ levels in the same way as fossil fuel emissions.
