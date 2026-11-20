# Cosmic History Explorer (Phase 1)

A standalone, bilingual (English/Russian) research module added alongside — not inside or in place of — the Earth System Trend Detective pipeline.

## Run
Open `index.html` in a modern browser. No build step, package installation, API key, server, or network request is required for the explorer itself. External source/catalogue links require internet access.

## What it does
- Compares published age estimates for HD 140283 (Methuselah).
- Plots central estimates and reported uncertainties where available.
- Shows the Planck-era Universe age as a reference line.
- Explains why estimates differ and why proximity does not imply youth.
- Exports the evidence register as JSON.
- Provides links to the Gaia Archive, MAST/TESS and SIMBAD.

## Evidence and interpretation
The estimates are not averaged. They are based on different stellar models, input abundances and constraints:
- Bond et al. (2013): 14.46 Gyr from parallax-only uncertainty; approximately ±0.8 Gyr after additional stellar-parameter and abundance uncertainties.
- Guillaume et al. (2024): 12.3 Gyr using abundance-tailored opacity tables; the abstract does not quote a symmetric uncertainty.
- Guillaume et al. (2025 workshop poster): 13.08 ± 0.85 Gyr; a preliminary 12.23 ± 0.51 Gyr when seismic data are included. These are labelled poster-stage results.
- Lundkvist et al. (2025): 14.2 ± 0.4 Gyr from TESS asteroseismology and BASTA modelling. The quoted uncertainty is internal; systematic effects are not fully included.

The reference Universe age is 13.787 ± 0.020 Gyr (Planck 2018 cosmological parameters, published 2020).

## Important limits
This is a curated literature explorer, not an independent stellar-age solver and not a live Gaia/TESS archive client. It does not claim that the star is older than the Universe. Error bars from different studies are not necessarily comparable. Do not average the values: their model assumptions and systematics differ.

## Sources
- Bond et al. 2013, ApJ: https://ui.adsabs.harvard.edu/abs/2013ApJ...765L..12B/abstract
- Guillaume et al. 2024, A&A: https://doi.org/10.1051/0004-6361/202451782
- Guillaume et al. 2025 workshop poster: https://orbi.uliege.be/handle/2268/334880
- Lundkvist et al. 2025, A&A 703, A232: https://doi.org/10.1051/0004-6361/202556292
- Planck Collaboration 2020: https://doi.org/10.1051/0004-6361/201833910
- Gaia Archive: https://gea.esac.esa.int/archive/
- MAST/TESS: https://mast.stsci.edu/portal/Mashup/Clients/Mast/Portal.html
- SIMBAD object record: https://simbad.cds.unistra.fr/simbad/sim-id?Ident=HD%20140283

## Scope
This module is an independent Phase 1 extension. It does not alter `science_core`, the existing Earth-observation desktop workflow, Android wrapper, or the default `main` branch.
