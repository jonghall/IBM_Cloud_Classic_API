__author__ = 'jonhall'
#
## Get Current Invoices
## Place APIKEY & Username in config.ini
## or pass via commandline  (example: GetNewInvoices.py -u=userid -k=apikey)
##

import sys, getopt, socket, SoftLayer, json, string, configparser, os, argparse


def initializeSoftLayerAPI():
    ## READ CommandLine Arguments and load configuration file
    parser = argparse.ArgumentParser(description="Print a report of NEW invoices which have a non zero balance between Start and End date.")
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
print ('{:<40} {:<40} {:>18} {:>16} {:>16} {:<16}'.format("Invoice Date /", "Invoice Number /", "Recurring Charges", "OneTime Charges", "Invoice Amount", "Type"))
print ('{:<40} {:<40} {:>18} {:>16} {:>16} {:<16}'.format("Top Level Item", "Hostname        ", "                 ", "               ", "              ", "    "))
print ('{:<40} {:<40} {:>18} {:>16} {:>16} {:<16}'.format("==============", "================", "=================", "===============", "==============", "===="))
for invoice in InvoiceList:
    if invoice['typeCode'] == "NEW" or invoice['typeCode'] == "ONE-TIME-CHARGE":
        invoiceID = invoice['id']
        Billing_Invoice = client['Billing_Invoice'].getObject(id=invoiceID, mask="invoiceTopLevelItemCount,invoiceTopLevelItems,invoiceTotalAmount, invoiceTotalOneTimeAmount, invoiceTotalRecurringAmount")
        if Billing_Invoice['invoiceTotalAmount'] > "0":
            # PRINT INVOICE SUMMARY
            print ('{:40} {:<40} {:>18,.2f} {:>16,.2f} {:>16,.2f} {:<16}'.format(Billing_Invoice['createDate'][0:10], Billing_Invoice['id'], float(Billing_Invoice['invoiceTotalAmount']), float(Billing_Invoice['invoiceTotalOneTimeAmount']), float(Billing_Invoice['invoiceTotalRecurringAmount']), Billing_Invoice['typeCode']))
            # GET associated items for recurring and onetime totals per Top Level TIem
            for item in Billing_Invoice['invoiceTopLevelItems']:
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
                category = item["categoryCode"][0:25]
                if recurringFee >0 or oneTimeFee > 0:
                    print ('{:<40} {:<40} {:>18,.2f} {:>16,.2f}'.format(category[0:40],hostName[0:40], round(recurringFee,2), round(oneTimeFee,2)))
            print()