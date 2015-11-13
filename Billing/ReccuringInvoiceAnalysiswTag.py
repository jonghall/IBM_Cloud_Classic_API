__author__ = 'jonhall'
#
## Get Current Invoices
## Place APIKEY & Username in config.ini
## or pass via commandline  (example: GetRecurringInvoices.py -u=userid -k=apikey)
##

import sys, getopt, socket, SoftLayer, json, string, configparser, os, argparse, csv



def initializeSoftLayerAPI():
    ## READ CommandLine Arguments and load configuration file
    parser = argparse.ArgumentParser(description="Print a report of Recurring invoices sorted by Hourly vs Monthly between Start and End date.")
    parser.add_argument("-u", "--username", help="SoftLayer API Username")
    parser.add_argument("-k", "--apikey", help="SoftLayer APIKEY")
    parser.add_argument("-c", "--config", help="config.ini file to load")

    args = parser.parse_args()

    if args.config != None:
        filename=args.config
    else:
        filename="config.ini"

    if (os.path.isfile(filename) is True) and (args.username == None and args.apikey == None):
        ## Read APIKEY from configuration file
        config = configparser.ConfigParser()
        config.read(filename)
        client = SoftLayer.Client(username=config['api']['username'], api_key=config['api']['apikey'])
    else:
        ## Read APIKEY from commandline arguments
        if args.username == None and args.apikey == None:
            print ("You must specify a username and APIkey to use.")
            quit()
        if args.username == None:
            print ("You must specify a username with your APIKEY.")
            quit()
        if args.apikey == None:
            print("You must specify a APIKEY with the username.")
            quit()
        client = SoftLayer.Client(username=args.username, api_key=args.apikey)
    return client


#
# Get APIKEY from config.ini & initialize SoftLayer API
#

client = initializeSoftLayerAPI()



#
# GET LIST OF INVOICES
#
print ()

startdate=input("Report Start Date (MM/DD/YYYY): ")
enddate=input("Report End Date (MM/DD/YYYY): ")
outputname=input("CSV Filename: ")

outfile = open(outputname, 'w')
csvwriter = csv.writer(outfile, delimiter='\t', quotechar='"', quoting=csv.QUOTE_ALL)


fieldnames = ['Invoice_Date', 'Invoice_Number', 'InstanceType', 'hostName', 'Category', 'Tag', 'Description',
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
        count=0
        # PRINT INVOICE SUMMARY LINE
        print ('{:35} {:<30} {:>8} {:>16} {:>16,.2f} {:>16,.2f} {:<15}'.format(Billing_Invoice['createDate'][0:10], Billing_Invoice['id'], " ", " ", float(Billing_Invoice['invoiceTotalAmount']), float(Billing_Invoice['invoiceTotalRecurringAmount']), Billing_Invoice['typeCode']))

        # ITERATE THROUGH DETAIL
        for item in Billing_Invoice['invoiceTopLevelItems']:
            count=count + 1
            print ("%s of %s" % (count, Billing_Invoice['invoiceTopLevelItemCount']), end='\r')
            category = item["categoryCode"]

            if 'hostName' in item:
                hostName = item['hostName']+"."+item['domainName']
            else:
                hostName = "Unnamed Device"

            tags == client['Tag'].getObject(id=item['billingid'])

            if category == "performance_storage_iscsi" or category == "storage_service_enterprise" or category == "Network Attached Storageq0":
                   #SoftLayer_Billing_Item_Network_PerformanceStorage_Iscsi
                    storage = client["SoftLayer_Network_Storage"].getObject(id=item["billingItemId"])
                    print (json.dumps(storage,ident=4))
                    quit()

            if 'hourlyRecurringFee' in item:
                instanceType = "Hourly"
                recurringFee = float(client['Billing_Invoice_Item'].getTotalRecurringAmount(id=item['id']))
                associated_children = client['Billing_Invoice_Item'].getNonZeroAssociatedChildren(id=item['id'],mask="hourlyRecurringFee")
                hourlyRecurringFee = float(item['hourlyRecurringFee']) + sum(float(child['hourlyRecurringFee']) for child in associated_children)
                hours = round(float(item['recurringFee']) / hourlyRecurringFee)
            else:
                instanceType = "Monthly/Other"
                hourlyRecurringFee = 0
                Hourly_Rate = 0
                hours = 0
                recurringFee = float(client['Billing_Invoice_Item'].getTotalRecurringAmount(id=item['id']))

            description=item['description']
            description = description.replace('\n', " ")
            # BUILD CSV OUTPUT & WRITE ROW
            row = {'Invoice_Date': Billing_Invoice['createDate'][0:10],
                   'Invoice_Number': invoiceID,
                   'InstanceType': instanceType,
                   'hostName': hostName,
                   'Category': category,
                   'Tag': tag,
                   'Description': description,
                   'Hours': hours,
                   'Hourly_Rate': round(hourlyRecurringFee,3),
                   'RecurringCharge': round(recurringFee,2),
                   'InvoiceTotal': float(Billing_Invoice['invoiceTotalAmount']),
                   'InvoiceRecurring': float(Billing_Invoice['invoiceTotalRecurringAmount']),
                   'Type': Billing_Invoice['typeCode']
                    }
            csvwriter.writerow(row)

##close CSV File
outfile.close()



