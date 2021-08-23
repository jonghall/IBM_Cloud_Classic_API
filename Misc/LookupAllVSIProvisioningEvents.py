import time,  SoftLayer, configparser, os, argparse, csv, math,logging
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
    return formatedDate

def getDescription(categoryCode, detail):
    for item in detail:
        if item['categoryCode']==categoryCode:
            return item['description']
    return "Not Found"

def initializeSoftLayerAPI(user, key, configfile):
    if user == None and key == None:
        if configfile != None:
            filename=args.config
        else:
            filename="config.ini"
        config = configparser.ConfigParser()
        config.read(filename)
        client = SoftLayer.Client(username=config['api']['username'], api_key=config['api']['apikey'])
    else:
        #client = SoftLayer.Client(username=config['api']['username'], api_key=config['api']['apikey'],endpoint_url=SoftLayer.API_PRIVATE_ENDPOINT)
        client = SoftLayer.Client(username=user, api_key=key)
    return client


#
# Get APIKEY from config.ini & initialize SoftLayer API
#


## READ CommandLine Arguments and load configuration file
parser = argparse.ArgumentParser(description="z.")
parser.add_argument("-u", "--username", help="SoftLayer API Username")
parser.add_argument("-k", "--apikey", help="SoftLayer APIKEY")
parser.add_argument("-c", "--config", help="config.ini file to load")
parser.add_argument("-s", "--startdate", help="start date mm/dd/yy")
parser.add_argument("-e", "--enddate", help="End date mm/dd/yyyy")
parser.add_argument("-o", "--output", help="Outputfile")
args = parser.parse_args()

client = initializeSoftLayerAPI(args.username, args.apikey, args.config)


if args.startdate == None:
    startdate=input("Report Start Date (MM/DD/YYYY): ")
else:
    startdate=args.startdate

if args.enddate == None:
    enddate=input("Report End Date (MM/DD/YYYY): ")
else:
    enddate=args.enddate

if args.output == None:
    outputname=input("Output filename: ")
else:
    outputname=args.output



fieldnames = ['InvoiceID', 'BillingItemId', 'TransactionID', 'Datacenter', 'Product', 'Cores', 'Memory', 'Disk', 'OS', 'Hostname',
              'CreateDate', 'CreateTime', 'PowerOnDate', 'PowerOnTime', 'PowerOnDelta', 'ProvisionedDate',
              'ProvisionedTime', 'ProvisionedDelta', 'CancellationDate', 'CancellationTime', 'HoursUsed', 'HourlyRecurringFee']

outfile = open(outputname, 'w')
csvwriter = csv.DictWriter(outfile, delimiter=',', fieldnames=fieldnames)
csvwriter.writerow(dict((fn, fn) for fn in fieldnames))
## OPEN CSV FILE TO READ LIST OF SERVERS


logging.basicConfig(filename='lookupAllVSIProvisioningEvents.log', format='%(asctime)s %(message)s', level=logging.WARNING)
logging.warning ('%s Checking Provisioning Events.' % (datetime.strftime(datetime.now(),"%m/%d/%Y %H:%M:%S")))

InvoiceList = client['Account'].getInvoices(mask='createDate,typeCode, id, invoiceTotalAmount', filter={
        'invoices': {
            'createDate': {
                'operation': 'betweenDate',
                'options': [
                     {'name': 'startDate', 'value': [startdate+" 0:0:0"]},
                     {'name': 'endDate', 'value': [enddate+" 23:59:59"]}
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


logging.info('Starting %s NEW/ONE-TIME Invoices between %s and %s.' % (len(InvoiceList),startdate,enddate))
for invoice in InvoiceList:
    invoiceID = invoice['id']
    invoicedetail=""
    logging.warning('Getting invoice detail for invoice %s.' % (invoiceID))
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
            billing_detail=""
            logging.warning('Getting detail for billingitemId %s.' % (billingItemId))
            while billing_detail is "":
                try:
                    time.sleep(1)
                    billing_detail = client['Billing_Invoice_Item'].getFilteredAssociatedChildren(id=itemId)
                except SoftLayer.SoftLayerAPIError as e:
                    logging.warning("Billing_Invoice_Item::getFilteredAssociatedChildren: %s, %s" % (e.faultCode, e.faultString))
                    time.sleep(5)

            os=getDescription("os", billing_detail)
            memory=getDescription("ram", billing_detail)
            disk=getDescription("guest_disk0", billing_detail)


            if 'product' in item:
                product=item['product']['description']
                cores=item['product']['totalPhysicalCoreCount']

            billingInvoiceItem=""
            logging.warning('Getting item detail for itemId %s.' % (itemId))
            while billingInvoiceItem is "":
                try:
                   time.sleep(1)
                   billingInvoiceItem = client['Billing_Invoice_Item'].getBillingItem(id=itemId, mask="cancellationDate, provisionTransaction")
                except SoftLayer.SoftLayerAPIError as e:
                   logging.warning("Billing_Invoice_Item::getBillingItem: %s, %s" % (e.faultCode, e.faultString))
                   time.sleep(5)

            if 'provisionTransaction' in billingInvoiceItem:
                provisionTransaction = billingInvoiceItem['provisionTransaction']
                provisionId = provisionTransaction['id']
                guestId = provisionTransaction['guestId']
                provisionDateStamp = convert_timestamp(provisionTransaction['modifyDate'])
            else:
                provisionTransaction = "0"
                provisionId = "0"
                guestId = "0"
                provisionDateStamp = convert_timestamp(item['createDate'])

            # determine cancelation date of VSI to calculate total hours; otherwise assume still running
            if 'cancellationDate' in billingInvoiceItem:
                if billingInvoiceItem['cancellationDate'] != "":
                    cancellationDateStamp=convert_timestamp(billingInvoiceItem['cancellationDate'])
            else:
                cancellationDateStamp="Running"

            # If still running use current timestamp to calculate hoursUsed otherwise use cancellation date.

            if cancellationDateStamp == "Running":
                    currentDateStamp=datetime.datetime.now()
                    hoursUsed=math.ceil(convert_timedelta(currentDateStamp-provisionDateStamp)/60)
            else:
                    hoursUsed=math.ceil(convert_timedelta(cancellationDateStamp-provisionDateStamp)/60)


            # CALCULATE HOURLY CHARGE INCLUDING ASSOCIATED CHILDREN
            if 'hourlyRecurringFee' in item:
                hourlyRecurringFee = round(float(item['hourlyRecurringFee']),3)
            else:
                hourlyRecurringFee = 0


            for child in billing_detail:
                if 'hourlyRecurringFee' in child:
                    hourlyRecurringFee = round(hourlyRecurringFee + float(child['hourlyRecurringFee']),3)


            # Search for oldest powerOn event in Event Log
            eventdate = provisionDateStamp
            powerOnDateStamp = provisionDateStamp
            found=0
            logging.warning('Getting POWERON detail for guestId %s.' % (guestId))
            events=""
            try:
                time.sleep(1)
                events = client['Event_Log'].getAllObjects(mask="objectId,eventName,eventCreateDate",filter={'objectId': {'operation': guestId},
                                                         'eventName': {'operation': 'Power On'}})
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

            # FORMAT DATE & TIME STAMPS AND DELTAS FOR CSV
            createDate=datetime.strftime(createDateStamp,"%Y-%m-%d")
            createTime=datetime.strftime(createDateStamp,"%H:%M:%S")
            provisionDate=datetime.strftime(provisionDateStamp,"%Y-%m-%d")
            provisionTime=datetime.strftime(provisionDateStamp,"%H:%M:%S")
            provisionDelta=convert_timedelta(provisionDateStamp-createDateStamp)

            # Calculate poweron if found
            if found==1:
                powerOnDate=datetime.strftime(powerOnDateStamp,"%Y-%m-%d")
                powerOnTime=datetime.strftime(powerOnDateStamp,"%H:%M:%S")
                powerOnDelta=convert_timedelta(powerOnDateStamp-createDateStamp)
            else:
                powerOnDate="Not Found"
                powerOnTime="Not Found"
                logging.warning('POWERON detail for guestId %s NOT FOUND.' % (guestId))
                powerOnDelta=0

            if cancellationDateStamp=="Running":
                cancellationDate="Running"
                cancellationTime="Running"
            else:
                cancellationDate=datetime.strftime(cancellationDateStamp,"%Y-%m-%d")
                cancellationTime=datetime.strftime(cancellationDateStamp,"%H:%M:%S")

            # Create CSV Record
            logging.warning('Writting record for InvoiceId %s, BillingItemId %s, GuestId %s.' % (invoiceID, billingItemId, guestId))
            row = {'InvoiceID': invoiceID,
                   'BillingItemId': billingItemId,
                   'TransactionID': guestId,
                   'Datacenter': location,
                   'Product': product,
                   'Cores': cores,
                   'OS': os,
                   'Memory': memory,
                   'Disk': disk,
                   'Hostname': hostName,
                   'CreateDate': createDate,
                   'CreateTime': createTime,
                   'PowerOnDate': powerOnDate,
                   'PowerOnTime': powerOnTime,
                   'PowerOnDelta': powerOnDelta,
                   'ProvisionedDate': provisionDate,
                   'ProvisionedTime': provisionTime,
                   'ProvisionedDelta': provisionDelta,
                   'CancellationDate': cancellationDate,
                   'CancellationTime': cancellationTime,
                   'HoursUsed': hoursUsed,
                   'HourlyRecurringFee': hourlyRecurringFee,
                   }

            csvwriter.writerow(row)

##close CSV File
logging.info('Finished %s NEW/ONE-TIME Invoices between %s and %s.' % (len(InvoiceList),startdate,enddate))
outfile.close()