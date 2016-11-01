__author__ = 'jonhall'
#
## GetBlockStorageDetail1 -
## Report of deailed Performance/Endurance Storage authroizations by invoice line item.
## Pass via commandline  (example: GetBlockStorageDetail1.py -u=userid -k=apikey)

import SoftLayer,configparser, argparse, csv, json,logging,time
from datetime import datetime

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
parser = argparse.ArgumentParser(description="Report of deailed Performance/Endurance Storage authroizations by invoice line item.")
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



fieldnames = ['Invoice_Date', 'Invoice_Number', 'BillingItemId', 'ResourceTableId', 'Allocation_Date', 'StorageType',
              'Location', 'LUNName', 'IOPS', 'Size', 'Snapshot', 'TotalAuthorized', 'AuthorizedServers', 'AllowedSubets', 'Notes', 'Cost']
csvwriter = csv.DictWriter(outfile, delimiter=',', fieldnames=fieldnames)
csvwriter.writerow(dict((fn, fn) for fn in fieldnames))

logging.basicConfig(filename='GetBlockStorageDetail1.log', format='%(asctime)s %(message)s', datefmt='%Y-%m-%d %I:%M:%S %p',level=logging.WARNING)

## OPEN CSV FILE FOR OUTPUT

print()
print("Looking up invoices....")

# Request Invoice List
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
    logging.warning("Retreiving Billing Invoice %s" % (invoiceID))
    while Billing_Invoice is "":
        try:
            time.sleep(1)
            # get Invoice Detail
            Billing_Invoice = client['Billing_Invoice'].getObject(id=invoiceID, mask="invoiceTotalAmount, createDate, typeCode")
        except SoftLayer.SoftLayerAPIError as e:
            logging.warning("Billing_Invoice:getObject(id=%s): %s, %s" % (invoiceID, e.faultCode, e.faultString))

    invoiceTopLevelItems=""
    logging.warning("Retreiving Billing Invoice %s Top Level Items." % (invoiceID))
    while invoiceTopLevelItems is "":
        try:
            time.sleep(1)
            # get Invoice Top Level Items
            invoiceTopLevelItems = client['Billing_Invoice'].getInvoiceTopLevelItems(id=invoiceID, mask="id,description,categoryCode,billingItemId,resourceTableId,product,location,totalRecurringAmount",
                                 filter={
                                     'invoiceTopLevelItems': {
                                         'categoryCode': {
                                             'operation': 'in',
                                             'options': [
                                                 {'name': 'data',
                                                  'value': [
                                                      'storage_service_enterprise',
                                                      'performance_storage_iscsi']}
                                             ]
                                         },
                                     }
                                 })

        except SoftLayer.SoftLayerAPIError as e:
            logging.warning("Billing_Invoice:getInvoiceTopLevelItems(id=%s): %s, %s" % (invoiceID, e.faultCode, e.faultString))

    if Billing_Invoice['invoiceTotalAmount'] > "0":
        invoiceType=Billing_Invoice['typeCode']
        invoiceDate=Billing_Invoice['createDate'][0:10]
        count=len(invoiceTopLevelItems)
        for item in invoiceTopLevelItems:
            category = item["categoryCode"]
            storageType=item["product"]['description']
            totalRecurringAmount=item['totalRecurringAmount']
            itemId = item['id']
            location=item['location']['name']
            product=item['description']
            billingItemId = item['billingItemId']
            resourceTableId= item['resourceTableId']
            #print(json.dumps(item,indent=4))

            billing_detail=""
            logging.warning("Getting Billing Item %s Detail." % (itemId))
            while billing_detail is "":
                try:
                    time.sleep(1)
                    billing_detail = client['Billing_Invoice_Item'].getChildren(id=itemId, mask="description,categoryCode,product")
                except SoftLayer.SoftLayerAPIError as e:
                    logging.warning("Billing_Invoice_iten:getChildren(id=%s): %s, %s" % (itemId,e.faultCode, e.faultString))

            if category=="storage_service_enterprise":
                iops=getDescription("storage_tier_level", billing_detail)
                storage=getDescription("performance_storage_space", billing_detail)
                snapshot=getDescription("storage_snapshot_space", billing_detail)

            if category=="performance_storage_iscsi":
                iops=getDescription("performance_storage_iops", billing_detail)
                storage=getDescription("performance_storage_space", billing_detail)
                snapshot=getDescription("storage_snapshot_space", billing_detail)

            resource_detail=""
            logging.warning("Getting Network Storage Detail for resource %s." % (resourceTableId))
            while resource_detail is "":
                try:
                    time.sleep(1)
                    resource_detail = client['Network_Storage'].getObject(id=resourceTableId, mask="createDate,username,notes,allowedVirtualGuests,allowedSubnets,allowedHardware")
                except SoftLayer.SoftLayerAPIError as e:
                    logging.warning("Network_Storage:getObject(%s): %s, %s" % (resourceTableId, e.faultCode, e.faultString))
                    if e.faultCode=="SoftLayer_Exception_ObjectNotFound":
                        logging.warning(json.dumps(billing_detail,indent=4))
                        resource_detail="none"

            #print (json.dumps(resource_detail,indent=4))
            if resource_detail=="none":
                notes=""
                storageName=""
                authorizedServers=""
                allowedSubnets=""
                allocationDate=""
            else:
                allocationDate = resource_detail['createDate'][0:10]
                if 'notes' in resource_detail:
                    notes=resource_detail['notes']
                else:
                    notes=""

                storageName=resource_detail['username']
                allowedSubnets=resource_detail['allowedSubnets']
                authorizedServers=[]
                if 'allowedVirtualGuests' in resource_detail:
                   authorizedGuests=resource_detail['allowedVirtualGuests']
                   for guest in authorizedGuests:
                        authorizedServers.append(guest['hostname'])

                if 'allowedHardware' in resource_detail:
                   authorizedHardware=resource_detail['allowedHardware']
                   for server in authorizedHardware:
                        authorizedServers.append(server['hostname'])


                # BUILD CSV OUTPUT & WRITE ROW
                row = {'Invoice_Date': invoiceDate,
                       'Allocation_Date': allocationDate,
                       'Invoice_Number': invoiceID,
                       'BillingItemId': billingItemId,
                       'ResourceTableId': resourceTableId,
                       'StorageType': storageType,
                       'Location': location,
                       'LUNName': storageName,
                       'IOPS': iops,
                       'Size': storage,
                       'Snapshot': snapshot,
                       'TotalAuthorized': len(authorizedServers),
                       'AuthorizedServers': authorizedServers,
                       'AllowedSubets': allowedSubnets,
                       'Notes': notes,
                       'Cost': totalRecurringAmount
                        }
                csvwriter.writerow(row)
                print(row)
##close CSV File
outfile.close()