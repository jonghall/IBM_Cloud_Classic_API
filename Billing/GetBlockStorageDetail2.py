__author__ = 'jonhall'
#
## GetBlockStorageDetail2
## Report of deailed Performance/Endurance Storage authroizations by authorized server.
##

import SoftLayer, configparser, argparse, csv, json,logging,time
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
parser = argparse.ArgumentParser(description="Report of deailed Performance/Endurance Storage authroizations by authorized server.")
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
              'Location', 'LUNName', 'IOPS', 'Size', 'Snapshot', 'AuthorizedServer', 'AllAuths', 'AuthorizedSubnets', 'Notes', 'Cost']
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


for invoice in InvoiceList:
    invoiceID = invoice['id']
    Billing_Invoice=""
    while Billing_Invoice is "":
        try:
            time.sleep(1)
            Billing_Invoice = client['Billing_Invoice'].getObject(id=invoiceID, mask="invoiceTotalAmount, createDate, typeCode, invoiceTopLevelItems, invoiceTopLevelItems.product,invoiceTopLevelItems.location,invoiceTopLevelItems.totalRecurringAmount")
        except SoftLayer.SoftLayerAPIError as e:
            logging.warning("%s, %s" % (e.faultCode, e.faultString))

    if Billing_Invoice['invoiceTotalAmount'] > "0":
        invoiceType=Billing_Invoice['typeCode']
        invoiceDate=Billing_Invoice['createDate'][0:10]
        count=0
        for item in Billing_Invoice['invoiceTopLevelItems']:
            category = item["categoryCode"]
            storageType=item["product"]['description']
            totalRecurringAmount=item['totalRecurringAmount']
            count=count + 1
            if category=="storage_service_enterprise" or category=="performance_storage_iscsi":
                itemId = item['id']
                location=item['location']['name']
                product=item['description']
                billingItemId = item['billingItemId']
                resourceTableId= item['resourceTableId']
                #print(json.dumps(item,indent=4))

                billing_detail=""
                while billing_detail is "":
                    try:
                        time.sleep(1)
                        billing_detail = client['Billing_Invoice_Item'].getChildren(id=itemId, mask="description,categoryCode,product")
                    except SoftLayer.SoftLayerAPIError as e:
                        logging.warning("%s, %s" % (e.faultCode, e.faultString))


                if category=="storage_service_enterprise":
                    iops=getDescription("storage_tier_level", billing_detail)
                    storage=getDescription("performance_storage_space", billing_detail)
                    snapshot=getDescription("storage_snapshot_space", billing_detail)

                if category=="performance_storage_iscsi":
                    iops=getDescription("performance_storage_iops", billing_detail)
                    storage=getDescription("performance_storage_space", billing_detail)
                    snapshot=getDescription("storage_snapshot_space", billing_detail)

                #SoftLayer_Network_Storage_Iscsi::getObject
                resource_detail=""
                while resource_detail is "":
                    try:
                        time.sleep(1)
                        resource_detail = client['Network_Storage'].getObject(id=resourceTableId, mask="createDate,username,notes,allowedVirtualGuests,allowedSubnets,allowedHardware,iscsiLuns,lunId")
                    except SoftLayer.SoftLayerAPIError as e:
                        logging.warning("%s, %s" % (e.faultCode, e.faultString))
                        if e.faultCode=="SoftLayer_Exception_ObjectNotFound":
                            logging.warning(json.dumps(billing_detail,indent=4))
                            resource_detail="none"

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
                    authorizedSubnets=resource_detail['allowedSubnets']
                    authorizedServers=[]
                    if 'allowedVirtualGuests' in resource_detail:
                       for server in resource_detail['allowedVirtualGuests']:
                            authorizedServers.append(server['hostname'])

                    if 'allowedHardware' in resource_detail:
                       for server in resource_detail['allowedHardware']:
                            authorizedServers.append(server['hostname'])

                numServers=len(authorizedServers)
                for x in range(0, numServers):
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
                           'AuthorizedServer': authorizedServers[x],
                           'AllAuths': authorizedServers,
                           'AuthorizedSubnets': authorizedSubnets,
                           'Notes': notes,
                           'Cost': totalRecurringAmount/numServers
                            }
                    csvwriter.writerow(row)
                    print(row)
##close CSV File
outfile.close()