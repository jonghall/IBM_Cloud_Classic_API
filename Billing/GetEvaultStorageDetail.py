__author__ = 'jonhall'
#
## Get eVault Storage detail
## Place APIKEY & Username in config.ini
## or pass via commandline  (example: GetRecurringInvoices.py -u=userid -k=apikey)
##

import SoftLayer, configparser, argparse, csv,logging,time

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
        client = SoftLayer.Client(username=config['api']['username'], api_key=config['api']['apikey'],timeout=240)
    else:
        client = SoftLayer.Client(username=user, api_key=key,timeout=120)
    return client


## READ CommandLine Arguments and load configuration file
parser = argparse.ArgumentParser(description="Report of deailed eVault allocations.")
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


#
# GET LIST OF INVOICES
#


outfile = open(outputname, 'w')
csvwriter = csv.writer(outfile, delimiter='\t', quotechar='"', quoting=csv.QUOTE_ALL)


fieldnames = ['Invoice_Date', 'Invoice_Number', 'BillingItemId', 'Allocation_Date', 'StorageType',
              'evaultUser', 'evaultResource','ServerBackedUp', 'Cost']
csvwriter = csv.DictWriter(outfile, delimiter=',', fieldnames=fieldnames)
csvwriter.writerow(dict((fn, fn) for fn in fieldnames))

## OPEN CSV FILE FOR OUTPUT

print()
print("Looking up invoices....")

# Build Filter for Invoices
InvoiceList = client['Account'].getInvoices(filter={
        'invoices': {
            'createDate': {
                'operation': 'betweenDate',
                'options': [
                     {'name': 'startDate', 'value': [startdate+" 0:0:0"]},
                     {'name': 'endDate', 'value': [enddate+" 23:59:59"]}

                ]
            },
            'typeCode': {
                'operation': 'in',
                'options': [
                    {'name': 'data', 'value': ['RECURRING']}
                ]
                },
                    }
        })


for invoice in InvoiceList:
    invoiceID = invoice['id']
    Billing_Invoice=""
    while Billing_Invoice is "":
        try:
            time.sleep(1)
            Billing_Invoice = client['Billing_Invoice'].getObject(id=invoiceID, mask="invoiceTotalAmount, createDate, typeCode, invoiceTopLevelItems, invoiceTopLevelItems.product,invoiceTopLevelItems.location,invoiceTopLevelItems.totalRecurringAmount")
        except SoftLayer.SoftLayerAPIError as e:
            logging.warning("%s, %s" % (e.faultCode, e.faultString))

    if Billing_Invoice['invoiceTotalAmount'] > "0":
        invoiceType=Billing_Invoice['typeCode']
        invoiceDate=Billing_Invoice['createDate'][0:10]
        count=0
        for item in Billing_Invoice['invoiceTopLevelItems']:
            category = item["categoryCode"]
            storageType=item["product"]['description']
            totalRecurringAmount=item['totalRecurringAmount']
            count=count + 1
            if category=="evault":
                itemId = item['id']
                associatedInvoiceItemId = item['associatedInvoiceItemId']
                location=item['location']['name']
                product=item['description']
                billingItemId = item['billingItemId']
                resourceTableId= item['resourceTableId']
                #print(json.dumps(item,indent=4))

                #SoftLayer_Network_Storage_Iscsi::getObject
                resource_detail=""
                while resource_detail is "":
                    try:
                        time.sleep(1)
                        resource_detail = client['Network_Storage_Backup_Evault'].getObject(id=resourceTableId)
                    except SoftLayer.SoftLayerAPIError as e:
                        logging.warning("Network_Storage_Backup_Evault::getObject %s, %s" % (e.faultCode, e.faultString))
                        break
                if resource_detail=="":
                        resource_detail="none"
                else:
                    evaultUser=resource_detail['username']
                    evaultCapacity=resource_detail['capacityGb']
                    evaultAllocationDate=resource_detail['createDate'][0:10]
                    evaultResource=resource_detail['serviceResourceName']
                    evaultGuestId=resource_detail['guestId']
                    if 'guestId' in resource_detail:
                        guest = client['Virtual_Guest'].getObject(id=evaultGuestId,mask="hostname")
                        server=guest['hostname']
                    else:
                        guest = client['Hardware'].getObject(id=evaultGuestId,mask="hostname")
                        server=guest['hostname']


                    # BUILD CSV OUTPUT & WRITE ROW
                    row = {'Invoice_Date': invoiceDate,
                           'Allocation_Date': evaultAllocationDate,
                           'Invoice_Number': invoiceID,
                           'BillingItemId': billingItemId,
                           'StorageType': storageType,
                           'evaultUser': evaultUser,
                           'evaultResource': evaultResource,
                           'ServerBackedUp': server,
                           'Cost': totalRecurringAmount
                            }
                    csvwriter.writerow(row)
                    print(row)
##close CSV File
outfile.close()