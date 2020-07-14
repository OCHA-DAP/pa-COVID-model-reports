from matplotlib.pyplot import title
import utils
import os
import argparse
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import requests
import geopandas
from datetime import timedelta, date

from utils import set_matlotlib

CONFIG_FILE = 'config.yml'
DIR_PATH = os.path.dirname(os.path.realpath(__file__))
WHO_COVID_URL='https://docs.google.com/spreadsheets/d/e/2PACX-1vSe-8lf6l_ShJHvd126J-jGti992SUbNLu-kmJfx1IRkvma_r4DHi0bwEW89opArs8ZkSY5G2-Bc1yT/pub?gid=0&single=true&output=csv'
WHO_COVID_FILENAME=WHO_COVID_FILENAME='WHO_data/Data_ WHO Coronavirus Covid-19 Cases and Deaths - WHO-COVID-19-global-data.csv'

HLX_TAG_TOTAL_CASES = "#affected+infected+confirmed+total"
HLX_TAG_TOTAL_DEATHS = "#affected+infected+dead+total"
HLX_TAG_DATE = "#date"

FIG_SIZE=(8,6)

TODAY = date.today()
FOUR_WEEKS = TODAY + timedelta(days=28)
THREE_MONTHS = TODAY + timedelta(days=90)
LAST_MONTH = TODAY - timedelta(days=30)

NPI_COLOR='green'
NO_NPI_COLOR='red'
WHO_DATA_COLOR='dodgerblue'
SUBNATIONAL_DATA_COLOR='navy'

def main(country_iso3='AFG',download_covid=False):
    parameters = utils.parse_yaml(CONFIG_FILE)[country_iso3]
    if download_covid:
    # Download latest covid file tiles and read them in
        get_covid_data(WHO_COVID_URL,f'{DIR_PATH}/{WHO_COVID_FILENAME}')
    set_matlotlib(plt)

    generate_key_figures(country_iso3)
    generate_current_status(country_iso3,parameters)
    generate_daily_projections(country_iso3,parameters)
    create_maps(country_iso3, parameters)
    calculate_trends(country_iso3, parameters)
    plt.show()

def download_url(url, save_path, chunk_size=128):
    r = requests.get(url, stream=True)
    with open(save_path, 'wb') as fd:
        for chunk in r.iter_content(chunk_size=chunk_size):
            fd.write(chunk)
    print(f'Downloaded "{url}" to "{save_path}"')

def get_covid_data(url, save_path):
    # download covid data from HDX
    print(f'Getting upadated COVID data from WHO')
    try:
        download_url(url, save_path)
    except Exception:
        print(f'Cannot download COVID file from from HDX')

def get_bucky(country_iso3,admin_level,min_date,max_date,npi_filter):
    # get bucky with NPIs 
    bucky_npi=pd.read_csv(f'Bucky_results/{country_iso3}_{npi_filter}/{admin_level}_quantiles.csv')
    bucky_npi['date']=pd.to_datetime(bucky_npi['date']).dt.date
    bucky_npi=bucky_npi[(bucky_npi['date']>=min_date) &\
                        (bucky_npi['date']<=max_date)]
    bucky_npi=bucky_npi.set_index('date')
    return bucky_npi

def generate_key_figures(country_iso3):

    who_covid=get_who_covid(country_iso3,min_date=LAST_MONTH,max_date=FOUR_WEEKS)
    who_deaths_today=who_covid.loc[TODAY,'CumDeath']
    who_cases_today=who_covid.loc[TODAY,'CumCase']
    print(f'Current situation {TODAY}: {who_cases_today:.0f} cases, {who_deaths_today:.0f} deaths')

    bucky_npi=get_bucky(country_iso3,admin_level='adm0',min_date=TODAY,max_date=THREE_MONTHS,npi_filter='npi')
    reporting_rate=bucky_npi['CASE_REPORT'].mean()*100
    reff_npi=bucky_npi['Reff'].mean()
    min_cases_npi=bucky_npi[bucky_npi['q']==0.25].loc[FOUR_WEEKS,'cumulative_cases_reported']
    max_cases_npi=bucky_npi[bucky_npi['q']==0.75].loc[FOUR_WEEKS,'cumulative_cases_reported']
    min_deaths_npi=bucky_npi[bucky_npi['q']==0.25].loc[FOUR_WEEKS,'cumulative_deaths']
    max_deaths_npi=bucky_npi[bucky_npi['q']==0.75].loc[FOUR_WEEKS,'cumulative_deaths']
    print(f'- Projection date:{FOUR_WEEKS}')
    
    print(f'- ESTIMATED CASE REPORTING RATE {reporting_rate:.2f}')
    print(f'-- NPI: ESTIMATED Reff NPI {reff_npi:.2f}')
    print(f'-- NPI: Projected reported cases in 4w: {min_cases_npi:.0f} - {max_cases_npi:.0f}')
    print(f'-- NPI: Projected reported deaths in 4w: {min_deaths_npi:.0f} - {max_deaths_npi:.0f}')
    
    bucky_no_npi=get_bucky(country_iso3,admin_level='adm0',min_date=TODAY,max_date=THREE_MONTHS,npi_filter='no_npi')
    reff_no_npi=bucky_no_npi['Reff'].mean()
    min_cases_no_npi=bucky_no_npi[bucky_no_npi['q']==0.25].loc[FOUR_WEEKS,'cumulative_cases_reported']
    max_cases_no_npi=bucky_no_npi[bucky_no_npi['q']==0.75].loc[FOUR_WEEKS,'cumulative_cases_reported']
    min_deaths_no_npi=bucky_no_npi[bucky_no_npi['q']==0.25].loc[FOUR_WEEKS,'cumulative_deaths']
    max_deaths_no_npi=bucky_no_npi[bucky_no_npi['q']==0.75].loc[FOUR_WEEKS,'cumulative_deaths']
    # print(bucky_no_npi.loc[FOUR_WEEKS,:])
    print(f'--- no_npi: ESTIMATED Reff no_npi {reff_no_npi:.2f}')
    print(f'--- no_npi: Projected reported cases in 4w: {min_cases_no_npi:.0f} - {max_cases_no_npi:.0f}')
    print(f'--- no_npi: Projected reported deaths in 4w: {min_deaths_no_npi:.0f} - {max_deaths_no_npi:.0f}')
    

def generate_daily_projections(country_iso3,parameters):
    # generate plot with long term projections of daily cases
    bucky_npi=get_bucky(country_iso3,admin_level='adm0',min_date=TODAY,max_date=THREE_MONTHS,npi_filter='npi')
    bucky_no_npi=get_bucky(country_iso3,admin_level='adm0',min_date=TODAY,max_date=THREE_MONTHS,npi_filter='no_npi')

    # draw_daily_projections(country_iso3,bucky_npi,bucky_no_npi,parameters,'daily_cases_reported')
    # draw_daily_projections(country_iso3,bucky_npi,bucky_no_npi,parameters,'daily_deaths')
    draw_daily_projections(country_iso3,bucky_npi,bucky_no_npi,parameters,'hospitalizations')

def draw_daily_projections(country_iso3,bucky_npi,bucky_no_npi,parameters,metric):
    # draw NPI vs non NPIs projections
    if metric=='daily_cases_reported':
        bucky_var='daily_cases_reported'
        fig_title='Daily reported cases'
    elif metric=='daily_deaths':
        bucky_var='daily_deaths'
        fig_title='Daily deaths'
    elif metric=='hospitalizations':
        bucky_var='hospitalizations'
        fig_title='People requiring healthcare support'
    else:
        print(f'metric {metric} not implemented')
        return

    fig,axis=create_new_subplot(fig_title)
    # draw line NPI
    bucky_npi_median=bucky_npi[bucky_npi['q']==0.5][bucky_var]
    bucky_npi_reff=bucky_npi['Reff'].mean()
    bucky_npi_median.plot(c=NPI_COLOR,ax=axis,label='Keeping current NPIs ( Reff= {:.2f})'.format(bucky_npi_reff))
    axis.fill_between(bucky_npi_median.index,\
                          bucky_npi[bucky_npi['q']==0.25][bucky_var],
                          bucky_npi[bucky_npi['q']==0.75][bucky_var],
                          color=NPI_COLOR,alpha=0.2
                          )
    # draw line NO NPI
    bucky_no_npi_cases_median=bucky_no_npi[bucky_no_npi['q']==0.5][bucky_var]
    bucky_no_npi_reff=bucky_no_npi['Reff'].mean()
    bucky_no_npi_cases_median.plot(c=NO_NPI_COLOR,ax=axis,label='Back to normal ( Reff= {:.2f})'.format(bucky_no_npi_reff))
    axis.fill_between(bucky_no_npi_cases_median.index,\
                          bucky_no_npi[bucky_no_npi['q']==0.25][bucky_var],
                          bucky_no_npi[bucky_no_npi['q']==0.75][bucky_var],
                          color=NO_NPI_COLOR,alpha=0.2
                          )
    plt.legend()
    print(f'----{metric} statistics')
    metric_today_min=bucky_no_npi[bucky_no_npi['q']==0.25].loc[TODAY,bucky_var]
    metric_today_max=bucky_no_npi[bucky_no_npi['q']==0.75].loc[TODAY,bucky_var]
    metric_4w_npi_min=bucky_npi[bucky_npi['q']==0.25].loc[FOUR_WEEKS,bucky_var]
    metric_4w_npi_max=bucky_npi[bucky_npi['q']==0.75].loc[FOUR_WEEKS,bucky_var]
    metric_4w_no_npi_min=bucky_no_npi[bucky_no_npi['q']==0.25].loc[FOUR_WEEKS,bucky_var]
    metric_4w_no_npi_max=bucky_no_npi[bucky_no_npi['q']==0.75].loc[FOUR_WEEKS,bucky_var]
    print(f'----{metric} {TODAY}: {metric_today_min:.0f} - {metric_today_max:.0f}')
    print(f'----{metric} NPI {FOUR_WEEKS}: {metric_4w_npi_min:.0f} - {metric_4w_npi_max:.0f}')
    print(f'----{metric} NO NPI {FOUR_WEEKS}: {metric_4w_no_npi_min:.0f} - {metric_4w_no_npi_max:.0f}')
    fig.savefig(f'Outputs/{country_iso3}/projection_{metric}.png')

def get_subnational_covid(parameters,aggregate,min_date,max_date):
    # get subnational from COVID parameterization repo
    subnational_covid=pd.read_csv(parameters['subnational_cases_url'])
    subnational_covid[HLX_TAG_DATE]=pd.to_datetime(subnational_covid[HLX_TAG_DATE]).dt.date
    subnational_covid=subnational_covid[(subnational_covid[HLX_TAG_DATE]>=min_date) &\
                                        (subnational_covid[HLX_TAG_DATE]<=max_date)]
    if aggregate:
        subnational_covid=subnational_covid.groupby(HLX_TAG_DATE).sum()
    return subnational_covid

def get_who_covid(country_iso3,min_date,max_date):
    # Get national level data from WHO
    who_covid=pd.read_csv(WHO_COVID_FILENAME)
    who_covid=who_covid[who_covid['ISO_3_CODE']==country_iso3]
    who_covid['date_epicrv']=pd.to_datetime(who_covid['date_epicrv']).dt.date
    who_covid=who_covid[(who_covid['date_epicrv']>=min_date) &\
                        (who_covid['date_epicrv']<=max_date)]
    who_covid=who_covid.set_index('date_epicrv')
    return who_covid

def generate_current_status(country_iso3,parameters):
    # generate plot with subnational data, WHO data and projections
    subnational_covid=get_subnational_covid(parameters,aggregate=True,min_date=LAST_MONTH,max_date=FOUR_WEEKS)
    who_covid=get_who_covid(country_iso3,min_date=LAST_MONTH,max_date=FOUR_WEEKS)
    bucky_npi=get_bucky(country_iso3,admin_level='adm0',min_date=LAST_MONTH,max_date=FOUR_WEEKS,npi_filter='npi')
    bucky_no_npi=get_bucky(country_iso3,admin_level='adm0',min_date=LAST_MONTH,max_date=FOUR_WEEKS,npi_filter='no_npi')
    
    draw_current_status(country_iso3,subnational_covid,who_covid,bucky_npi,bucky_no_npi,parameters,'cumulative_reported_cases')
    draw_current_status(country_iso3,subnational_covid,who_covid,bucky_npi,bucky_no_npi,parameters,'cumulative_deaths')

def draw_current_status(country_iso3,subnational_covid,who_covid,bucky_npi,bucky_no_npi,parameters,metric):
    # plot the 4 inputs and save figure
    if metric=='cumulative_reported_cases':
        who_var='CumCase'
        bucky_var='cumulative_cases_reported'
        subnational_var=HLX_TAG_TOTAL_CASES
        subnational_source=parameters['subnational_cases_source']
        fig_title='Cumulative reported cases'
    elif metric=='cumulative_deaths':
        who_var='CumDeath'
        bucky_var='cumulative_deaths'
        subnational_var=HLX_TAG_TOTAL_DEATHS
        subnational_source=parameters['subnational_cases_source']
        fig_title='Cumulative reported deaths'
    else:
        print(f'metric {metric} not implemented')

    fig,axis=create_new_subplot(fig_title)

    # draw subnational reported cumulative cases
    axis.scatter(who_covid.index, who_covid[who_var],\
                     alpha=0.8, s=20,c=WHO_DATA_COLOR,marker='*',label='WHO')
    axis.scatter(subnational_covid.index, subnational_covid[subnational_var],\
                     alpha=0.8, s=20,c=SUBNATIONAL_DATA_COLOR,marker='o',label=subnational_source)
    # draw line NPI
    bucky_npi_median=bucky_npi[bucky_npi['q']==0.5][bucky_var]
    bucky_npi_reff=bucky_npi['Reff'].mean()
    bucky_npi_median.plot(c=NPI_COLOR,ax=axis,label='Keeping current NPIs ( Reff= {:.2f})'.format(bucky_npi_reff))
    axis.fill_between(bucky_npi_median.index,\
                          bucky_npi[bucky_npi['q']==0.25][bucky_var],
                          bucky_npi[bucky_npi['q']==0.75][bucky_var],
                          color=NPI_COLOR,alpha=0.2
                          )
    # draw line NO NPI
    bucky_no_npi_cases_median=bucky_no_npi[bucky_no_npi['q']==0.5][bucky_var]
    bucky_no_npi_reff=bucky_no_npi['Reff'].mean()
    bucky_no_npi_cases_median.plot(c=NO_NPI_COLOR,ax=axis,label='Back to normal ( Reff= {:.2f})'.format(bucky_no_npi_reff))
    axis.fill_between(bucky_no_npi_cases_median.index,\
                          bucky_no_npi[bucky_no_npi['q']==0.25][bucky_var],
                          bucky_no_npi[bucky_no_npi['q']==0.75][bucky_var],
                          color=NO_NPI_COLOR,alpha=0.2
                          )
    plt.legend()
    fig.savefig(f'Outputs/{country_iso3}/current_{metric}.png')

def create_new_subplot(fig_title):
    fig,axis=plt.subplots(figsize=(FIG_SIZE[0],FIG_SIZE[1]))
    # TODO debug why this is not working
    axis.yaxis.grid()
    
    locator = mdates.AutoDateLocator(minticks=3, maxticks=7)
    formatter = mdates.DateFormatter('%d %b')
    axis.xaxis.set_major_locator(locator)
    axis.xaxis.set_major_formatter(formatter)

    axis.set_title(fig_title)
    x_axis = axis.axes.get_xaxis()
    x_label = x_axis.get_label()
    x_label.set_visible(False)
    return fig,axis


def create_maps(country_iso3, parameters):
    # Total cases - four weeks projection
    npi_admin1 = pd.read_csv(parameters['npi_admin1'])
    npi_admin1['datetime'] = pd.to_datetime(npi_admin1['date']).dt.date
    reg_4weeks = npi_admin1.loc[
        (npi_admin1['datetime'] >= TODAY) & (npi_admin1['datetime'] <= FOUR_WEEKS) & (npi_admin1['q'] == 0.5)]
    reg_4weeks_grp = reg_4weeks[['adm1', 'cases_active']].groupby(
        'adm1').sum().reset_index()
    reg_4weeks_grp['adm1'] = parameters['country_iso2'] + reg_4weeks_grp['adm1'].apply(lambda x: "{0:0=2d}".format(int(x)))
    shape = geopandas.read_file(parameters['shape'])
    shape = shape.merge(reg_4weeks_grp, left_on='ADM1_PCODE', right_on='adm1', how='left')
    plt.figure(figsize=(8, 4))
    ax = shape.plot(column='cases_active', cmap='Blues', figsize=(10, 10), edgecolor='gray')
    ax.set(title="Active Cases Four Weeks Projection in Afghanistan")
    plt.savefig('active_cases_map.png')
    plt.savefig(f'Outputs/{country_iso3}/active_cases_map.png')
    return None


def calculate_trends(country_iso3, parameters):
    # Top 5 and bottom 5 districts - 4 weeks trend
    npi_admin1 = pd.read_csv(parameters['npi_admin1'])
    npi_admin1['datetime'] = pd.to_datetime(npi_admin1['date'])
    start = npi_admin1.loc[npi_admin1['datetime']==TODAY]
    end = npi_admin1.loc[npi_admin1['datetime'] == FOUR_WEEKS]
    combined = start.merge(end[['datetime', 'adm1', 'cases_per_100k']], how='left', on='adm1')
    combined['active_cases_change'] = (combined['cases_per_100k_y'] / combined['cases_per_100k_x']) * 100
    table = combined[['adm1', 'active_cases_change']]
    table['trend'] = table['active_cases_change'].apply(lambda x: 1 if x > 100 else 0)
    top = table.sort_values('active_cases_change', ascending=False)
    top.head().to_csv(f'Outputs/top_5_district{country_iso3}.csv', index=False)
    bottom = table.sort_values('active_cases_change', ascending=True)
    bottom.head().to_csv(f'{country_iso3}/Outputs/bottom_5_district_{country_iso3}.csv', index=False)
    return None



def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("country_iso3", help="Country ISO3")
    parser.add_argument('-d', '--download-covid', action='store_true',
                        help='Download the COVID-19 data')
    return parser.parse_args()

if __name__ == "__main__":
    args = parse_args()
    main(args.country_iso3.upper(),download_covid=args.download_covid)