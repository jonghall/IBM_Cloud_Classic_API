__author__ = 'jonhall'
#
## Get Current Invoices
## Place APIKEY & Username in config.ini
## or pass via commandline  (example: GetNewInvoices.py -u=userid -k=apikey)
##

import SoftLayer, json, configparser, argparse, csv


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


## READ CommandLine Arguments and load configuration file
parser = argparse.ArgumentParser(description="Print a report of NEW invoices which have a non zero balance between Start and End date.")
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


fieldnames = ['Invoice_Date', 'Invoice_Number', 'hostName', 'Category', 'Description',
              'RecurringCharge', 'OneTimeCharge', 'InvoiceTotalAmount', 'InvoiceTotalOneTimeAmount',
              'InvoiceTotalRecurringAmount', 'Type']
csvwriter = csv.DictWriter(outfile, delimiter=',', fieldnames=fieldnames)
csvwriter.writerow(dict((fn, fn) for fn in fieldnames))



print()
print("Looking up invoices....")

#topLevelCategories = client['Product_Item_Category'].getTopLevelCategories()
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


print ()
print ('{:<40} {:<40} {:>18} {:>16} {:>16} {:<16}'.format("Invoice Date /", "Invoice Number /", "Recurring Charges", "OneTime Charges", "Invoice Amount", "Type"))
print ('{:<40} {:<40} {:>18} {:>16} {:>16} {:<16}'.format("Hostname      ", "Description     ", "                 ", "               ", "              ", "    "))
print ('{:<40} {:<40} {:>18} {:>16} {:>16} {:<16}'.format("==============", "================", "=================", "===============", "==============", "===="))
for invoice in InvoiceList:
    invoiceID = invoice['id']
    if invoice['invoiceTotalAmount'] != "0":

        invoiceInfo = client['Billing_Invoice'].getObject(id=invoiceID,
                                     mask="id,createDate,typeCode,invoiceTotalAmount,invoiceTotalRecurringAmount,invoiceTotalOneTimeAmount,invoiceTopLevelItemCount")
        invoiceDate = invoiceInfo['createDate'][0:10]
        invoiceTotalAmount = float(invoiceInfo['invoiceTotalAmount'])
        invoiceTotalRecurringAmount = float(invoiceInfo['invoiceTotalRecurringAmount'])
        invoiceTotalOneTimeAmount = float(invoiceInfo['invoiceTotalOneTimeAmount'])
        invoiceType = invoiceInfo['typeCode']
        totalItems = invoiceInfo['invoiceTopLevelItemCount']

        # PRINT INVOICE SUMMARY LINE
        print('{:40} {:<40} {:>18,.2f} {:>16,.2f} {:>16,.2f} {:<16}'.format(invoiceDate,
                                                                            invoiceID,
                                                                            invoiceTotalAmount,
                                                                            invoiceTotalOneTimeAmount,
                                                                            invoiceTotalRecurringAmount,
                                                                            invoiceType))

        limit = 10  ## set limit of record t
        for offset in range(0, totalItems, limit):
            Billing_Invoice = client['Billing_Invoice'].getInvoiceTopLevelItems(id=invoiceID, limit=limit, offset=offset,
                                mask='id, billingItemId, categoryCode, hostName, domainName, description, createDate, recurringFee, oneTimeFee, totalRecurringAmount,hourlyRecurringFee')

            # GET associated items for recurring and onetime totals per Top Level TIem
            for item in Billing_Invoice:
                associated_children = client['Billing_Invoice_Item'].getAssociatedChildren(id=item['id'])
                recurringFee = float(item['recurringFee'])
                oneTimeFee = float(item['oneTimeFee'])
                for child in associated_children:
                     #print (json.dumps(item, indent=4))
                     recurringFee = recurringFee + float(child['recurringFee'])
                     oneTimeFee = oneTimeFee + float(child['oneTimeFee'])
                if 'hostName' in item:
                    hostName = item['hostName']+"."+item['domainName']
                else:
                    hostName = "Unnamed Device"


                # PRINT TOP LEVEL ITEMS DETAIL FOR  INVOICE
                if recurringFee >0 or oneTimeFee > 0:
                    category = item["categoryCode"]
                    #for topLevel in topLevelCategories:
                    #    if topLevel['categoryCode'] == category:
                    #        category = topLevel['name']
                    #        quit
                    print ('{:<40} {:<40} {:>18,.2f} {:>16,.2f}'.format(hostName[0:40], category[0:40], round(recurringFee,2), round(oneTimeFee,2)))
                    description=item['description']
                    description = description.replace('\n', " ")
                    # BUILD CSV OUTPUT & WRITE ROW
                    row = {'Invoice_Date': invoiceDate,
                           'Invoice_Number': invoiceID,
                           'hostName': hostName,
                           'Category': category,
                           'Description': description,
                           'RecurringCharge': round(recurringFee,2),
                           'OneTimeCharge': round(oneTimeFee,2),
                           'InvoiceTotalAmount': invoiceTotalAmount,
                           'InvoiceTotalOneTimeAmount': invoiceTotalOneTimeAmount,
                           'InvoiceTotalRecurringAmount': invoiceTotalRecurringAmount,
                           'Type': invoiceType
                            }
                    csvwriter.writerow(row)

        print()

##close CSV File
outfile.close()