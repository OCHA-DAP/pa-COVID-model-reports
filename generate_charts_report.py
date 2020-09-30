import utils
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
import matplotlib.colors as mcolors
import os
import geopandas as gpd
from datetime import datetime,timedelta
import matplotlib.dates as mdates
import sys 
import csv

from utils import *

country_iso_3 = sys.argv[1]

ASSESSMENT_DATE='2020-09-23'
# TODAY = date.today()
TODAY = datetime.strptime(ASSESSMENT_DATE, '%Y-%m-%d').date()
FOUR_WEEKS = TODAY + timedelta(days=28)
TWO_WEEKS = TODAY + timedelta(days=14)
LAST_TWO_MONTHS = TODAY - timedelta(days=60)
EARLIEST_DATE = datetime.strptime('2020-02-24', '%Y-%m-%d').date()

MIN_QUANTILE=0.25
MAX_QUANTILE=0.75
# MIN_QUANTILE=0.05
# MAX_QUANTILE=0.95

CONFIG_FILE = 'config.yml'
DIR_PATH = os.path.dirname(os.path.realpath(__file__))
WHO_COVID_URL='https://covid19.who.int/WHO-COVID-19-global-data.csv'
WHO_COVID_FILENAME='WHO_data/WHO-COVID-19-global-data.csv'
RESULTS_FILENAME=f'automated_reports/report_metrics/{country_iso_3}_results.csv'

NPI_COLOR='green'
NO_NPI_COLOR='red'
WHO_DATA_COLOR='dodgerblue'
SUBNATIONAL_DATA_COLOR='navy'

# todays_country_metrics = pd.DataFrame()

def main(country_iso3='AFG', download_covid=False):

    parameters = utils.parse_yaml(CONFIG_FILE)[country_iso3]
    if download_covid:
        # Download latest covid file tiles and read them in
        download_who_covid_data(WHO_COVID_URL,f'{DIR_PATH}/{WHO_COVID_FILENAME}')
    set_matlotlib(plt)
    print('\n\n\n')
    print(f'{country_iso3}')
    dt_npi, r_npi, dt_no_npi, r_no_npi = extract_reff(country_iso3)
    who_cases_today, who_deaths_today, CFR, trend_w_cases, trend_w_deaths, reporting_rate, min_cases_npi, max_cases_npi, rel_inc_min_cases_npi, rel_inc_max_cases_npi, min_deaths_npi, max_deaths_npi, rel_inc_min_deaths_npi, rel_inc_max_deaths_npi, min_cases_no_npi, max_cases_no_npi, min_deaths_no_npi, max_deaths_no_npi = generate_key_figures(country_iso3,parameters)
    generate_data_model_comparison(country_iso3,parameters)
    generate_data_model_comparison_lifetime(country_iso3,parameters)
    metric, metric_today_min, metric_today_max, metric_4w_npi_min, metric_4w_npi_max, metric_4w_no_npi_min, metric_4w_no_npi_max = generate_model_projections(country_iso3,parameters)
    create_subnational_map_cases100k(country_iso3, parameters, TODAY,"map_cases_per_100k_current.png")
    create_subnational_map_cases100k(country_iso3, parameters, TWO_WEEKS, "map_cases_per_100k_2w.png")
    create_binary_change_map(country_iso3, parameters)
    calculate_subnational_trends(country_iso3, parameters)
    if os.path.exists(RESULTS_FILENAME):
        df_all=pd.read_csv(RESULTS_FILENAME)
        #remove the rows that have same assessment date as current run
        #-->make sure not duplicate results for the same date
        df_all=df_all[df_all["assessment_date"]!=str(TODAY)]
    else:
        df_all=pd.DataFrame()
    results_df = pd.DataFrame({"metric_name": ["Estimated doubling time NPI",
                                                "NPI Reff",
                                                "Estimated doubling time No NPI",
                                                "No NPI Reff",
                                                "Current situation - WHO cases today",
                                                "Current situation - WHO deaths today",
                                                "CFR",
                                                "Weekly new cases wrt last week - trend",
                                                "Weekly new deaths wrt last week - trend",
                                                "Estimated case reporting rate",
                                                "NPI - projected reported cases in 4w - MIN",
                                                "NPI - projected reported cases in 4w - MAX",
                                                "NPI - projected TREND reported cases in 4w - MIN",
                                                "NPI - projected TREND reported cases in 4w - MAX",
                                                "NPI - projected reported deaths in 4w - MIN",
                                                "NPI - projected reported deaths in 4w - MAX",
                                                "NPI - projected TREND reported deaths in 4w - MIN",
                                                "NPI - projected TREND reported deaths in 4w - MAX",
                                                "NO NPI - projected reported cases in 4w - MIN",
                                                "NO NPI - projected reported cases in 4w - MAX",
                                                "NO NPI - projected reported deaths in 4w - MIN",
                                                "NO NPI - projected reported deaths in 4w - MAX",
                                                "Hospitalizations current situation - MIN",
                                                "Hospitalizations current situation - MAX",
                                                "NPI Hospitalizations projections 4w - MIN",
                                                "NPI Hospitalizations projections 4w - MAX",
                                                "NO NPI Hospitalizations projections 4w - MIN",
                                                "NO NPI Hospitalizations projections 4w - MAX"
                                                ],
                               "metric_value": [dt_npi,
                                                r_npi,
                                                dt_no_npi,
                                                r_no_npi,
                                                who_cases_today,
                                                who_deaths_today,
                                                CFR,
                                                trend_w_cases,
                                                trend_w_deaths,
                                                reporting_rate,
                                                min_cases_npi,
                                                max_cases_npi,
                                                rel_inc_min_cases_npi,
                                                rel_inc_max_cases_npi,
                                                min_deaths_npi,
                                                max_deaths_npi,
                                                rel_inc_min_deaths_npi,
                                                rel_inc_max_deaths_npi,
                                                min_cases_no_npi,
                                                max_cases_no_npi,
                                                min_deaths_no_npi,
                                                max_deaths_no_npi,
                                                metric_today_min,
                                                metric_today_max,
                                                metric_4w_npi_min,
                                                metric_4w_npi_max,
                                                metric_4w_no_npi_min,
                                                metric_4w_no_npi_max
                                                ]
                               })


    results_df['assessment_date'] = TODAY
    results_df['country'] = f'{country_iso_3}'

    df_all=df_all.append(results_df)
    df_all.to_csv(RESULTS_FILENAME,index=False)
    # results_df.to_csv(RESULTS_FILENAME, mode="a", index=False,header=(not os.path.exists(RESULTS_FILENAME)))
    # plt.show()


def extract_reff(country_iso3):
    bucky_npi=get_bucky(country_iso3,admin_level='adm0',min_date=TODAY,max_date=FOUR_WEEKS,npi_filter='npi')
    bucky_npi=bucky_npi[bucky_npi['q']==0.5]
    dt_npi,r_npi=get_bucky_dt_reff(bucky_npi)
    print(f'Estimated doubling time NPI {dt_npi}, Reff {r_npi}')
    
    bucky_no_npi=get_bucky(country_iso3,admin_level='adm0',min_date=TODAY,max_date=FOUR_WEEKS,npi_filter='no_npi')
    bucky_no_npi=bucky_no_npi[bucky_no_npi['q']==0.5]
    dt_no_npi,r_no_npi=get_bucky_dt_reff(bucky_no_npi)
    print(f'Estimated doubling time No NPI {dt_no_npi}, Reff {r_no_npi}')

    return dt_npi, r_npi, dt_no_npi, r_no_npi

def generate_key_figures(country_iso3,parameters):

    who_covid=get_who(WHO_COVID_FILENAME,parameters['iso2_code'],min_date=LAST_TWO_MONTHS,max_date=FOUR_WEEKS)
    who_deaths_today=who_covid.loc[TODAY,'Cumulative_deaths']
    who_cases_today=who_covid.loc[TODAY,'Cumulative_cases']    
    CFR=who_deaths_today/who_cases_today*100
    # get weekly new cases
    who_covid.index = pd.to_datetime(who_covid.index)
    new_WHO_w=who_covid.groupby(['Country_code']).resample('W').sum()[['New_cases','New_deaths']]
    ndays_w=who_covid.groupby(['Country_code']).resample('W').count()['New_cases']
    ndays_w=ndays_w.rename('ndays')
    new_WHO_w=pd.merge(left=new_WHO_w,right=ndays_w,left_index=True,right_index=True,how='inner')
    new_WHO_w=new_WHO_w[new_WHO_w['ndays']==7]
    new_WHO_w['New_cases_PercentChange'] = new_WHO_w.groupby('Country_code')['New_cases'].pct_change()
    new_WHO_w['New_deaths_PercentChange'] = new_WHO_w.groupby('Country_code')['New_deaths'].pct_change()
    trend_w_cases=new_WHO_w.loc[new_WHO_w.index[-1],'New_cases_PercentChange']*100
    trend_w_deaths=new_WHO_w.loc[new_WHO_w.index[-1],'New_deaths_PercentChange']*100
    print(f'Current situation {TODAY}: {who_cases_today:.0f} cases, {who_deaths_today:.0f} deaths')
    print(f'CFR {TODAY}: {CFR:.1f}')
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
    rel_inc_min_cases_npi=(min_cases_npi-bucky_npi_cases_today)/bucky_npi_cases_today*100
    rel_inc_max_cases_npi=(max_cases_npi-bucky_npi_cases_today)/bucky_npi_cases_today*100
    rel_inc_min_deaths_npi=(min_deaths_npi-bucky_npi_deaths_today)/bucky_npi_deaths_today*100
    rel_inc_max_deaths_npi=(max_deaths_npi-bucky_npi_deaths_today)/bucky_npi_deaths_today*100
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
    
    return who_cases_today, who_deaths_today, CFR, trend_w_cases, trend_w_deaths, reporting_rate, min_cases_npi, max_cases_npi, rel_inc_min_cases_npi, rel_inc_max_cases_npi, min_deaths_npi, max_deaths_npi, rel_inc_min_deaths_npi, rel_inc_max_deaths_npi, min_cases_no_npi, max_cases_no_npi, min_deaths_no_npi, max_deaths_no_npi

def generate_model_projections(country_iso3,parameters):
    # generate plot with long term projections of daily cases
    bucky_npi=get_bucky(country_iso3,admin_level='adm0',min_date=TODAY,max_date=FOUR_WEEKS,npi_filter='npi')
    bucky_no_npi=get_bucky(country_iso3,admin_level='adm0',min_date=TODAY,max_date=FOUR_WEEKS,npi_filter='no_npi')
    metric, metric_today_min, metric_today_max, metric_4w_npi_min, metric_4w_npi_max, metric_4w_no_npi_min, metric_4w_no_npi_max = draw_model_projections(country_iso3,bucky_npi,bucky_no_npi,parameters,'hospitalizations')
    return metric, metric_today_min, metric_today_max, metric_4w_npi_min, metric_4w_npi_max, metric_4w_no_npi_min, metric_4w_no_npi_max

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
    # draw bucky
    draw_bucky_projections(bucky_npi,bucky_no_npi,bucky_var,axis)

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

    return metric, metric_today_min, metric_today_max, metric_4w_npi_min, metric_4w_npi_max, metric_4w_no_npi_min, metric_4w_no_npi_max

def generate_data_model_comparison(country_iso3,parameters):
    # generate plot with subnational data, WHO data and projections
    subnational_covid=get_subnational_covid_data(parameters,aggregate=True,min_date=LAST_TWO_MONTHS,max_date=FOUR_WEEKS)
    who_covid=get_who(WHO_COVID_FILENAME,parameters['iso2_code'],min_date=LAST_TWO_MONTHS,max_date=FOUR_WEEKS)
    bucky_npi=get_bucky(country_iso3,admin_level='adm0',min_date=LAST_TWO_MONTHS,max_date=FOUR_WEEKS,npi_filter='npi')
    bucky_no_npi=get_bucky(country_iso3,admin_level='adm0',min_date=LAST_TWO_MONTHS,max_date=FOUR_WEEKS,npi_filter='no_npi')
    
    draw_data_model_comparison_cumulative(country_iso3,subnational_covid,who_covid,bucky_npi,bucky_no_npi,parameters,'cumulative_reported_cases')
    draw_data_model_comparison_cumulative(country_iso3,subnational_covid,who_covid,bucky_npi,bucky_no_npi,parameters,'cumulative_deaths')
    draw_data_model_comparison_new(country_iso3,who_covid,bucky_npi,bucky_no_npi,'daily_cases_reported')
    draw_data_model_comparison_new(country_iso3,who_covid,bucky_npi,bucky_no_npi,'daily_deaths')

def generate_data_model_comparison_lifetime(country_iso3,parameters):
    # generate plot with subnational data, WHO data and projections
    subnational_covid=get_subnational_covid_data(parameters,aggregate=True,min_date=EARLIEST_DATE,max_date=FOUR_WEEKS)
    who_covid=get_who(WHO_COVID_FILENAME,parameters['iso2_code'],min_date=EARLIEST_DATE,max_date=FOUR_WEEKS)
    bucky_npi=get_bucky(country_iso3,admin_level='adm0',min_date=EARLIEST_DATE,max_date=FOUR_WEEKS,npi_filter='npi')
    bucky_no_npi=get_bucky(country_iso3,admin_level='adm0',min_date=EARLIEST_DATE,max_date=FOUR_WEEKS,npi_filter='no_npi')
    
    draw_data_model_comparison_cumulative_lifetime(country_iso3,subnational_covid,who_covid,bucky_npi,bucky_no_npi,parameters,'cumulative_reported_cases')
    draw_data_model_comparison_cumulative_lifetime(country_iso3,subnational_covid,who_covid,bucky_npi,bucky_no_npi,parameters,'cumulative_deaths')
    draw_data_model_comparison_new_lifetime(country_iso3,who_covid,bucky_npi,bucky_no_npi,'daily_cases_reported')
    draw_data_model_comparison_new_lifetime(country_iso3,who_covid,bucky_npi,bucky_no_npi,'daily_deaths')

def draw_data_model_comparison_cumulative(country_iso3,subnational_covid,who_covid,bucky_npi,bucky_no_npi,parameters,metric):
    # plot the 4 inputs and save figure
    if metric=='cumulative_reported_cases':
        who_var='Cumulative_cases'
        bucky_var='cumulative_cases_reported'
        subnational_var=HLX_TAG_TOTAL_CASES
        subnational_source=parameters['subnational_cases_source']
        fig_title='Cumulative reported cases'
    elif metric=='cumulative_deaths':
        who_var='Cumulative_deaths'
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
    # draw bucky
    draw_bucky_projections(bucky_npi,bucky_no_npi,bucky_var,axis)

    plt.legend()
    fig.savefig(f'Outputs/{country_iso3}/current_{metric}.png')

def draw_data_model_comparison_cumulative_lifetime(country_iso3,subnational_covid,who_covid,bucky_npi,bucky_no_npi,parameters,metric):
    # plot the 4 inputs and save figure
    if metric=='cumulative_reported_cases':
        who_var='Cumulative_cases'
        bucky_var='cumulative_cases_reported'
        subnational_var=HLX_TAG_TOTAL_CASES
        subnational_source=parameters['subnational_cases_source']
        fig_title='Cumulative reported cases'
    elif metric=='cumulative_deaths':
        who_var='Cumulative_deaths'
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
    # draw bucky
    draw_bucky_projections(bucky_npi,bucky_no_npi,bucky_var,axis)

    plt.legend(loc="lower right", prop={'size': 8})
    fig.savefig(f'Outputs/{country_iso3}/lifetime_{metric}.png')

def draw_data_model_comparison_new(country_iso3,who_covid,bucky_npi,bucky_no_npi,metric):
    # plot the 4 inputs and save figure
    if metric=='daily_cases_reported':
        who_var='New_cases'
        bucky_var='daily_cases_reported'
        fig_title='Daily reported cases'
    elif metric=='daily_deaths':
        who_var='New_deaths'
        bucky_var='daily_deaths'
        fig_title='Daily reported deaths'
    else:
        print(f'metric {metric} not implemented')
        return False
    fig,axis=create_new_subplot(fig_title)
    # draw subnational reported cumulative cases
    axis.bar(who_covid.index, who_covid[who_var],alpha=0.8,color=WHO_DATA_COLOR,label='WHO')
    # compute rolling 7-day average
    who_covid_rolling = who_covid[who_var].rolling(window=7).mean()
    axis.plot(who_covid_rolling.index, who_covid_rolling,\
        lw=3,color=lighten_color(WHO_DATA_COLOR,1.6),label='WHO - 7d rolling average')
    # draw bucky
    draw_bucky_projections(bucky_npi,bucky_no_npi,bucky_var,axis)
    
    plt.legend()
    fig.savefig(f'Outputs/{country_iso3}/current_{metric}.png')

def draw_data_model_comparison_new_lifetime(country_iso3,who_covid,bucky_npi,bucky_no_npi,metric):
    # plot the 4 inputs and save figure
    if metric=='daily_cases_reported':
        who_var='New_cases'
        bucky_var='daily_cases_reported'
        fig_title='Daily reported cases'
    elif metric=='daily_deaths':
        who_var='New_deaths'
        bucky_var='daily_deaths'
        fig_title='Daily reported deaths'
    else:
        print(f'metric {metric} not implemented')
        return False
    fig,axis=create_new_subplot(fig_title)
    # draw subnational reported cumulative cases
    axis.bar(who_covid.index, who_covid[who_var],alpha=0.8,color=WHO_DATA_COLOR,label='WHO')
    # compute rolling 7-day average
    who_covid_rolling = who_covid[who_var].rolling(window=7).mean()
    axis.plot(who_covid_rolling.index, who_covid_rolling,\
        lw=3,color=lighten_color(WHO_DATA_COLOR,1.6),label='WHO - 7d rolling average')
    # draw bucky
    draw_bucky_projections(bucky_npi,bucky_no_npi,bucky_var,axis)
    
    plt.legend(loc="upper right", prop={'size': 8})
    fig.savefig(f'Outputs/{country_iso3}/lifetime_{metric}.png')

def draw_bucky_projections(bucky_npi,bucky_no_npi,bucky_var,axis):
    bucky_npi=bucky_npi[bucky_npi[bucky_var]>0]
    bucky_npi_median=bucky_npi[bucky_npi['q']==0.5][bucky_var]
    bucky_npi_median.plot(c=NPI_COLOR,ax=axis,label='Current NPIs maintained')
    axis.fill_between(bucky_npi_median.index,\
                          bucky_npi[bucky_npi['q']==MIN_QUANTILE][bucky_var],
                          bucky_npi[bucky_npi['q']==MAX_QUANTILE][bucky_var],
                          color=NPI_COLOR,alpha=0.2
                          )
    # draw line NO NPI
    bucky_no_npi=bucky_no_npi[bucky_no_npi[bucky_var]>0]
    bucky_no_npi_median=bucky_no_npi[bucky_no_npi['q']==0.5][bucky_var]
    bucky_no_npi_median.plot(c=NO_NPI_COLOR,ax=axis,label='No NPIs in place'.format())
    axis.fill_between(bucky_no_npi_median.index,\
                          bucky_no_npi[bucky_no_npi['q']==MIN_QUANTILE][bucky_var],
                          bucky_no_npi[bucky_no_npi['q']==MAX_QUANTILE][bucky_var],
                          color=NO_NPI_COLOR,alpha=0.2
                          )

def create_subnational_map_cases100k(country_iso3, parameters,date,output_file):
    bucky_npi = get_bucky(country_iso3, admin_level='adm1', min_date=date, max_date=date, npi_filter='npi')
    bucky_npi = bucky_npi[bucky_npi['q'] == 0.5][['adm1', 'cases_per_100k']]
    bucky_npi = bucky_npi.loc[date, :]
    adm1_pcode_prefix = parameters['iso2_code']
    if country_iso3 == 'IRQ':
        adm1_pcode_prefix = 'IQG'
    bucky_npi['adm1'] = adm1_pcode_prefix + bucky_npi['adm1'].apply(lambda x: "{0:0=2d}".format(int(x)))
    bucky_npi["cases_per_100k"] = bucky_npi["cases_per_100k"].astype(int)
    shapefile = gpd.read_file(parameters['shape'])
    shapefile = shapefile.merge(bucky_npi, left_on=parameters['adm1_pcode'], right_on='adm1', how='left')

    fig_title = f'Projected number of cases per 100,000 people on {date}'
    fig, axis = create_new_subplot(fig_title)
    axis.axis('off')

    # get historical max value. Using this instead of current to keep bins over the weeks more equal
    # if patterns change heavily, could also choose to set min_date to a more current date
    hist_bucky = get_bucky(country_iso3, admin_level='adm1', min_date=date - timedelta(days=90), max_date=date+timedelta(days=14),
                           npi_filter='npi')
    hist_buckys = hist_bucky[hist_bucky['q'] == 0.5]
    cases_max = hist_buckys["cases_per_100k"].astype(int).max()
    num_bins = 5
    cmap = "YlOrRd"
    bins_list = np.concatenate(([0], np.linspace(1, cases_max * 1.2, num_bins + 1, dtype=int)))
    # set bins
    norm2 = mcolors.BoundaryNorm(boundaries=bins_list, ncolors=256)
    shapefile.plot(column='cases_per_100k', cmap=cmap, norm=norm2, ax=axis)
    fig.colorbar(axis.collections[0], cax=fig.add_axes([0.9, 0.2, 0.03, 0.60]))
    shapefile.boundary.plot(linewidth=0.1, ax=axis)
    fig.savefig(f'Outputs/{country_iso3}/{output_file}',bbox_inches="tight")

def create_binary_change_map(country_iso3, parameters):
    """
    Generate a subnational map that indicates which areas are expected to have an increase and decrease in cases per 100k in two weeks
    """
    color_dict={"Increase":"red","Stable":"grey","Decrease":"green"}
    fig_title = f'Projected trend in number of cases per 100,000 people'
    df_change=calculate_subnational_trends(country_iso3,parameters)
    shapefile = gpd.read_file(parameters['shape'])
    shapefile = shapefile.merge(df_change, left_on=parameters['adm1_pcode'], right_on='adm1', how='left')
    #Classify as "increase" if cases per 100k is projected to increase by 5 or more percent in two weeks
    #decrease if this is more than -5, else stable.
    # Also stable for regions with less than 1 active cases (=nans from calculate_subnational_trends)
    shapefile.loc[:,"change_name"]=shapefile["cases_per_100k_change"].apply(lambda x: "Increase" if x>=5 else ("Decrease" if x<=-5 else "Stable"))

    fig, ax = plt.subplots(figsize=(10, 10))
    for k in shapefile["change_name"].unique():
        shapefile[shapefile["change_name"]==k].plot(color=color_dict[k], ax=ax,edgecolor='gray')
    legend_elements= [Line2D([0], [0], marker='o',markersize=15,label=k,color=color_dict[k],linestyle='None') for k in color_dict.keys()]
    leg=plt.legend(title="Legend",frameon=False,handles=legend_elements,bbox_to_anchor=(1.3,0.8))
    leg._legend_box.align = "left"

    shapefile.boundary.plot(linewidth=0.1,ax=ax,color="white")
    ax.set_axis_off()
    ax.set_title(fig_title)
    fig.savefig(f'Outputs/{country_iso3}/map_binary_change_cases_per_100k_2w.png',bbox_inches="tight")

def calculate_subnational_trends(country_iso3, parameters):
    # Top 5 and bottom 5 districts - 4 weeks trend
    bucky_npi =  get_bucky(country_iso3 ,admin_level='adm1',min_date=TODAY,max_date=TWO_WEEKS,npi_filter='npi')
    # to remove noise
    bucky_npi=bucky_npi[bucky_npi['cases_active']>1]
    bucky_npi = bucky_npi[bucky_npi['q']==0.5][['adm1','Reff','cases_per_100k']]
    adm1_pcode_prefix=parameters['iso2_code']
    if country_iso3 == 'IRQ':
        adm1_pcode_prefix='IQG'
    bucky_npi['adm1']=adm1_pcode_prefix + bucky_npi['adm1'].apply(lambda x:  "{0:0=2d}".format(int(x)))
    # make the col selector a list to ensure always a dataframe is returned (and not a series)
    start = bucky_npi.loc[[TODAY], :]
    end = bucky_npi.loc[[TWO_WEEKS], :]
    combined = start.merge(end[['adm1', 'cases_per_100k']], how='left', on='adm1')
    combined.rename(columns = {'cases_per_100k_x':'cases_per_100k_today', 'cases_per_100k_y':'cases_per_100k_inTWOweeks'}, inplace = True) 
    combined['cases_per_100k_change'] = (combined['cases_per_100k_inTWOweeks']-combined['cases_per_100k_today']) / combined['cases_per_100k_today'] * 100
    shapefile = gpd.read_file(parameters['shape'])
    shapefile=shapefile[[parameters['adm1_pcode'],parameters['adm1_name']]]
    combined=combined.merge(shapefile,how='left',left_on='adm1',right_on=parameters['adm1_pcode'])
    combined = combined.sort_values('cases_per_100k_change', ascending=False)
    combined=combined.dropna()
    combined['cases_per_100k_change']=combined['cases_per_100k_change'].astype(int)
    # combined=combined[[parameters['adm1_name'],'cases_per_100k_change']]
    combined.to_csv(f'Outputs/{country_iso3}/ADM1_ranking.csv', index=False)
    return combined





if __name__ == "__main__":
    args = parse_args()
    main(args.country_iso3.upper(),download_covid=args.download_covid)


def generate_new_cases_graph(country_iso3):
    # get all time cases and deaths
    who_covid_new = get_who(WHO_COVID_FILENAME,country_iso3, min_date=pd.to_datetime('2000-01-01'),max_date=TODAY)
    who_covid_new.reset_index(inplace=True)

    # compute rolling 7-day average
    who_covid_new['new_cases_rolling_mean'] = who_covid_new.NewCase.rolling(window=7).mean()

    # Create figure and plot space
    fig, ax = plt.subplots(figsize=(10, 10))

    # Add x-axis and y-axis
    ax.bar(who_covid_new['date_epicrv'],
            who_covid_new['NewCase'],
            color='cornflowerblue')

    # format the ticks
    months = mdates.MonthLocator()  
    months_fmt = mdates.DateFormatter('%m-%Y')

    ax.xaxis.set_major_locator(months)
    ax.xaxis.set_major_formatter(months_fmt)

    # Set title and labels for axes
    ax.set(xlabel="Date",
        ylabel="New Cases",
        title="Daily Cases")

    # add rolling average trend line
    plt.plot(who_covid_new['date_epicrv'], who_covid_new['new_cases_rolling_mean'], label='7-day average', color='navy')

    # place a label near the trendline
    ax.text(0.05, 0.13, "Seven-day average", transform=ax.transAxes, fontsize=14,
            verticalalignment='top', color='navy')

    plt.show()
    fig.savefig(f'Outputs/{country_iso3}/current_new_cases.png')

def generate_new_deaths_graph(country_iso3):
    # compute rolling 7-day average
    who_covid_new['new_deaths_rolling_mean'] = who_covid_new.NewDeath.rolling(window=7).mean()

    # Create figure and plot space
    fig, ax = plt.subplots(figsize=(10, 10))

    # Add x-axis and y-axis
    ax.bar(who_covid_new['date_epicrv'],
            who_covid_new['NewDeath'],
            color='indianred')

    # format the ticks
    months = mdates.MonthLocator()
    months_fmt = mdates.DateFormatter('%m-%Y')

    ax.xaxis.set_major_locator(months)
    ax.xaxis.set_major_formatter(months_fmt)

    # Set title and labels for axes
    ax.set(xlabel="Date",
        ylabel="New Deaths",
        title="Daily Deaths")

    # add rolling average trend line
    plt.plot(who_covid_new['date_epicrv'], who_covid_new['new_deaths_rolling_mean'], label='7-day average', color='darkred')

    # place a label near the trendline
    ax.text(0.05, 0.13, "Seven-day average", transform=ax.transAxes, fontsize=14,
            verticalalignment='top', color='darkred')

    plt.show()
    fig.savefig(f'Outputs/{country_iso3}/current_new_deaths.png')