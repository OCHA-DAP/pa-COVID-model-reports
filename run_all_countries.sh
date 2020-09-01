#!/bin/bash
for iso3 in AFG SSD SDN COD SOM IRQ
do
    python generate_charts_report.py $iso3 -d
    # python generate_charts_report.py $iso3
done