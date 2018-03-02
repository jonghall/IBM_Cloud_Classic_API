__author__ = 'jonhall'
#
## Get Current Invoices
## Place APIKEY & Username in config.ini
## or pass via commandline  (example: GetRecurringInvoices.py -u=userid -k=apikey)
##

import sys, getopt, socket, SoftLayer, json, string, configparser, os, argparse, csv,logging,time

def getDescription(categoryCode, detail):
    for item in detail:
        if 'categoryCode' in item:
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
        client = SoftLayer.Client(username=user, api_key=key)
    return client


## READ CommandLine Arguments and load configuration file
parser = argparse.ArgumentParser(description="Print a report of Recurring invoices sorted by Hourly vs Monthly between Start and End date.")
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


fieldnames = ['Invoice_Date', 'Invoice_Number', 'BillingItemId', 'InstanceType', 'hostName', 'Category', 'Description',
             'Hours', 'Hourly_Rate', 'RecurringCharge', 'InvoiceTotal', 'InvoiceRecurring', 'Type']
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


print ()
print ('{:<35} {:<30} {:>8} {:>16} {:>16} {:>16} {:<15}'.format("Invoice Date /", "Invoice Number /", " ", "Items", "Recurring Charge",  "Invoice Amount", "Type"))
print ('{:<35} {:<30} {:>8} {:>16} {:>16} {:>16} {:<15}'.format("==============", "================", " ", "=====", "================",  "==============", "===="))
for invoice in InvoiceList:
    invoiceID = invoice['id']
    invoiceInfo = client['Billing_Invoice'].getObject(id=invoiceID,mask="id,createDate,typeCode,invoiceTotalAmount,invoiceTotalRecurringAmount,invoiceTopLevelItemCount")
    invoiceDate = invoiceInfo['createDate'][0:10]
    invoiceTotalAmount = float(invoiceInfo['invoiceTotalAmount'])
    invoiceTotalRecurringAmount = float(invoiceInfo['invoiceTotalRecurringAmount'])
    invoiceType = invoiceInfo['typeCode']
    totalItems=invoiceInfo['invoiceTopLevelItemCount']

    # PRINT INVOICE SUMMARY LINE
    print('{:35} {:<30} {:>8} {:>16} {:>16,.2f} {:>16,.2f} {:<15}'.format(invoiceDate,
                                                                          invoiceInfo['id'], " ",
                                                                          totalItems,
                                                                          invoiceTotalAmount,
                                                                          invoiceTotalRecurringAmount, invoiceType))

    limit = 10 ## set limit of record t
    for offset in range(0,totalItems,limit):
        print ("Lookup at Offset %s" % offset)
        time.sleep(1)
        Billing_Invoice = client['Billing_Invoice'].getInvoiceTopLevelItems(id=invoiceID, limit=limit, offset=offset,
                                mask='id, billingItemId, categoryCode, hostName, domainName, description, createDate, totalRecurringAmount,hourlyRecurringFee')
        count=0
        # ITERATE THROUGH DETAIL
        for item in Billing_Invoice:
            billingItemId = item['billingItemId']
            category = item["categoryCode"]

            if 'hostName' in item:
                hostName = item['hostName']+"."+item['domainName']
            else:
                hostName = "Unnamed Device"

            recurringFee = float(item['totalRecurringAmount'])

            #IF Monthly calculate hourly rate and total hours
            if 'hourlyRecurringFee' in item:
                instanceType = "Hourly"
                associated_children=""
                while associated_children is "":
                    try:
                        time.sleep(0.5)
                        associated_children = client['Billing_Invoice_Item'].getNonZeroAssociatedChildren(id=item['id'],mask="hourlyRecurringFee")
                    except SoftLayer.SoftLayerAPIError as e:
                        logging.warning("getNonZeroAssociatedChildren(): %s, %s" % (e.faultCode, e.faultString))
                        time.sleep(5)
                #calculate total hourlyRecurringFree from associated childrent

                hourlyRecurringFee = float(item['hourlyRecurringFee']) + sum(float(child['hourlyRecurringFee']) for child in associated_children)
                if hourlyRecurringFee > 0:
                    hours = round(float(recurringFee) / hourlyRecurringFee)
                else:
                    hours=0
            else:
                instanceType = "Monthly/Other"
                hourlyRecurringFee = 0
                hours = 0

            if category=="storage_service_enterprise" or category=="performance_storage_iscsi":
                billing_detail=""
                while billing_detail is "":
                    try:
                        time.sleep(1)
                        billing_detail = client['Billing_Invoice_Item'].getChildren(id=item['id'], mask="description,categoryCode,product")
                    except SoftLayer.SoftLayerAPIError as e:
                        logging.warning("%s, %s" % (e.faultCode, e.faultString))

                if category=="storage_service_enterprise":
                    iops=getDescription("storage_tier_level", billing_detail)
                    storage=getDescription("performance_storage_space",billing_detail)
                    snapshot=getDescription("storage_snapshot_space", billing_detail)
                    if snapshot=="Not Found":
                        description=storage+" "+iops+" "
                    else:
                        description=storage+" "+iops+" with "+snapshot
                else:
                    iops=getDescription("performance_storage_iops", billing_detail)
                    storage=getDescription("performance_storage_space", billing_detail)
                    description=storage+" "+iops
            else:
                description=item['description']
                description = description.replace('\n', " ")
            # BUILD CSV OUTPUT & WRITE ROW
            row = {'Invoice_Date': invoiceDate,
                   'Invoice_Number': invoiceID,
                   'BillingItemId': billingItemId,
                   'InstanceType': instanceType,
                   'hostName': hostName,
                   'Category': category,
                   'Description': description,
                   'Hours': hours,
                   'Hourly_Rate': round(hourlyRecurringFee,3),
                   'RecurringCharge': round(recurringFee,2),
                   'InvoiceTotal': invoiceTotalAmount,
                   'InvoiceRecurring': invoiceTotalRecurringAmount,
                   'Type': invoiceType
                    }
            csvwriter.writerow(row)
            print(row)
##close CSV File
outfile.close()