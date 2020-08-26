import utils
import pandas as pd
import matplotlib.pyplot as plt
import os
import geopandas as gpd
from datetime import datetime,timedelta
import matplotlib.dates as mdates

from utils import *

ASSESSMENT_DATE='2020-08-26' 
# TODAY = date.today()
TODAY = datetime.strptime(ASSESSMENT_DATE, '%Y-%m-%d').date()
FOUR_WEEKS = TODAY + timedelta(days=28)
TWO_WEEKS = TODAY + timedelta(days=14)
LAST_TWO_MONTHS = TODAY - timedelta(days=60)

MIN_QUANTILE=0.25
MAX_QUANTILE=0.75
# MIN_QUANTILE=0.05
# MAX_QUANTILE=0.95

CONFIG_FILE = 'config.yml'
DIR_PATH = os.path.dirname(os.path.realpath(__file__))
WHO_COVID_URL='https://covid19.who.int/WHO-COVID-19-global-data.csv'
WHO_COVID_FILENAME='WHO_data/WHO-COVID-19-global-data.csv'

NPI_COLOR='green'
NO_NPI_COLOR='red'
WHO_DATA_COLOR='dodgerblue'
SUBNATIONAL_DATA_COLOR='navy'

def main(country_iso3='AFG',download_covid=False):

    parameters = utils.parse_yaml(CONFIG_FILE)[country_iso3]
    if download_covid:
        # Download latest covid file tiles and read them in
        download_who_covid_data(WHO_COVID_URL,f'{DIR_PATH}/{WHO_COVID_FILENAME}')
    set_matlotlib(plt)
    print('\n\n\n')
    print(f'{country_iso3}')
    extract_reff(country_iso3)
    generate_key_figures(country_iso3,parameters)
    generate_data_model_comparison(country_iso3,parameters)
    generate_model_projections(country_iso3,parameters)
    create_subnational_map(country_iso3, parameters)
    calculate_subnational_trends(country_iso3, parameters)
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


def create_subnational_map(country_iso3, parameters):
    # Total cases - four weeks projection
    bucky_npi =  get_bucky(country_iso3 ,admin_level='adm1',min_date=TODAY,max_date=TWO_WEEKS,npi_filter='npi')
    bucky_npi = bucky_npi[bucky_npi['q']==0.5][['adm1','cases_per_100k']]
    bucky_npi = bucky_npi.loc[TWO_WEEKS,:]
    bucky_npi['adm1']=parameters['iso2_code'] + bucky_npi['adm1'].apply(lambda x:  "{0:0=2d}".format(int(x)))
    shapefile = gpd.read_file(parameters['shape'])
    shapefile = shapefile.merge(bucky_npi, left_on=parameters['adm1_pcode'], right_on='adm1', how='left')
    fig_title=f'Projected number of cases per 100,000 people'
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