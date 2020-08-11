The code in this repository generates the analysis and the figures for the [COVID-19 reports](https://drive.google.com/drive/u/1/folders/16FR8owccpfIm-tspdAa4YTEwPoZKHtvI) that the Centre for Humanitarian data is sharing with partners.
In order to update the analysis please follow the following steps:
1. Make sure you have the latest results from the Bucky model in the *Bucky_results* folder
2. Set the ASSESSMENT_DATE variable in *generate_charts_report.py* to the desired date. The assessment date should correspond to the latest date of the data used to seed the simulations.
3. Run the *generate_charts_report.py* with the -d option to automatically update the WHO data. Alternatively you can run the *run_all_countries.sh* script to update all countries.