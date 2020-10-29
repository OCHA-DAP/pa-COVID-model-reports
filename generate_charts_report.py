import os
import shutil
import geopandas as gpd
from datetime import datetime,timedelta
import sys
import matplotlib
import matplotlib.colors as mcolors

import utils
from utils import *

country_iso_3 = sys.argv[1]

ASSESSMENT_DATE='2020-10-27'
TODAY = datetime.strptime(ASSESSMENT_DATE, '%Y-%m-%d').date()
FOUR_WEEKS = TODAY + timedelta(days=28)
TWO_WEEKS = TODAY + timedelta(days=14)
LAST_TWO_MONTHS = TODAY - timedelta(days=60)
EARLIEST_DATE = datetime.strptime('2020-02-24', '%Y-%m-%d').date()

#these are the quantile values to consider for min and max projected numbers
MIN_QUANTILE=0.25
MAX_QUANTILE=0.75

CONFIG_FILE = 'config.yml'
DIR_PATH = os.path.dirname(os.path.realpath(__file__))
WHO_COVID_URL='https://covid19.who.int/WHO-COVID-19-global-data.csv'
WHO_COVID_FILENAME='WHO_data/WHO-COVID-19-global-data.csv'
RESULTS_FILENAME=f'automated_reports/report_metrics/{country_iso_3}_results.csv'
OUTPUT_DIR=f'Outputs/{country_iso_3}/'
NPISHEET_PATH=f'{OUTPUT_DIR}npis_googlesheet.csv'

NPI_COLOR='green'
NO_NPI_COLOR='red'
WHO_DATA_COLOR='dodgerblue'
SUBNATIONAL_DATA_COLOR='navy'

def main(country_iso3, download_covid=False,output_folder=OUTPUT_DIR):

    parameters = utils.parse_yaml(CONFIG_FILE)[country_iso3]
    if download_covid:
        # Download latest covid file tiles and read them in
        download_who_covid_data(WHO_COVID_URL,f'{DIR_PATH}/{WHO_COVID_FILENAME}')

    #function from utils to set plot parameters
    set_matlotlib(plt)

    #create folder if doesn't exist and if it exists empty the folder
    #done such that old files with changed filenames are not lingering around in the output folder
    if os.path.exists(output_folder):
        shutil.rmtree(output_folder)
    os.makedirs(output_folder)

    print('\n\n\n')
    print(f'{country_iso3}')

    #retrieve file with previously computed metrics
    if os.path.exists(RESULTS_FILENAME):
        df_all=pd.read_csv(RESULTS_FILENAME)
        #remove the rows that have same assessment date as current run
        #-->make sure not duplicate results for the same date
        df_all=df_all[df_all['assessment_date']!=str(TODAY)]
    else:
        df_all=pd.DataFrame()

    #compute metrics wrt to TODAY (can also be projections)
    df_reff = extract_reff(country_iso3)
    df_keyfigures = generate_key_figures(country_iso3,parameters)
    df_hospitalizations = generate_model_projections(country_iso3, parameters)
    #create dataframe with metrics computed wrt to TODAY
    results_df=pd.concat([df_reff,df_keyfigures,df_hospitalizations]).reset_index()
    results_df.columns=['metric_name','metric_value']
    results_df['assessment_date'] = TODAY
    results_df['country'] = f'{country_iso_3}'
    #append metrics to file with metrics of all dates
    df_all = df_all.append(results_df)
    df_all.to_csv(RESULTS_FILENAME, index=False)

    #calculate trends (being saved to separate csv within function)
    calculate_subnational_trends(country_iso3, parameters)

    #retrieve active, modelled NPIS (Non Pharmeutical Interventions)
    #currently not used in report so not added to results_df
    retrieve_current_npis(parameters['npis_url'],NPISHEET_PATH)

    #retrieve the incidence (=NEW daily cases/100k) per admin and country average, for total and reported incidence
    calculate_subnational_incidence(country_iso3, parameters, TODAY + timedelta(days=1))

    #create graphs of cumulative cases, cumulative deaths, new daily cases, daily deaths
    #of last two months
    generate_data_model_comparison(country_iso3,parameters)
    #of start COVID
    generate_data_model_comparison_lifetime(country_iso3,parameters)

    #active hospitalizations/100k TODAY
    create_subnational_map_incidence_100k('hospitalizations_per_100k', country_iso3, parameters, TODAY, 'Current Reported Hospitalizations \n Per 100,000 People',
                           'map_hospitalizations_per_100k_current.png')
    #new reported daily cases/100k on TODAY+1
    #set to TODAY+1 instead of TODAY since on TODAY the output can be negative due to initialization. This should be fixed in a future version of the model
    create_subnational_map_incidence_100k('daily_reported_cases_per_100k', country_iso3, parameters, TODAY+timedelta(days=1), 'Current Reported New Daily Cases \n Per 100,000 People',
                           'map_dailyreportedcases_per_100k_current.png')
    #new estimated total daily cases/100k (i.e. reported cases*reporting rate) on TODAY+1
    create_subnational_map_incidence_100k('daily_cases_total_per_100k', country_iso3, parameters, TODAY+timedelta(days=1), 'Current Estimated Total New Daily Cases \n Per 100,000 People',
                           'map_dailytotalcases_per_100k_current.png')
    #new reported daily cases/100k in TWO_WEEKS
    create_subnational_map_incidence_100k('daily_reported_cases_per_100k', country_iso3, parameters, TWO_WEEKS, 'Projected Reported New Daily Cases \n Per 100,000 People',
                           'map_dailyreportedcases_per_100k_2w.png')
    #new estimated total daily cases/100k in TWO_WEEKS
    create_subnational_map_incidence_100k('daily_cases_total_per_100k', country_iso3, parameters, TWO_WEEKS, 'Projected Estimated Total New Daily Cases \n Per 100,000 People',
                           'map_dailytotalcases_per_100k_2w.png')
    #not being used in current report
    # create_binary_change_map(country_iso3, parameters)


def retrieve_current_npis(npis_url,output_path):
    """
    Display the NPIs that are currently in place and are given as input to the model
    Note: these NPIs might not be fully up to date
    Args:
        npis_url: url to the csv with the list of all npis
        output_path: path to where to save the npi csv while downloading
    """
    download_url(npis_url, output_path)
    df_npis_sheet = pd.read_csv(output_path)
    #final_input==Yes indicates that the npi is given as input to the model
    df_npis_model = df_npis_sheet[df_npis_sheet['final_input'] == 'Yes']
    print('Currently in place NPIs')
    print(df_npis_model[['acaps_category', 'acaps_measure', 'bucky_measure', 'affected_pcodes', 'compliance_level', 'start_date','end_date']])

def extract_reff(country_iso3):
    """
    Calculate the estimated doubling time and the effective reproduction number of the coming four weeks, for the scenarios when current NPIs are in place and when they wouldn't
    Args:
        country_iso3: iso3 code of the country of interest
    Returns:
        df_metrics: DataFrame containing the computed metrics
    """
    bucky_npi=get_bucky(country_iso3,admin_level='adm0',min_date=TODAY,max_date=FOUR_WEEKS,npi_filter='npi')
    bucky_npi=bucky_npi[bucky_npi['quantile']==0.5]
    #this is calculated over the period that is included in bucky_npi, so from TODAY till FOUR_WEEKS and is based on the reported cumulative cases
    dt_npi,r_npi=get_bucky_dt_reff(bucky_npi)
    #Reff= effective reproduction number, i.e. average number of secondary cases/infectious case in a population given the context, e.g. including measurements
    print(f'Estimated doubling time NPI {dt_npi}, Reff {r_npi}')

    bucky_no_npi=get_bucky(country_iso3,admin_level='adm0',min_date=TODAY,max_date=FOUR_WEEKS,npi_filter='no_npi')
    bucky_no_npi=bucky_no_npi[bucky_no_npi['quantile']==0.5]
    dt_no_npi,r_no_npi=get_bucky_dt_reff(bucky_no_npi)
    print(f'Estimated doubling time No NPI {dt_no_npi}, Reff {r_no_npi}')

    #create dict with all metrics
    dict_metrics={'Estimated doubling time NPI':dt_npi,'NPI Reff':r_npi,'Estimated doubling time No NPI':dt_no_npi,'No NPI Reff':r_no_npi}
    #convert dict to dataframe
    df_metrics=pd.DataFrame.from_dict(dict_metrics,orient='index')
    return df_metrics

def generate_key_figures(country_iso3,parameters):
    """
    Retrieve the current cumulative cases and deaths given by WHO, MPHO (subnational) and the model (Bucky).
    Moreover, compute the percentual change in new cases over the last week compared to the previous week based on WHO data
    And, compute the expected number of cumulative cases and deaths in four weeks, both with and without current NPIs in place, based on the model output.
    Args:
        country_iso3: iso3 code of the country of interest
        parameters: country specific parameters, retrieved from config

    Returns:
        df_metrics: DataFrame containing the computed metrics
    """
    #This is the World Health Organization (WHO) data and is available on national level
    #all the numbers of WHO are reported numbers
    who_covid=get_who(WHO_COVID_FILENAME,parameters['iso2_code'],min_date=LAST_TWO_MONTHS,max_date=TODAY)
    who_covid.index = pd.to_datetime(who_covid.index)
    who_deaths_today=who_covid.loc[TODAY,'Cumulative_deaths']
    who_cases_today=who_covid.loc[TODAY,'Cumulative_cases']
    #CFR= Case Fatality Rate
    CFR=who_deaths_today/who_cases_today*100
    print(
        f'Current situation WHO {TODAY}: {who_cases_today:.0f} cumulative reported cases, {who_deaths_today:.0f} cumulative reported deaths')
    # computed over cumulative cases
    print(f'CFR from WHO based on cumulative cases up to {TODAY}: {CFR:.1f}')

    # this is the data reported by the Ministry of Public Health (MPHO) and is available on subnational level
    # all the numbers of MPHO are reported numbers
    subnational_covid = get_subnational_covid_data(parameters, aggregate=True, min_date=LAST_TWO_MONTHS, max_date=TODAY)
    subnational_covid.sort_index(inplace=True)
    subnational_lastdate = subnational_covid.iloc[-1].name.strftime('%Y-%m-%d')
    subnational_cases_latest = subnational_covid.iloc[-1][HLX_TAG_TOTAL_CASES].astype(int)
    subnational_deaths_latest = subnational_covid.iloc[-1][HLX_TAG_TOTAL_DEATHS].astype(int)
    print(
        f'Latest date of data by MPHO (subnational) was {subnational_lastdate}: {subnational_cases_latest} cumulative reported cases, {subnational_deaths_latest} cumulative reported deaths')


    bucky_npi = get_bucky(country_iso3, admin_level='adm0', min_date=TODAY, max_date=FOUR_WEEKS, npi_filter='npi')

    #cumulative cases TODAY - cumulative cases YESTERDAY might not always equal the daily cases TODAY. This is due to the model being run several times after which the results are divided in quantiles.
    bucky_npi_cases_today = round(bucky_npi[bucky_npi['quantile'] == 0.5].loc[TODAY, 'cumulative_reported_cases']).astype(int)
    bucky_npi_cases_today_notrep = round(bucky_npi[bucky_npi['quantile'] == 0.5].loc[TODAY, 'cumulative_cases']).astype(int)
    bucky_npi_deaths_today = round(bucky_npi[bucky_npi['quantile'] == 0.5].loc[TODAY, 'cumulative_deaths']).astype(int)
    reporting_rate = bucky_npi['case_reporting_rate'].mean() * 100
    print(
        f'Current situation Bucky {TODAY}: {bucky_npi_cases_today:.0f} cumulative reported cases, {bucky_npi_deaths_today:.0f} cumulative reported deaths')
    print(f'Current situation Bucky {TODAY}: {bucky_npi_cases_today_notrep:.0f} cumulative estimated total cases')
    print(f'- ESTIMATED CASE REPORTING RATE {reporting_rate:.0f}%')

    #calculate average over 7 last 7 days for the WHO data (MPHO data is too sparse to compute this on)
    #select the last week and use rolling, which returns nan if less than min_periods datapoints
    who_covid_mean = who_covid.loc[TODAY-timedelta(days=6):TODAY,['New_cases','New_deaths']].rolling(window=7,min_periods=4).mean()
    who_covid_newcases_avg_week = who_covid_mean.loc[TODAY,'New_cases']
    who_covid_newdeaths_avg_week = who_covid_mean.loc[TODAY,'New_deaths']
    print(f'Average new daily cases of the last 7 days from WHO: {who_covid_newcases_avg_week:.2f}')
    print(f'Average new daily deaths of the last 7 days from WHO: {who_covid_newdeaths_avg_week:.2f}')

    #this is currently not in use in the report. We chose to go with TODAY - 7 days instead of Mon-Sun because of data freshness
    # #calculate the percentual change of the sum of new cases and new deaths of last week compared to the previous week
    # #this is done with WHO data, on national level
    # #a week is defined being from Mon-Sun and thus last week is the last complete week
    # #this is done to avoid biases due to delays in reporting, some countries report cases only after a few days (and not reporting over the weekend).
    # who_covid.groupby(['Country_code']).resample('W')
    # # get the sum of weekly NEW cases and deaths
    # new_WHO_w=who_covid.groupby(['Country_code']).resample('W').sum()[['New_cases','New_deaths']]
    # new_WHO_w[['Average_cases','Average_deaths']]=who_covid.groupby(['Country_code']).resample('W').mean()[['New_cases','New_deaths']]
    # # ndays_w is the number of days present of each week in the data
    # # this is max 7, first and last week can contain less days
    # ndays_w=who_covid.groupby(['Country_code']).resample('W').count()['New_cases']
    # new_WHO_w['ndays'] = ndays_w
    # # select only the weeks of which all days are present
    # new_WHO_w=new_WHO_w[new_WHO_w['ndays']==7]
    # # get percentual change of cases and deaths compared to previous week
    # # percentual change=((cases week n)-(cases week n-1))/(cases week n-1)
    # new_WHO_w['New_cases_PercentChange'] = new_WHO_w.groupby('Country_code')['New_cases'].pct_change()
    # new_WHO_w['New_deaths_PercentChange'] = new_WHO_w.groupby('Country_code')['New_deaths'].pct_change()
    # # get percentual change of last full week (Mon-Sun)
    # trend_w_cases=new_WHO_w.loc[new_WHO_w.index[-1],'New_cases_PercentChange']*100
    # trend_w_deaths=new_WHO_w.loc[new_WHO_w.index[-1],'New_deaths_PercentChange']*100
    # # print(f'Average new daily cases previous week: {new_WHO_w.loc[new_WHO_w.index[-2],'Average_cases']}')
    # # print(f'Average new daily cases during last week (Mon-Sun) from WHO: {new_WHO_w.loc[new_WHO_w.index[-1],'Average_cases']:.2f}')
    # #new cases during a week period
    # print(f'Percentual change in new cases and deaths during last week (Mon-Sun) wrt previous week: {trend_w_cases:.0f}% cases, {trend_w_deaths:.0f}% deaths')

    #model (i.e. bucky) outputs are not always integers. This cannot reflect the real situation, but nevertheless we choose to use the floats such that trend calculations more precisely reflect the projected development
    #numbers are only rounded for reporting purposes
    min_cases_npi=round(bucky_npi[bucky_npi['quantile']==MIN_QUANTILE].loc[FOUR_WEEKS,'cumulative_reported_cases']).astype(int)
    max_cases_npi=round(bucky_npi[bucky_npi['quantile']==MAX_QUANTILE].loc[FOUR_WEEKS,'cumulative_reported_cases']).astype(int)
    min_additional_cases_npi = min_cases_npi - bucky_npi_cases_today
    max_additional_cases_npi = max_cases_npi - bucky_npi_cases_today
    min_deaths_npi=round(bucky_npi[bucky_npi['quantile']==MIN_QUANTILE].loc[FOUR_WEEKS,'cumulative_deaths']).astype(int)
    max_deaths_npi=round(bucky_npi[bucky_npi['quantile']==MAX_QUANTILE].loc[FOUR_WEEKS,'cumulative_deaths']).astype(int)
    min_additional_deaths_npi = min_deaths_npi - bucky_npi_deaths_today
    max_additional_deaths_npi = max_deaths_npi - bucky_npi_deaths_today

    #Compute the expected percentual change in CUMULATIVE reported cases and deaths over four weeks
    rel_inc_min_cases_npi=(min_cases_npi-bucky_npi_cases_today)/bucky_npi_cases_today*100
    rel_inc_max_cases_npi=(max_cases_npi-bucky_npi_cases_today)/bucky_npi_cases_today*100
    rel_inc_min_deaths_npi=(min_deaths_npi-bucky_npi_deaths_today)/bucky_npi_deaths_today*100
    rel_inc_max_deaths_npi=(max_deaths_npi-bucky_npi_deaths_today)/bucky_npi_deaths_today*100
    print(f'- Projection date:{FOUR_WEEKS}')
    print(f'-- NPI: Projected reported cumulative cases in 4w: {min_cases_npi:.0f} - {max_cases_npi:.0f}')
    print(f'-- NPI: Projected reported additional cases in 4w: {min_additional_cases_npi:.0f} - {max_additional_cases_npi:.0f}')
    print(f'-- NPI: Projected trend reported cases in 4w: {rel_inc_min_cases_npi:.0f}% - {rel_inc_max_cases_npi:.0f}%')
    print(f'-- NPI: Projected reported cumulative deaths in 4w: {min_deaths_npi:.0f} - {max_deaths_npi:.0f}')
    print(f'-- NPI: Projected additional reported deaths in 4w: {min_additional_deaths_npi:.0f} - {max_additional_deaths_npi:.0f}')
    print(f'-- NPI: Projected trend reported deaths in 4w: {rel_inc_min_deaths_npi:.0f}% - {rel_inc_max_deaths_npi:.0f}%')

    # Compute the expected percentual change in CUMULATIVE reported cases and deaths when there are no NPIs in place
    bucky_no_npi=get_bucky(country_iso3,admin_level='adm0',min_date=TODAY,max_date=FOUR_WEEKS,npi_filter='no_npi')
    min_cases_no_npi=round(bucky_no_npi[bucky_no_npi['quantile']==MIN_QUANTILE].loc[FOUR_WEEKS,'cumulative_reported_cases']).astype(int)
    max_cases_no_npi=round(bucky_no_npi[bucky_no_npi['quantile']==MAX_QUANTILE].loc[FOUR_WEEKS,'cumulative_reported_cases']).astype(int)
    min_additional_cases_no_npi = min_cases_no_npi - bucky_npi_cases_today
    max_additional_cases_no_npi = max_cases_no_npi - bucky_npi_cases_today
    min_deaths_no_npi=round(bucky_no_npi[bucky_no_npi['quantile']==MIN_QUANTILE].loc[FOUR_WEEKS,'cumulative_deaths']).astype(int)
    max_deaths_no_npi=round(bucky_no_npi[bucky_no_npi['quantile']==MAX_QUANTILE].loc[FOUR_WEEKS,'cumulative_deaths']).astype(int)
    min_additional_deaths_no_npi = min_deaths_no_npi - bucky_npi_deaths_today
    max_additional_deaths_no_npi = max_deaths_no_npi - bucky_npi_deaths_today
    print(f'--- no_npi: Projected cumulative reported cases in 4w: {min_cases_no_npi:.0f} - {max_cases_no_npi:.0f}')
    print(f'-- no_npi: Projected additional reported cases in 4w: {min_additional_cases_no_npi:.0f} - {max_additional_cases_no_npi:.0f}')
    print(f'--- no_npi: Projected cumulative reported deaths in 4w: {min_deaths_no_npi:.0f} - {max_deaths_no_npi:.0f}')
    print(f'-- no_npi: Projected additional reported deaths in 4w: {min_additional_deaths_no_npi:.0f} - {max_additional_deaths_no_npi:.0f}')

    #compute the maximum projected increase in cumulative reported cases and deaths in four weeks if the NPIs were lifted
    no_npi_max_increase_cases=max_cases_no_npi-min_cases_npi
    no_npi_max_increase_deaths = max_deaths_no_npi - min_deaths_npi
    print(f'Maximum number of extra cases if NPIs are lifted: {no_npi_max_increase_cases:.0f}')
    print(f'Maximum number of extra deaths if NPIs are lifted: {no_npi_max_increase_deaths:.0f}')
    dict_metrics={'Current situation - WHO cases today': who_cases_today,
                  'Current situation - WHO deaths today': who_deaths_today,
                    'CFR':CFR,
                    #currently not in use in the report
                    # 'Weekly new cases wrt last week - trend':trend_w_cases,
                    # 'Weekly new deaths wrt last week - trend':trend_w_deaths,
                    'Estimated case reporting rate': reporting_rate,
                    'NPI - projected reported cases in 4w - MIN': min_cases_npi,
                    'NPI - projected reported cases in 4w - MAX': max_cases_npi,
                    'NPI - projected additional reported cases in 4w - MIN': min_additional_cases_npi,
                    'NPI - projected additional reported cases in 4w - MAX': max_additional_cases_npi,
                    'NPI - projected TREND reported cases in 4w - MIN': rel_inc_min_cases_npi,
                    'NPI - projected TREND reported cases in 4w - MAX': rel_inc_max_cases_npi,
                    'NPI - projected reported deaths in 4w - MIN': min_deaths_npi,
                    'NPI - projected reported deaths in 4w - MAX': max_deaths_npi,
                    'NPI - projected additional reported deaths in 4w - MIN': min_additional_deaths_npi,
                    'NPI - projected additional reported deaths in 4w - MAX': max_additional_deaths_npi,
                    'NPI - projected TREND reported deaths in 4w - MIN': rel_inc_min_deaths_npi,
                    'NPI - projected TREND reported deaths in 4w - MAX': rel_inc_max_deaths_npi,
                    'NO NPI - projected reported cases in 4w - MIN': min_cases_no_npi,
                    'NO NPI - projected reported cases in 4w - MAX': max_cases_no_npi,
                    'NO NPI - projected additional reported cases in 4w - MIN': min_additional_cases_no_npi,
                    'NO NPI - projected additional reported cases in 4w - MAX': max_additional_cases_no_npi,
                    'NO NPI - projected reported deaths in 4w - MIN': min_deaths_no_npi,
                    'NO NPI - projected reported deaths in 4w - MAX': max_deaths_no_npi,
                    'NO NPI - projected additional reported deaths in 4w - MIN': min_additional_deaths_no_npi,
                    'NO NPI - projected additional reported deaths in 4w - MAX': max_additional_deaths_no_npi,
                    'Maximum number of extra cases if NPIs are lifted': no_npi_max_increase_cases,
                    'Maximum number of extra deaths if NPIs are lifted': no_npi_max_increase_deaths,
                    'Current situation - latest date MPHO reported numbers': subnational_lastdate,
                    'Current situation - latest MPHO cases': subnational_cases_latest,
                    'Current situation - latest MPHO deaths': subnational_deaths_latest,
                    'Current situation - WHO daily new cases, 7-day average': who_covid_newcases_avg_week,
                    'Current situation - WHO daily new deaths, 7-day average': who_covid_newdeaths_avg_week
                }

    df_metrics=pd.DataFrame.from_dict(dict_metrics, orient='index')
    return df_metrics

def generate_model_projections(country_iso3,parameters):
    """
    Compute metrics and draw a graph related to the current and projected number of hospitalizations
    Args:
        country_iso3: iso3 code of the country of interest
        parameters: country specific parameters, retrieved from config

    Returns:
        df_metrics: DataFrame with the computed metrics
    """
    # generate plot with four-weeks ahead projections of daily cases
    bucky_npi=get_bucky(country_iso3,admin_level='adm0',min_date=TODAY,max_date=FOUR_WEEKS,npi_filter='npi')
    bucky_no_npi=get_bucky(country_iso3,admin_level='adm0',min_date=TODAY,max_date=FOUR_WEEKS,npi_filter='no_npi')
    metric, metric_today_min, metric_today_max, metric_4w_npi_min, metric_4w_npi_max, metric_4w_no_npi_min, metric_4w_no_npi_max, metric_additional_npi_min, metric_additional_npi_max, metric_additional_no_npi_min, metric_additional_no_npi_max = draw_model_projections(country_iso3,bucky_npi,bucky_no_npi,parameters,'hospitalizations')

    dict_metric={f'{metric.capitalize()} current situation - MIN': metric_today_min,
    f'{metric.capitalize()} current situation - MAX':metric_today_max,
    f'NPI {metric.capitalize()} projections 4w - MIN': metric_4w_npi_min,
    f'NPI {metric.capitalize()} projections 4w - MAX': metric_4w_npi_max,
    f'NPI additional {metric.capitalize()} projections 4w - MIN': metric_additional_npi_min,
    f'NPI additional {metric.capitalize()} projections 4w - MAX': metric_additional_npi_max,
    f'NO NPI {metric.capitalize()} projections 4w - MIN': metric_4w_no_npi_min,
    f'NO NPI {metric.capitalize()} projections 4w - MAX': metric_4w_no_npi_max,
    f'NO NPI additional {metric.capitalize()} projections 4w - MIN': metric_additional_no_npi_min,
    f'NO NPI additional {metric.capitalize()} projections 4w - MAX': metric_additional_no_npi_max}

    df_metrics=pd.DataFrame.from_dict(dict_metric,orient='index')
    return df_metrics

def draw_model_projections(country_iso3,bucky_npi,bucky_no_npi,parameters,metric):
    """
    Compute the projected trends of the given metric, if NPIs are in place and when they are lifted, and produce a plot
    Args:
        country_iso3: iso3 code of the country of interest
        bucky_npi: DataFrame with model projections given the current NPIs
        bucky_no_npi: DataFrame with model projections given the NPIs are lifted
        parameters:
        metric: the column name to compute the metrics on
        parameters: country specific parameters, retrieved from config
    Returns:
        the min and max value of the metric today and in four weeks, with and without NPIs
    """
    # draw NPI vs non NPIs projections
    if metric=='daily_reported_cases':
        bucky_var='daily_reported_cases'
        fig_title='Daily reported cases'
    elif metric=='daily_deaths':
        bucky_var='daily_deaths'
        fig_title='Daily deaths'
    elif metric=='hospitalizations':
        bucky_var='current_hospitalizations'
        fig_title='People requiring healthcare support'
    else:
        print(f'metric {metric} not implemented')
        return

    #plot the history and projection of the metric, including uncertainty intervals
    fig,axis=create_new_subplot(fig_title)
    draw_bucky_projections(bucky_npi,bucky_no_npi,bucky_var,axis)
    plt.legend()
    print(f'----{metric} statistics')
    #bucky_no_npi and bucky_npi are initialized with the same numbers, so doesn't matter which is being used for displaying the current situation
    metric_today_min=round(bucky_no_npi[bucky_no_npi['quantile']==MIN_QUANTILE].loc[TODAY,bucky_var]).astype(int)
    metric_today_max=round(bucky_no_npi[bucky_no_npi['quantile']==MAX_QUANTILE].loc[TODAY,bucky_var]).astype(int)
    metric_4w_npi_min=round(bucky_npi[bucky_npi['quantile']==MIN_QUANTILE].loc[FOUR_WEEKS,bucky_var]).astype(int)
    metric_4w_npi_max=round(bucky_npi[bucky_npi['quantile']==MAX_QUANTILE].loc[FOUR_WEEKS,bucky_var]).astype(int)
    metric_4w_no_npi_min=round(bucky_no_npi[bucky_no_npi['quantile']==MIN_QUANTILE].loc[FOUR_WEEKS,bucky_var]).astype(int)
    metric_4w_no_npi_max=round(bucky_no_npi[bucky_no_npi['quantile']==MAX_QUANTILE].loc[FOUR_WEEKS,bucky_var]).astype(int)
    metric_additional_npi_min=metric_4w_npi_min-metric_today_min
    metric_additional_npi_max=metric_4w_npi_max-metric_today_max
    metric_additional_no_npi_min=metric_4w_no_npi_min-metric_today_min
    metric_additional_no_npi_max=metric_4w_no_npi_max-metric_today_max

    print(f'----{metric} {TODAY}: {metric_today_min:.0f} - {metric_today_max:.0f}')
    print(f'----{metric} NPI {FOUR_WEEKS}: {metric_4w_npi_min:.0f} - {metric_4w_npi_max:.0f}')
    print(f'----{metric} additional NPI {FOUR_WEEKS}: {metric_additional_npi_min:.0f} - {metric_additional_npi_max:.0f}')
    print(f'----{metric} NO NPI {FOUR_WEEKS}: {metric_4w_no_npi_min:.0f} - {metric_4w_no_npi_max:.0f}')
    print(f'----{metric} additional NO NPI {FOUR_WEEKS}: {metric_additional_no_npi_min:.0f} - {metric_additional_no_npi_max:.0f}')
    fig.savefig(f'Outputs/{country_iso3}/projection_{metric}.png')

    return metric, metric_today_min, metric_today_max, metric_4w_npi_min, metric_4w_npi_max, metric_4w_no_npi_min, metric_4w_no_npi_max, metric_additional_npi_min, metric_additional_npi_max, metric_additional_no_npi_min, metric_additional_no_npi_max

def generate_data_model_comparison(country_iso3,parameters):
    """
    Produce plots of the last two months and the projections of the coming four weeks with cumulative reported cases, cumulative deaths, daily new cases, and daily deaths
    Args:
        country_iso3: iso3 code of the country of interest
        parameters: country specific parameters, retrieved from config
    """
    # generate plot with subnational data, WHO data and projections
    subnational_covid=get_subnational_covid_data(parameters,aggregate=True,min_date=LAST_TWO_MONTHS,max_date=FOUR_WEEKS)
    who_covid=get_who(WHO_COVID_FILENAME,parameters['iso2_code'],min_date=LAST_TWO_MONTHS,max_date=FOUR_WEEKS)
    bucky_npi=get_bucky(country_iso3,admin_level='adm0',min_date=LAST_TWO_MONTHS,max_date=FOUR_WEEKS,npi_filter='npi')
    bucky_no_npi=get_bucky(country_iso3,admin_level='adm0',min_date=LAST_TWO_MONTHS,max_date=FOUR_WEEKS,npi_filter='no_npi')

    #cumulative reported cases
    draw_data_model_comparison_cumulative(country_iso3,subnational_covid,who_covid,bucky_npi,bucky_no_npi,parameters,'cumulative_reported_cases')
    #cumulative deaths
    draw_data_model_comparison_cumulative(country_iso3,subnational_covid,who_covid,bucky_npi,bucky_no_npi,parameters,'cumulative_deaths')

    #daily new reported cases
    draw_data_model_comparison_new(country_iso3,who_covid,bucky_npi,bucky_no_npi,'daily_reported_cases')
    #daily reported deaths
    draw_data_model_comparison_new(country_iso3,who_covid,bucky_npi,bucky_no_npi,'daily_deaths')

def generate_data_model_comparison_lifetime(country_iso3,parameters):
    """
    Produce plots from the moment cases were reported till now plus projections of the coming four weeks with cumulative reported cases, cumulative deaths, daily new cases, and daily deaths
    Args:
        country_iso3: iso3 code of the country of interest
        parameters: country specific parameters, retrieved from config
    """
    # generate plot with subnational data, WHO data and projections
    subnational_covid=get_subnational_covid_data(parameters,aggregate=True,min_date=EARLIEST_DATE,max_date=FOUR_WEEKS)
    who_covid=get_who(WHO_COVID_FILENAME,parameters['iso2_code'],min_date=EARLIEST_DATE,max_date=FOUR_WEEKS)
    bucky_npi=get_bucky(country_iso3,admin_level='adm0',min_date=EARLIEST_DATE,max_date=FOUR_WEEKS,npi_filter='npi')
    bucky_no_npi=get_bucky(country_iso3,admin_level='adm0',min_date=EARLIEST_DATE,max_date=FOUR_WEEKS,npi_filter='no_npi')

    #cumulative reported cases
    draw_data_model_comparison_cumulative_lifetime(country_iso3,subnational_covid,who_covid,bucky_npi,bucky_no_npi,parameters,'cumulative_reported_cases')
    #cumulative reported deaths
    draw_data_model_comparison_cumulative_lifetime(country_iso3,subnational_covid,who_covid,bucky_npi,bucky_no_npi,parameters,'cumulative_deaths')

    #daily new reported cases
    draw_data_model_comparison_new_lifetime(country_iso3,who_covid,bucky_npi,bucky_no_npi,'daily_reported_cases')
    #daily deaths
    draw_data_model_comparison_new_lifetime(country_iso3,who_covid,bucky_npi,bucky_no_npi,'daily_deaths')

def draw_data_model_comparison_cumulative(country_iso3,subnational_covid,who_covid,bucky_npi,bucky_no_npi,parameters,metric):
    """
    For the given metric, plot the WHO and subnational historical data for the last two months plus the projected numbers by the model, given npis are in place and are lifted
    Args:
        country_iso3: iso3 code of the country of interest
        subnational_covid: DataFrame with historical subnational data reported by MPHO
        who_covid: DataFrame with historical national data reported by WHO
        bucky_npi: DataFrame with model projections given the current NPIs
        bucky_no_npi: DataFrame with model projections given the NPIs are lifted
        parameters: country specific parameters, retrieved from config
        metric: the column name to plot the data from
    """
    if metric=='cumulative_reported_cases':
        who_var='Cumulative_cases'
        bucky_var='cumulative_reported_cases'
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

    # draw WHO national reported numbers
    axis.scatter(who_covid.index, who_covid[who_var],
                     alpha=0.8, s=20,c=WHO_DATA_COLOR,marker='*',label='WHO')
    # draw subnational reported numbers
    axis.scatter(subnational_covid.index, subnational_covid[subnational_var],\
                     alpha=0.8, s=20,c=SUBNATIONAL_DATA_COLOR,marker='o',label=subnational_source)
    # draw bucky projections and uncertainty intervals
    draw_bucky_projections(bucky_npi,bucky_no_npi,bucky_var,axis)

    plt.legend()
    fig.savefig(f'Outputs/{country_iso3}/current_{metric}.png')

def draw_data_model_comparison_cumulative_lifetime(country_iso3,subnational_covid,who_covid,bucky_npi,bucky_no_npi,parameters,metric):
    """
    For the given metric, plot the WHO and subnational historical data from the moment numbers were reported plus the projected numbers by the model, given npis are in place and are lifted
    Args:
        country_iso3: iso3 code of the country of interest
        subnational_covid: DataFrame with historical subnational data reported by MPHO
        who_covid: DataFrame with historical national data reported by WHO
        bucky_npi: DataFrame with model projections given the current NPIs
        bucky_no_npi: DataFrame with model projections given the NPIs are lifted
        parameters: country specific parameters, retrieved from config
        metric: the column name to plot the data from
    """
    if metric=='cumulative_reported_cases':
        who_var='Cumulative_cases'
        bucky_var='cumulative_reported_cases'
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
    who_mindate=who_covid[(who_covid[['Cumulative_cases','Cumulative_deaths']] > 0).any(1)].index.min()
    subnational_mindate=subnational_covid[(subnational_covid[[HLX_TAG_TOTAL_CASES,HLX_TAG_TOTAL_DEATHS]] > 0).any(1)].index.min()
    mindate=min(who_mindate,subnational_mindate)-timedelta(days=14)
    who_covid_start=who_covid.loc[mindate:,:]
    subnational_covid_start=subnational_covid.loc[mindate:,:]
    bucky_npi_start=bucky_npi.loc[mindate:,:]
    bucky_no_npi_start=bucky_no_npi.loc[mindate:,:]


    # draw subnational reported cumulative cases
    axis.scatter(who_covid_start.index, who_covid_start[who_var],
                     alpha=0.8, s=20,c=WHO_DATA_COLOR,marker='*',label='WHO')
    axis.scatter(subnational_covid_start.index, subnational_covid_start[subnational_var],
                     alpha=0.8, s=20,c=SUBNATIONAL_DATA_COLOR,marker='o',label=subnational_source)
    # draw bucky
    draw_bucky_projections(bucky_npi_start,bucky_no_npi_start,bucky_var,axis)

    plt.legend(loc='lower right', prop={'size': 8})
    fig.savefig(f'Outputs/{country_iso3}/lifetime_{metric}.png')

def draw_data_model_comparison_new(country_iso3,who_covid,bucky_npi,bucky_no_npi,metric):
    """
    For the given metric, plot the daily numbers with a 7-day rolling average of the last two months. Plus the projected numbers as given by the model
    Args:
        country_iso3: iso3 code of the country of interest
        who_covid: DataFrame with historical national data reported by WHO
        bucky_npi: DataFrame with model projections given the current NPIs
        bucky_no_npi: DataFrame with model projections given the NPIs are lifted
        metric: the column name to plot the data from
    """
    # plot the 4 inputs and save figure
    if metric=='daily_reported_cases':
        who_var='New_cases'
        bucky_var='daily_reported_cases'
        fig_title='Daily reported cases'
    elif metric=='daily_deaths':
        who_var='New_deaths'
        bucky_var='daily_deaths'
        fig_title='Daily reported deaths'
    else:
        print(f'metric {metric} not implemented')
        return False

    fig,axis=create_new_subplot(fig_title)
    # draw reported data by who
    axis.bar(who_covid.index, who_covid[who_var],alpha=0.8,color=WHO_DATA_COLOR,label='WHO')
    # compute rolling 7-day average
    who_covid_rolling = who_covid[who_var].rolling(window=7).mean()
    axis.plot(who_covid_rolling.index, who_covid_rolling,
        lw=3,color=lighten_color(WHO_DATA_COLOR,1.6),label='WHO - 7d rolling average')
    # draw bucky
    draw_bucky_projections(bucky_npi,bucky_no_npi,bucky_var,axis)

    plt.legend()
    fig.savefig(f'Outputs/{country_iso3}/current_{metric}.png')

def draw_data_model_comparison_new_lifetime(country_iso3,who_covid,bucky_npi,bucky_no_npi,metric):
    """
    For the given metric, plot the daily numbers with a 7-day rolling average from the moment numbers were reported. Plus the projected numbers as given by the model
    Args:
        country_iso3: iso3 code of the country of interest
        who_covid: DataFrame with historical national data reported by WHO
        bucky_npi: DataFrame with model projections given the current NPIs
        bucky_no_npi: DataFrame with model projections given the NPIs are lifted
        metric: the column name to plot the data from
    """
    if metric=='daily_reported_cases':
        who_var='New_cases'
        bucky_var='daily_reported_cases'
        fig_title='Daily reported cases'
    elif metric=='daily_deaths':
        who_var='New_deaths'
        bucky_var='daily_deaths'
        fig_title='Daily reported deaths'
    else:
        print(f'metric {metric} not implemented')
        return False
    fig,axis=create_new_subplot(fig_title)
    axis.bar(who_covid.index, who_covid[who_var],alpha=0.8,color=WHO_DATA_COLOR,label='WHO')
    # compute rolling 7-day average
    who_covid_rolling = who_covid[who_var].rolling(window=7).mean()
    axis.plot(who_covid_rolling.index, who_covid_rolling,\
        lw=3,color=lighten_color(WHO_DATA_COLOR,1.6),label='WHO - 7d rolling average')
    # draw bucky
    draw_bucky_projections(bucky_npi,bucky_no_npi,bucky_var,axis)

    plt.legend(loc='upper right', prop={'size': 8})
    fig.savefig(f'Outputs/{country_iso3}/lifetime_{metric}.png')

def draw_bucky_projections(bucky_npi,bucky_no_npi,bucky_var,axis):
    """
    Draw historical and projection of the bucky_var, including the uncertainty intervals
    Args:
        bucky_npi: DataFrame with model projections given the current NPIs
        bucky_no_npi: DataFrame with model projections given the NPIs are lifted
        bucky_var: the column name to plot
        axis: the fig axis to plot them on
    """
    bucky_npi=bucky_npi[bucky_npi[bucky_var]>0]
    bucky_npi_median=bucky_npi[bucky_npi['quantile']==0.5][bucky_var]
    bucky_npi_median.plot(c=NPI_COLOR,ax=axis,label='Current NPIs maintained')
    axis.fill_between(bucky_npi_median.index,
                          bucky_npi[bucky_npi['quantile']==MIN_QUANTILE][bucky_var],
                          bucky_npi[bucky_npi['quantile']==MAX_QUANTILE][bucky_var],
                          color=NPI_COLOR,alpha=0.2
                          )
    # draw line NO NPI
    bucky_no_npi=bucky_no_npi[bucky_no_npi[bucky_var]>0]
    bucky_no_npi_median=bucky_no_npi[bucky_no_npi['quantile']==0.5][bucky_var]
    bucky_no_npi_median.plot(c=NO_NPI_COLOR,ax=axis,label='No NPIs in place'.format())
    axis.fill_between(bucky_no_npi_median.index,
                          bucky_no_npi[bucky_no_npi['quantile']==MIN_QUANTILE][bucky_var],
                          bucky_no_npi[bucky_no_npi['quantile']==MAX_QUANTILE][bucky_var],
                          color=NO_NPI_COLOR,alpha=0.2
                          )

def calculate_subnational_incidence(country_iso3, parameters, date):
    """
    Compute the reported and total estimated daily NEW cases per 100k on DATE and display these per admin1 and national average
    Args:
        country_iso3: iso3 code of the country of interest
        parameters: country specific parameters, retrieved from config
        date: date for which the metrics are computed
    """
    bucky_npi = get_bucky(country_iso3, admin_level='adm1', min_date=date, max_date=date, npi_filter='npi')
    bucky_npi = bucky_npi[bucky_npi['quantile'] == 0.5]
    adm1_pcode_prefix = parameters['iso2_code']
    if country_iso3 == 'IRQ':
        adm1_pcode_prefix = 'IQG'
    bucky_npi['adm1'] = adm1_pcode_prefix + bucky_npi['adm1'].apply(lambda x: '{0:0=2d}'.format(int(x)))
    #in the model output the daily_cases per admin1 is given. The N column gives the population per admin1 through which the cases/100k can be calculated
    bucky_npi['daily_reported_cases_per_100k'] = bucky_npi['daily_reported_cases'] /(bucky_npi['total_population']/100000)
    bucky_npi['daily_cases_total_per_100k'] = bucky_npi['daily_cases'] /(bucky_npi['total_population']/100000)
    print(f'Daily reported and estimated total cases per admin1 region on {date}')
    print(bucky_npi[['adm1','daily_reported_cases_per_100k','daily_cases_total_per_100k']])
    daily_rep_avg=bucky_npi['daily_reported_cases_per_100k'].mean()
    daily_tot_avg=bucky_npi['daily_cases_total_per_100k'].mean()
    print(f'Average over all admin regions of reported new daily cases per 100K: {daily_rep_avg:.2f}')
    print(f'Average over all admin regions of total estimated new daily cases per 100K: {daily_tot_avg:.2f}')

def create_subnational_map_incidence_100k(metric, country_iso3, parameters, date,fig_title,output_file):
    """
    Plot a map with the given metric per 100k per admin1 region.
    The bins and color scheme being used are according to the guidelines of the Harvard Global Health Institute, see https://globalhealth.harvard.edu/key-metrics-for-covid-suppression-researchers-and-public-health-experts-unite-to-bring-clarity-to-key-metrics-guiding-coronavirus-response/
    Args:
        metric: the name to plot the data for
        country_iso3: iso3 code of the country of interest
        parameters: country specific parameters, retrieved from config
        date: the date to plot the data for
        fig_title: the title of the plot
        output_file: the filename to save the figure to
    """
    bucky_npi = get_bucky(country_iso3, admin_level='adm1', min_date=date, max_date=date, npi_filter='npi')
    bucky_npi = bucky_npi[bucky_npi['quantile'] == 0.5]
    adm1_pcode_prefix = parameters['iso2_code']
    if country_iso3 == 'IRQ':
        adm1_pcode_prefix = 'IQG'
    bucky_npi['adm1'] = adm1_pcode_prefix + bucky_npi['adm1'].apply(lambda x: '{0:0=2d}'.format(int(x)))
    #calculate metrics per 100k that are not in the output of the model but can be given as in put 'metric'
    bucky_npi['daily_reported_cases_per_100k'] = bucky_npi['daily_reported_cases'] /(bucky_npi['total_population']/100000)
    bucky_npi['daily_cases_total_per_100k'] = bucky_npi['daily_cases'] /(bucky_npi['total_population']/100000)
    bucky_npi['hospitalizations_per_100k'] = bucky_npi['current_hospitalizations'] /(bucky_npi['total_population']/100000)

    shapefile = gpd.read_file(parameters['shape'])
    shapefile = shapefile.merge(bucky_npi, left_on=parameters['adm1_pcode'], right_on='adm1', how='left')

    fig, axis = create_new_subplot(fig_title)
    axis.axis('off')
    #bins according to recommendations from https://globalhealth.harvard.edu/key-metrics-for-covid-suppression-researchers-and-public-health-experts-unite-to-bring-clarity-to-key-metrics-guiding-coronavirus-response/
    bins_list=np.array([0,1,10,25,100000])
    cmap = matplotlib.colors.LinearSegmentedColormap.from_list('', ['#00a67e','#f8b931','#f88c29','#df431d'])
    # set bins
    norm2 = mcolors.BoundaryNorm(boundaries=bins_list, ncolors=256)
    # print(shapefile)
    shapefile.plot(column=metric, cmap=cmap, norm=norm2, ax=axis)
    #plot legend
    # cbar=fig.colorbar(axis.collections[0], cax=fig.add_axes([0.9, 0.2, 0.03, 0.60]))
    # cbar.ax.set_yticklabels(['0', '1', '10','25+',''])
    #plot boundaries of admin regions
    shapefile.boundary.plot(linewidth=0.1, ax=axis,color='lightgrey')
    fig.tight_layout()
    fig.set_size_inches(7,6)
    fig.savefig(f'Outputs/{country_iso3}/{output_file}')

def calculate_subnational_trends(country_iso3, parameters):
    """
    Compute the absolute and percentual change in ACTIVE cases/100k in TWO_WEEKS compared to TODAY
    Args:
        country_iso3: iso3 code of the country of interest
        parameters: country specific parameters, retrieved from config

    Returns:
        combined_change: DataFrame with the metrics related to the change in active cases/100k. Also includes the English admin1 names
    """
    bucky_npi = get_bucky(country_iso3 ,admin_level='adm1',min_date=TODAY,max_date=TWO_WEEKS,npi_filter='npi')
    bucky_npi = bucky_npi[bucky_npi['quantile']==0.5]
    adm1_pcode_prefix=parameters['iso2_code']
    if country_iso3 == 'IRQ':
        adm1_pcode_prefix='IQG'
    bucky_npi['adm1']=adm1_pcode_prefix + bucky_npi['adm1'].apply(lambda x:  '{0:0=2d}'.format(int(x)))
    bucky_npi['daily_reported_cases_per_100k'] = bucky_npi['daily_reported_cases'] / (bucky_npi['total_population'] / 100000)
    # bucky_npi['daily_cases_total_per_100k'] = bucky_npi['daily_cases'] / (bucky_npi['total_population'] / 100000)
    # make the col selector a list to ensure always a dataframe is returned (and not a series)
    start = bucky_npi.loc[[TODAY+timedelta(days=1)], :]
    end = bucky_npi.loc[[TWO_WEEKS], :]
    combined = start[['adm1','R_eff','daily_reported_cases_per_100k']].merge(end[['adm1', 'daily_reported_cases_per_100k']], how='outer', on='adm1',suffixes=('_today','_inTWOweeks'))

    combined['daily_reported_cases_per_100k_abs_change']=combined['daily_reported_cases_per_100k_inTWOweeks'] - combined['daily_reported_cases_per_100k_today']

    # Select the row if current OR projected have at least one active case
    # to remove noise
    #for now we decided to also include <1 active/new cases since it is a statistical model so non-integer cases are okay, plus you have the chance of then displaying the regions as if there is no change while there is
    #however this only works for absolute numbers and not for percentual because then it can get very skewed!
    # combined_cases=combined.loc[(combined['cases_active_today']>=1) | (combined['cases_active_inTWOweeks']>=1),:].copy()
    # combined_cases['cases_per_100k_perc_change'] = (combined_cases['cases_per_100k_inTWOweeks'] -combined_cases['cases_per_100k_today'])/ combined_cases['cases_per_100k_today'] * 100
    # combined_change=combined.merge(combined_cases[['adm1','cases_per_100k_perc_change']],on='adm1',how='left')

    shapefile = gpd.read_file(parameters['shape'],encoding='UTF-8')
    shapefile=shapefile[[parameters['adm1_pcode'],parameters['adm1_name']]]

    combined_shp=combined.merge(shapefile,how='left',left_on='adm1',right_on=parameters['adm1_pcode'])
    #inf values are given when cases_per100k TODAY was 0 and in two weeks this is larger than 0
    # combined_change=combined_change.replace(np.inf,np.nan)
    # combined_shp.loc[:,'cases_per_100k_perc_change']=combined_shp.loc[:,'cases_per_100k_perc_change'].astype('float')
    combined_shp = combined_shp.sort_values('adm1')
    # combined_shp = combined_shp.sort_values('daily_reported_cases_per_100k_abs_change', ascending=False)
    combined_shp.to_csv(f'Outputs/{country_iso3}/ADM1_ranking.csv', index=False)
    return combined_shp

#this map is currently not used and has to be revised given the changes in metrics we made (especially active vs new cases)
# def create_binary_change_map(country_iso3, parameters):
#     """
#     Generate a subnational map that indicates which areas are expected to have an increase and decrease in cases per 100k in two weeks
#     Args:
#         country_iso3: iso3 code of the country of interest
#         parameters: country specific parameters, retrieved from config
#     """
#     fig_title = f'Projected trend in number of cases per 100,000 people'
#     df_change=calculate_subnational_trends(country_iso3,parameters)
#
#     shapefile = gpd.read_file(parameters['shape'])
#     shapefile = shapefile.merge(df_change, left_on=parameters['adm1_pcode'], right_on='adm1', how='left')
#     #Classify as "increase" if cases per 100k is projected to increase by 5 or more percent in two weeks
#     #decrease if this is more than -5, else stable.
#     # Also stable for regions with less than 1 active cases (=nans from calculate_subnational_trends)
#     change_threshold=10
#     shapefile.loc[:,'change_name']=shapefile['cases_per_100k_abs_change'].apply(lambda x: f'Increase of {change_threshold}+' if x>=change_threshold else (f'Decrease of {change_threshold}+' if x<=-change_threshold else f'Less than {change_threshold} change'))
#     color_dict={f'Increase of {change_threshold}+' :'red',f'Less than {change_threshold} change':'grey',f'Decrease of {change_threshold}+':'green'}
#
#     fig, ax = plt.subplots(figsize=(10, 10))
#     for k in shapefile['change_name'].unique():
#         shapefile[shapefile['change_name']==k].plot(color=color_dict[k], ax=ax,edgecolor='gray')
#     legend_elements= [Line2D([0], [0], marker='o',markersize=15,label=k,color=color_dict[k],linestyle='None') for k in color_dict.keys()]
#     leg=plt.legend(title='Legend',frameon=False,handles=legend_elements,bbox_to_anchor=(1.5,0.8))
#     leg._legend_box.align = 'left'
#
#     shapefile.boundary.plot(linewidth=0.1,ax=ax,color='white')
#     ax.set_axis_off()
#     ax.set_title(fig_title)
#     fig.savefig(f'Outputs/{country_iso3}/map_binary_change_cases_per_100k_2w.png',bbox_inches="tight")


if __name__ == "__main__":
    args = parse_args()
    main(args.country_iso3.upper(),download_covid=args.download_covid)

# # this graph is currently not being used
# def generate_new_cases_graph(country_iso3):
#     # get all time cases and deaths
#     who_covid_new = get_who(WHO_COVID_FILENAME,country_iso3, min_date=pd.to_datetime('2000-01-01'),max_date=TODAY)
#     who_covid_new.reset_index(inplace=True)
#
#     # compute rolling 7-day average
#     who_covid_new['new_cases_rolling_mean'] = who_covid_new.NewCase.rolling(window=7).mean()
#
#     # Create figure and plot space
#     fig, ax = plt.subplots(figsize=(10, 10))
#
#     # Add x-axis and y-axis
#     ax.bar(who_covid_new['date_epicrv'],
#             who_covid_new['NewCase'],
#             color='cornflowerblue')
#
#     # format the ticks
#     months = mdates.MonthLocator()
#     months_fmt = mdates.DateFormatter('%m-%Y')
#
#     ax.xaxis.set_major_locator(months)
#     ax.xaxis.set_major_formatter(months_fmt)
#
#     # Set title and labels for axes
#     ax.set(xlabel='Date',
#         ylabel='New Cases',
#         title='Daily Cases')
#
#     # add rolling average trend line
#     plt.plot(who_covid_new['date_epicrv'], who_covid_new['new_cases_rolling_mean'], label='7-day average', color='navy')
#
#     # place a label near the trendline
#     ax.text(0.05, 0.13, 'Seven-day average', transform=ax.transAxes, fontsize=14,
#             verticalalignment='top', color='navy')
#
#     plt.show()
#     fig.savefig(f'Outputs/{country_iso3}/current_new_cases.png')
#
# # this graph is currently not being used
# def generate_new_deaths_graph(country_iso3):
#     # compute rolling 7-day average
#     who_covid_new['new_deaths_rolling_mean'] = who_covid_new.NewDeath.rolling(window=7).mean()
#
#     # Create figure and plot space
#     fig, ax = plt.subplots(figsize=(10, 10))
#
#     # Add x-axis and y-axis
#     ax.bar(who_covid_new['date_epicrv'],
#             who_covid_new['NewDeath'],
#             color='indianred')
#
#     # format the ticks
#     months = mdates.MonthLocator()
#     months_fmt = mdates.DateFormatter('%m-%Y')
#
#     ax.xaxis.set_major_locator(months)
#     ax.xaxis.set_major_formatter(months_fmt)
#
#     # Set title and labels for axes
#     ax.set(xlabel='Date',
#         ylabel='New Deaths',
#         title='Daily Deaths')
#
#     # add rolling average trend line
#     plt.plot(who_covid_new['date_epicrv'], who_covid_new['new_deaths_rolling_mean'], label='7-day average', color='darkred')
#
#     # place a label near the trendline
#     ax.text(0.05, 0.13, 'Seven-day average', transform=ax.transAxes, fontsize=14,
#             verticalalignment='top', color='darkred')
#
#     plt.show()
#     fig.savefig(f'Outputs/{country_iso3}/current_new_deaths.png')