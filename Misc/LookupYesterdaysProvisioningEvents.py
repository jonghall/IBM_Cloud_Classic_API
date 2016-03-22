import sys, getopt, socket, time,  SoftLayer, json, string, configparser, os, argparse, csv, math, pytz
from datetime import datetime, timedelta, tzinfo

import sendgrid


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
parser = argparse.ArgumentParser(description="Check Audit Log for VSI.")
parser.add_argument("-u", "--username", help="SoftLayer API Username")
parser.add_argument("-k", "--apikey", help="SoftLayer APIKEY")
parser.add_argument("-c", "--config", help="config.ini file to load")
parser.add_argument("-o", "--output", help="Outputfile")
parser.add_argument("-d", "--date", help="Date to check.")
args = parser.parse_args()

client = initializeSoftLayerAPI(args.username, args.apikey, args.config)

if args.date == None:
    yesterday = datetime.now() - timedelta(days=1)
else:
    yesterday=datetime.strptime(args.date+" 0:0:0","%m/%d/%Y %H:%M:%S")

startdate = datetime.strftime(yesterday, "%m/%d/%Y") + " 0:0:0"
enddate = datetime.strftime(yesterday,"%m/%d/%Y") + " 23:59:59"

if args.output == None:
    outputname="daily"+datetime.strftime(yesterday, "%m%d%Y")+".csv"
else:
    outputname=args.output

# DEFINE SENDGRID DETAILS FOR OUTPUT
emailto = ['Name#1 <email1@us.ibm.com>','Name#2 <email2@us.ibm.com>']
emailfrom = "From <from@us.ibm.com>"
sendgridkey = "apikey"

print ('%s Running Daily Provisioning Report for %s.' % (datetime.strftime(datetime.now(),"%m/%d/%Y %H:%M:%S"),datetime.strftime(yesterday, "%m/%d/%Y")))

distfields = ['Date','Requested', 'NotAllocated', 'NA', 'Reason', '0to30', '31-60', '61-90', '91-120', 'gt120']

fieldnames = ['InvoiceId', 'BillingItemId', 'GuestId', 'Datacenter', 'Product', 'Cores', 'Memory', 'Disk', 'OS', 'Hostname',
              'CreateDate', 'CreateTime', 'PowerOnDate', 'PowerOnTime', 'PowerOnDelta', 'ProvisionedDate',
              'ProvisionedTime', 'ProvisionedDelta']

outfile = open(outputname, 'w')
csvwriter = csv.DictWriter(outfile, delimiter=',', fieldnames=fieldnames)
csvwriter.writerow(dict((fn, fn) for fn in fieldnames))

## OPEN CSV FILE TO READ LIST OF SERVERS


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


provisionRequests=0
provisionRequestsgt30=0
provisionrequestsgt30dict=[]
powerOnNotFound=0
timedistributiongt0=0
timedistributiongt30=0
timedistributiongt60=0
timedistributiongt90=0
timedistributiongt120=0

for invoice in InvoiceList:
    invoiceID = invoice['id']
    invoicedetail=""
    print ('%s Looking up InvoiceId %s.' % (datetime.strftime(datetime.now(),"%m/%d/%Y %H:%M:%S"),invoiceID))
    while invoicedetail is "":
        try:
            time.sleep(1)
            invoicedetail = client['Billing_Invoice'].getObject(id=invoiceID, mask="closedDate, invoiceTopLevelItems, invoiceTopLevelItems.product,invoiceTopLevelItems.location")
        except SoftLayer.SoftLayerAPIError as e:
            print("Billing_Invoice::getObject: %s, %s" % (e.faultCode, e.faultString))
            time.sleep(5)

    invoiceTopLevelItems=invoicedetail['invoiceTopLevelItems']
    invoiceDate=convert_timestamp(invoicedetail["closedDate"])
    for item in invoiceTopLevelItems:
        if item['categoryCode']=="guest_core":
            provisionRequests=provisionRequests+1
            itemId = item['id']
            billingItemId = item['billingItemId']
            location=item['location']['name']
            hostName = item['hostName']+"."+item['domainName']
            createDateStamp = convert_timestamp(item['createDate'])
            product=item['description']
            cores=""
            billing_detail=""
            print ('%s Looking up billing Invoice Item for %s.' % (datetime.strftime(datetime.now(),"%m/%d/%Y %H:%M:%S"),itemId))
            while billing_detail is "":
                try:
                    time.sleep(1)
                    billing_detail = client['Billing_Invoice_Item'].getFilteredAssociatedChildren(id=itemId)
                except SoftLayer.SoftLayerAPIError as e:
                    print("Billing_Invoice_Item::getFilteredAssociatedChildren: %s, %s" % (e.faultCode, e.faultString))
                    time.sleep(5)

            os=getDescription("os", billing_detail)
            memory=getDescription("ram", billing_detail)
            disk=getDescription("guest_disk0", billing_detail)


            if 'product' in item:
                product=item['product']['description']
                cores=item['product']['totalPhysicalCoreCount']

            billingInvoiceItem=""
            print ('%s Searching for provisioning detail for billing Item for %s.' % (datetime.strftime(datetime.now(),"%m/%d/%Y %H:%M:%S"),itemId))
            while billingInvoiceItem is "":
                try:
                   time.sleep(1)
                   billingInvoiceItem = client['Billing_Invoice_Item'].getBillingItem(id=itemId, mask="cancellationDate, provisionTransaction")
                except SoftLayer.SoftLayerAPIError as e:
                   print("Billing_Invoice_Item::getBillingItem: %s, %s" % (e.faultCode, e.faultString))
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

            eventdate = provisionDateStamp
            powerOnDateStamp = provisionDateStamp
            found=0

            print ('%s Searching event Log for POWERON detail for guestId %s.' % (datetime.strftime(datetime.now(),"%m/%d/%Y %H:%M:%S"),guestId))
            # GET OLDEST POWERON EVENT FROM EVENTLOG FOR GUESTID AS INITIAL RESOURCE ALLOCATION TIMESTAMP

            events=""
            try:
                time.sleep(1)
                events = client['Event_Log'].getAllObjects(mask="objectId,eventName,eventCreateDate",filter={'objectId': {'operation': guestId},
                                                         'eventName': {'operation': 'Power On'}})
            except SoftLayer.SoftLayerAPIError as e:
                print("Event_Log::getAllObjects: %s, %s" % (e.faultCode, e.faultString))

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
                print ('%s POWERON detail for guestId %s FOUND.' % (datetime.strftime(datetime.now(),"%m/%d/%Y %H:%M:%S"),guestId))
                powerOnDate=datetime.strftime(powerOnDateStamp,"%Y-%m-%d")
                powerOnTime=datetime.strftime(powerOnDateStamp,"%H:%M:%S")
                powerOnDelta=convert_timedelta(powerOnDateStamp-createDateStamp)
                if powerOnDelta>30:
                    provisionRequestsgt30=provisionRequestsgt30+1
                    provisionrequestsgt30dict.append({
                            'invoiceID': invoiceID,
                            'billingItemId': billingItemId,
                            'guestId': guestId,
                            'powerOnDelta': powerOnDelta
                    })

            else:
                print ('%s POWERON detail for guestId %s NOT FOUND.' % (datetime.strftime(datetime.now(),"%m/%d/%Y %H:%M:%S"),guestId))
                powerOnDate="Not Found"
                powerOnTime="Not Found"
                powerOnDelta=0
                powerOnNotFound=powerOnNotFound+1

            row = {'InvoiceId': invoiceID,
                   'BillingItemId': billingItemId,
                   'GuestId': guestId,
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
                   'ProvisionedDelta': provisionDelta
                   }
            csvwriter.writerow(row)
            # Create Provisioning Time Distirbution
            if provisionDelta>=121:
                timedistributiongt120=timedistributiongt120+1
            elif provisionDelta>=91:
                timedistributiongt90=timedistributiongt90+1
            elif provisionDelta>=61:
                timedistributiongt60=timedistributiongt60+1
            elif provisionDelta>=31:
                timedistributiongt30=timedistributiongt30+1
            elif provisionDelta>0:
                timedistributiongt0=timedistributiongt0+1

            print ('%s Added Invoice %s GuestId %s to CSV file.' % (datetime.strftime(datetime.now(),"%m/%d/%Y %H:%M:%S"), invoiceID, guestId))


##close CSV File
outfile.close()

# FORMAT & SEND EMAIL VIA SENDGRID ACCOUNT
sg = sendgrid.SendGridClient(sendgridkey)
message = sendgrid.Mail()
message.add_to(emailfrom)
message.set_subject('Daily Provisioning Report')
body=('<style>table, th, td {border: 1px solid black;}</style><p>Provisioning detail for %s.<br/>Total Provisioning Requests = %s.<br/>' \
      'PowerOn events exceeding 30 minutes = %s.<br/>PowerOn events Not Found = %s.</p>' \
       % (datetime.strftime(yesterday, "%m/%d/%Y"),provisionRequests, provisionRequestsgt30,powerOnNotFound))

body=body+('<p>Time Distribution Export<br><table width="200"><tr>' \
           '<th>Date</th><th>Requested</th><th>NotAllocated</th><th>0to30</th><th>31-60</th><th>61-90</th><th>91-120</th><th>gt120</th></tr>' \
           '<td style="text-align: center;">%s</td><td style="text-align: center;">%s</dh><td style="text-align: center;">%s</td>' \
           '<td style="text-align: center;">%s</td><td style="text-align: center;">%s</td><td style="text-align: center;">%s</td>' \
           '<td style="text-align: center;">%s</td><td style="text-align: center;">%s</td></tr></table></p>'
            % (datetime.strftime(yesterday, "%d-%b"),provisionRequests,provisionRequestsgt30,timedistributiongt0,timedistributiongt30,timedistributiongt60,timedistributiongt90,timedistributiongt120))

if provisionRequestsgt30>0:
            body=body+('<table width="600"><tr><th>%s</th><th>%s</th><th>%s</th><th>%s</th></tr>' % ("InvoiceID","BillingItemId","GuestId", "PowerOnDelta"))
            for list in provisionrequestsgt30dict:
                body=body+('<tr><td style="text-align: center;">%s</td><td style="text-align: center;">%s</td><td style="text-align: center;">%s</td><td style="text-align: center;">%s</td></tr>' % (list['invoiceID'],list['billingItemId'],list['guestId'],list['powerOnDelta']))
            body=body+"</table>"

message.set_html(body)
message.set_from(emailfrom)
message.add_attachment(outputname, './'+outputname)
status, msg = sg.send(message)

print ('%s Sending Daily Provisioning Report for %s.' % (datetime.strftime(datetime.now(),"%m/%d/%Y %H:%M:%S"),datetime.strftime(yesterday, "%m/%d/%Y")))
