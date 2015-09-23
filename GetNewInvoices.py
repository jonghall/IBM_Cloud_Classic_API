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


class TablePrinter(object):
    #
    # FORMAT TABLE
    #
    "Print a list of dicts as a table"

    def __init__(self, fmt, sep=' ', ul=None):
        """
        @param fmt: list of tuple(heading, key, width)
                        heading: str, column label
                        key: dictionary key to value to print
                        width: int, column width in chars
        @param sep: string, separation between columns
        @param ul: string, character to underline column label, or None for no underlining
        """
        super(TablePrinter, self).__init__()
        self.fmt = str(sep).join('{lb}{0}:{1}{rb}'.format(key, width, lb='{', rb='}') for heading, key, width in fmt)
        self.head = {key: heading for heading, key, width in fmt}
        self.ul = {key: str(ul) * width for heading, key, width in fmt} if ul else None
        self.width = {key: width for heading, key, width in fmt}

    def row(self, data):
        return self.fmt.format(**{k: str(data.get(k, ''))[:w] for k, w in self.width.items()})

    def __call__(self, dataList):
        _r = self.row
        res = [_r(data) for data in dataList]
        res.insert(0, _r(self.head))
        if self.ul:
            res.insert(1, _r(self.ul))
        return '\n'.join(res)


#
# Get APIKEY from config.ini & initialize SoftLayer API
#

client = initializeSoftLayerAPI()

NewInvoiceReport = [
    ('Invoice Date', 'createDate', 12),
    ('Invoice', 'id', 10),
    ('Prorated Charges', 'invoiceTotalRecurringAmount',18),
    ('One-time Amount', 'invoiceTotalOneTimeAmount', 18),
    ('Invoice Amount', 'invoiceTotalAmount', 18),
    ('Type', 'typeCode', 15),
    ('Status', 'statusCode', 10)
]


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

#print (json.dumps(InvoiceList,indent=4))

data =[]


for invoice in InvoiceList:
    if invoice['typeCode'] == "NEW" or invoice['typeCode'] == "ONE-TIME-CHARGE":
        InvoiceReportRow = {}
        invoiceID = invoice['id']
        Billing_Invoice = client['Billing_Invoice'].getObject(id=invoiceID, mask="invoiceTotalAmount, invoiceTotalOneTimeAmount, invoiceTotalRecurringAmount")
        #print (json.dumps(Billing_Invoice,indent=4))
        if Billing_Invoice['invoiceTotalAmount'] > "0":
            InvoiceReportRow['id'] = Billing_Invoice['id']
            InvoiceReportRow['createDate'] = Billing_Invoice['createDate'][0:10]
            InvoiceReportRow['invoiceTotalAmount'] = Billing_Invoice['invoiceTotalAmount']
            InvoiceReportRow['invoiceTotalOneTimeAmount'] = Billing_Invoice['invoiceTotalOneTimeAmount']
            InvoiceReportRow['invoiceTotalRecurringAmount'] = Billing_Invoice['invoiceTotalRecurringAmount']
            InvoiceReportRow['typeCode'] = Billing_Invoice['typeCode']
            InvoiceReportRow['statusCode'] = Billing_Invoice['statusCode']
            data.append(InvoiceReportRow)

print()
print("                    Invoices with new Recurring & One Time Charges")
print("                          Between %s and %s" % (startdate, enddate))
print()
print(TablePrinter(NewInvoiceReport, ul='=')(data))


