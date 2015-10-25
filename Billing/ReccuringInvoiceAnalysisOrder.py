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
#startdate="10/01/2015"
#enddate="10/31/2015"
#outputname="test.csv"

outfile = open(outputname, 'w')
csvwriter = csv.writer(outfile, delimiter='\t', quotechar='"', quoting=csv.QUOTE_ALL)


fieldnames = ['Invoice_Date', 'Invoice_Number', 'InstanceType', 'hostName', 'Category', 'Description', "virtualCores",
              'physicalCores', 'memory', 'createDate', 'cancelationDate',
              'Hours', 'Hourly_Rate', 'RecurringCharge', 'InvoiceTotal', 'InvoiceRecurring', 'Type']
csvwriter = csv.DictWriter(outfile, delimiter=',', fieldnames=fieldnames)
csvwriter.writerow(dict((fn, fn) for fn in fieldnames))

## OPEN CSV FILE FOR OUTPUT



print()
print("Looking up invoices....")

# Build Filter for Invoices
InvoiceList = client['Account'].getInvoices(mask='createDate,typeCode, id, invoiceTotalAmount',filter={
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
            }
        }
    })


print ()
print ('{:<35} {:<30} {:>8} {:>16} {:>16} {:>16} {:<15}'.format("Invoice Date /", "Invoice Number /", " ", " ", "Recurring Charge",  "Invoice Amount", "Type"))
print ('{:<35} {:<30} {:>8} {:>16} {:>16} {:>16} {:<15}'.format("==============", "================", " ", " ", "================",  "==============", "===="))
for invoice in InvoiceList:
        invoiceID = invoice['id']
        if invoice['invoiceTotalAmount'] > "0":
            try:
                Billing_Invoice = client['Billing_Invoice'].getObject(id=invoiceID, mask="invoiceTopLevelItemCount,invoiceTopLevelItems,invoiceTopLevelItems.product,"
                                                                    "invoiceTotalAmount, invoiceTotalRecurringAmount",
                                                                    filter= {
                                                                        'invoices': {
                                                                                'categoryCode': {'operation': "guest_core"}
                                                                        }
                                                                    })
            except SoftLayer.SoftLayerAPIError as e:
                print("Error: %s, %s" % (e.faultCode, e.faultString))
                quit()

            # PRINT INVOICE SUMMARY LINE
            print ('{:35} {:<30} {:>8} {:>16} {:>16,.2f} {:>16,.2f} {:<15}'.format(Billing_Invoice['createDate'][0:10], Billing_Invoice['id'], " ", " ", float(Billing_Invoice['invoiceTotalAmount']), float(Billing_Invoice['invoiceTotalRecurringAmount']), Billing_Invoice['typeCode']))
            print ()
            print ('Analyzing Top Level Items from invoice....')
            # ITERATE THROUGH DETAIL
            count=0
            for item in Billing_Invoice['invoiceTopLevelItems']:
                count=count + 1
                print ("%s of %s" % (count, Billing_Invoice['invoiceTopLevelItemCount']), end='\r')
                category = item["categoryCode"]

                if 'hostName' in item:
                    hostName = item['hostName']+"."+item['domainName']
                else:
                    hostName = "Unnamed Device"

                # DETAILED ORDER/CANCEL INFORMATION
                billingItemId = item['billingItemId']

                try:
                    Billing_Item = client['Billing_Item'].getObject(id=billingItemId,
                                                                    mask="createDate,cycleStartDate,lastBillDate,cancellationDate,recurringMonths")
                except SoftLayer.SoftLayerAPIError as e:
                    print("Error: %s, %s" % (e.faultCode, e.faultString))
                    quit()

                createDate=Billing_Item['createDate']
                cycleStartDate=Billing_Item['cycleStartDate']
                cancelationDate=Billing_Item['cancellationDate']
                recurringMonths=Billing_Item['recurringMonths']
                description=item['description']
                description = description.replace('\n', " ")

                physicalCores = ""
                virtualCores = ""
                memory = ""

                if category == "server":
                    try:
                        getmemory = client['Billing_Invoice_Item'].getFilteredAssociatedChildren(id=item['id'],mask="id,product",
                                filter={'filteredAssociatedChildren': {'categoryCode': {'operation': '*=ram'}}})
                    except SoftLayer.SoftLayerAPIError as e:
                        print("Error: %s, %s" % (e.faultCode, e.faultString))
                        quit()
                    if 'product' in getmemory:
                            memory = getmemory[0]["product"]["capacity"]
                    if 'physicalCores' in item["product"]:
                        physicalCores = item["product"]["totalPhysicalCoreCount"]


                    speed = item["product"]["capacity"]
                    description = item["product"]["description"]

                if category == "guest_core":
                    virtualCores = item["product"]["capacity"]
                    description = item["product"]["description"]
                    try:
                        getmemory = client['Billing_Invoice_Item'].getFilteredAssociatedChildren(id=item['id'],mask="id,product",
                                filter={'filteredAssociatedChildren': {'categoryCode': {'operation': '*=ram'}}})
                    except SoftLayer.SoftLayerAPIError as e:
                        print("Error: %s, %s" % (e.faultCode, e.faultString))
                    memory = getmemory[0]["product"]["capacity"]


                if 'hourlyRecurringFee' in item:
                    instanceType = "Hourly"
                    try:
                        recurringFee = float(client['Billing_Invoice_Item'].getTotalRecurringAmount(id=item['id']))
                    except SoftLayer.SoftLayerAPIError as e:
                        print("Error: %s, %s" % (e.faultCode, e.faultString))
                    try:
                        associated_children = client['Billing_Invoice_Item'].getNonZeroAssociatedChildren(id=item['id'],mask="hourlyRecurringFee")
                    except SoftLayer.SoftLayerAPIError as e:
                        print("Error: %s, %s" % (e.faultCode, e.faultString))
                    hourlyRecurringFee = float(item['hourlyRecurringFee']) + sum(float(child['hourlyRecurringFee']) for child in associated_children)
                    hours = round(float(item['recurringFee']) / hourlyRecurringFee)
                else:
                    instanceType = "Monthly/Other"
                    hourlyRecurringFee = 0
                    Hourly_Rate = 0
                    hours = 0
                    try:
                        recurringFee = float(client['Billing_Invoice_Item'].getTotalRecurringAmount(id=item['id']))
                    except SoftLayer.SoftLayerAPIError as e:
                        print("Error: %s, %s" % (e.faultCode, e.faultString))



                # BUILD CSV OUTPUT & WRITE ROW
                row = {'Invoice_Date': Billing_Invoice['createDate'][0:10],
                       'Invoice_Number': invoiceID,
                       'InstanceType': instanceType,
                       'hostName': hostName,
                       'Category': category,
                       'Description': description,
                       'virtualCores': virtualCores,
                       'physicalCores': physicalCores,
                       'memory': memory,
                       'createDate': createDate,
                       'cancelationDate': cancelationDate,
                       'Hours': hours,
                       'Hourly_Rate': round(hourlyRecurringFee,3),
                       'RecurringCharge': round(recurringFee,2),
                       'InvoiceTotal': float(Billing_Invoice['invoiceTotalAmount']),
                       'InvoiceRecurring': float(Billing_Invoice['invoiceTotalRecurringAmount']),
                       'Type': Billing_Invoice['typeCode']
                        }
                csvwriter.writerow(row)
                client = initializeSoftLayerAPI()

##close CSV File
outfile.close()



