library('rmarkdown')
rmarkdown::render('report_generation_AFG.Rmd',
                  params = list(assignment_date = as.Date("2020-09-01")))

country_files <- c('report_generation_AFG.Rmd',
                   'report_generation_COD.Rmd',
                   'report_generation_IRQ.Rmd',
                   'report_generation_SDN.Rmd',
                   'report_generation_SOM.Rmd',
                   'report_generation_SSD.Rmd')
                 

# for (f in country_files) rmarkdown::render(f,
#                                            params = list(assignment_date = as.Date("2020-08-01")))



# Note regarding putting the output files in another directory from the author of rmarkdown:
# For output_file, do not put it in a different directory; output_file = 'test.md' is good, and foo/test.md is bad;
# If you want the output to be in a different directory, render it in the current directory, then move the files to the directory you want (you may call file.rename()).