#!/bin/bash
for iso3 in AFG SSD SDN COD SOM
do
    python generate_charts_report.py -d $iso3
done