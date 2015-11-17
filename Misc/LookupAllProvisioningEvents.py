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

fieldnames = ['InvoiceID','ID', 'Hostname', 'CreateDate', 'CreateTime', 'PowerOnDate', 'PowerOnTime', 'PowerOnDelta', 'ProvisionedDate', 'ProvisionedTime', 'ProvisionedDelta']

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
    invoiceTopLevelItems = client['Billing_Invoice'].getInvoiceTopLevelItems(id=invoiceID)
    # GET associated items for recurring and onetime totals per Top Level TIem
    for item in invoiceTopLevelItems:
        if item["categoryCode"]=="guest_core":
            #print (json.dumps(item,indent=4))
            invoiceDate=convert_timestamp(item["invoice"]["closedDate"])
            hostName = item['hostName']+"."+item['domainName']
            createDate = convert_timestamp(item['createDate'])
            billingItemId = item['id']
            #SoftLayer_Billing_Invoice_Item::getBillingItem
            billingInvoiceItem = client['Billing_Invoice_Item'].getBillingItem(id=billingItemId, mask="provisionTransaction")
            provisionTransaction = billingInvoiceItem['provisionTransaction']
            #print (json.dumps(billingInvoiceItem,indent=4))
            provisionId = provisionTransaction['id']
            guestId = provisionTransaction['guestId']
            provisionDate = convert_timestamp(provisionTransaction['modifyDate'])
            #print ("HostName %s" % (hostName))
            #print ("InvoiceDate %s " % (invoiceDate))
            #print ("CreateDate %s" % (createDate))
            #print ("provisionDate %s" % (provisionDate))

            eventdate = provisionDate
            powerOnDate = provisionDate

            found=0

            events = client['Event_Log'].getAllObjects(filter={'objectId': {'operation': guestId},
                                                             'eventName': {'operation': 'Power On'}})
            for event in events:
                print (json.dumps(event,indent=4))
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
                   'Hostname': hostName,
                   'CreateDate': datetime.strftime(createDate,"%Y-%m-%d"),
                   'CreateTime': datetime.strftime(createDate,"%H:%M:%S%z"),
                   'PowerOnDate': datetime.strftime(powerOnDate,"%Y-%m-%d"),
                   'PowerOnTime': datetime.strftime(powerOnDate,"%H:%M:%S%z"),
                   'PowerOnDelta': convert_timedelta(powerOnDate-createDate),
                   'ProvisionedDate': datetime.strftime(provisionDate,"%Y-%m-%d"),
                   'ProvisionedTime': datetime.strftime(provisionDate,"%H:%M:%S%z"),
                   'ProvisionedDelta': convert_timedelta(provisionDate-createDate)
                   }
                print (json.dumps(row,indent=4))
                csvwriter.writerow(row)
            else:
                row = {'InvoiceID': invoiceID,
                   'ID': guestId,
                   'Hostname': hostName,
                   'CreateDate': datetime.strftime(createDate,"%Y-%m-%d"),
                   'CreateTime': datetime.strftime(createDate,"%H:%M:%S%z"),
                   'PowerOnDate': 'Not Available',
                   'PowerOnTime': 'Not Available',
                   'PowerOnDelta': convert_timedelta(powerOnDate-createDate),
                   'ProvisionedDate': datetime.strftime(provisionDate,"%Y-%m-%d"),
                   'ProvisionedTime': datetime.strftime(provisionDate,"%H:%M:%S%z"),
                   'ProvisionedDelta': convert_timedelta(provisionDate-createDate)
                   }
                print (json.dumps(row,indent=4))
                csvwriter.writerow(row)
##close CSV File
outfile.close()