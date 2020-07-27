import utils
import os
import argparse
import pandas as pd
import matplotlib.pyplot as plt

import matplotlib.dates as mdates
import requests
import geopandas as gpd
from datetime import datetime,timedelta
from scipy.optimize import curve_fit
import numpy as np

from utils import set_matlotlib

ASSESSMENT_DATE='2020-07-22'
# TODAY = date.today()
TODAY = datetime.strptime(ASSESSMENT_DATE, '%Y-%m-%d').date()
FOUR_WEEKS = TODAY + timedelta(days=28)
TWO_WEEKS = TODAY + timedelta(days=14)
LAST_MONTH = TODAY - timedelta(days=30)

MIN_QUANTILE=0.25
MAX_QUANTILE=0.75
# MIN_QUANTILE=0.05
# MAX_QUANTILE=0.95

CONFIG_FILE = 'config.yml'
DIR_PATH = os.path.dirname(os.path.realpath(__file__))
WHO_COVID_URL='https://docs.google.com/spreadsheets/d/e/2PACX-1vSe-8lf6l_ShJHvd126J-jGti992SUbNLu-kmJfx1IRkvma_r4DHi0bwEW89opArs8ZkSY5G2-Bc1yT/pub?gid=0&single=true&output=csv'
WHO_COVID_FILENAME=WHO_COVID_FILENAME='WHO_data/Data_ WHO Coronavirus Covid-19 Cases and Deaths - WHO-COVID-19-global-data.csv'

HLX_TAG_TOTAL_CASES = "#affected+infected+confirmed+total"
HLX_TAG_TOTAL_DEATHS = "#affected+infected+dead+total"
HLX_TAG_DATE = "#date"
HLX_TAG_ADM2_PCODE='#adm2+pcode'

FIG_SIZE=(8,6)


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
    print('\n\n\n')
    print(f'{country_iso3}')
    extract_reff(country_iso3)
    generate_key_figures(country_iso3)
    generate_data_model_comparison(country_iso3,parameters)
    generate_model_projections(country_iso3,parameters)
    create_subnational_map(country_iso3, parameters)
    calculate_subnational_trends(country_iso3, parameters)
    # plt.show()

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
    bucky_df=pd.read_csv(f'Bucky_results/{country_iso3}_{npi_filter}/{admin_level}_quantiles.csv')
    bucky_df['date']=pd.to_datetime(bucky_df['date']).dt.date
    # if country_iso3=='AFG':
    #     # scaling afghanistan to take into account delays in reporting
    #     bucky_df['date']=bucky_df['date']+timedelta(days=10)
    #     bucky_df['cumulative_deaths']=bucky_df['cumulative_deaths']*1147/807
    #     bucky_df['cumulative_cases_reported']=bucky_df['cumulative_cases_reported']*35229/32022
    #     bucky_df['hospitalizations']=bucky_df['hospitalizations']*35229/32022
    #     bucky_df['cases_per_100k']=bucky_df['cases_per_100k']*35229/32022
    # if country_iso3=='SDN':
    #     # scaling afghanistan to take into account delays in reporting
    #     bucky_df['date']=bucky_df['date']+timedelta(days=11)
    #     bucky_df['cumulative_deaths']=bucky_df['cumulative_deaths']*668/691
    #     bucky_df['cumulative_cases_reported']=bucky_df['cumulative_cases_reported']*10527/10084
    #     bucky_df['hospitalizations']=bucky_df['hospitalizations']*10527/10084
    #     bucky_df['cases_per_100k']=bucky_df['cases_per_100k']*10527/10084
    bucky_df=bucky_df[(bucky_df['date']>=min_date) &\
                        (bucky_df['date']<=max_date)]
    bucky_df=bucky_df.set_index('date')
    return bucky_df

def extract_reff(country_iso3):
    bucky_npi=get_bucky(country_iso3,admin_level='adm0',min_date=TODAY,max_date=FOUR_WEEKS,npi_filter='npi')
    bucky_npi=bucky_npi[bucky_npi['q']==0.5]
    dt_npi,r_npi=get_bucky_dt_reff(bucky_npi)
    print(f'Estimated doubling time NPI {dt_npi}, Reff {r_npi}')
    
    bucky_no_npi=get_bucky(country_iso3,admin_level='adm0',min_date=TODAY,max_date=FOUR_WEEKS,npi_filter='no_npi')
    bucky_no_npi=bucky_no_npi[bucky_no_npi['q']==0.5]
    dt_no_npi,r_no_npi=get_bucky_dt_reff(bucky_no_npi)
    print(f'Estimated doubling time No NPI {dt_no_npi}, Reff {r_no_npi}')
    

def get_bucky_dt_reff(df_bucky):
    # start fit
    dates_proj = df_bucky.index
    xfit=[(x-dates_proj[0]).days for x in dates_proj]
    yfit = df_bucky['cumulative_cases_reported']
    initial_caseload=yfit[0]
    initial_parameters=[initial_caseload,0.03]
    # # TODO check quality of the fit
    popt, _ = curve_fit(func,xfit,yfit,p0=initial_parameters)
    doubling_time_fit=np.log(2)/popt[1]
    # parameters suggested by Matt
    Tg = 7.
    Ts = 5.
    n = 3
    f = .4
    m = 2
    r = np.log(2)/doubling_time_fit
    Te=calc_Te(Tg, Ts, n, f)
    reff=calc_Reff(m, n, Tg, Te, r)
    # old method
    # # https://www.acpjournals.org/doi/10.7326/M20-0504
    # infectious_period=5.2
    # # according to eq 1 in https://www.mdpi.com/2306-7381/7/1/2/htm#B17-vetsci-07-00002
    # reff=1+(np.log(2)/doubling_time_fit)*infectious_period
    return doubling_time_fit,reff

def calc_Te(Tg, Ts, n, f):
    num = 2.0 * n * f / (n + 1.0) * Tg - Ts
    den = 2.0 * n * f / (n + 1.0) - 1.0
    return num / den

def calc_Reff(m, n, Tg, Te, r):
    tdiff = Tg - Te
    num = 2.0 * n * r / (n + 1.0) * (Tg - Te) * (1.0 + r * Te / m) ** m
    den = 1.0 - (1.0 + 2.0 * r / (n + 1.0) * (Tg - Te)) ** (-n)
    return num / den

# not used at the moment
# def calc_Ti(Te, Tg, n):
    # return (Tg - Te) * 2.0 * n / (n + 1.0)

def func(x, p0, beta):
    return p0 * np.exp(x*beta)

def generate_key_figures(country_iso3):

    who_covid=get_who_covid(country_iso3,min_date=LAST_MONTH,max_date=FOUR_WEEKS)
    who_deaths_today=who_covid.loc[TODAY,'CumDeath']
    who_cases_today=who_covid.loc[TODAY,'CumCase']    
    # get weekly new cases
    who_covid.index = pd.to_datetime(who_covid.index)
    new_WHO_w=who_covid.groupby(['ISO_3_CODE']).resample('W').sum()[['NewCase','NewDeath']]
    ndays_w=who_covid.groupby(['ISO_3_CODE']).resample('W').count()['NewCase']
    ndays_w=ndays_w.rename('ndays')
    new_WHO_w=pd.merge(left=new_WHO_w,right=ndays_w,left_index=True,right_index=True,how='inner')
    new_WHO_w=new_WHO_w[new_WHO_w['ndays']==7]
    new_WHO_w['NewCase_PercentChange'] = new_WHO_w.groupby('ISO_3_CODE')['NewCase'].pct_change()
    new_WHO_w['NewDeath_PercentChange'] = new_WHO_w.groupby('ISO_3_CODE')['NewDeath'].pct_change()
    trend_w_cases=new_WHO_w.loc[new_WHO_w.index[-1],'NewCase_PercentChange']*100
    trend_w_deaths=new_WHO_w.loc[new_WHO_w.index[-1],'NewDeath_PercentChange']*100
    
    print(f'Current situation {TODAY}: {who_cases_today:.0f} cases, {who_deaths_today:.0f} deaths')
    print(f'Weekly new cases wrt last week: {trend_w_cases:.0f}% cases, {trend_w_deaths:.0f}% deaths')

    bucky_npi=get_bucky(country_iso3,admin_level='adm0',min_date=TODAY,max_date=FOUR_WEEKS,npi_filter='npi')
    reporting_rate=bucky_npi['CASE_REPORT'].mean()*100
    # reff_npi=bucky_npi['Reff'].mean()
    min_cases_npi=bucky_npi[bucky_npi['q']==MIN_QUANTILE].loc[FOUR_WEEKS,'cumulative_cases_reported']
    max_cases_npi=bucky_npi[bucky_npi['q']==MAX_QUANTILE].loc[FOUR_WEEKS,'cumulative_cases_reported']
    min_deaths_npi=bucky_npi[bucky_npi['q']==MIN_QUANTILE].loc[FOUR_WEEKS,'cumulative_deaths']
    max_deaths_npi=bucky_npi[bucky_npi['q']==MAX_QUANTILE].loc[FOUR_WEEKS,'cumulative_deaths']
    bucky_npi_cases_today=bucky_npi[bucky_npi['q']==0.5].loc[TODAY,'cumulative_cases_reported']
    bucky_npi_deaths_today=bucky_npi[bucky_npi['q']==0.5].loc[TODAY,'cumulative_deaths']
    rel_inc_min_cases_npi=(min_cases_npi-who_cases_today)/bucky_npi_cases_today*100
    rel_inc_max_cases_npi=(max_cases_npi-who_cases_today)/bucky_npi_cases_today*100
    rel_inc_min_deaths_npi=(min_deaths_npi-who_deaths_today)/bucky_npi_deaths_today*100
    rel_inc_max_deaths_npi=(max_deaths_npi-who_deaths_today)/bucky_npi_deaths_today*100
    print(f'- Projection date:{FOUR_WEEKS}')
    
    print(f'- ESTIMATED CASE REPORTING RATE {reporting_rate:.0f}')
    # print(f'-- NPI: ESTIMATED Reff NPI {reff_npi:.2f}')
    print(f'-- NPI: Projected reported cases in 4w: {min_cases_npi:.0f} - {max_cases_npi:.0f}')
    print(f'-- NPI: Projected trend reported cases in 4w: {rel_inc_min_cases_npi:.0f}% - {rel_inc_max_cases_npi:.0f}%')
    print(f'-- NPI: Projected reported deaths in 4w: {min_deaths_npi:.0f} - {max_deaths_npi:.0f}')
    print(f'-- NPI: Projected trend reported deaths in 4w: {rel_inc_min_deaths_npi:.0f}% - {rel_inc_max_deaths_npi:.0f}%')
    
    bucky_no_npi=get_bucky(country_iso3,admin_level='adm0',min_date=TODAY,max_date=FOUR_WEEKS,npi_filter='no_npi')
    # reff_no_npi=bucky_no_npi['Reff'].mean()
    min_cases_no_npi=bucky_no_npi[bucky_no_npi['q']==MIN_QUANTILE].loc[FOUR_WEEKS,'cumulative_cases_reported']
    max_cases_no_npi=bucky_no_npi[bucky_no_npi['q']==MAX_QUANTILE].loc[FOUR_WEEKS,'cumulative_cases_reported']
    min_deaths_no_npi=bucky_no_npi[bucky_no_npi['q']==MIN_QUANTILE].loc[FOUR_WEEKS,'cumulative_deaths']
    max_deaths_no_npi=bucky_no_npi[bucky_no_npi['q']==MAX_QUANTILE].loc[FOUR_WEEKS,'cumulative_deaths']
    # print(f'--- no_npi: ESTIMATED Reff no_npi {reff_no_npi:.2f}')
    print(f'--- no_npi: Projected reported cases in 4w: {min_cases_no_npi:.0f} - {max_cases_no_npi:.0f}')
    print(f'--- no_npi: Projected reported deaths in 4w: {min_deaths_no_npi:.0f} - {max_deaths_no_npi:.0f}')
    

def generate_model_projections(country_iso3,parameters):
    # generate plot with long term projections of daily cases
    bucky_npi=get_bucky(country_iso3,admin_level='adm0',min_date=TODAY,max_date=FOUR_WEEKS,npi_filter='npi')
    bucky_no_npi=get_bucky(country_iso3,admin_level='adm0',min_date=TODAY,max_date=FOUR_WEEKS,npi_filter='no_npi')

    draw_model_projections(country_iso3,bucky_npi,bucky_no_npi,parameters,'hospitalizations')

def draw_model_projections(country_iso3,bucky_npi,bucky_no_npi,parameters,metric):
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
    # bucky_npi_reff=bucky_npi['Reff'].mean()
    # bucky_npi_median.plot(c=NPI_COLOR,ax=axis,label='Current NPIs maintained ( Reff= {:.2f})'.format(bucky_npi_reff))
    bucky_npi_median.plot(c=NPI_COLOR,ax=axis,label='Current NPIs maintained'.format())
    axis.fill_between(bucky_npi_median.index,\
                          bucky_npi[bucky_npi['q']==MIN_QUANTILE][bucky_var],
                          bucky_npi[bucky_npi['q']==MAX_QUANTILE][bucky_var],
                          color=NPI_COLOR,alpha=0.2
                          )
    # draw line NO NPI
    bucky_no_npi_cases_median=bucky_no_npi[bucky_no_npi['q']==0.5][bucky_var]
    # bucky_no_npi_reff=bucky_no_npi['Reff'].mean()
    # bucky_no_npi_cases_median.plot(c=NO_NPI_COLOR,ax=axis,label='No NPIs in place ( Reff= {:.2f})'.format(bucky_no_npi_reff))
    bucky_no_npi_cases_median.plot(c=NO_NPI_COLOR,ax=axis,label='No NPIs in place'.format())
    axis.fill_between(bucky_no_npi_cases_median.index,\
                          bucky_no_npi[bucky_no_npi['q']==MIN_QUANTILE][bucky_var],
                          bucky_no_npi[bucky_no_npi['q']==MAX_QUANTILE][bucky_var],
                          color=NO_NPI_COLOR,alpha=0.2
                          )
    plt.legend()
    print(f'----{metric} statistics')
    metric_today_min=bucky_no_npi[bucky_no_npi['q']==MIN_QUANTILE].loc[TODAY,bucky_var]
    metric_today_max=bucky_no_npi[bucky_no_npi['q']==MAX_QUANTILE].loc[TODAY,bucky_var]
    metric_4w_npi_min=bucky_npi[bucky_npi['q']==MIN_QUANTILE].loc[FOUR_WEEKS,bucky_var]
    metric_4w_npi_max=bucky_npi[bucky_npi['q']==MAX_QUANTILE].loc[FOUR_WEEKS,bucky_var]
    metric_4w_no_npi_min=bucky_no_npi[bucky_no_npi['q']==MIN_QUANTILE].loc[FOUR_WEEKS,bucky_var]
    metric_4w_no_npi_max=bucky_no_npi[bucky_no_npi['q']==MAX_QUANTILE].loc[FOUR_WEEKS,bucky_var]
    print(f'----{metric} {TODAY}: {metric_today_min:.0f} - {metric_today_max:.0f}')
    print(f'----{metric} NPI {FOUR_WEEKS}: {metric_4w_npi_min:.0f} - {metric_4w_npi_max:.0f}')
    print(f'----{metric} NO NPI {FOUR_WEEKS}: {metric_4w_no_npi_min:.0f} - {metric_4w_no_npi_max:.0f}')
    fig.savefig(f'Outputs/{country_iso3}/projection_{metric}.png')

def get_subnational_covid_data(parameters,aggregate,min_date,max_date):
    # get subnational from COVID parameterization repo
    subnational_covid=pd.read_csv(parameters['subnational_cases_url'])
    subnational_covid[HLX_TAG_DATE]=pd.to_datetime(subnational_covid[HLX_TAG_DATE]).dt.date
    subnational_covid=subnational_covid[(subnational_covid[HLX_TAG_DATE]>=min_date) &\
                                        (subnational_covid[HLX_TAG_DATE]<=max_date)]
    if aggregate:
        # date and adm2 are the unique keys
        dates=sorted(set(subnational_covid[HLX_TAG_DATE]))
        adm2pcodes=set(subnational_covid[HLX_TAG_ADM2_PCODE])
        unique_keys=[HLX_TAG_DATE,HLX_TAG_ADM2_PCODE]
        # create a multi-index to fill missing combinations with None values
        mind = pd.MultiIndex.from_product([dates,adm2pcodes],names=unique_keys)
        subnational_covid=subnational_covid.set_index(unique_keys).reindex(mind,fill_value=None)
        # forward fill missing values for each pcode
        subnational_covid=subnational_covid.groupby(HLX_TAG_ADM2_PCODE).ffill()
        # sum by date
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

def generate_data_model_comparison(country_iso3,parameters):
    # generate plot with subnational data, WHO data and projections
    subnational_covid=get_subnational_covid_data(parameters,aggregate=True,min_date=LAST_MONTH,max_date=FOUR_WEEKS)
    who_covid=get_who_covid(country_iso3,min_date=LAST_MONTH,max_date=FOUR_WEEKS)
    bucky_npi=get_bucky(country_iso3,admin_level='adm0',min_date=LAST_MONTH,max_date=FOUR_WEEKS,npi_filter='npi')
    bucky_no_npi=get_bucky(country_iso3,admin_level='adm0',min_date=LAST_MONTH,max_date=FOUR_WEEKS,npi_filter='no_npi')
    
    draw_data_model_comparison(country_iso3,subnational_covid,who_covid,bucky_npi,bucky_no_npi,parameters,'cumulative_reported_cases')
    draw_data_model_comparison(country_iso3,subnational_covid,who_covid,bucky_npi,bucky_no_npi,parameters,'cumulative_deaths')

def draw_data_model_comparison(country_iso3,subnational_covid,who_covid,bucky_npi,bucky_no_npi,parameters,metric):
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
        return False

    fig,axis=create_new_subplot(fig_title)

    # draw subnational reported cumulative cases
    axis.scatter(who_covid.index, who_covid[who_var],\
                     alpha=0.8, s=20,c=WHO_DATA_COLOR,marker='*',label='WHO')
    axis.scatter(subnational_covid.index, subnational_covid[subnational_var],\
                     alpha=0.8, s=20,c=SUBNATIONAL_DATA_COLOR,marker='o',label=subnational_source)
    # draw line NPI
    bucky_npi_median=bucky_npi[bucky_npi['q']==0.5][bucky_var]
    # bucky_npi_reff=bucky_npi['Reff'].mean()
    # bucky_npi_median.plot(c=NPI_COLOR,ax=axis,label='Current NPIs maintained ( Reff= {:.2f})'.format(bucky_npi_reff))
    bucky_npi_median.plot(c=NPI_COLOR,ax=axis,label='Current NPIs maintained')
    axis.fill_between(bucky_npi_median.index,\
                          bucky_npi[bucky_npi['q']==MIN_QUANTILE][bucky_var],
                          bucky_npi[bucky_npi['q']==MAX_QUANTILE][bucky_var],
                          color=NPI_COLOR,alpha=0.2
                          )
    # draw line NO NPI
    bucky_no_npi_cases_median=bucky_no_npi[bucky_no_npi['q']==0.5][bucky_var]
    # bucky_no_npi_reff=bucky_no_npi['Reff'].mean()
    # bucky_no_npi_cases_median.plot(c=NO_NPI_COLOR,ax=axis,label='No NPIs in place ( Reff= {:.2f})'.format(bucky_no_npi_reff))
    bucky_no_npi_cases_median.plot(c=NO_NPI_COLOR,ax=axis,label='No NPIs in place'.format())
    axis.fill_between(bucky_no_npi_cases_median.index,\
                          bucky_no_npi[bucky_no_npi['q']==MIN_QUANTILE][bucky_var],
                          bucky_no_npi[bucky_no_npi['q']==MAX_QUANTILE][bucky_var],
                          color=NO_NPI_COLOR,alpha=0.2
                          )
    plt.legend()
    fig.savefig(f'Outputs/{country_iso3}/current_{metric}.png')

def create_new_subplot(fig_title):
    fig,axis=plt.subplots(figsize=(FIG_SIZE[0],FIG_SIZE[1]))
    
    locator = mdates.AutoDateLocator(minticks=3, maxticks=7)
    formatter = mdates.DateFormatter('%d %b')
    axis.xaxis.set_major_locator(locator)
    axis.xaxis.set_major_formatter(formatter)

    axis.set_title(fig_title)
    x_axis = axis.axes.get_xaxis()
    x_label = x_axis.get_label()
    x_label.set_visible(False)
    axis.grid(linestyle='-', linewidth='0.5', color='black',alpha=0.2)
    return fig,axis


def create_subnational_map(country_iso3, parameters):
    # Total cases - four weeks projection
    bucky_npi =  get_bucky(country_iso3 ,admin_level='adm1',min_date=TODAY,max_date=TWO_WEEKS,npi_filter='npi')
    bucky_npi = bucky_npi[bucky_npi['q']==0.5][['adm1','cases_per_100k']]
    bucky_npi = bucky_npi.loc[TWO_WEEKS,:]
    bucky_npi['adm1']=parameters['iso2_code'] + bucky_npi['adm1'].apply(lambda x:  "{0:0=2d}".format(int(x)))
    shapefile = gpd.read_file(parameters['shape'])
    shapefile = shapefile.merge(bucky_npi, left_on=parameters['adm1_pcode'], right_on='adm1', how='left')
    fig_title=f'Ranking: number of cases per 100,000 people on {TWO_WEEKS}'
    # fig_title=f'Ranking: number of cases per 100,000 people on {TWO_WEEKS}'
    fig,axis=create_new_subplot(fig_title)
    axis.axis('off')
    shapefile.plot(column='cases_per_100k', figsize=(10, 10),edgecolor='gray',ax=axis,
                #    legend=True,
                #    legend_kwds={'label': "Cases per 100,000 people",'orientation': "horizontal"},
                   scheme='Quantiles',k=len(shapefile)
                   )
    shapefile.boundary.plot(linewidth=0.1,ax=axis)
    fig.savefig(f'Outputs/{country_iso3}/map_cases_per_100k_2w.png')

def calculate_subnational_trends(country_iso3, parameters):
    # Top 5 and bottom 5 districts - 4 weeks trend
    bucky_npi =  get_bucky(country_iso3 ,admin_level='adm1',min_date=TODAY,max_date=TWO_WEEKS,npi_filter='npi')
    # to remove noise
    bucky_npi=bucky_npi[bucky_npi['cases_active']>10]
    bucky_npi = bucky_npi[bucky_npi['q']==0.5][['adm1','Reff','cases_per_100k']]
    bucky_npi['adm1']=parameters['iso2_code'] + bucky_npi['adm1'].apply(lambda x:  "{0:0=2d}".format(int(x)))
    start = bucky_npi.loc[TODAY,:]
    end = bucky_npi.loc[TWO_WEEKS,:]
    combined = start.merge(end[['adm1', 'cases_per_100k']], how='left', on='adm1')
    combined['cases_per_100k_change'] = (combined['cases_per_100k_y']-combined['cases_per_100k_x']) / combined['cases_per_100k_x'] * 100
    shapefile = gpd.read_file(parameters['shape'])
    shapefile=shapefile[[parameters['adm1_pcode'],parameters['adm1_name']]]
    combined=combined.merge(shapefile,how='left',left_on='adm1',right_on=parameters['adm1_pcode'])
    combined = combined.sort_values('cases_per_100k_change', ascending=False)
    combined=combined.dropna()
    combined['cases_per_100k_change']=combined['cases_per_100k_change'].astype(int)
    # combined=combined[[parameters['adm1_name'],'cases_per_100k_change']]
    combined.to_csv(f'Outputs/{country_iso3}/ADM1_ranking.csv', index=False)


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("country_iso3", help="Country ISO3")
    parser.add_argument('-d', '--download-covid', action='store_true',
                        help='Download the COVID-19 data')
    return parser.parse_args()

if __name__ == "__main__":
    args = parse_args()
    main(args.country_iso3.upper(),download_covid=args.download_covid)