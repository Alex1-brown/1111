# Data, software, and attribution

This file records the sources and reuse notes for the project submission. Check the current provider metadata and product DOI pages again before redistributing any source assets.

## Project source code

The original project code is released under the MIT License in [LICENSE](LICENSE).

## NASA data products

### MODIS/Terra MOD13Q1 Version 6.1

- Product: MODIS/Terra Vegetation Indices 16-Day L3 Global 250 m SIN Grid, Version 6.1.
- DOI and authoritative product landing page: https://doi.org/10.5067/MODIS/MOD13Q1.061
- Product producer/distributor: NASA LP DAAC.
- Citation: use the product-specific citation supplied by the DOI landing page and credit NASA LP DAAC.
- LP DAAC guidance states that current LP DAAC data products have no restrictions on reuse, sale, or redistribution, while requesting proper citation: https://lpdaac.usgs.gov/data/data-citation-and-policies/

The current Microsoft Planetary Computer STAC collection metadata has been observed to declare its collection license as `proprietary`, while identifying NASA LP DAAC as the producer/licensor/processor. The project therefore records both the NASA product DOI and the mirror's collection metadata. Do not assume that a hosting mirror's metadata can be ignored: before redistributing downloaded COG source files, check the current collection-specific terms. The project submission should prefer derived statistics, charts, and provenance metadata over republishing source COG assets.

## NASA POWER

- Source: NASA POWER Daily API.
- Documentation: https://power.larc.nasa.gov/docs/services/api/temporal/daily/
- Cite NASA POWER and the specific parameters, coordinates, temporal interval, and retrieval date in any report using the downloaded data.

## Third-party software

Runtime dependencies are listed in [requirements.txt](requirements.txt). Their own upstream licenses and notices remain applicable; the project's MIT license does not replace or relicense third-party packages.

- Pillow: https://pillow.readthedocs.io/
- Rasterio: https://rasterio.readthedocs.io/

## AI assistance disclosure

AI tools assisted with implementation, code review, statistical-method review, and documentation. Scientific observations are retrieved from the cited NASA data services and are not AI-generated. AI assistance does not replace independent scientific review. No NASA logo, insignia, or NASA-branded visual asset is AI-generated or modified.
