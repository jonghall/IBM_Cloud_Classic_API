__author__ = 'jonhall'
#
## Get eVault Storage detail
## Place APIKEY & Username in config.ini
## or pass via commandline  (example: GetRecurringInvoices.py -u=userid -k=apikey)

import SoftLayer, configparser, argparse, csv,logging,time, json, decimal

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
parser.add_argument("-o", "--output", help="Outputfile")

args = parser.parse_args()

client = initializeSoftLayerAPI(args.username, args.apikey, args.config)


if args.output == None:
    outputname=input("Output filename: ")
else:
    outputname=args.output



outfile = open(outputname, 'w')
csvwriter = csv.writer(outfile, delimiter='\t', quotechar='"', quoting=csv.QUOTE_ALL)


fieldnames = ['BillingItemId', 'Allocation_Date', 'evaultUser', 'evaultResource','ServerBackedUp', 'ServerNotes',
              'currentCapacityGb', 'currentUsedGb', 'currentEvaultPackage', 'currentEvaultFee','currentlyOverAllocation', 'LastBillDate',
              'lastInvoiceId', 'lastInvoiceFee', 'item1Description', 'item1Fee', 'item2Description', 'item2Fee', 'cancellationDate']


csvwriter = csv.DictWriter(outfile, delimiter=',', fieldnames=fieldnames)
csvwriter.writerow(dict((fn, fn) for fn in fieldnames))

## OPEN CSV FILE FOR OUTPUT
logging.basicConfig(format='%(asctime)s %(message)s', datefmt='%Y-%m-%d %I:%M:%S %p',level=logging.WARNING)

# Get last invoice ID, to be used to check actuals for each evault Allocation
logging.warning("Getting Last Invoice Id")
latestRecurringInvoice = client['Account'].getLatestRecurringInvoice()
lastInvoiceId = latestRecurringInvoice['id']


logging.warning("Retreiving all current evault allocations.")

# get list of evault allocations currently active in account
evaults=""
while evaults is "":
    try:
        time.sleep(1)
        evaults = client['Account'].getEvaultNetworkStorage(mask="id,createDate,username,nasType,hardwareId,billingItem.description,billingItem.recurringFee,billingItem.id,billingItem.lastBillDate,"
                                                                 "billingItem.cancellationDate,serviceResource, serviceResourceName,totalBytesUsed,virtualGuest,hardware")
    except SoftLayer.SoftLayerAPIError as e:
        logging.warning("Account:getEvaultNetworkStorage: %s, %s" % ( e.faultCode, e.faultString))


for evault in evaults:
    #  Get related invoiceItems from last Invoice
    logging.warning("Searching invoiceItems on last Invoice for billingItem %s." % (evault['billingItem']['id']))
    try:
        time.sleep(1)
        invoiceItems = client['Billing_Item'].getInvoiceItems(id=evault['billingItem']['id'], filter={
                        'invoiceItems': {
                            'invoiceId': {
                                 'operation': lastInvoiceId
                        }}})
    except SoftLayer.SoftLayerAPIError as e:
        logging.warning("Billing_Item::getInvoiceItems(id=%s): %s, %s" % (evault['billingItem']['id'], e.faultCode, e.faultString))


    # Get parent ID for the last Invoice
    parentId = invoiceItems[0]['parentId']
    evaultId=evault['id']
    billingItemId=evault['billingItem']['id']
    createDate=evault['createDate'][0:10]
    lastBillDate=evault['billingItem']['lastBillDate'][0:10]
    cancellationDate=evault['billingItem']['cancellationDate'][0:10]
    description=evault['billingItem']['description']  #evault package purchased
    recurringFee="${:6,.2f}".format(float(evault['billingItem']['recurringFee'] )) # evault package recurring Fee
    nasType=evault['nasType']
    serviceResourceName=evault['serviceResourceName']
    username=evault['username']
    currentCapacityGb = description[0:description.find("GB")]# currently allocated amount, not always package amount
    totalBytesUsed=float(evault['totalBytesUsed'])
    usedGb=totalBytesUsed/1024/1024/1024
    if int(usedGb) > int(currentCapacityGb):
        overAllocation=True
    else:
        overAllocation=False

    usedGb="{0:.2f}".format(usedGb)

    #Determine eVault Server being backed up
    if 'virtualGuest' in evault:
        server = evault['virtualGuest']['hostname']
        if 'notes' in evault['virtualGuest']:
            server_notes =  evault['virtualGuest']['notes']
        else:
            server_notes = ""
    elif 'hardware' in evault:
        server = evault['hardware']['hostname']
        if 'notes' in evault['hardware']:
            server_notes =  evault['hardware']['notes']
        else:
            server_notes = ""
    else:
        server = ""
        server_notes = ""

    # Get the last Invoice Billing detail to determine actual charges
    logging.warning("Searching for overage charges on last invoice for parent item %s." % (parentId))
    try:
        time.sleep(1)
        billingDetail = client['Billing_Invoice_Item'].getFilteredAssociatedChildren(id=parentId, filter={
            'filteredAssociatedChildren': {
                'categoryCode': {
                    'operation': 'in',
                    'options': [
                        {'name': 'data',
                         'value': [
                             'evault',
                             'storagelayer_additional_storage']}]
                }}})
    except SoftLayer.SoftLayerAPIError as e:
        logging.warning("Billing_Invoice_Item::getFilteredAssociatedChildren(id=%s): %s, %s" % (parentId, e.faultCode, e.faultString))

    # Calculate total charge including overages for last invoice for related items.
    total=0
    item1Descrition=""
    item1Fee=0
    item2Description=""
    item2Fee=0

    for detail in billingDetail:
            if detail['categoryCode'] == "evault":
                item1Description=detail['description'].replace('\n', " ")
                item1Fee="${:6,.2f}".format(float(detail['recurringFee']))
            if detail['categoryCode'] == "storagelayer_additional_storage":
                item2Description=detail['description'].replace('\n', " ")
                item2Fee="${:6,.2f}".format(float(detail['recurringFee']))
            total=total+float(detail['recurringFee'])
    lastInvoiceTotal= ("${:6,.2f}".format(total))


    # BUILD CSV OUTPUT & WRITE ROW
    row = {'LastBillDate': lastBillDate,
           'Allocation_Date': createDate,
           'BillingItemId': billingItemId,
           'evaultUser': username,
           'evaultResource': serviceResourceName,
           'ServerBackedUp': server,
           'ServerNotes': server_notes,
           'currentCapacityGb': currentCapacityGb,
           'currentUsedGb': usedGb,
           'currentEvaultPackage': description,
           'currentEvaultFee': recurringFee,
           'currentlyOverAllocation': overAllocation,
           'lastInvoiceId': lastInvoiceId,
           'lastInvoiceFee': lastInvoiceTotal,
           'item1Description': item1Description,
           'item1Fee': item1Fee,
           'item2Description': item2Description,
           'item2Fee': item2Fee,
           'cancellationDate': cancellationDate
            }
    csvwriter.writerow(row)

##close CSV File
outfile.close()

