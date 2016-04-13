__author__ = 'jonhall'
## PowerOn Halted Servers that meet criteria.


import SoftLayer, configparser, argparse, csv, json, pytz, logging
import SoftLayerProvision
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
            config = configparser.ConfigParser()
            config.read(filename)
            client = SoftLayer.Client(username=config['api']['username'], api_key=config['api']['apikey'])
        else:
            #filename="config.ini"
            client = SoftLayer.Client()
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

parser.add_argument("--provision", help="Flag to provision servers if needed", action='store_true')
parser.add_argument("--hostname", help="Hostname for provisioning")
parser.add_argument("--domain", help="Domain for provisioning")
parser.add_argument("--cpus", help="CPU count for provisioning")
parser.add_argument("--memory", help="Memory size for provisioning")
parser.add_argument("--tag", help="Tag value for provisioning")

args = parser.parse_args()

client = initializeSoftLayerAPI(args.username, args.apikey, args.config)

## Configure Log
#logging.basicConfig(filename="powerOn.log", format='%(asctime)s %(message)s', datefmt='%Y-%m-%d %I:%M:%S %p',level=logging.WARNING)
logging.basicConfig( format='%(asctime)s %(message)s', datefmt='%Y-%m-%d %I:%M:%S %p',level=logging.WARNING)

def getVirtualServers():
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

    if args.vlan != None:
        virtualServerFilter['hourlyVirtualGuests'].update({'networkVlans': {'vlanNumber': {'operation': args.vlan}}})
        
    try:
        virtualServers = client['Account'].getHourlyVirtualGuests(mask='id,provisionDate,hostname,createDate, powerState,activeTransactionCount, datacenter.name,networkVlans,primaryBackendIpAddress,blockDeviceTemplateGroup',filter=virtualServerFilter)
        return virtualServers
    except SoftLayer.SoftLayerAPIError as e:
        logging.warning("Error: Account::getHourlyVirtualGuests(): %s" % (server['id'], e.faultString))
        #quit()
        return None

central = pytz.timezone("US/Central")
if args.quantity != None:
    quantity = int(args.quantity)
else:
    print ("Quantity parameter required.")
    quit()

virtualServers = getVirtualServers()
if virtualServers == None:
    quit()


# If the quantity requested is less than available
if args.provision and len(virtualServers) < quantity:
    needed = quantity - len(virtualServers)

    provisionClient = SoftLayerProvision.SoftLayerVirtual(client)

    # Get vlan Id
    vlanId = None
    if args.vlan != None:
        vlanId = provisionClient.getVlanIdFromName(args.datacenter, args.vlan)

    # Get Image Guid
    templateGuid = None
    if args.image != None:
        templateGuid = provisionClient.getImageTemplateGuid(args.image)

    # Need to move these to a config file or parameters
    print 'Need to provision ' + str(needed) +' server(s)'
    hostname = args.hostname
    domain = args.domain
    cpus = args.cpus
    memory = args.memory
    localDisk = False
    private = False
    hourly = True
    datacenter = args.datacenter
    osCode = ''
    privateVlan = vlanId
    nicSpeed = 1000
    dedicated = False
    templateGuid = templateGuid
    postInstallUrl = ''
    tag = args.tag

    provisionClient.provisionServers(needed, hostname, domain, cpus, memory, localDisk, private, hourly, datacenter, osCode, privateVlan, nicSpeed, dedicated, templateGuid, postInstallUrl, tag)

    virtualServers = getVirtualServers()

# If the quanity requested is less than available through error.
ip_addresses = []
guestIdList = []

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