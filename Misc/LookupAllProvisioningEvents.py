import sys, getopt, socket, time,  SoftLayer, json, string, configparser, os, argparse, csv
from datetime import datetime, timedelta, tzinfo
import pytz

def convert_timedelta(duration):
    seconds = duration.seconds
    minutes = round((seconds / 60),2)
    return minutes

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
        client = SoftLayer.Client(username=config['api']['username'], api_key=config['api']['apikey'],endpoint_url=SoftLayer.API_PRIVATE_ENDPOINT)
    else:
        #client = SoftLayer.Client(username=config['api']['username'], api_key=config['api']['apikey'],endpoint_url=SoftLayer.API_PRIVATE_ENDPOINT)
        client = SoftLayer.Client(username=user, api_key=key)
    return client


#
# Get APIKEY from config.ini & initialize SoftLayer API
#


## READ CommandLine Arguments and load configuration file
parser = argparse.ArgumentParser(description="Check Audit Log for VSI.")
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

fieldnames = ['InvoiceID','ID', 'Datacenter', 'Product', 'Cores', 'Memory', 'Disk', 'OS', 'Hostname', 'CreateDate', 'CreateTime', 'PowerOnDate', 'PowerOnTime', 'PowerOnDelta', 'ProvisionedDate', 'ProvisionedTime', 'ProvisionedDelta']

outfile = open(outputname, 'w')
csvwriter = csv.DictWriter(outfile, delimiter=',', fieldnames=fieldnames)
csvwriter.writerow(dict((fn, fn) for fn in fieldnames))
## OPEN CSV FILE TO READ LIST OF SERVERS

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



for invoice in InvoiceList:
    invoiceID = invoice['id']
    invoicedetail=""
    while invoicedetail is "":
        try:
            invoicedetail = client['Billing_Invoice'].getObject(id=invoiceID, mask="closedDate, invoiceTopLevelItems, invoiceTopLevelItems.product,invoiceTopLevelItems.location")
        except SoftLayer.SoftLayerAPIError as e:
            print("Error: %s, %s" % (e.faultCode, e.faultString))
            time.sleep(5)

    #print (json.dumps(invoicedetail,indent=4))

    # GET associated items for recurring and onetime totals per Top Level TIem
    #print (json.dumps(invoicedetail,indent=4))
    invoiceTopLevelItems=invoicedetail['invoiceTopLevelItems']
    invoiceDate=convert_timestamp(invoicedetail["closedDate"])
    for item in invoiceTopLevelItems:
        if item['categoryCode']=="guest_core":
            billingItemId = item['id']
            location=item['location']['name']
            hostName = item['hostName']+"."+item['domainName']
            createDate = convert_timestamp(item['createDate'])
            product=item['description']
            cores=""
            billing_detail=""
            while billing_detail is "":
                try:
                    billing_detail = client['Billing_Invoice_Item'].getFilteredAssociatedChildren(id=billingItemId)
                except SoftLayer.SoftLayerAPIError as e:
                    print("Error: %s, %s" % (e.faultCode, e.faultString))
                    time.sleep(5)
            os=getDescription("os", billing_detail)
            memory=getDescription("ram", billing_detail)
            disk=getDescription("guest_disk0", billing_detail)

            if 'product' in item:
                product=item['product']['description']
                cores=item['product']['totalPhysicalCoreCount']

            billingInvoiceItem=""
            while billingInvoiceItem is "":
                try:
                   billingInvoiceItem = client['Billing_Invoice_Item'].getBillingItem(id=billingItemId, mask="provisionTransaction")
                except SoftLayer.SoftLayerAPIError as e:
                   print("Error: %s, %s" % (e.faultCode, e.faultString))
                   time.sleep(5)

            if 'provisionTransaction' in billingInvoiceItem:
                provisionTransaction = billingInvoiceItem['provisionTransaction']
                provisionId = provisionTransaction['id']
                guestId = provisionTransaction['guestId']
                provisionDate = convert_timestamp(provisionTransaction['modifyDate'])
            else:
                provisionTransaction = "0"
                provisionId = "0"
                guestId = "0"
                provisionDate = convert_timestamp(item['createDate'])

            eventdate = provisionDate
            powerOnDate = provisionDate

            found=0

            # GET OLDEST POWERON EVENT FROM EVENTLOG FOR GUESTID AS INITIAL RESOURCE ALLOCATION TIMESTAMP
            events = client['Event_Log'].getAllObjects(filter={'objectId': {'operation': guestId},
                                                             'eventName': {'operation': 'Power On'}})
            for event in events:
                #print (json.dumps(event,indent=4))
                if event['eventName']=="Power On":
                    eventdate = event["eventCreateDate"]
                    eventdate = eventdate[0:29]+eventdate[-2:]
                    eventdate = datetime.strptime(eventdate, "%Y-%m-%dT%H:%M:%S.%f%z")
                    if eventdate<powerOnDate:
                        powerOnDate = eventdate
                        found=1

            if found==1:
                row = {'InvoiceID': invoiceID,
                   'ID': guestId,
                   'Datacenter': location,
                   'Product': product,
                   'Cores': cores,
                   'OS': os,
                   'Memory': memory,
                   'Disk': disk,
                   'Hostname': hostName,
                   'CreateDate': datetime.strftime(createDate,"%Y-%m-%d"),
                   'CreateTime': datetime.strftime(createDate,"%H:%M:%S"),
                   'PowerOnDate': datetime.strftime(powerOnDate,"%Y-%m-%d"),
                   'PowerOnTime': datetime.strftime(powerOnDate,"%H:%M:%S"),
                   'PowerOnDelta': convert_timedelta(powerOnDate-createDate),
                   'ProvisionedDate': datetime.strftime(provisionDate,"%Y-%m-%d"),
                   'ProvisionedTime': datetime.strftime(provisionDate,"%H:%M:%S"),
                   'ProvisionedDelta': convert_timedelta(provisionDate-createDate)
                   }
                print(json.dumps(row))
                csvwriter.writerow(row)
            else:
                row = {'InvoiceID': invoiceID,
                   'ID': guestId,
                   'Datacenter': location,
                   'Product': product,
                   'Cores': cores,
                   'OS': os,
                   'Memory': memory,
                   'Disk': disk,
                   'Hostname': hostName,
                   'CreateDate': datetime.strftime(createDate,"%Y-%m-%d"),
                   'CreateTime': datetime.strftime(createDate,"%H:%M:%S"),
                   'PowerOnDate': 'Not Available',
                   'PowerOnTime': 'Not Available',
                   'PowerOnDelta': '0',
                   'ProvisionedDate': datetime.strftime(provisionDate,"%Y-%m-%d"),
                   'ProvisionedTime': datetime.strftime(provisionDate,"%H:%M:%S"),
                   'ProvisionedDelta': convert_timedelta(provisionDate-createDate)
                   }
                print(json.dumps(row))
                csvwriter.writerow(row)
##close CSV File
outfile.close()