import utils
import argparse
import pandas as pd
import matplotlib.pyplot as plt
from datetime import timedelta, date

CONFIG_FILE = 'config.yml'
WHO_COVID_URL='https://docs.google.com/spreadsheets/d/e/2PACX-1vSe-8lf6l_ShJHvd126J-jGti992SUbNLu-kmJfx1IRkvma_r4DHi0bwEW89opArs8ZkSY5G2-Bc1yT/pub?gid=0&single=true&output=csv'

HLX_TAG_TOTAL_CASES = "#affected+infected+confirmed+total"
HLX_TAG_TOTAL_DEATHS = "#affected+infected+dead+total"
HLX_TAG_DATE = "#date"

FIG_SIZE=(8,4)

TODAY = date.today()
TWO_WEEKS = TODAY + timedelta(days=14)
LAST_MONTH = TODAY - timedelta(days=30)

def main(country_iso3):
    parameters = utils.parse_yaml(CONFIG_FILE)[country_iso3]
    generate_current_status(country_iso3,parameters)

    # print(parameters)

def generate_current_status(country_iso3,parameters):
    subnational_covid=pd.read_csv(parameters['subnational_cases_url'])
    subnational_covid[HLX_TAG_DATE]=pd.to_datetime(subnational_covid[HLX_TAG_DATE]).dt.date
    subnational_covid=subnational_covid[(subnational_covid[HLX_TAG_DATE]>=LAST_MONTH) &\
                                        (subnational_covid[HLX_TAG_DATE]<=TODAY)]
    subnational_covid=subnational_covid.groupby(HLX_TAG_DATE).sum()

    # TODO can be downloaded only once?
    who_covid=pd.read_csv(WHO_COVID_URL)
    who_covid=who_covid[who_covid['ISO_3_CODE']==country_iso3]
    who_covid['date_epicrv']=pd.to_datetime(who_covid['date_epicrv']).dt.date
    who_covid=who_covid[(who_covid['date_epicrv']>=LAST_MONTH) &\
                        (who_covid['date_epicrv']<=TODAY)]
    print(who_covid)
    # who_covid=who_covid[who_covid['ISO_3_CODE']==country_iso3]

    fig_cases,ax_cases=plt.subplots(figsize=(FIG_SIZE[0],FIG_SIZE[1]))
    # draw subnational reported cumulative cases
    ax_cases.scatter(subnational_covid.index, subnational_covid[HLX_TAG_TOTAL_CASES],\
                     alpha=0.8, s=10,c='blue',marker='o',label=parameters['subnational_cases_source'])
    
    plt.legend()
    plt.show()


    print(subnational_covid)


    print(parameters)


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("country_iso3", help="Country ISO3")
    return parser.parse_args()

if __name__ == "__main__":
    args = parse_args()
    main(args.country_iso3.upper())