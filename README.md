# MIRACA

[MIRACA](https://miraca-project.eu) (Multi-hazard Infrastructure Risk Assessment
for Climate Adaptation) is a research project building an evidence-based decision
support toolkit that meets real world demands.

This project has received funding from the European Union’s Horizon Europe research
programme under grant agreement No 101004174.

### Deliverable 2.3: Mapping lifeline network supply and demands to locations of other CI and societal actors. 

## Short Overview

This program is part of the MIRACA Project – Deliverable 2.3, which focuses on mapping lifeline network supply and demands to locations of other critical infrastructure (CI) and societal actors. The energy modelling component of this framework is essential to integrating production units and consumers into the network model and preserving the robustness, scalability, and consistency of the representation of the energy system.

This work provides a methodology for assessing network resilience through the power flow analysis and is based on the core concepts of PyPSA-EUR (Hörsch et al., 2018). We achieve this by enhancing the technical precision and realism of supply-demand analysis through the use of open-source datasets, innovative mapping techniques, and fallback mechanisms. This framework provides a flexible and scalable model for understanding and improving the resilience of the European energy system through the use of dynamic demand modelling and high-resolution transmission grid data.

## Accessibility

The energy modelling program including the neccesary data can also be found in the Zenodo Repository: MIRACA Energy Modelling D2.3, https://doi.org/10.5281/zenodo.15659119 (DOI). 

However, when utilizing the model from GitHub Repozitory, it is essential to download the dataset separately from https://doi.org/10.5281/zenodo.15657306 (DOI), as the repository does not include the required data.

## Acknowledgments
This project utilizes the following datasets, scripts, and tools:

- Prebuilt electricity network for PyPSA-Eur based on OpenStreetMap data [1] from Zenodo repository (version 0.6): https://doi.org/10.5281/zenodo.14144752  
- PyPSA-Eur scripts [2]
- OPSD time series dataset [3]
- Powerplantmatching database [4]
- NUTS datasets and territorial statistical units [5]
- geoBoundaries data for NUTS and non-NUTS regions [6]
- Pandapower electricity modeling tool [7]
- European Energy Exchange (EEX) Auctions dataset [8]
- Costs dataset from PyPSA [9]
- Gross Domestic Product (GDP) data by NUTS 3 region [10]
- Regional population data for GDP calculations [11]
- Data on energy price trends from Destatis [12]
- Extracted UK NUTS from Eurostat 2021 dataset [13]

### References:
[1] Hörsch, J., Hofmann, F., Schlachtberger, D., & Brown, T. (2025). PyPSA-EUR: An open optimization model of the European transmission system. Scientific Data, 12(4), Article 2. https://doi.org/10.1038/s41597-025-04550-7  
[2] Hörsch, J., Hofmann, F., Schlachtberger, D., & Brown, T. (2018). PyPSA-Eur: An open optimization model of the European transmission system [Preprint]. arXiv. https://doi.org/10.48550/arXiv.1806.01613  
[3] Open Power System Data. (2020). Time series dataset (Version 2020-10-06) [Data set]. https://open-power-system-data.org/  
[4] Gotzens, F., Heinrichs, H., Hörsch, J., & Hofmann, F. (2019). Performing energy modeling exercises in a transparent way – The issue of data quality in power plant databases. Energy Strategy Reviews, 23, 1–12. https://doi.org/10.1016/j.esr.2018.11.004  
[5] Eurostat. (2025). NUTS – Nomenclature of Territorial Units for Statistics [Web page]. https://ec.europa.eu/eurostat/web/nuts/overview  
[6] Runfola, D., Anderson, A., Baier, H., Crittenden, M., Dowker, E., Fuhrig, S., et al. (2020). geoBoundaries: A global database of political administrative boundaries. PLOS ONE, 15(4), e0231866. https://doi.org/10.1371/journal.pone.0231866  
[7] Thurner, L., Scheidler, A., Schäfer, F., et al. (2018). pandapower – an Open Source Python Tool for Convenient Modeling, Analysis and Optimization of Electric Power Systems. IEEE Transactions on Power Systems, 33(6), 6510–6521. https://doi.org/10.1109/TPWRS.2018.2829021  
[8] European Energy Exchange (EEX). (2025). EU ETS Auctions: Emission Spot Primary Market Auction Report 2012–2024 [Report]. https://www.eex.com/en/markets/environmental-markets/eu-ets-auctions  
[9] PyPSA. (2020). Costs dataset [Data file]. GitHub repository.  https://github.com/PyPSA/technology-data/blob/master/outputs/costs_2020.csv  
[10] Eurostat. (2025). Gross Domestic Product (GDP) at current market prices by NUTS 3 region [Data set]. https://doi.org/10.2908/NAMA_10R_3GDP  
[11] Eurostat. (2025). Regional population and GDP data: NAMA_10R_3POPGDP & NAMA_10R_3GDP [Data set]. https://doi.org/10.2908/NAMA_10R_3POPGDP  
[12] German Federal Statistical Office (Destatis). (2025). Energy price trends [Data file]. https://www.destatis.de/EN/Themes/Economy/Prices/Publications/Downloads-Energy-Price-Trends/energy-price-trends-xlsx-5619002.xlsx    
[13] Hörsch, J., Hofmann, F., Schlachtberger, D., Glaum, P., Neumann, F., Brown, T., Riepin, I., & Xiong, B. (2025). Data bundle for PyPSA-Eur: An Open Optimisation Model of the European Transmission System (Version v0.6.0) [Data set]. Zenodo. https://zenodo.org/records/15143557
