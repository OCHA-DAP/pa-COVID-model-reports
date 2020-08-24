import matplotlib.dates as mdates

# get all time cases and deaths
#who_covid_new = get_who(WHO_COVID_FILENAME,country_iso3,min_date=LAST_TWO_MONTHS,max_date=FOUR_WEEKS)
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

# compute rolling 7-day average
who_covid_new['new_deaths_rolling_mean'] = who_covid_new.NewDeath.rolling(window=7).mean()

# Create figure and plot space
fig, ax = plt.subplots(figsize=(10, 10))

# Add x-axis and y-axis
ax.bar(who_covid_new['date_epicrv'],
        who_covid_new['NewDeath'],
        color='lightcoral')

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

