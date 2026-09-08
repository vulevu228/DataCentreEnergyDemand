"""Extraction package: one module per source, plus join.py to merge them.

  net.py     shared HTTP GET with retry/back-off (named `net`, not `http`, to
             avoid shadowing the standard-library `http` package)
  eia.py     US hourly load per balancing authority / sub-BA (EIA Open Data v2)
  entsoe.py  EU actual total load per bidding zone (ENTSO-E Transparency, XML)
  hf.py      Hugging Face public-model growth, used as an AI-compute proxy
  join.py    reshape the three into the tidy panel + derived metrics

Entry point is ../run_extract.py (run from the repo root). See ../METHODOLOGY.md
for what each fetcher is supposed to return.
"""
