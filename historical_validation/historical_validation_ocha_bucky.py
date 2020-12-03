import os
dir_path = os.path.dirname(os.path.realpath('__file__'))
import sys
sys.path.insert(0, dir_path)
from datetime import datetime
from utils import *
import pandas as pd

country_iso3='SSD'
country_iso2='SS'
github_repo='https://raw.githubusercontent.com/OCHA-DAP/pa-COVID-model-reports'
WHO_COVID_FILENAME='WHO_data/WHO-COVID-19-global-data.csv'
WHO_DATA_COLOR='dodgerblue'
download_csv=False

TODAY = datetime.today().date()
EARLIEST_DATE = datetime.strptime('2020-02-24', '%Y-%m-%d').date()


def download_bucky_results(dir_path,country_iso3,github_repo):
    data_folder=f'{dir_path}/historical_validation/data/{country_iso3}'
    log_file=f'{data_folder}/gitlog.txt'
    bucky_csv_file=f'Bucky_results/{country_iso3}_npi/adm0_quantiles.csv'
    os.system(f'git log {dir_path}/{bucky_csv_file} > {log_file}')
    with open (log_file, 'rt') as myfile:  
        for myline in myfile:              
            if not 'commit' in myline: continue
            commit_id = myline.split(' ')[1].replace('\n','')
            os.system(f'wget {github_repo}/{commit_id}/{bucky_csv_file} > {data_folder}/adm0_quantiles_{commit_id}.csv')

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

def draw_data_model_comparison_new(country_iso3,who_covid,metric):
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

def get_historical_bucky(country_iso3):
    data_folder=f'{dir_path}/historical_validation/data/{country_iso3}'
    for filename in os.listdir(data_folder):
        if filename.endswith(".csv"):
            filename=os.path.join(data_folder, filename)
            print(filename)
            df=pd.read_csv(filename)
            print(df)
        else:
            continue

if __name__ == "__main__":

    if download_csv:
        download_bucky_results(dir_path,country_iso3,github_repo)
    
    # who_covid=get_who(WHO_COVID_FILENAME,country_iso2,min_date=EARLIEST_DATE,max_date=TODAY)
    bucky_npi=get_historical_bucky(country_iso3)

    # draw_data_model_comparison_new(country_iso3,who_covid,'daily_reported_cases')
    # plt.legend()
    # plt.show()


    
    
