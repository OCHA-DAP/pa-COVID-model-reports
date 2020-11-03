The code in this repository generates the metrics and figures for the [COVID-19 reports](https://drive.google.com/drive/u/1/folders/16FR8owccpfIm-tspdAa4YTEwPoZKHtvI) that the Centre for Humanitarian data shares with partners.

**Step 1. Generating updated metrics and figuress**

In order to update the analysis please follow the steps described in [Updating COVID reports](https://docs.google.com/document/d/172RZ29d9Uv3a-ohw6vIYqRA3QCG_1xCHlRC4r5H1B34/edit).

**Step 2. Creating the reports**

Country-specific PDF reports are automatically generated using R markdown. For step-by-step instructions, see [Updating COVID reports](https://docs.google.com/document/d/172RZ29d9Uv3a-ohw6vIYqRA3QCG_1xCHlRC4r5H1B34/edit).

**General notes on the data sources**  

We use data from three sources. We use historical data provided by WHO (national level) and the national Ministry of Public Health (subnational level). For both sources the reported numbers consist of cumulative cases and deaths  
For projections we use outputs from the model developed in cooperation with the APL of John Hopkins Univeristy  
The model outputs a wide range of variables, which can be divided in cumulative, active and new.   
Cumulative: the total number since the start of the pandemic. Cases and deaths are reported for this  
New: the new daily confirmations. Cases and deaths are reported for this.   
Active: the current active confirmations. Cases and hospitalizaitons are reported for this.   

Additional information on model outputs
For cases, a reporting rate is also calculated which estimates the percentage of cases that is reported. By using this rate, the reported cases can be converted to an estimated total cases.   
For deaths, it is assumed that the reported deaths equal the total deaths, i.e. there is no underreporting of deaths.  
For the model outputs, the cumulative cases on (TODAY - cumulative cases YESTERDAY) doesn't always exactly line up with the new cases TODAY. This is due to the fact that for producing the output the model is run multiple times after which the results are divided in quantiles.  
The new cases of TODAY might return negative values. This is due to initialization of the model and might be changed in the future. 


**Developer notes**

Since 27 October 2020, several column names of the `Bucky_results` were changed and these changes have been reflected in this repository. If using Bucky outputs that were generated before that day, use the code of commit `56871e063fd11f858a3140e2916b102b1d7a84a6` 
