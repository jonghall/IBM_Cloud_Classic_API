__author__ = 'jonhall'
#
## Get eVault Storage detail
## Place APIKEY & Username in config.ini
## or pass via commandline  (example: GetRecurringInvoices.py -u=userid -k=apikey)
##

import SoftLayer, configparser, argparse, csv,logging,time, json

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


#
# GET LIST OF INVOICES
#


outfile = open(outputname, 'w')
csvwriter = csv.writer(outfile, delimiter='\t', quotechar='"', quoting=csv.QUOTE_ALL)


fieldnames = ['LastBillDate' , 'BillingItemId', 'Allocation_Date', 'StorageType', 'BytesUsed',
              'evaultUser', 'evaultResource','ServerBackedUp', 'ServerNotes', 'Cost']
csvwriter = csv.DictWriter(outfile, delimiter=',', fieldnames=fieldnames)
csvwriter.writerow(dict((fn, fn) for fn in fieldnames))

## OPEN CSV FILE FOR OUTPUT
logging.basicConfig( format='%(asctime)s %(message)s', datefmt='%Y-%m-%d %I:%M:%S %p',level=logging.WARNING)




logging.warning("Looking up current evault allocations.")

evaults=""
while evaults is "":
    try:
        time.sleep(1)
        # get list of evault allocations
        evaults = client['Account'].getEvaultNetworkStorage(mask="id,createDate,capacityGb,username,nasType,hardwareId,billingItem,serviceResource,serviceResourceName,totalBytesUsed,hardware,virtualGuest")
    except SoftLayer.SoftLayerAPIError as e:
        logging.warning("Account:getEvaultNetworkStorage: %s, %s" % ( e.faultCode, e.faultString))


for evault in evaults:

    createDate=evault['createDate'][0:10]
    lastBillDate=evault['billingItem']['lastBillDate']
    cancelationDate=evault['billingItem']['cancellationDate']
    billingItemId=evault['billingItem']['id']
    capacityGb=evault['capacityGb']
    username=evault['username']
    nasType=evault['nasType']
    description=evault['billingItem']['description']
    recurringFee=evault['billingItem']['recurringFee']
    serviceResourceName=evault['serviceResourceName']
    totalBytesUsed=evault['totalBytesUsed']

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


    # BUILD CSV OUTPUT & WRITE ROW
    row = {'LastBillDate': lastBillDate,
           'Allocation_Date': createDate,
           'BillingItemId': billingItemId,
           'StorageType': description,
           'BytesUsed': totalBytesUsed,
           'evaultUser': username,
           'evaultResource': serviceResourceName,
           'ServerBackedUp': server,
           'ServerNotes': server_notes,
           'Cost': recurringFee
            }
    csvwriter.writerow(row)
    print(row)
##close CSV File
outfile.close()