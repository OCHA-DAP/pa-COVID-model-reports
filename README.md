The code in this repository generates the metrics and figures for the [COVID-19 reports](https://drive.google.com/drive/u/1/folders/16FR8owccpfIm-tspdAa4YTEwPoZKHtvI) that the Centre for Humanitarian data shares with partners.

**Step 1. Generating updated metrics and figuress**

In order to update the analysis please follow the steps described in [Updating COVID reports](https://docs.google.com/document/d/172RZ29d9Uv3a-ohw6vIYqRA3QCG_1xCHlRC4r5H1B34/edit).

**Step 2. Creating the reports**

Country-specific PDF reports are automatically generated using R markdown. For step-by-step instructions, see [Updating COVID reports](https://docs.google.com/document/d/172RZ29d9Uv3a-ohw6vIYqRA3QCG_1xCHlRC4r5H1B34/edit).

**General notes on the data sources:**  
We use data from three sources. We use historical data provided by WHO (national level) and the national Ministry of Public Health (subnational level). For both sources the reported numbers consist of cumulative cases and deaths  
For projections we use outputs from the model developed in cooperation with the APL of John Hopkins Univeristy  
The model outputs a wide range of variables, which can be divided in cumulative, active and new.   
Cumulative: the total number since the start of the pandemic. Cases and deaths are reported for this  
New: the new daily confirmations. Cases and deaths are reported for this.   
Active: the current active confirmations. Cases and hospitalizaitons are reported for this.   

For cases, a reporting rate is also calculated which estimates the percentage of cases that is reported. By using this rate, the reported cases can be converted to an estimated total cases.   
