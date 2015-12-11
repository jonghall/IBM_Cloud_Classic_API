__author__ = 'jonhall'
#
## Get Current Invoices
## Place APIKEY & Username in config.ini
## or pass via commandline  (example: GetRecurringInvoices.py -u=userid -k=apikey)
##

import sys, getopt, socket, SoftLayer, json, string, configparser, os, argparse, csv

def initializeSoftLayerAPI(user, key, configfile):
    if user == None and key == None:
        if configfile != None:
            filename=args.config
        else:
            filename="config.ini"
        config = configparser.ConfigParser()
        config.read(filename)
        client = SoftLayer.Client(username=config['api']['username'], api_key=config['api']['apikey'],endpoint_url=SoftLayer.API_PRIVATE_ENDPOINT,timeout=240)
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
print ('{:<35} {:<30} {:>8} {:>16} {:>16} {:>16} {:<15}'.format("Invoice Date /", "Invoice Number /", " ", " ", "Recurring Charge",  "Invoice Amount", "Type"))
print ('{:<35} {:<30} {:>8} {:>16} {:>16} {:>16} {:<15}'.format("==============", "================", " ", " ", "================",  "==============", "===="))
for invoice in InvoiceList:
    invoiceID = invoice['id']
    Billing_Invoice = client['Billing_Invoice'].getObject(id=invoiceID, mask="invoiceTopLevelItemCount,invoiceTopLevelItems,invoiceTotalAmount,invoiceTotalRecurringAmount")
    if Billing_Invoice['invoiceTotalAmount'] > "0":
        invoiceTotalAmount=float(Billing_Invoice['invoiceTotalAmount'])
        invoiceTotalRecurringAmount=float(Billing_Invoice['invoiceTotalRecurringAmount'])
        invoiceType=Billing_Invoice['typeCode']
        count=0
        # PRINT INVOICE SUMMARY LINE
        print ('{:35} {:<30} {:>8} {:>16} {:>16,.2f} {:>16,.2f} {:<15}'.format(Billing_Invoice['createDate'][0:10], Billing_Invoice['id'], " ", " ", invoiceTotalAmount, invoiceTotalRecurringAmount, invoiceType))
        # ITERATE THROUGH DETAIL
        for item in Billing_Invoice['invoiceTopLevelItems']:
            count=count + 1
            billingItemId = item['billingItemId']
            print ("%s of %s" % (count, Billing_Invoice['invoiceTopLevelItemCount']), end='\r')
            category = item["categoryCode"]

            if 'hostName' in item:
                hostName = item['hostName']+"."+item['domainName']
            else:
                hostName = "Unnamed Device"

            recurringFee = float(client['Billing_Invoice_Item'].getTotalRecurringAmount(id=item['id']))

            #IF Monthly calculate hourly rate and total hours
            if 'hourlyRecurringFee' in item:
                instanceType = "Hourly"
                associated_children = client['Billing_Invoice_Item'].getNonZeroAssociatedChildren(id=item['id'],mask="hourlyRecurringFee")
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

            description=item['description']
            description = description.replace('\n', " ")
            # BUILD CSV OUTPUT & WRITE ROW
            row = {'Invoice_Date': Billing_Invoice['createDate'][0:10],
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
##close CSV File
outfile.close()