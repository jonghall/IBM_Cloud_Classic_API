__author__ = 'jonhall'
#
## Get Current Invoices
## Place APIKEY & Username in config.ini
## or pass via commandline  (example: GetRecurringInvoices.py -u=userid -k=apikey)
##

import sys, getopt, socket, SoftLayer, json, string, configparser, os, argparse



def initializeSoftLayerAPI():
    ## READ CommandLine Arguments and load configuration file
    parser = argparse.ArgumentParser(description="Print a report of Recurring invoices between Start and End date.")
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


print()
print("Looking up invoices....")

InvoiceList = client['Account'].getInvoices(filter={
        'invoices': {
            'createDate': {
                'operation': 'betweenDate',
                'options': [
                     {'name': 'startDate', 'value': [startdate+" 0:0:0"]},
                     {'name': 'endDate', 'value': [enddate+" 23:59:59"]}

                ]
            },
                    }
        })


print ()
print ('{:<25} {:<40} {:>8} {:>16} {:>16} {:>16} {:<15}'.format("Invoice Date /", "Invoice Number /", "Hours", "Hourly Rate", "Recurring Charge",  "Invoice Amount", "Type"))
print ('{:<25} {:<40} {:>8} {:>16} {:>16} {:>16} {:<15}'.format("Top Level Type", "Hostname        ", "     ", "           ", "                ",  "              ", "    "))
print ('{:<25} {:<40} {:>8} {:>16} {:>16} {:>16} {:<15}'.format("==============", "================", "=====", "===========", "================",  "==============", "===="))
for invoice in InvoiceList:
    if invoice['typeCode'] == "RECURRING":
        invoiceID = invoice['id']
        Billing_Invoice = client['Billing_Invoice'].getObject(id=invoiceID, mask="invoiceTopLevelItemCount,invoiceTopLevelItems,invoiceTotalAmount, invoiceTotalOneTimeAmount, invoiceTotalRecurringAmount")
        if Billing_Invoice['invoiceTotalAmount'] > "0":
            # PRINT INVOICE SUMMARY LINE
            print ('{:25} {:<40} {:>8} {:>16} {:>16,.2f} {:>16,.2f} {:<15}'.format(Billing_Invoice['createDate'][0:10], Billing_Invoice['id'], " ", " ", float(Billing_Invoice['invoiceTotalAmount']), float(Billing_Invoice['invoiceTotalRecurringAmount']), Billing_Invoice['typeCode']))

            print ()
            print ("** HOURLY ITEMS BILLED IN ARREARS")
            print ()
            # ITERATE THROUGH DETAIL SELCTING HOURLY ITEMS
            for item in Billing_Invoice['invoiceTopLevelItems']:
                associated_children = client['Billing_Invoice_Item'].getAssociatedChildren(id=item['id'])

                if 'hourlyRecurringFee' in item:
                    recurringFee = float(item['recurringFee'])
                    hourlyRecurringFee = float(item['hourlyRecurringFee'])
                    hours = round(float(item['recurringFee']) / hourlyRecurringFee)

                    # SUM UP HOURLY CHARGE
                    for child in associated_children:
                        recurringFee = recurringFee + float(child['recurringFee'])
                        if 'hourlyRecurringFee' in child:
                            hourlyRecurringFee = hourlyRecurringFee + float(child['hourlyRecurringFee'])
                        else:
                            hourlyRecurringFee = 0

                    if 'hostName' in item:
                        hostName = item['hostName']+"."+item['domainName']
                    else:
                        hostName = "Unnamed Device"

                    category = item["categoryCode"]
                    # PRINT LINE ITEM DETAIL FOR TOP LEVEL ITEM
                    print ('{:<25} {:<40} {:>8} {:>16,.3f} {:>16,.2f}'.format(category[0:25],hostName[0:40], hours, round(hourlyRecurringFee,3), round(recurringFee,2)))
            print()


            print ()
            print ("** MONTLY ITEMS BILLED IN ADVANCE")
            print ()

            for item in Billing_Invoice['invoiceTopLevelItems']:
                associated_children = client['Billing_Invoice_Item'].getAssociatedChildren(id=item['id'])
                if 'hourlyRecurringFee' not in item:
                    recurringFee = float(item['recurringFee'])
                    hourlyRecurringFee = 0
                    hours = 0
                    for child in associated_children:
                        recurringFee = recurringFee + float(child['recurringFee'])

                    if 'hostName' in item:
                        hostName = item['hostName']+"."+item['domainName']
                    else:
                        hostName = "Unnamed Device"

                    category = item["categoryCode"]
                    # PRINT LINE ITEM DETAIL FOR TOP LEVEL ITEM
                    print ('{:<25} {:<40} {:>8} {:>16,.3f} {:>16,.2f}'.format(category[0:40],hostName[0:40], hours, round(hourlyRecurringFee,3), round(recurringFee,2)))
            print()





