library(rmarkdown)
library(webshot)
library(tinytex)

country_files <- c('report_generation_AFG.Rmd',
                   'report_generation_COD.Rmd',
                   'report_generation_IRQ.Rmd',
                   'report_generation_SDN.Rmd',
                   'report_generation_SOM.Rmd',
                   'report_generation_SSD.Rmd')

country_list <- c('Afghanistan', 'Democratic Republic of Congo', 'Iraq', 'Sudan', 'Somalia', "South Sudan")

countries <- data.frame(country_files, country_list)

# assignment_date should be Wednesday's date
assignment_date <- as.Date("2021-02-24")

# render each report using assignment_date
for (country in countries$country_list) {
  
  country_file <- countries[which(countries$country_list == country), 'country_files']
  
  rmarkdown::render(country_file,
                    params = list(assignment_date = assignment_date), 
                    output_file = paste0(country, " ", assignment_date, ".pdf")
                    )
}

# move PDF and log files to archive folder
filenames <- dir(".", pattern = "*.pdf", ignore.case = TRUE)
logs <- dir(".", pattern = "*.log", ignore.case = TRUE)
  
for (i in 1:length(filenames)) file.rename(from = filenames[i], to = paste0("archive/", filenames[i]))
for (i in 1:length(logs)) file.rename(from = logs[i], to = paste0("archive/_logs/", logs[i]))




## Note from the author of rmarkdown regarding putting the output files in another directory:
# For output_file, do not put it in a different directory; output_file = 'test.md' is good, and foo/test.md is bad;
# If you want the output to be in a different directory, render it in the current directory, then move the files to the directory you want (you may call file.rename()).

## Regarding filenames:
# Due to the inability to automatically put the output file in a separate directory, the output filename is NOT parameterized with the country name and date to avoid overcrowding the repo. 
# An alternative would be to parameterize it and then manually move the files after rendering.