library('rmarkdown')

country_files <- c('report_generation_AFG.Rmd',
                   'report_generation_COD.Rmd',
                   'report_generation_IRQ.Rmd',
                   'report_generation_SDN.Rmd',
                   'report_generation_SOM.Rmd',
                   'report_generation_SSD.Rmd')

country_list <- c('Afghanistan', 'Democratic Republic of Congo', 'Iraq', 'Sudan', 'Somalia', "South Sudan")

# assignment_date should be Wednesday's date
for (i in 1:length(country_files)) rmarkdown::render(country_files[i],
                                           params = list(
                                           assignment_date = "2020-11-16"), 
                                           output_file = paste0(country_list[i], " ", assignment_date, ".pdf"),
                                           )

filenames <- dir(".", pattern = "*.pdf", ignore.case = TRUE)
  
for (i in 1:length(filenames)) file.rename(from = filenames[i], to = paste0("archive/", filenames[i]))

## Note from the author of rmarkdown regarding putting the output files in another directory:
# For output_file, do not put it in a different directory; output_file = 'test.md' is good, and foo/test.md is bad;
# If you want the output to be in a different directory, render it in the current directory, then move the files to the directory you want (you may call file.rename()).

## Regarding filenames:
# Due to the inability to automatically put the output file in a separate directory, the output filename is NOT parameterized with the country name and date to avoid overcrowding the repo. 
# An alternative would be to parameterize it and then manually move the files after rendering.