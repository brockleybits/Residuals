# NAME: scrape_residuals.py
# DATE: 02 Feb 2021
# BY: Todd Brotze
# DESCRIPTION: Scrapes SAG-AFTRA Residuals Portal & PaymentHub,
#   then outputs to a .csv file for spreadsheet import.

# Imports
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from pathlib import Path
from datetime import datetime, timedelta
import time
import re
import getpass


# ====================
#      FUNCTIONS
# ====================

# Scrape PaymentHub
def scrapePaymentHub(d):

    # Load page content
    try:
        driver.find_element(By.LINK_TEXT, 'Direct Deposit').click()
    except:
        print('Login error. Quitting.\n')
        driver.close()
        driver.quit()
        quit()
    
    print('Scraping Payment Hub:')
    payHubDict = {}
    driver.find_element_by_xpath("//form[@id='PostForm']/input[@class='button btn']").click()

    try:
        WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.ID, "payee_payments_table")))
    except:
        print('Waiting 10 seconds...')
        time.sleep(10)
    time.sleep(2)
    driver.find_element_by_xpath("//div[@class='paginate_results_pp']/ul/li[3]").click()
    time.sleep(3)

    # Scrape table
    c = 0
    while c < 250:
        checkTable = driver.find_element_by_xpath("//table[@id='payee_payments_table']")
        checkBody = checkTable.find_element(By.TAG_NAME, 'tbody')
        checkRow = checkBody.find_elements(By.TAG_NAME, 'tr')[c]
        try:
            checkRow.find_element_by_xpath("td[4]/span[contains(concat(' ',normalize-space(@class),' '),' payments_status_cleared ')]")
            ckStatus = True
        except:
            ckStatus = False
        if ckStatus:
            print('Row ', c+1, ': ', end='')
            checkRow.find_element_by_xpath("td[7]/a").click()
            time.sleep(3)
            checkInfo = driver.find_element_by_xpath("//div[@id='modal-body']/div/div[2]/payee-payment-detail/div")
            ckCleared = str(checkInfo.find_element_by_xpath("div[5]/div[2]/div[2]").text)
            ckCleared = datetime.strptime(ckCleared, "%B %d, %Y %I:%M %p %Z")

            # Build Check Cleared Date: first year, then add month, last add day
            ckClrDate = str(ckCleared.year)
            ckClrDate = ckClrDate + str(ckCleared.month) if ckCleared.month > 9 else ckClrDate + '0' + str(ckCleared.month)
            ckClrDate = ckClrDate + str(ckCleared.day) if ckCleared.month > 9 else ckClrDate + '0' + str(ckCleared.day)
            
            ckTestDate = datetime(ckCleared.year, ckCleared.month, ckCleared.day)
            if ckTestDate < d - timedelta(days = 2):
                print('date exceeded')
                break
            ckNtAmt = float(str(checkInfo.find_element_by_xpath("div/span").text)[1:].replace(',',''))
            ckNo = str(checkInfo.find_element_by_xpath("div[10]/div[2]").text)
            ckIssued = str(checkInfo.find_element_by_xpath("div[11]/div[2]").text)[:10]
            ckIssued = ckIssued[5:7] + '/' + ckIssued[8:] + '/' + ckIssued[0:4]
            ntAmtStr = '{:.2f}'.format(ckNtAmt).replace('.', '')
            print(f'#{ckNo}\t${ckNtAmt}\tIssued: {ckIssued}\tCleared: {ckCleared}')
            payHubDict[ckNo + ntAmtStr] = [ckNtAmt, ckIssued, ckCleared, ckNo]
            # print(ckNo + ntAmtStr, payHubDict[ckNo + ntAmtStr])
            driver.find_element(By.CSS_SELECTOR, '.modal-close').click()
            time.sleep(1)
        c +=1
    print()

    # Return to SAG-AFTRA residual portal
    driver.get('https://www.sagaftra.org/residuals-portal')
    time.sleep(5)

    # This is payHubDict: {ckNo + ntAmtStr : [ckNtAmt, ckIssued, ckClrDate, ckNo]}
    return payHubDict


# Scrape SAG-AFTRA Residuals Portal
def scrapeSagTable(dLimit, phD):

    # Scrape table from available page(s)
    print('Scraping SAG-AFTRA...')
    resD = {}
    pageCount = 1
    while True:
        rowCount = len(driver.find_elements(By.TAG_NAME, 'tr')[1:])
        for i in range(rowCount):

            # Scrape summary rows at SAG-AFTRA and assign variables
            currentRow = driver.find_elements(By.TAG_NAME, 'tr')[i+1]
            sentDate = str(currentRow.find_elements(By.TAG_NAME, 'td')[1].text)
            dateList = re.findall('[0-9]+', sentDate)
            sntDate = dateList[2] + dateList[0] + dateList[1]
            testDate = datetime(int(dateList[2]), int(dateList[0]), int(dateList[1]))
            if testDate < dLimit: continue
            payor = str(currentRow.get_attribute('data-payor'))[7:]
            checkNum = str(currentRow.get_attribute('data-check'))[9:]
            netAmount = float(str(currentRow.get_attribute('data-net_amount'))[12:].replace(',',''))
            grossAmount = float(str(currentRow.find_elements(By.TAG_NAME, 'td')[2].text)[1:].replace(',',''))
            commission = round(grossAmount * 0.1, 2)
            currentRow.find_element(By.CSS_SELECTOR, 'td.details-control').click()

            # Gather detailed check info & construct resD
            detailsDict = scrapeDetails()  # {'title' : ['gross', [usage, usage ...]], ...}
            if len(detailsDict) == 1:
                for k, v in detailsDict.items():
                    dictKey = checkNum + '{:.2f}'.format(netAmount).replace('.', '')
                    if netAmount != phD[dictKey][0]:
                        print(f'\n*** WARNING - Conflict between PayHub & SAG-AFTRA: {dictKey} ***\n')
                    else:
                        # {Check No./Net : [Gross, Net, Check No., Issued, Cleared, Sent, Title, Prod. Co, Commission, [Usage]]}
                        resD[dictKey] = [v[0], netAmount, phD[dictKey][3], phD[dictKey][1], phD[dictKey][2], sentDate, k, payor, commission, v[1:]]
            else:
                suffix = 1
                for k, v in detailsDict.items():
                    dictKey = checkNum + '{:.2f}'.format(netAmount).replace('.', '')
                    if netAmount != phD[dictKey][0]:
                        print(f'\n*** WARNING - Conflict between PayHub & SAG-AFTRA: {dictKey} ***\n')
                    else:
                        newDictKey = dictKey + '_' + str(suffix)
                        newNet = round(netAmount * (v[0]/grossAmount), 2)
                        newComm = round(v[0] * 0.1, 2)
                        # {Check No./Net : [Gross, newNet, Check No., Issued, Cleared, Sent, Title, Prod. Co, Commission, [Usage]]}
                        resD[newDictKey] = [v[0], newNet, phD[dictKey][3], phD[dictKey][1], phD[dictKey][2], sentDate, k, payor, newComm, v[1:]]
                    suffix += 1

            currentRow.find_element(By.CSS_SELECTOR, 'td.details-control').click()
            time.sleep(1)
        lastPage = driver.find_element(By.LINK_TEXT, 'Next').get_attribute('class').strip()
        if 'disabled' not in lastPage:
            pageCount += 1
            driver.find_element(By.LINK_TEXT, str(pageCount)).click()
            time.sleep(3)
        else: break
    return resD


# Gather detailed data for each check issued
def scrapeDetails():
    time.sleep(1)
    detailColl = {}
    detailedTable = driver.find_element_by_xpath("//table[@class='residuals_payments sticky-enabled']")
    detailedDataRows = detailedTable.find_elements(By.TAG_NAME, 'tr')[1:]
    for r in range(len(detailedDataRows)):
        detailedData = detailedDataRows[r].find_elements(By.TAG_NAME, 'td')
        title = str(detailedData[0].text)
        payType = str(detailedData[1].text)
        payAmt = float(str(detailedData[2].text)[1:].replace(',',''))
        if (r == 0 or title not in detailColl.keys()) and payAmt == 0:
            detailColl[title] = [0]
        elif r == 0 or title not in detailColl.keys():
            detailColl[title] = [payAmt, payType]
        elif payAmt == 0:
            continue
        else:
            detailColl[title][0] += payAmt
            detailColl[title].append(payType)
        detailColl[title][0] = round(detailColl[title][0], 2)
    return detailColl


# Build .csv file
def buildReport(rD):

    # rD looks like this: {Check No./Net : [Gross, Net, Check No., Issued, Cleared, Sent, Title, Prod. Co, Commission, [Usage]]}

    print('\nBuilding CVS file:\n')
    stopDate = stopAtDateCleared.strftime('%Y%m%d')
    newFileName = str(Path.cwd()) + '/residual_txt_files/4Import_from_' + stopDate + '.txt'
    newFileHandle = open(newFileName, 'w')
    newFileHandle.write('TITLE, EPISODE, PRODUCTION CO., CHECK NUMBER, CHECK ISSUED, PAYMENT RECEIVED, GROSS AMT., NET AMT., COMMISSION, USAGE\n')
    for k, v in rD.items():
        lineTitle, lineScript = re.findall('(.+)\s/\s(.+)', v[6])[0] if '/' in v[6] else (v[6], '')
        lineTitle = lineTitle.replace(',','') if ',' in lineTitle else lineTitle
        lineScript = lineScript.replace(',','') if ',' in lineScript else lineScript
        v[7] = v[7].replace(',','') if ',' in v[7] else v[7]
        # TITLE, EPISODE, PRODUCTION CO., CHECK NUMBER, CHECK ISSUED, PAYMENT RECEIVED, GROSS AMT., NET AMT., COMMISSION, USAGE
        lineItem = '{},{},{},{},{},{},{},{},{},{}\n'
        if len(v[9]) > 1:
            usages = v[9][0]
            for i in range(len(v[9])-1):
                usages += ' / ' + v[9][i+1]
        else:
            usages = v[9][0]
        print(lineItem.format(lineTitle,lineScript,v[7],v[2],v[3],v[5],v[0],v[1],v[8],usages))
        newFileHandle.write(lineItem.format(lineTitle,lineScript,v[7],v[2],v[3],v[5],v[0],v[1],v[8],usages))
    newFileHandle.close()
    return



# ====================
#    PROGRAM BODY
# ====================


# Take Inputs
print('\nEnter SAG-AFTRA credentials:')
user = input('Username: ')
password = getpass.getpass('Password: ')

try:
    print('Collect residuals back to (90 day maximum):')
    stopAtDateCleared = datetime.fromisoformat(input('(YYYY-MM-DD) '))
    maxRange = datetime.today() - timedelta(days = 90)
except:
    print('Date entry error. Quitting.')
    quit()

if stopAtDateCleared < maxRange:
    print('Max date range exceeded. 90 day maximum allowed. Quitting.')
    quit()


# Set up Web Driver *-*-*-*- CHANGE THIS OS PATHWAY & DRIVER INFO BASED ON YOUR INSTALLED WEB DRIVER -*-*-*-*
webdriverPath = '/Applications/selenium/geckodriver'
driver = webdriver.Firefox(executable_path = str(Path.home()) + webdriverPath)


# Login at SAG-AFTRA.org
driver.get('https://www.sagaftra.org/login')
driver.find_element(By.CSS_SELECTOR, 'input#edit-name').send_keys(user)
driver.find_element(By.CSS_SELECTOR, 'input#edit-pass').send_keys(password)
driver.find_element(By.CSS_SELECTOR, 'input#sagaftra-login-button-submit').click()
driver.get('https://www.sagaftra.org/residuals-portal')
time.sleep(2)
print()


# Build dictionary by scraping residuals info from PaymentHub & SAG-AFTRA
payHubCollection = scrapePaymentHub(stopAtDateCleared)
residualCollection = scrapeSagTable(stopAtDateCleared, payHubCollection)


# Create CSV file & print output
buildReport(residualCollection)


# Quit
print()
driver.close()
driver.quit()
