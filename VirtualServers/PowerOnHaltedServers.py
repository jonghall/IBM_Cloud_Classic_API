__author__ = 'jonhall'
## PowerOn Halted Servers that meet criteria.


import SoftLayer, configparser, argparse, csv, json, pytz, logging
from datetime import datetime, timedelta, tzinfo

def convert_timestamp(sldate):
    formatedDate = sldate
    formatedDate = formatedDate[0:22]+formatedDate[-2:]
    formatedDate = datetime.strptime(formatedDate, "%Y-%m-%dT%H:%M:%S%z")
    return formatedDate.astimezone(central)

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
parser = argparse.ArgumentParser(description="PowerOn Halted Servers that meet criteria.")
parser.add_argument("-u", "--username", help="SoftLayer API Username")
parser.add_argument("-k", "--apikey", help="SoftLayer APIKEY")
parser.add_argument("-c", "--config", help="config.ini file to load")
parser.add_argument("-d", "--datacenter", help="Filter by Datacenter")
parser.add_argument("-i", "--image", help="TemplateImage name required")
parser.add_argument("-v", "--vlan", help="VLAN required")
parser.add_argument("-q", "--quantity", help="Quantity of Servers required")



args = parser.parse_args()

client = initializeSoftLayerAPI(args.username, args.apikey, args.config)

## Configure Log
#logging.basicConfig(filename="powerOn.log", format='%(asctime)s %(message)s', datefmt='%Y-%m-%d %I:%M:%S %p',level=logging.WARNING)
logging.basicConfig( format='%(asctime)s %(message)s', datefmt='%Y-%m-%d %I:%M:%S %p',level=logging.WARNING)

## Create Filter for provisioned hourly guests with powerState=Halted and activeTransactionCount=0
virtualServerFilter={'hourlyVirtualGuests': {'powerState':{'keyName': {'operation': 'HALTED'}}}}
virtualServerFilter['hourlyVirtualGuests'].update({'provisionDate':{'operation': 'not null'}})
virtualServerFilter['hourlyVirtualGuests'].update({'activeTransactionCount':{'operation': "=0"}})

## Add parameters to filter
if args.datacenter != None:
    virtualServerFilter['hourlyVirtualGuests'].update({'datacenter': {'name': {'operation': args.datacenter}}})
    datacenter=args.datacenter

if args.image != None:
    virtualServerFilter['hourlyVirtualGuests'].update({'blockDeviceTemplateGroup': {'name': {'operation': args.image}}})
    image = args.image

if args.vlan != None:
    virtualServerFilter['hourlyVirtualGuests'].update({'networkVlans': {'vlanNumber': {'operation': args.vlan}}})
    image = args.image

if args.quantity != None:
        quantity = int(args.quantity)
else:
    print ("Quantity parameter required.")
    quit()


central = pytz.timezone("US/Central")
try:
    virtualServers = client['Account'].getHourlyVirtualGuests(mask='id,provisionDate,hostname,createDate, powerState,activeTransactionCount, datacenter.name,networkVlans,primaryBackendIpAddress,blockDeviceTemplateGroup',filter=virtualServerFilter)
except SoftLayer.SoftLayerAPIError as e:
    logging.warning("Error: Account::getHourlyVirtualGuests(): %s" % (server['id'], e.faultString))
    quit()

# If the quanity requested is less than available through error.
if len(virtualServers) >= quantity:
    ip_addresses = []
    guestIdList = []
    turnedon=0
    logging.warning("%s servers requested." % (quantity))

    # FOR LIST OF SERVERS MEETING CRITERIA POWER EACH ON FOR USE
    for server in virtualServers:
        try:
            poweron = client['Virtual_Guest'].powerOn(id=server['id'])
        except SoftLayer.SoftLayerAPIError as e:
            logging.warning("Error: Virtual_Guest::powerOn(id=%s): %s" % (server['id'], e.faultString))
            result="failure"
            continue
        else:
            logging.warning("GuestId %s with IP %s powered on successfully." % (server['id'], server['primaryBackendIpAddress']))
            ip_addresses.append(server['primaryBackendIpAddress'])
            guestIdList.append(server['id'])
            result="success"
            turnedon=turnedon+1

    if turnedon == quantity:
        logging.warning("Quantity requested (%s) have successfully been powered on." % (quantity))
    else:
        logging.warning("Warning, only %s servers could be powered on. You requested %s." % (turnedon, quantity))
else:
    logging.warning("%s requested, but only %s available." % (quantity, len(virtualServers)))

logging.warning("ip_addresses %s" % (ip_addresses))
logging.warning("guestIdList %s" % (guestIdList))