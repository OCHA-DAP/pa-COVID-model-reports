import utils
import os
import argparse
import pandas as pd
import matplotlib.pyplot as plt
import requests
from datetime import timedelta, date

CONFIG_FILE = 'config.yml'
DIR_PATH = os.path.dirname(os.path.realpath(__file__))
WHO_COVID_URL='https://docs.google.com/spreadsheets/d/e/2PACX-1vSe-8lf6l_ShJHvd126J-jGti992SUbNLu-kmJfx1IRkvma_r4DHi0bwEW89opArs8ZkSY5G2-Bc1yT/pub?gid=0&single=true&output=csv'
WHO_COVID_FILENAME=WHO_COVID_FILENAME='WHO_data/Data_ WHO Coronavirus Covid-19 Cases and Deaths - WHO-COVID-19-global-data.csv'


HLX_TAG_TOTAL_CASES = "#affected+infected+confirmed+total"
HLX_TAG_TOTAL_DEATHS = "#affected+infected+dead+total"
HLX_TAG_DATE = "#date"

FIG_SIZE=(8,8)

TODAY = date.today()
FOUR_WEEKS = TODAY + timedelta(days=28)
LAST_MONTH = TODAY - timedelta(days=30)

NPI_COLOR='g'
NO_NPI_COLOR='orange'

def main(country_iso3='AFG',download_covid=False):
    parameters = utils.parse_yaml(CONFIG_FILE)[country_iso3]
    if download_covid:
    # Download latest covid file tiles and read them in
        get_covid_data(WHO_COVID_URL,f'{DIR_PATH}/{WHO_COVID_FILENAME}')
    
    generate_current_status(country_iso3,parameters)
    plt.show()
 
    # print(parameters)

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

def generate_current_status(country_iso3,parameters):
    # get subnational from COVID parameterization repo
    subnational_covid=pd.read_csv(parameters['subnational_cases_url'])
    subnational_covid[HLX_TAG_DATE]=pd.to_datetime(subnational_covid[HLX_TAG_DATE]).dt.date
    subnational_covid=subnational_covid[(subnational_covid[HLX_TAG_DATE]>=LAST_MONTH) &\
                                        (subnational_covid[HLX_TAG_DATE]<=TODAY)]
    subnational_covid=subnational_covid.groupby(HLX_TAG_DATE).sum()

    # Get national level data from WHO
    who_covid=pd.read_csv(WHO_COVID_FILENAME)
    who_covid=who_covid[who_covid['ISO_3_CODE']==country_iso3]
    who_covid['date_epicrv']=pd.to_datetime(who_covid['date_epicrv']).dt.date
    who_covid=who_covid[(who_covid['date_epicrv']>=LAST_MONTH) &\
                        (who_covid['date_epicrv']<=TODAY)]
    who_covid=who_covid.set_index('date_epicrv')
    
    # get bucky with NPIs 
    bucky_npi=pd.read_csv(f'Bucky_results/{country_iso3}_npi/adm0_quantiles.csv')
    bucky_npi['date']=pd.to_datetime(bucky_npi['date']).dt.date
    bucky_npi=bucky_npi[(bucky_npi['date']>=LAST_MONTH) &\
                        (bucky_npi['date']<=FOUR_WEEKS)]
    bucky_npi=bucky_npi.set_index('date')
    
    # get bucky without NPIs 
    bucky_no_npi=pd.read_csv(f'Bucky_results/{country_iso3}_no_npi/adm0_quantiles.csv')
    bucky_no_npi['date']=pd.to_datetime(bucky_no_npi['date']).dt.date
    bucky_no_npi=bucky_no_npi[(bucky_no_npi['date']>=LAST_MONTH) &\
                        (bucky_no_npi['date']<=FOUR_WEEKS)]
    bucky_no_npi=bucky_no_npi.set_index('date')
    
    draw_current_status(country_iso3,subnational_covid,who_covid,bucky_npi,bucky_no_npi,parameters,'reported_cases')
    draw_current_status(country_iso3,subnational_covid,who_covid,bucky_npi,bucky_no_npi,parameters,'deaths')

def draw_current_status(country_iso3,subnational_covid,who_covid,bucky_npi,bucky_no_npi,parameters,metric):
    if metric=='reported_cases':
        who_var='CumCase'
        bucky_var='cumulative_cases_reported'
        subnational_var=HLX_TAG_TOTAL_CASES
        subnational_source=parameters['subnational_cases_source']
        fig_title='Cumulative reported cases'
    elif metric=='deaths':
        who_var='CumDeath'
        bucky_var='cumulative_deaths'
        subnational_var=HLX_TAG_TOTAL_DEATHS
        subnational_source=parameters['subnational_cases_source']
        fig_title='Cumulative reported deaths'
    else:
        print(f'metric {metric} not implemented')
        

    fig,axis=plt.subplots(figsize=(FIG_SIZE[0],FIG_SIZE[1]))
    axis.set_title(fig_title)
    # draw subnational reported cumulative cases
    axis.scatter(who_covid.index, who_covid[who_var],\
                     alpha=0.8, s=20,c='red',marker='*',label='WHO')
    axis.scatter(subnational_covid.index, subnational_covid[subnational_var],\
                     alpha=0.8, s=20,c='blue',marker='o',label=subnational_source)
    # draw line NPI
    bucky_npi_median=bucky_npi[bucky_npi['q']==0.5][bucky_var]
    bucky_npi_median.plot(c=NPI_COLOR,ax=axis,label='Keeping current NPIs')
    axis.fill_between(bucky_npi_median.index,\
                          bucky_npi[bucky_npi['q']==0.25][bucky_var],
                          bucky_npi[bucky_npi['q']==0.75][bucky_var],
                          color=NPI_COLOR,alpha=0.2
                          )
    # draw line NO NPI
    bucky_no_npi_cases_median=bucky_no_npi[bucky_no_npi['q']==0.5][bucky_var]
    bucky_no_npi_cases_median.plot(c=NO_NPI_COLOR,ax=axis,label='Back to normal')
    axis.fill_between(bucky_no_npi_cases_median.index,\
                          bucky_no_npi[bucky_no_npi['q']==0.25][bucky_var],
                          bucky_no_npi[bucky_no_npi['q']==0.75][bucky_var],
                          color=NO_NPI_COLOR,alpha=0.2
                          )
    plt.legend()
    fig.savefig(f'Outputs/{country_iso3}/{metric}_2w.png')

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("country_iso3", help="Country ISO3")
    parser.add_argument('-d', '--download-covid', action='store_true',
                        help='Download the COVID-19 data')
    return parser.parse_args()

if __name__ == "__main__":
    args = parse_args()
    main(args.country_iso3.upper(),download_covid=args.download_covid)