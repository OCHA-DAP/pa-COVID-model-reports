import os
DIR_PATH = os.path.dirname(os.path.realpath('__file__'))
import sys
sys.path.insert(0, DIR_PATH)
from datetime import datetime, timedelta
import utils
from utils import *
import pandas as pd
from matplotlib import cm

iso3s=['SSD','AFG','SOM','COD','SDN','IRQ']
iso2s=['SS', 'AF', 'SO', 'CD', 'SD', 'IQ']

download_bucky_csv=1
download_WHO_csv=1

TODAY = datetime.today().date()
EARLIEST_DATE = datetime.strptime('2020-06-01', '%Y-%m-%d').date()

GITHUB_REPO='https://raw.githubusercontent.com/OCHA-DAP/pa-COVID-model-reports'
CONFIG_FILE = 'config.yml'
WHO_COVID_URL='https://covid19.who.int/WHO-COVID-19-global-data.csv'
WHO_COVID_FILENAME='WHO_data/WHO-COVID-19-global-data.csv'
WHO_DATA_COLOR='dodgerblue'
# NPI_COLOR='green'
SUBNATIONAL_DATA_COLOR='navy'
#these are the quantile values to consider for min and max projected numbers
MIN_QUANTILE=0.05
MAX_QUANTILE=0.95



def get_list_of_commits(BUCKY_CSV_FILE):
    os.system(f'git log {DIR_PATH}/{BUCKY_CSV_FILE} > {GIT_LOGFILE}')
    commit_ids=list()
    dates=list()
    with open (GIT_LOGFILE, 'rt') as myfile:  
        for myline in myfile:
            if 'commit' in myline:
                commit_ids.append(myline.split(' ')[1].replace('\n',''))
            if 'Date' in myline:
                dates.append(myline.split('   ')[1].replace('\n',''))
    dates=pd.to_datetime(dates)
    hour_diffs=[abs(t - s).total_seconds()/3600 for s, t in zip(dates, dates[1:])]
    # we always want to select the latest commit (position 0)
    hour_diffs.insert(0,1000)
    # at least 5 days (120 hours) from the following commit
    commit_ids_download=[commit_id for commit_id,hour_diff in zip(commit_ids, hour_diffs) if hour_diff>=120]
    return commit_ids_download

def download_bucky_results(DATA_FOLDER,GITHUB_REPO,BUCKY_CSV_FILE):
    for commit_id in get_list_of_commits(BUCKY_CSV_FILE):
        os.system(f'wget -O {DATA_FOLDER}/adm0_quantiles_{commit_id}.csv {GITHUB_REPO}/{commit_id}/{BUCKY_CSV_FILE}')

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

def get_historical_bucky_collection(country_iso3,bucky_var):

    DATA_FOLDER=f'{DIR_PATH}/historical_validation/data/{country_iso3}'
    bucky_collection={}
    for commit_id in get_list_of_commits():
    # for filename in os.listdir(DATA_FOLDER):
    #     if filename.endswith(".csv"):
    #         filename=os.path.join(DATA_FOLDER, filename)
        csv_filename=f'{DATA_FOLDER}/adm0_quantiles_{commit_id}.csv'
        df=pd.read_csv(csv_filename)
        bucky_metric=''
        quantile='quantile'
        if not quantile in df.columns:
            quantile='q'
        for var in bucky_var:
            if var in df.columns:
                bucky_metric=var
                break
        df=df.set_index('date')
        out_df=pd.DataFrame({
            'med':df[df[quantile]==0.5][bucky_metric],
            'min':df[df[quantile]==MIN_QUANTILE][bucky_metric],
            'max':df[df[quantile]==MAX_QUANTILE][bucky_metric],
        })
        out_df.index = pd.to_datetime(out_df.index)
        # the first date of the simulation should be removed, as it is an adjustment of the model
        out_df = out_df.iloc[1:]
        # finally remove all projections before EARLIEST_DATE
        if min(out_df.index) < EARLIEST_DATE:
            continue
        bucky_collection[csv_filename]=out_df
    return bucky_collection


def draw_data_model_comparison_new(country_iso3,country_iso2,metric):
    # plot the 4 inputs and save figure
    if metric=='cumulative_reported_cases':
        who_var='Cumulative_cases'
        bucky_var=['cumulative_reported_cases','cumulative_cases_reported']
        subnational_var=HLX_TAG_TOTAL_CASES
        fig_title='Cumulative reported cases'
    elif metric=='daily_reported_cases':
        who_var='New_cases'
        bucky_var=['daily_reported_cases','daily_cases_reported']
        fig_title='Daily reported cases'
    elif metric=='daily_deaths':
        who_var='New_deaths'
        bucky_var=['daily_deaths']
        fig_title='Daily reported deaths'
    elif metric=='cumulative_deaths':
        who_var='Cumulative_deaths'
        bucky_var=['cumulative_deaths']
        subnational_var=HLX_TAG_TOTAL_DEATHS
        fig_title='Cumulative deaths'
    else:
        print(f'metric {metric} not implemented')
        return False

    parameters = utils.parse_yaml(CONFIG_FILE)[country_iso3]
    who_covid=get_who(WHO_COVID_FILENAME,country_iso2,min_date=EARLIEST_DATE,max_date=TODAY)
    subnational_covid = get_subnational_covid_data(parameters, aggregate=True, min_date=EARLIEST_DATE, max_date=TODAY)
    bucky_npi_collection=get_historical_bucky_collection(country_iso3,bucky_var)

    fig,axis=create_new_subplot(fig_title)

    evenly_spaced_interval = np.linspace(0, 1, len(bucky_npi_collection))
    colors = [cm.viridis(x) for x in evenly_spaced_interval]

    for icolor,(_, bucky_npi) in enumerate(bucky_npi_collection.items()):
        bucky_npi=bucky_npi[bucky_npi['med']>0]
        bucky_npi['med'].plot(c=colors[icolor],ax=axis,label='_nolegend_',lw=5, zorder=0)
        axis.fill_between(bucky_npi.index,
                          bucky_npi['min'],
                          bucky_npi['max'],
                          color=colors[icolor],
                          alpha=0.4)

    # draw reported data by who
    if 'daily' in metric:
        axis.bar(who_covid.index, who_covid[who_var],alpha=0.8,color=WHO_DATA_COLOR,label='WHO')
        # compute rolling 7-day average
        who_covid_rolling = who_covid[who_var].rolling(window=7).mean()
        axis.plot(who_covid_rolling.index, who_covid_rolling,
        lw=3,color=lighten_color(WHO_DATA_COLOR,1.6),label='WHO - 7d rolling average')
    else:
        # draw WHO national reported numbers
        axis.scatter(who_covid.index, who_covid[who_var],
                     alpha=0.8, s=20,c=WHO_DATA_COLOR,marker='*',label='WHO')

    axis.set_xlim(EARLIEST_DATE,TODAY)
    if 'daily' in metric:
        axis.add_artist(plt.legend(title='COVID-19 data',loc='upper left',ncol=2))
        axis.add_artist(get_bucky_legend(colors,location='upper right'))
        fig.savefig(f'{DATA_FOLDER}/{country_iso3}_{metric}.png')
        return
    # draw subnational reported numbers
    axis.scatter(subnational_covid.index, subnational_covid[subnational_var],\
                     alpha=0.8, s=20,c=SUBNATIONAL_DATA_COLOR,marker='o',label='MoPH')

    axis.add_artist(plt.legend(title='COVID-19 data',loc='upper left',ncol=2))
    axis.add_artist(get_bucky_legend(colors,location='lower right'))
    fig.savefig(f'{DATA_FOLDER}/{country_iso3}_{metric}.png')
    return

def get_bucky_legend(colors,location):
    from matplotlib.lines import Line2D
    custom_lines = [Line2D([0], [0], color=colors[0], lw=4),
                    Line2D([0], [0], color=colors[-1], lw=4)]
    return plt.legend(custom_lines, ['Recent','Past'],title='OCHA-Bucky projections',loc=location,ncol=2)


if __name__ == "__main__":

    for icountry,country_iso3 in enumerate(iso3s):
        country_iso2=iso2s[icountry]
        BUCKY_CSV_FILE=f'Bucky_results/{country_iso3}_npi/adm0_quantiles.csv'
        DATA_FOLDER=f'{DIR_PATH}/historical_validation/data/{country_iso3}'
        GIT_LOGFILE=f'{DATA_FOLDER}/gitlog.txt'

        if download_bucky_csv:
            # get all bucky results from github
            download_bucky_results(DATA_FOLDER,GITHUB_REPO,BUCKY_CSV_FILE)
        if download_WHO_csv:
            # Download latest covid file tiles and read them in
            download_who_covid_data(WHO_COVID_URL,WHO_COVID_FILENAME)

        # draw_data_model_comparison_new(country_iso3,country_iso2,'daily_reported_cases')
        # draw_data_model_comparison_new(country_iso3,country_iso2,'cumulative_reported_cases')
        # draw_data_model_comparison_new(country_iso3,country_iso2,'daily_deaths')
        # draw_data_model_comparison_new(country_iso3,country_iso2,'cumulative_deaths')
        # plt.show()