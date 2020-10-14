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

logger = logging.getLogger(__name__)


FIG_SIZE=(8,6)

HLX_TAG_TOTAL_CASES = "#affected+infected+confirmed+total"
HLX_TAG_TOTAL_DEATHS = "#affected+infected+dead+total"
HLX_TAG_DATE = "#date"
HLX_TAG_ADM2_PCODE='#adm2+pcode'

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
    df_numeric_columns = list(df.select_dtypes(include=[np.number]).columns.values)
    for c in df_numeric_columns:
        try:
            assert all(i >= 0 for i in df[c])
        except AssertionError:
            logger.error(f'{data_name}: Negative values in column {c}')
    # set negative numbers to 0
    # Explanation for negative numbers from WHO data documentation (found on https://data.humdata.org/dataset/coronavirus-covid-19-cases-and-deaths):
    # Bucky mainly occurs for first date due to initalization of model
    # df._get_numeric_data()[df._get_numeric_data() < 0] = 0

    return df

def get_bucky(country_iso3,admin_level,min_date,max_date,npi_filter):
    bucky_df=pd.read_csv(f'Bucky_results/{country_iso3}_{npi_filter}/{admin_level}_quantiles.csv')
    bucky_df['date']=pd.to_datetime(bucky_df['date']).dt.date
    bucky_df=bucky_df[(bucky_df['date']>=min_date) &
                        (bucky_df['date']<=max_date)]
    bucky_df=bucky_df.set_index('date')
    # quality_check_negative(bucky_df,"Bucky")
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

    who_covid=quality_check_negative(who_covid,"WHO")
    #TO DO: check if this is the best way to handle the negative numbers
    # set negative numbers to 0
    # Explanation for negative numbers from WHO data documentation (found on https://data.humdata.org/dataset/coronavirus-covid-19-cases-and-deaths):
    who_covid._get_numeric_data()[who_covid._get_numeric_data() < 0] = 0
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

    #TO DO: decide what to do with negative numbers
    subnational_covid=quality_check_negative(subnational_covid,"subnational")
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