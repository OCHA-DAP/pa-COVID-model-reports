# global level functions
import yaml
import requests
import pandas as pd
import matplotlib.pyplot as plt
import argparse
import matplotlib.dates as mdates
from scipy.optimize import curve_fit
import numpy as np
import matplotlib.colors as mc
import colorsys
import logging
import coloredlogs
from datetime import timedelta

logger = logging.getLogger(__name__)


FIG_SIZE=(8,6)

HLX_TAG_TOTAL_CASES = "#affected+infected+confirmed+total"
HLX_TAG_TOTAL_DEATHS = "#affected+infected+dead+total"
HLX_TAG_DATE = "#date"
HLX_TAG_ADM2_PCODE='#adm2+pcode'

def config_logger(level='INFO'):
    #set styling of logger
    # Colours selected from here:
    # http://humanfriendly.readthedocs.io/en/latest/_images/ansi-demo.png
    coloredlogs.install(
        level=level,
        fmt="%(asctime)s %(name)s %(levelname)s %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        field_styles={
            'name': {'color': 8 },
            'asctime': {'color': 248},
            'levelname': {'color': 8, 'bold': True},
        },
    )

def set_matlotlib(plt):

    plt.rcParams['axes.grid'] = True    
    plt.rcParams['grid.color'] = 'lightgrey'
    plt.rcParams['grid.linestyle'] = 'solid'
    plt.rcParams['grid.linewidth'] = 0.5
    plt.rcParams.update({'font.size': 15})

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("country_iso3", help="Country ISO3")
    parser.add_argument('-d', '--download-covid', action='store_true',
                        help='Download the COVID-19 data')
    return parser.parse_args()

def parse_yaml(filename):
    with open(filename, "r") as stream:
        config = yaml.safe_load(stream)
    return config

def download_url(url, save_path, chunk_size=128):
    r = requests.get(url, stream=True)
    with open(save_path, 'wb') as fd:
        for chunk in r.iter_content(chunk_size=chunk_size):
            fd.write(chunk)
    print(f'Downloaded "{url}" to "{save_path}"')

def download_who_covid_data(url, save_path):
    # download covid data from HDX
    print(f'Getting upadated COVID data from WHO')
    try:
        download_url(url, save_path)

    except Exception:
        print(f'Cannot download COVID file from from HDX')


def quality_check_negative(df, data_name):
    negative_values=False
    df_numeric_columns = list(df.select_dtypes(include=[np.number]).columns.values)
    for c in df_numeric_columns:
        try:
            assert all(i >= 0 for i in df[c])
        except AssertionError:
            neg_dates = df[df[c] < 0].index.unique()
            neg_dates_str=",".join([n.strftime("%d-%m-%Y") for n in neg_dates])
            logger.warning(f'{data_name}: Negative value in column {c} on {neg_dates_str}')
            negative_values= True
    return negative_values


def quality_check_missing_dates(df,data_name,today,window=14):
    df_window=df.loc[today-timedelta(days=window):today,:]
    dates_window=list(df_window.index.values)
    dates_total=list(df.index.values)
    try:
        assert not len(dates_total)<window
    except AssertionError:
        logger.warning(f'{data_name} less than {window} data points')
    try:
        assert not len(dates_window)==0
    except AssertionError:
        logger.warning(f'{data_name} no values in last {window} days')

def quality_check_nondecreasing(df,data_name):
    decreasing_values=False
    df_numeric_columns = list(df.select_dtypes(include=[np.number]).columns.values)
    for c in df_numeric_columns:
        try:
            assert all(x <= y for x, y in zip(df[c], df[c][1:]))
        except AssertionError:
            df_copy=df.copy()
            df_copy["prev_val"]=df_copy[c].shift(1)
            neg_dates = df_copy[df_copy[c] < df_copy["prev_val"]].index.unique()
            neg_dates_str = ",".join([n.strftime("%d-%m-%Y") for n in neg_dates])
            logger.warning(f'{data_name}: Decreasing value in column {c} on {neg_dates_str}')
            decreasing_values = True
    return decreasing_values

def quality_check_allsources(country_iso3,parameters,who_filename,min_date,max_date,today):
    # Explanation for negative numbers from WHO data documentation (found on https://data.humdata.org/dataset/coronavirus-covid-19-cases-and-deaths)
    # Due to the recent trend of countries conducting data reconciliation exercises which remove large numbers of cases or deaths from their total counts,
    # such data may reflect as negative numbers in the new cases / new deaths counts as appropriate.
    # This will aid users in identifying when such adjustments occur.
    # When additional details become available that allow the subtractions to be suitably apportioned to previous days, data will be updated accordingly.
    who_covid=get_who(who_filename,parameters["iso2_code"],min_date,max_date)
    quality_check_negative(who_covid, "WHO")
    quality_check_nondecreasing(who_covid[["Cumulative_cases","Cumulative_deaths"]], "WHO")
    quality_check_missing_dates(who_covid,"WHO",today)
    subnational_covid=get_subnational_covid_data(parameters,aggregate=True,min_date=min_date,max_date=max_date)
    subnational_covid.index=subnational_covid.index.date
    quality_check_negative(subnational_covid, "subnational")
    quality_check_nondecreasing(subnational_covid[[HLX_TAG_TOTAL_CASES,HLX_TAG_TOTAL_DEATHS]],"subnational")
    quality_check_missing_dates(subnational_covid,"subnational",today)
    # Bucky negative values mainly occur for first date due to initalization of model
    bucky_npi_adm0=get_bucky(country_iso3,admin_level='adm0', min_date=min_date, max_date=max_date, npi_filter='npi')#.reset_index(inplace=True)
    quality_check_negative(bucky_npi_adm0,"Bucky NPI Adm0")
    quality_check_nondecreasing(bucky_npi_adm0.loc[bucky_npi_adm0["q"]==0.5,["cumulative_cases","cumulative_cases_reported","cumulative_deaths"]],"Bucky NPI Adm0")
    bucky_no_npi_adm0=get_bucky(country_iso3,admin_level='adm0', min_date=min_date, max_date=max_date, npi_filter='no_npi')
    quality_check_negative(bucky_no_npi_adm0, "Bucky NO NPI Adm0")
    quality_check_nondecreasing(bucky_no_npi_adm0.loc[bucky_npi_adm0["q"]==0.5,["cumulative_cases","cumulative_cases_reported","cumulative_deaths"]],"Bucky NO NPI Adm0")
    #don't do quality check nondecreasing for adm1 level because you would have to do this for every admin separately
    bucky_npi_adm1=get_bucky(country_iso3,admin_level='adm1', min_date=min_date, max_date=max_date, npi_filter='npi')
    quality_check_negative(bucky_npi_adm1, "Bucky NPI Adm1")
    bucky_no_npi_adm1=get_bucky(country_iso3,admin_level='adm1', min_date=min_date, max_date=max_date, npi_filter='no_npi')
    quality_check_negative(bucky_no_npi_adm1, "Bucky NO NPI Adm1")

def get_bucky(country_iso3,admin_level,min_date,max_date,npi_filter):
    bucky_df=pd.read_csv(f'Bucky_results/{country_iso3}_{npi_filter}/{admin_level}_quantiles.csv')
    bucky_df['date']=pd.to_datetime(bucky_df['date']).dt.date
    bucky_df=bucky_df[(bucky_df['date']>=min_date) &
                        (bucky_df['date']<=max_date)]
    bucky_df=bucky_df.set_index('date')
    return bucky_df
    
def get_who(filename,country_iso2,min_date,max_date):
    # Get national level data from WHO
    who_covid=pd.read_csv(filename)
    who_covid=who_covid.rename(columns=lambda x: x.strip())
    who_covid=who_covid[who_covid['Country_code']==country_iso2]
    who_covid['Date_reported']=pd.to_datetime(who_covid['Date_reported']).dt.date
    who_covid=who_covid[(who_covid['Date_reported']>=min_date) &\
                        (who_covid['Date_reported']<=max_date)]
    who_covid=who_covid.set_index('Date_reported')
    return who_covid


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

def lighten_color(color, amount=0.5):
    """
    Lightens the given color by multiplying (1-luminosity) by the given amount.
    Input can be matplotlib color string, hex string, or RGB tuple.
    
    Examples:
    >> lighten_color('g', 0.3)
    >> lighten_color('#F034A3', 0.6)
    >> lighten_color((.3,.55,.1), 0.5)
    """

    try:
        c = mc.cnames[color]
    except:
        c = color
    c = np.array(colorsys.rgb_to_hls(*mc.to_rgb(c)))
    return colorsys.hls_to_rgb(c[0],1-amount * (1-c[1]),c[2])