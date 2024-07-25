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
