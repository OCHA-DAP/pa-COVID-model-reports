import os
import geopandas as gpd
from datetime import datetime,timedelta
import sys
import matplotlib
import matplotlib.colors as mcolors
from matplotlib.lines import Line2D

import utils
from utils import *

country_iso_3 = sys.argv[1]

ASSESSMENT_DATE='2020-10-07'
TODAY = datetime.strptime(ASSESSMENT_DATE, '%Y-%m-%d').date()
FOUR_WEEKS = TODAY + timedelta(days=28)
TWO_WEEKS = TODAY + timedelta(days=14)
LAST_TWO_MONTHS = TODAY - timedelta(days=60)
EARLIEST_DATE = datetime.strptime('2020-02-24', '%Y-%m-%d').date()

MIN_QUANTILE=0.25
MAX_QUANTILE=0.75

CONFIG_FILE = 'config.yml'
DIR_PATH = os.path.dirname(os.path.realpath(__file__))
WHO_COVID_URL='https://covid19.who.int/WHO-COVID-19-global-data.csv'
WHO_COVID_FILENAME='WHO_data/WHO-COVID-19-global-data.csv'
RESULTS_FILENAME=f'automated_reports/report_metrics/{country_iso_3}_results.csv'
NPISHEET_PATH=f"Outputs/{country_iso_3}/npis_googlesheet.csv"

NPI_COLOR='green'
NO_NPI_COLOR='red'
WHO_DATA_COLOR='dodgerblue'
SUBNATIONAL_DATA_COLOR='navy'

def main(country_iso3='AFG', download_covid=False):

    parameters = utils.parse_yaml(CONFIG_FILE)[country_iso3]
    if download_covid:
        # Download latest covid file tiles and read them in
        download_who_covid_data(WHO_COVID_URL,f'{DIR_PATH}/{WHO_COVID_FILENAME}')

    #function from utils to set plot parameters
    set_matlotlib(plt)

    print('\n\n\n')
    print(f'{country_iso3}')

    #retrieve file with previously computed metrics
    if os.path.exists(RESULTS_FILENAME):
        df_all=pd.read_csv(RESULTS_FILENAME)
        #remove the rows that have same assessment date as current run
        #-->make sure not duplicate results for the same date
        df_all=df_all[df_all["assessment_date"]!=str(TODAY)]
    else:
        df_all=pd.DataFrame()

    #compute metrics current date
    df_reff = extract_reff(country_iso3)
    df_keyfigures = generate_key_figures(country_iso3,parameters)
    df_hospitalizations = generate_model_projections(country_iso3, parameters)
    #create dataframe with metrics of current date
    results_df=pd.concat([df_reff,df_keyfigures,df_hospitalizations]).reset_index()
    results_df.columns=["metric_name","metric_value"]
    results_df['assessment_date'] = TODAY
    results_df['country'] = f'{country_iso_3}'
    #append metrics to file with metrics of all dates
    df_all = df_all.append(results_df)
    df_all.to_csv(RESULTS_FILENAME, index=False)

    #calculate trends (being saved to separate csv within function)
    calculate_subnational_trends(country_iso3, parameters)

    #currently not used in report so not added to results_df
    retrieve_current_npis(parameters["npis_url"],NPISHEET_PATH)

    #create graphs
    generate_data_model_comparison(country_iso3,parameters)
    generate_data_model_comparison_lifetime(country_iso3,parameters)
    create_subnational_map_metric_100k("cases_per_100k", country_iso3, parameters, TODAY, "Current Reported Daily New Cases Per 100,000 People",
                           "map_cases_per_100k_reported_current.png")
    create_subnational_map_metric_100k("cases_per_100k_total", country_iso3, parameters, TODAY, "Current Estimated Daily New Cases Per 100,000 People",
                           "map_cases_per_100k_total_current.png")
    create_subnational_map_metric_100k("cases_per_100k",country_iso3, parameters, TWO_WEEKS, "Projected Reported Daily New Cases Per 100,000 People",
                           "map_cases_per_100k_2w.png")
    create_subnational_map_metric_100k("hospitalizations_per_100k_active", country_iso3, parameters, TODAY, "Current Reported Hospitalizations Per 100,000 People",
                           "map_hospitalizations_per_100k_current.png")
    create_binary_change_map(country_iso3, parameters)


def retrieve_current_npis(npis_url,output_path):
    download_url(npis_url, output_path)
    df_npis_sheet = pd.read_csv(output_path)
    df_npis_model = df_npis_sheet[df_npis_sheet["final_input"] == "Yes"]
    print("Currently in place NPIs")
    print(df_npis_model[["acaps_category", "acaps_measure", "bucky_measure", "affected_pcodes", "compliance_level", "start_date","end_date"]])

def extract_reff(country_iso3):
    bucky_npi=get_bucky(country_iso3,admin_level='adm0',min_date=TODAY,max_date=FOUR_WEEKS,npi_filter='npi')
    bucky_npi=bucky_npi[bucky_npi['q']==0.5]
    dt_npi,r_npi=get_bucky_dt_reff(bucky_npi)
    print(f'Estimated doubling time NPI {dt_npi}, Reff {r_npi}')
    
    bucky_no_npi=get_bucky(country_iso3,admin_level='adm0',min_date=TODAY,max_date=FOUR_WEEKS,npi_filter='no_npi')
    bucky_no_npi=bucky_no_npi[bucky_no_npi['q']==0.5]
    dt_no_npi,r_no_npi=get_bucky_dt_reff(bucky_no_npi)
    print(f'Estimated doubling time No NPI {dt_no_npi}, Reff {r_no_npi}')

    #create dict with all metrics
    dict_metrics={"Estimated doubling time NPI":dt_npi,"NPI Reff":r_npi,"Estimated doubling time No NPI":dt_no_npi,"No NPI Reff":r_no_npi}
    #convert dict to dataframe
    return pd.DataFrame.from_dict(dict_metrics,orient="index")

def generate_key_figures(country_iso3,parameters):

    who_covid=get_who(WHO_COVID_FILENAME,parameters['iso2_code'],min_date=LAST_TWO_MONTHS,max_date=TODAY)
    who_covid.index = pd.to_datetime(who_covid.index)
    who_deaths_today=who_covid.loc[TODAY,'Cumulative_deaths']
    who_cases_today=who_covid.loc[TODAY,'Cumulative_cases']    
    #CFR= Case Fatality Rate
    CFR=who_deaths_today/who_cases_today*100
    #calculate the trend of the cases and deaths of last week compared to the previous week
    #a week is defined being from Mon-Sun and thus last week is the last complete week
    #this is done to avoid biases due to delays in reporting.
    #some countries report cases only after a few days (and not reporting over the weekend).
    # resample('W') is from Mon-Sun
    who_covid.groupby(['Country_code']).resample('W')
    # get the sum of weekly new cases
    new_WHO_w=who_covid.groupby(['Country_code']).resample('W').sum()[['New_cases','New_deaths']]
    # ndays_w is the number of days present of each week in the data
    # this is max 7, first and last week can contain less days
    ndays_w=who_covid.groupby(['Country_code']).resample('W').count()['New_cases']
    new_WHO_w["ndays"] = ndays_w
    # select only the weeks of which all days are present
    new_WHO_w=new_WHO_w[new_WHO_w['ndays']==7]
    # get percentual change of cases and deaths compared to previous week
    # percentual change=((cases week n)-(cases week n-1))/(cases week n-1)
    new_WHO_w['New_cases_PercentChange'] = new_WHO_w.groupby('Country_code')['New_cases'].pct_change()
    new_WHO_w['New_deaths_PercentChange'] = new_WHO_w.groupby('Country_code')['New_deaths'].pct_change()
    # get percentual change of last full week (Mon-Sun)
    trend_w_cases=new_WHO_w.loc[new_WHO_w.index[-1],'New_cases_PercentChange']*100
    trend_w_deaths=new_WHO_w.loc[new_WHO_w.index[-1],'New_deaths_PercentChange']*100
    print(f'Current situation {TODAY}: {who_cases_today:.0f} cases, {who_deaths_today:.0f} deaths')
    print(f'CFR {TODAY}: {CFR:.1f}')
    print(f'Percentual change in new cases and deaths during last week (Mon-Sun) wrt previous week: {trend_w_cases:.0f}% cases, {trend_w_deaths:.0f}% deaths')

    bucky_npi=get_bucky(country_iso3,admin_level='adm0',min_date=TODAY,max_date=FOUR_WEEKS,npi_filter='npi')
    reporting_rate=bucky_npi['CASE_REPORT'].mean()*100

    #model (i.e. bucky) outputs are not always round numbers.
    # Therefore convert them to ints, such that trends are computed based on ints and thus numbers in report correspond
    min_cases_npi=bucky_npi[bucky_npi['q']==MIN_QUANTILE].loc[FOUR_WEEKS,'cumulative_cases_reported'].astype(int)
    max_cases_npi=bucky_npi[bucky_npi['q']==MAX_QUANTILE].loc[FOUR_WEEKS,'cumulative_cases_reported'].astype(int)
    min_deaths_npi=bucky_npi[bucky_npi['q']==MIN_QUANTILE].loc[FOUR_WEEKS,'cumulative_deaths'].astype(int)
    max_deaths_npi=bucky_npi[bucky_npi['q']==MAX_QUANTILE].loc[FOUR_WEEKS,'cumulative_deaths'].astype(int)
    bucky_npi_cases_today=bucky_npi[bucky_npi['q']==0.5].loc[TODAY,'cumulative_cases_reported'].astype(int)
    bucky_npi_cases_today_notrep=bucky_npi[bucky_npi['q']==0.5].loc[TODAY,'cumulative_cases'].astype(int)
    bucky_npi_deaths_today=bucky_npi[bucky_npi['q']==0.5].loc[TODAY,'cumulative_deaths'].astype(int)
    print(f'Current situation WHO {TODAY}: {who_cases_today:.0f} cases (cumulative), {who_deaths_today:.0f} deaths (cumulative)')

    print(f'Current situation Bucky {TODAY}: {bucky_npi_cases_today:.0f} cases reported (cumulative), {bucky_npi_deaths_today:.0f} deaths (cumulative)')
    print(f'Current situation Bucky {TODAY}: {bucky_npi_cases_today_notrep:.0f} cases (cumulative)')
    subnational_covid=get_subnational_covid_data(parameters,aggregate=True,min_date=LAST_TWO_MONTHS,max_date=FOUR_WEEKS)
    subnational_covid.sort_index(inplace=True)
    #want to only retrieve the data up to TODAY, in case analysis is re-run after TODAY and thus might include data in the "future"
    subnational_covid_maxtoday=subnational_covid[subnational_covid.index.date <= TODAY]
    subnational_lastdate=subnational_covid_maxtoday.iloc[-1].name.strftime("%Y-%m-%d")
    subnational_cases_latest=subnational_covid_maxtoday.iloc[-1][HLX_TAG_TOTAL_CASES].astype(int)
    subnational_deaths_latest=subnational_covid_maxtoday.iloc[-1][HLX_TAG_TOTAL_DEATHS].astype(int)
    print(f"Latest number of cases reported by MPHO (subnational) was on {subnational_lastdate} and equalled {subnational_cases_latest} cases (cumulative)")
    print(f"Latest number of deaths reported by MPHO (subnational) was on {subnational_lastdate} and equalled {subnational_deaths_latest} cases (cumulative)")

    #this are the expected percentual change in CUMULATIVE cases/deaths
    rel_inc_min_cases_npi=(min_cases_npi-bucky_npi_cases_today)/bucky_npi_cases_today*100
    rel_inc_max_cases_npi=(max_cases_npi-bucky_npi_cases_today)/bucky_npi_cases_today*100
    rel_inc_min_deaths_npi=(min_deaths_npi-bucky_npi_deaths_today)/bucky_npi_deaths_today*100
    rel_inc_max_deaths_npi=(max_deaths_npi-bucky_npi_deaths_today)/bucky_npi_deaths_today*100
    print(f'- Projection date:{FOUR_WEEKS}')
    print(f'- ESTIMATED CASE REPORTING RATE {reporting_rate:.0f}')
    print(f'-- NPI: Projected reported cases in 4w: {min_cases_npi:.0f} - {max_cases_npi:.0f}')
    print(f'-- NPI: Projected trend reported cases in 4w: {rel_inc_min_cases_npi:.0f}% - {rel_inc_max_cases_npi:.0f}%')
    print(f'-- NPI: Projected reported deaths in 4w: {min_deaths_npi:.0f} - {max_deaths_npi:.0f}')
    print(f'-- NPI: Projected trend reported deaths in 4w: {rel_inc_min_deaths_npi:.0f}% - {rel_inc_max_deaths_npi:.0f}%')
    
    bucky_no_npi=get_bucky(country_iso3,admin_level='adm0',min_date=TODAY,max_date=FOUR_WEEKS,npi_filter='no_npi')
    min_cases_no_npi=bucky_no_npi[bucky_no_npi['q']==MIN_QUANTILE].loc[FOUR_WEEKS,'cumulative_cases_reported'].astype(int)
    max_cases_no_npi=bucky_no_npi[bucky_no_npi['q']==MAX_QUANTILE].loc[FOUR_WEEKS,'cumulative_cases_reported'].astype(int)
    min_deaths_no_npi=bucky_no_npi[bucky_no_npi['q']==MIN_QUANTILE].loc[FOUR_WEEKS,'cumulative_deaths'].astype(int)
    max_deaths_no_npi=bucky_no_npi[bucky_no_npi['q']==MAX_QUANTILE].loc[FOUR_WEEKS,'cumulative_deaths'].astype(int)
    print(f'--- no_npi: Projected reported cases in 4w: {min_cases_no_npi:.0f} - {max_cases_no_npi:.0f}')
    print(f'--- no_npi: Projected reported deaths in 4w: {min_deaths_no_npi:.0f} - {max_deaths_no_npi:.0f}')

    no_npi_max_increase_cases=(max_cases_no_npi-min_cases_npi).astype(int)
    no_npi_max_increase_deaths = (max_deaths_no_npi - min_deaths_npi).astype(int)
    print(f'Maximum number of extra cases if NPIs are lifted: {no_npi_max_increase_cases:.0f}')
    print(f'Maximum number of extra deaths if NPIs are lifted: {no_npi_max_increase_deaths:.0f}')
    dict_metrics={"Current situation - WHO cases today": who_cases_today,"Current situation - WHO deaths today": who_deaths_today,
                    "CFR":CFR,
                    "Weekly new cases wrt last week - trend":trend_w_cases,
                    "Weekly new deaths wrt last week - trend":trend_w_deaths,
                    "Estimated case reporting rate": reporting_rate,
                    "NPI - projected reported cases in 4w - MIN": min_cases_npi,
                    "NPI - projected reported cases in 4w - MAX": max_cases_npi,
                    "NPI - projected TREND reported cases in 4w - MIN": rel_inc_min_cases_npi,
                    "NPI - projected TREND reported cases in 4w - MAX": rel_inc_max_cases_npi,
                    "NPI - projected reported deaths in 4w - MIN": min_deaths_npi,
                    "NPI - projected reported deaths in 4w - MAX": max_deaths_npi,
                    "NPI - projected TREND reported deaths in 4w - MIN": rel_inc_min_deaths_npi,
                    "NPI - projected TREND reported deaths in 4w - MAX": rel_inc_max_deaths_npi,
                    "NO NPI - projected reported cases in 4w - MIN": min_cases_no_npi,
                    "NO NPI - projected reported cases in 4w - MAX": max_cases_no_npi,
                    "NO NPI - projected reported deaths in 4w - MIN": min_deaths_no_npi,
                    "NO NPI - projected reported deaths in 4w - MAX": max_deaths_no_npi,
                    "Maximum number of extra cases if NPIs are lifted": no_npi_max_increase_cases,
                    "Maximum number of extra deaths if NPIs are lifted": no_npi_max_increase_deaths,
                    "Current situation - latest date MPHO reported numbers": subnational_lastdate,
                    "Current situation - latest MPHO cases": subnational_cases_latest,
                    "Current situation - latest MPHO deaths": subnational_deaths_latest,
                }

    return pd.DataFrame.from_dict(dict_metrics,orient="index")

def generate_model_projections(country_iso3,parameters):
    # generate plot with long term projections of daily cases
    bucky_npi=get_bucky(country_iso3,admin_level='adm0',min_date=TODAY,max_date=FOUR_WEEKS,npi_filter='npi')
    bucky_no_npi=get_bucky(country_iso3,admin_level='adm0',min_date=TODAY,max_date=FOUR_WEEKS,npi_filter='no_npi')
    metric, metric_today_min, metric_today_max, metric_4w_npi_min, metric_4w_npi_max, metric_4w_no_npi_min, metric_4w_no_npi_max = draw_model_projections(country_iso3,bucky_npi,bucky_no_npi,parameters,'hospitalizations')

    dict_metric={f"{metric.capitalize()} current situation - MIN": metric_today_min,
    f"{metric.capitalize()} current situation - MAX":metric_today_max,
    f"NPI {metric.capitalize()} projections 4w - MIN": metric_4w_npi_min,
    f"NPI {metric.capitalize()} projections 4w - MAX": metric_4w_npi_max,
    f"NO NPI {metric.capitalize()} projections 4w - MIN": metric_4w_no_npi_min,
    f"NO NPI {metric.capitalize()} projections 4w - MAX": metric_4w_no_npi_max}

    return pd.DataFrame.from_dict(dict_metric,orient="index")

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
    #bucky_no_npi and bucky_npi are initialized with the same numbers, so doesn't matter which is being used for displaying the current situation
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

    who_mindate=who_covid[who_covid[who_var]>0].index.min()
    subnational_mindate=subnational_covid[subnational_covid[subnational_var]>0].index.min()
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

def create_subnational_map_metric_100k(metric, country_iso3, parameters, date,fig_title,output_file):
    bucky_npi = get_bucky(country_iso3, admin_level='adm1', min_date=LAST_TWO_MONTHS, max_date=date, npi_filter='npi')

    bucky_npi = bucky_npi[bucky_npi['q'] == 0.5]
    adm1_pcode_prefix = parameters['iso2_code']
    if country_iso3 == 'IRQ':
        adm1_pcode_prefix = 'IQG'
    bucky_npi['adm1'] = adm1_pcode_prefix + bucky_npi['adm1'].apply(lambda x: "{0:0=2d}".format(int(x)))
    bucky_npi["cases_per_100k"] = bucky_npi["cases_per_100k"].astype(int)
    if metric=="cases_per_100k_total":
        reporting_rate = bucky_npi['CASE_REPORT'].mean() * 100
        bucky_npi["cases_per_100k_total"]=bucky_npi["cases_per_100k"]*reporting_rate
    if metric=="hospitalizations_per_100k_active":
        bucky_npi["hospitalizations_per_100k_active"] = bucky_npi["hospitalizations"] /(bucky_npi["N"]/100000)

    bucky_npi = bucky_npi.loc[date, ["adm1",metric]]
    shapefile = gpd.read_file(parameters['shape'])
    shapefile = shapefile.merge(bucky_npi, left_on=parameters['adm1_pcode'], right_on='adm1', how='left')

    fig, axis = create_new_subplot(fig_title)
    axis.axis('off')
    #bins according to recommendations from https://globalhealth.harvard.edu/key-metrics-for-covid-suppression-researchers-and-public-health-experts-unite-to-bring-clarity-to-key-metrics-guiding-coronavirus-response/
    bins_list=np.array([0,1,10,25,100000])
    cmap = matplotlib.colors.LinearSegmentedColormap.from_list("", ["#00a67e","#f8b931","#f88c29","#df431d"])
    # set bins
    norm2 = mcolors.BoundaryNorm(boundaries=bins_list, ncolors=256)
    shapefile.plot(column=metric, cmap=cmap, norm=norm2, ax=axis)
    #plot legend
    # cbar=fig.colorbar(axis.collections[0], cax=fig.add_axes([0.9, 0.2, 0.03, 0.60]))
    # cbar.ax.set_yticklabels(["0", "1", "10","25+",""])
    #plot boundaries of admin regions
    shapefile.boundary.plot(linewidth=0.1, ax=axis,color="lightgrey")
    fig.savefig(f'Outputs/{country_iso3}/{output_file}',bbox_inches="tight")

def create_binary_change_map(country_iso3, parameters):
    """
    Generate a subnational map that indicates which areas are expected to have an increase and decrease in cases per 100k in two weeks
    """
    fig_title = f'Projected trend in number of cases per 100,000 people'
    df_change=calculate_subnational_trends(country_iso3,parameters)

    shapefile = gpd.read_file(parameters['shape'])
    shapefile = shapefile.merge(df_change, left_on=parameters['adm1_pcode'], right_on='adm1', how='left')
    #Classify as "increase" if cases per 100k is projected to increase by 5 or more percent in two weeks
    #decrease if this is more than -5, else stable.
    # Also stable for regions with less than 1 active cases (=nans from calculate_subnational_trends)
    change_threshold=10
    shapefile.loc[:,"change_name"]=shapefile["cases_per_100k_abs_change"].apply(lambda x: f"Increase of {change_threshold}+" if x>=change_threshold else (f"Decrease of {change_threshold}+" if x<=-change_threshold else f"Less than {change_threshold} change"))
    color_dict={f"Increase of {change_threshold}+" :"red",f"Less than {change_threshold} change":"grey",f"Decrease of {change_threshold}+":"green"}

    fig, ax = plt.subplots(figsize=(10, 10))
    for k in shapefile["change_name"].unique():
        shapefile[shapefile["change_name"]==k].plot(color=color_dict[k], ax=ax,edgecolor='gray')
    legend_elements= [Line2D([0], [0], marker='o',markersize=15,label=k,color=color_dict[k],linestyle='None') for k in color_dict.keys()]
    leg=plt.legend(title="Legend",frameon=False,handles=legend_elements,bbox_to_anchor=(1.5,0.8))
    leg._legend_box.align = "left"

    shapefile.boundary.plot(linewidth=0.1,ax=ax,color="white")
    ax.set_axis_off()
    ax.set_title(fig_title)
    fig.savefig(f'Outputs/{country_iso3}/map_binary_change_cases_per_100k_2w.png',bbox_inches="tight")


def calculate_subnational_trends(country_iso3, parameters):
    bucky_npi =  get_bucky(country_iso3 ,admin_level='adm1',min_date=TODAY,max_date=TWO_WEEKS,npi_filter='npi')
    bucky_npi = bucky_npi.loc[bucky_npi['q']==0.5,['adm1','Reff','cases_per_100k',"cases_active"]]
    adm1_pcode_prefix=parameters['iso2_code']
    if country_iso3 == 'IRQ':
        adm1_pcode_prefix='IQG'
    bucky_npi['adm1']=adm1_pcode_prefix + bucky_npi['adm1'].apply(lambda x:  "{0:0=2d}".format(int(x)))
    
    # make the col selector a list to ensure always a dataframe is returned (and not a series)
    start = bucky_npi.loc[[TODAY], :]
    end = bucky_npi.loc[[TWO_WEEKS], :]
    combined = start.merge(end[['adm1', 'cases_per_100k',"cases_active"]], how='outer', on='adm1',suffixes=("_today","_inTWOweeks"))

    combined["cases_per_100k_abs_change"]=combined['cases_per_100k_inTWOweeks'] - combined['cases_per_100k_today']
    
    # Select the row if current OR projected have at least one active case
    # to remove noise
    combined_cases=combined.loc[(combined['cases_active_today']>=1) | (combined['cases_active_inTWOweeks']>=1),:].copy()
    combined_cases['cases_per_100k_perc_change'] = (combined_cases['cases_per_100k_inTWOweeks'] -combined_cases['cases_per_100k_today'])/ combined_cases['cases_per_100k_today'] * 100
    combined_change=combined.merge(combined_cases[["adm1","cases_per_100k_perc_change"]],on="adm1",how="left")

    shapefile = gpd.read_file(parameters['shape'])
    shapefile=shapefile[[parameters['adm1_pcode'],parameters['adm1_name']]]
    
    combined_change=combined_change.merge(shapefile,how='left',left_on='adm1',right_on=parameters['adm1_pcode'])
    #inf values are given when cases_per100k TODAY was 0 and in two weeks this is larger than 0
    # combined_change=combined_change.replace(np.inf,np.nan)
    combined_change.loc[:,'cases_per_100k_perc_change']=combined_change.loc[:,'cases_per_100k_perc_change'].astype('float')
    combined_change = combined_change.sort_values('cases_per_100k_perc_change', ascending=False)
    combined_change.to_csv(f'Outputs/{country_iso3}/ADM1_ranking.csv', index=False)
    return combined_change





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