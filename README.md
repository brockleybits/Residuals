# SAG-AFTRA Residual Scraper
We all want to pay our agents their fair share each month, but it's a pain in the\
a** to go through the Residual Portal and Payment Hub line by line and tally up\
commissions.

This Python script scrapes both Payment Hub and SAG-AFTRA's residual portal, then\
aggregates jobs and tallies commissions based on your gross earnings. It outputs a CSV\
file that may be imported into your favorite spreadsheet app.

See `example_screenshot.png` for a peek at what the import could look like. Enjoy!

## Prior to Launch:
- You must be set up with Payment Hub to receive direct deposits of your\
SAG-AFTRA residual payments.
- You must have a Selenium web driver installed locally on your machine.\
See their documentation: [Install Drivers](https://www.selenium.dev/documentation/webdriver/getting_started/install_drivers/)
- You must modify this `scrape_residuals.py` file (see line 235) to point\
this app to your locally installed web driver.

## To Launch:
Run `python3 scrape_residuals.py` from the project directory.