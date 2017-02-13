#################################################################################################
# Script runs nightly to generate the previous days VSI Provisioning Stats Report
# emails are sent with excel file and stats added to database
#################################################################################################

import time,  SoftLayer, json, configparser, argparse, pytz, logging,sendgrid, couchdb
import pandas as pd
import numpy as np
from cloudant.client import Cloudant
from datetime import datetime, timedelta, tzinfo

def convert_timedelta(duration):
    days, seconds = duration.days, duration.seconds
    hours = days * 24 + seconds // 3600
    minutes = (seconds % 3600) // 60
    seconds = seconds % 60
    totalminutes = round((days * 1440) + (hours * 60) + minutes + (seconds/60),1)
    return totalminutes

def convert_timestamp(sldate):
    formatedDate = sldate
    formatedDate = formatedDate[0:22]+formatedDate[-2:]
    formatedDate = datetime.strptime(formatedDate, "%Y-%m-%dT%H:%M:%S%z")
    return formatedDate.astimezone(central)

def getDescription(categoryCode, detail):
    for item in detail:
        if item['categoryCode']==categoryCode:
            return item['description']
    return "Not Found"

############################################################
## READ CommandLine Arguments and load configuration file
############################################################
parser = argparse.ArgumentParser(description="Generate report for daily provisioning statistics.")
parser.add_argument("-u", "--username", help="SoftLayer API Username")
parser.add_argument("-k", "--apikey", help="SoftLayer APIKEY")
parser.add_argument("-c", "--config", help="config.ini file to load")
parser.add_argument("-o", "--output", help="Outputfile")
parser.add_argument("-d", "--date", help="Date to generate report for.")

args = parser.parse_args()

# Read Config File
if args.config != None:
        filename = args.config
else:
        filename = "config.ini"

config = configparser.ConfigParser()
config.read(filename)

# Use username/apikey passed if available, otherwise use config file.
if args.username != None:
    username=args.username
else:
    username=config['api']['username']

if args.apikey != None:
    apikey=args.apikey
else:
    apikey=config['api']['apikey']

if args.date == None:
    reportdate = datetime.now() - timedelta(days=1)
else:
    reportdate=datetime.strptime(args.date+" 0:0:0","%m/%d/%Y %H:%M:%S")

central = pytz.timezone("US/Central")
startdate = datetime.strftime(reportdate, "%m/%d/%Y") + " 0:0:0"
enddate = datetime.strftime(reportdate,"%m/%d/%Y") + " 23:59:59"

if args.output == None:
    outputname="daily"+datetime.strftime(reportdate, "%m%d%Y")+".xlsx"
else:
    outputname=args.output


######################################
# Connect to SoftLayer API
######################################
client = SoftLayer.Client(username=username, api_key=apikey, endpoint_url=SoftLayer.API_PRIVATE_ENDPOINT)

######################################
# Enable Logging
######################################

logging.basicConfig(filename='daily.log', format='%(asctime)s %(message)s', datefmt='%Y-%m-%d %I:%M:%S %p',level=logging.WARNING)

logging.warning('Running Daily Provisioning Report for %s.' % (datetime.strftime(reportdate, "%m/%d/%Y")))


######################################
# set Script Behavior Flags
######################################
lookupPowerOn = True
createExcel = True

######################################
# Notification Variables
######################################

if config['sendGrid']['apiKey'] == None:
    sendEmails = False
    sendGridApi = ""
    sendGridTo = []
    sendGridFrom = ""
    sendGridSubject = ""
else:
    sendEmails = True
    sendGridApi = config['sendGrid']['apiKey']
    sendGridTo = config['sendGrid']['to'].split(",")
    sendGridFrom = config['sendGrid']['from']
    sendGridSubject = config['sendGrid']['subject']

###########################################################
# define cloudant database in bluemix to hold daily results
###########################################################

if config['cloudant']['username'] == None:
    createDB = False
    queryDB = False
else:
    createDB = True
    queryDB = True
    cloudant = Cloudant(config['cloudant']['username'], config['cloudant']['password'], url=config['cloudant']['url'])
    cloudant.connect()
    vsistatsDb = cloudant["vsistats"]

df=pd.DataFrame()
logging.warning('Getting invoice list for Account from %s.' % (datetime.strftime(reportdate, "%m/%d/%Y")))
InvoiceList=""
while InvoiceList is "":
    try:
        InvoiceList = client['Account'].getInvoices(mask='createDate,typeCode, id, invoiceTotalAmount', filter={
            'invoices': {
                'createDate': {
                    'operation': 'betweenDate',
                    'options': [
                         {'name': 'startDate', 'value': [startdate]},
                         {'name': 'endDate', 'value': [enddate]}
                         ],
                    },
                'typeCode': {
                    'operation': 'in',
                    'options': [
                        {'name': 'data', 'value': ['ONE-TIME-CHARGE', 'NEW']}
                    ]
                    },
                }
            })
    except SoftLayer.SoftLayerAPIError as e:
        logging.warning("Account::getInvoices: %s, %s" % (e.faultCode, e.faultString))
        df = pd.DataFrame()

for invoice in InvoiceList:
    invoiceID = invoice['id']
    invoicedetail=""
    logging.warning('Looking up InvoiceId %s.' % (invoiceID))
    while invoicedetail is "":
        try:
            time.sleep(1)
            invoicedetail = client['Billing_Invoice'].getObject(id=invoiceID, mask="closedDate, invoiceTopLevelItems, invoiceTopLevelItems.product,invoiceTopLevelItems.location")
        except SoftLayer.SoftLayerAPIError as e:
            logging.warning("Billing_Invoice::getObject: %s, %s" % (e.faultCode, e.faultString))
            time.sleep(5)

    invoiceTopLevelItems=invoicedetail['invoiceTopLevelItems']
    invoiceDate=convert_timestamp(invoicedetail["closedDate"])
    for item in invoiceTopLevelItems:
        if item['categoryCode']=="guest_core":
            itemId = item['id']
            billingItemId = item['billingItemId']
            location=item['location']['name']
            hostName = item['hostName']+"."+item['domainName']
            createDateStamp = convert_timestamp(item['createDate'])
            product=item['description']
            cores=""

            if 'product' in item:
                product=item['product']['description']
                cores=item['product']['totalPhysicalCoreCount']

            billing_detail=""
            logging.warning('Looking up billing Invoice Detail for %s.' % (itemId))

            while billing_detail is "":
                try:
                    time.sleep(1)
                    billing_detail = client['Billing_Invoice_Item'].getObject(id=itemId,
                                                                              mask="filteredAssociatedChildren.product," \
                                                                                   "filteredAssociatedChildren.categoryCode," \
                                                                                   "filteredAssociatedChildren.description," \
                                                                                   "billingItem.cancellationDate, " \
                                                                                   "billingItem.provisionTransaction")
                except SoftLayer.SoftLayerAPIError as e:
                    logging.warning("Billing_Invoice_Item::getObject(%s): %s, %s" % (itemId,e.faultCode, e.faultString))
                    time.sleep(5)


            filteredAssociatedChildren=billing_detail['filteredAssociatedChildren']
            billingItem=billing_detail['billingItem']

            os=getDescription("os", filteredAssociatedChildren)
            memory=getDescription("ram", filteredAssociatedChildren)
            disk=getDescription("guest_disk0", filteredAssociatedChildren)

            if 'provisionTransaction' in billingItem:
                provisionTransaction = billingItem['provisionTransaction']
                provisionId = provisionTransaction['id']
                guestId = provisionTransaction['guestId']
                provisionDateStamp = convert_timestamp(provisionTransaction['modifyDate'])
            else:
                provisionTransaction = "0"
                provisionId = "0"
                guestId = "0"
                provisionDateStamp = convert_timestamp(item['createDate'])

            eventdate = provisionDateStamp
            powerOnDateStamp = provisionDateStamp

            # FORMAT DATE & TIME STAMPS AND DELTAS FOR CSV
            createDate = datetime.strftime(createDateStamp, "%Y-%m-%d")
            createTime = datetime.strftime(createDateStamp, "%H:%M:%S")
            provisionDate = datetime.strftime(provisionDateStamp, "%Y-%m-%d")
            provisionTime = datetime.strftime(provisionDateStamp, "%H:%M:%S")
            provisionDelta = convert_timedelta(provisionDateStamp - createDateStamp)


            found=0
            if lookupPowerOn == True:
                logging.warning('Searching event Log for POWERON detail for guestId %s.' % (guestId))
                # GET OLDEST POWERON EVENT FROM EVENTLOG FOR GUESTID AS INITIAL RESOURCE ALLOCATION TIMESTAMP

                events=""
                try:
                    time.sleep(1)
                    events = client['Event_Log'].getAllObjects(mask="objectId,eventName,eventCreateDate",filter={
                                                            'eventName': {'operation': 'Power On'},
                                                            'objectId': {'operation': guestId}})
                except SoftLayer.SoftLayerAPIError as e:
                    logging.warning("Event_Log::getAllObjects: %s, %s" % (e.faultCode, e.faultString))

                for event in events:
                    if event['eventName']=="Power On":
                        eventdate = event["eventCreateDate"]
                        eventdate = eventdate[0:29]+eventdate[-2:]
                        eventdate = datetime.strptime(eventdate, "%Y-%m-%dT%H:%M:%S.%f%z")
                        if eventdate<powerOnDateStamp:
                            powerOnDateStamp = eventdate
                            found=1


                # Calculate poweron if found
                if found==1:
                    logging.warning('POWERON detail for guestId %s FOUND.' % (guestId))
                    powerOnDateStamp=powerOnDateStamp.astimezone(central)
                    powerOnDate=datetime.strftime(powerOnDateStamp,"%Y-%m-%d")
                    powerOnTime=datetime.strftime(powerOnDateStamp,"%H:%M:%S")
                    powerOnDelta=convert_timedelta(powerOnDateStamp-createDateStamp)
                else:
                    logging.warning('POWERON detail for guestId %s NOT FOUND.' % (guestId))
                    powerOnDate="Not Found"
                    powerOnTime="Not Found"
                    powerOnDelta=0
            else:
                powerOnDate = "Not Found"
                powerOnTime = "Not Found"
                powerOnDelta = 0


            ######################################
            # Get VSI detail from Bluemix database
            ######################################
            key = str(guestId)

            if queryDB == True:
                try:
                    doc=vsistatsDb[key]
                    logging.warning('VSI detail found in database for %s.' % (key))
                    serverRoom = doc['serverRoom']
                    router = doc['router']
                    vlan = doc['vlan']
                    primaryBackendIpAddress = doc['primaryBackendIpAddress']
                    templateImage = doc['templateImage']
                    if templateImage == "no":
                        templateImage = "Stock Image"
                except:
                    logging.warning('Detailed VSI data note found in database for %s.' % (key))
                    serverRoom =""
                    router =""
                    vlan =""
                    primaryBackendIpAddress =""
                    templateImage="Unknown Image"
            else:
                serverRoom = ""
                router = ""
                vlan = ""
                primaryBackendIpAddress = ""
                templateImage = "Unknown Image"

            row = {'InvoiceId': invoiceID,
                   'BillingItemId': billingItemId,
                   'GuestId': guestId,
                   'Datacenter': location,
                   'ServerRoom': serverRoom,
                   'Router': router,
                   'Vlan': vlan,
                   'IP': primaryBackendIpAddress,
                   'Product': product,
                   'Cores': cores,
                   'OS': os,
                   'Memory': memory,
                   'Disk': disk,
                   'Image': templateImage,
                   'Hostname': hostName,
                   'CreateDate': createDate,
                   'CreateTime': createTime,
                   'PowerOnDate': powerOnDate,
                   'PowerOnTime': powerOnTime,
                   'PowerOnDelta': powerOnDelta,
                   'ProvisionedDate': provisionDate,
                   'ProvisionedTime': provisionTime,
                   'ProvisionedDelta': provisionDelta
                   }
            df = df.append(row, ignore_index=True)


########################################################
## Generate Statisitics & Create HTML for message
#########################################################
logging.warning("Generating Statistics and formating email message.")
header_html = ("<p><center><b>AFI Provisionings Statistics for %s</b></center></br></p>" % ((datetime.strftime(reportdate, "%m/%d/%Y"))))

########################################################
##  Describe Overall Provisioning Statistics
########################################################
stats=(df["ProvisionedDelta"].describe())
stats_html= "<p><b>Provisioning Statistics</b></br>"+(stats.to_frame().to_html())+"</p>"

########################################################
# Create Pivot Table for Datacenter & Image Statistiics
########################################################
imagePivot = pd.pivot_table(df,index=['Datacenter', 'Image'], values='ProvisionedDelta', aggfunc=[len, np.min, np.average, np.std, np.max],margins=True)
imagePivot_html= "<p><b>Datacenter & Image Statistics</b></br>"+imagePivot.to_html()+"</p>"

# Create Time Distribution
provisionRequests=len(df)
notAllocated=len(df[(df.PowerOnDelta >30)])
distribution0=len(df[df.ProvisionedDelta.between(0,30,inclusive=True)])
distribution30=len(df[df.ProvisionedDelta.between(31,60,inclusive=True)])
distribution60=len(df[df.ProvisionedDelta.between(61,90,inclusive=True)])
distribution90=len(df[df.ProvisionedDelta.between(91,120,inclusive=True)])
distribution120=len(df[df.ProvisionedDelta.between(121,360,inclusive=True)])
distribution360=len(df[df.ProvisionedDelta.between(361,999999,inclusive=True)])


distribution_html=('<p><b>Time Distribution Report</b></br><table width="400" border="1" class="dataframe"><tr>' \
           '<th>Total</th><th>NotAlloc</th><th>0to30</th><th>31-60</th><th>61-90</th><th>91-120</th><th>121-360</th><th>gt360</th></tr><tr>' \
           '<td style="text-align: center;">%s</td><td style="text-align: center;">%s</td><td style="text-align: center;">%s</dh><td style="text-align: center;">%s</td>' \
           '<td style="text-align: center;">%s</td><td style="text-align: center;">%s</td><td style="text-align: center;">%s</td><td style="text-align: center;">%s</td>' \
           '</tr></table></p>' % (provisionRequests,notAllocated,distribution0, distribution30, distribution60, distribution90, distribution120, distribution360))

html=header_html+stats_html+distribution_html+imagePivot_html

##########################################
# Store Daily Stats in database
##########################################

freq = {"Total": provisionRequests,
                "0-30": distribution0,
                "31-60": distribution30,
                "61-90": distribution60,
                "91-120": distribution90,
                "121-360": distribution120,
                ">360": distribution360}

if createDB == True:
    record = {'_id': datetime.strftime(reportdate, "%m%d%Y"),
             'docType': "dailystats",
             'distribution': json.dumps(freq),
             'detail': df.to_json(),
             'pivot': imagePivot.to_json(),  # total provisioning VSI by datacenter
             }
    try:
        doc = vsistatsDb.create_document(record)
        logging.warning("Daily stats written to document %s written in database." % (doc['_id']))
    except:
        logging.warning("Daily stats could not be written to database.")

##########################################
# Write Output to Excel
##########################################

if createExcel == True:
    logging.warning("Creating Excel File.")
    writer = pd.ExcelWriter(outputname, engine='xlsxwriter')
    df.to_excel(writer,'Detail')
    imagePivot.to_excel(writer,'Image_Pivot')
    writer.save()

#########################################
# FORMAT & SEND EMAIL VIA SENDGRID ACCOUNT
##########################################
if sendEmails == True:
    sg = sendgrid.SendGridClient(sendGridApi)
    logging.warning("Sending report via email.")
    message = sendgrid.Mail()
    message.add_to(sendGridTo)
    message.set_subject(sendGridSubject)
    message.set_html(html)
    message.set_from(sendGridFrom)
    message.add_attachment(outputname, './'+outputname)
    status, msg = sg.send(message)
    logging.warning("Email Send status code = %s." % status)
logging.warning('Finished Daily Provisioning Report Job for %s.' % (datetime.strftime(reportdate, "%m/%d/%Y")))
