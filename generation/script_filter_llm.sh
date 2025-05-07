#!/bin/bash

# Define years to process
YEARS=(1994 1995 1996 1997 1998 1999 2000 2001 2002 2003 2004 2005 2006)

# Process each year sequentially
for YEAR in "${YEARS[@]}"; do
    echo "Processing year: $YEAR"
    python filter_llm.py "data_arxiv/cond-mat/parsed/$YEAR/" --port 8010
done