"""
This script expects to have access to the COVID model results, and outputs charts for the template.
"""

# Imports
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns; sns.set()
import geopandas
from datetime import timedelta, date
sns.set_style("white")

# Set global parameters

COUNTRY = 'AFG' # Can be one of AFG, SSD, CAR, SOM, COD
COUNTRY_2L = 'AF'

# NPI_ADMIN0 = pd.read_csv('../ocha_run2_viz/'+COUNTRY+'_npi/adm0_quantiles.csv')
# NPI_ADMIN1 = pd.read_csv('../ocha_run2_viz/'+COUNTRY+'_npi/adm1_quantiles.csv')
# NO_NPI_ADMIN0 = pd.read_csv('../ocha_run2_viz/'+COUNTRY+'_no_npi/adm0_quantiles.csv')
# NO_NPI_ADMIN1 = pd.read_csv('../ocha_run2_viz/'+COUNTRY+'_no_npi/adm1_quantiles.csv')

# confirmed_cases = pd.read_csv("../time_series/time_series_covid19_confirmed_global.csv")
# confirmed_deaths = pd.read_csv("../time_series/time_series_covid19_deaths_global.csv")
# confirmed_cases = confirmed_cases.loc[confirmed_cases['Country/Region'] == 'Afghanistan']
# confirmed_deaths = confirmed_deaths.loc[confirmed_deaths['Country/Region'] == 'Afghanistan']

# SHAPE = geopandas.read_file('../afg_admbnda_adm1_agcho_20180522/afg_admbnda_adm1_agcho_20180522.shp')

# TODAY = date.today()
# TWO_WEEKS = TODAY + timedelta(days=14)

# LABELS = []
# for k, v in enumerate(NPI_ADMIN0['date'].unique()):
#     if k % 5 == 0:
#         LABELS.append(v.replace('2020-',''))
#     else:
#         LABELS.append('')

# def parse_args():
#     parser = argparse.ArgumentParser()
#     parser.add_argument('-d', '--download-covid', action='store_true',
#                         help='Download the COVID-19 data')
#     return parser.parse_args()

# def create_mitigation_chart():
#     plt.figure(figsize=(8, 4))
#     ax = sns.lineplot(x="date", y="daily_cases", data=NPI_ADMIN0, label='NPIs')
#     ax1 = sns.lineplot(x="date", y="daily_cases", data=NO_NPI_ADMIN0, label='NO NPIs')
#     ax.set(xticklabels=LABELS, xlabel="", ylabel="Daily Cases", title='Daily new Covid-19 cases in Afghanistan')
#     plt.savefig('npis_daily_cases_' + COUNTRY + '.png')
#     return None


def create_current_status_charts():
    # Confirmed cases
    cases_afg=pd.read_csv('')
    print(cases_afg)
    # cases_afg = pd.DataFrame(columns=['date', 'confirmed_cases'])
#     cases_afg['date'] = confirmed_cases.columns[4:]
#     cases_afg['date'] = pd.to_datetime(cases_afg['date'])
#     cases_afg['confirmed_cases'] = confirmed_cases.values[0][4:]
#     cases_afg.set_index('date', inplace=True)
#     plt.figure(figsize=(8,4))
#     cases_afg.plot(color='blue')
#     plt.savefig('current_confirmed_cases_'+COUNTRY+'.png')

#     # Confirmed deaths
#     deaths_afg = pd.DataFrame(columns=['date', 'confirmed_deaths'])
#     deaths_afg['date'] = confirmed_deaths.columns[4:]
#     deaths_afg['date'] = pd.to_datetime(deaths_afg['date'])
#     deaths_afg['confirmed_deaths'] = confirmed_deaths.values[0][4:]
#     deaths_afg.set_index('date', inplace=True)
#     plt.figure(figsize=(8, 4))
#     deaths_afg.plot(color='red')
#     plt.savefig('current_confirmed_deaths_' + COUNTRY + '.png')
#     return None


# def create_national_projections_charts():
#     '''
#     Save charts for new daily cases, cumulative cases, severe cases, and cumulative deaths
#     '''

#     # New daily cases
#     plt.figure(figsize=(8, 4))
#     ax = sns.lineplot(x="date", y="daily_cases", data=NPI_ADMIN0)
#     ax.set(xticklabels=LABELS, xlabel="", ylabel="Daily Cases", title='Daily new Covid-19 cases in Afghanistan')
#     plt.savefig('new_daily_cases_'+COUNTRY+'.png')

#     # Cumulative cases
#     plt.figure(figsize=(8, 4))
#     ax = sns.lineplot(x="date", y="cumulative_cases", data=NPI_ADMIN0)
#     ax.set(xticklabels=LABELS, xlabel="", ylabel="Cumulative Cases", title='Cumulative Covid-19 cases in Afghanistan')
#     plt.savefig('cumulative_cases_'+COUNTRY+'.png')

#     # Severe cases
#     plt.figure(figsize=(8, 4))
#     ax = sns.lineplot(x="date", y="hospitalizations", data=NPI_ADMIN0, color='orange')
#     ax.set(xticklabels=LABELS, xlabel="", ylabel="Severe Cases", title='Covid-19 severe cases in Afghanistan')
#     plt.savefig('severe_cases_' + COUNTRY + '.png')

#     # Cumulative deaths
#     plt.figure(figsize=(8, 4))
#     ax = sns.lineplot(x="date", y="cumulative_deaths", data=NPI_ADMIN0, color='red')
#     ax.set(xticklabels=LABELS, xlabel="", ylabel="Cumulative Deaths", title='Cumulative Covid-19 deaths in Afghanistan')
#     plt.savefig('cumulative_deaths_' + COUNTRY + '.png')
#     return None


# def create_maps(SHAPE=SHAPE):
#     # New Cases
#     NPI_ADMIN1['datetime'] = pd.to_datetime(NPI_ADMIN1['date'])
#     reg_2weeks = NPI_ADMIN1.loc[(NPI_ADMIN1['datetime'] >= TODAY) & (NPI_ADMIN1['datetime'] <= TWO_WEEKS) & (NPI_ADMIN1['q'] == 0.5)]
#     reg_2weeks_grp = reg_2weeks[['adm1', 'daily_cases', 'cases_active', 'daily_deaths']].groupby(
#         'adm1').sum().reset_index()
#     reg_2weeks_grp['adm1'] = COUNTRY_2L+ reg_2weeks_grp['adm1'].apply(lambda x:  "{0:0=2d}".format(int(x)))
#     SHAPE = SHAPE.merge(reg_2weeks_grp, left_on='ADM1_PCODE', right_on='adm1', how='left')
#     plt.figure(figsize=(8, 4))
#     ax = SHAPE.plot(column='cases_active', cmap='Blues', figsize=(10, 10), edgecolor='gray')
#     ax.set(title="Active Cases Two Weeks Projection in Afghanistan")
#     plt.savefig('active_cases_map.png')

#     # Daily Deaths
#     plt.figure(figsize=(8,4))
#     ax = SHAPE.plot(column='daily_cases', cmap='Reds', figsize=(10, 10), edgecolor='gray')
#     ax.set(title="Daily Cases Two Weeks Projection in Afghanistan")
#     plt.savefig('daily_cases_map.png')

#     return None


# def create_trends_chart():
#     return None


if __name__=='__main__':
    create_current_status_charts()
    # create_national_projections_charts()
    # create_mitigation_chart()
    # create_maps()
    # create_trends_chart()

