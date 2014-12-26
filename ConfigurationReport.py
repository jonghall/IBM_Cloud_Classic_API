##
## Account Bare Metal Configuration Report
## Place APIKEY & Username in config.ini
## or pass via commandline  (example: ConfigurationReport.py -u=userid -k=apikey)
##

import sys, getopt, socket, SoftLayer, json, string, configparser, os, argparse


def initializeSoftLayerAPI():
    ## READ CommandLine Arguments and load configuration file
    parser = argparse.ArgumentParser(description="Configuration Report prints details of BareMetal Servers such as Network, VLAN, and hardware configuration")
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
        client = SoftLayer.Client(username=args.username, api_key=args.apikey, endpoint_url='https://api.service.softlayer.com/xmlrpc/v3.1/')
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

#
# BUILD TABLES
#
networkFormat = [
    ('Interface', 'interface', 10),
    ('MAC ', 'mac', 17),
    ('IpAddress', 'primaryIpAddress', 16),
    ('speed', 'speed', 5),
    ('status', 'status', 10),
    ('Vlan', 'vlan', 5),
    ('Vlan Name', 'vlanName', 20),
    ('Switch', 'switch',17),
    ('Router', 'router', 17),
    ('Manufacturer', 'router_mfg',12),
    ('RouterIP','router_ip',16)
]

serverFormat = [
    ('Type   ', 'devicetype', 15),
    ('Manufacturer', 'manufacturer', 15),
    ('Name', 'name', 20),
    ('Description', 'description', 30),
    ('Modify Date', 'modifydate', 25),
    ('Serial Number', 'serialnumber', 15)
]

trunkFormat = [
    ('Interface', 'interface', 10),
    ('Vlan #', 'vlanNumber', 8),
    ('VlanName', 'vlanName', 20)
]

storageFormat = [
    ('StorageType', 'type', 11),
    ('Address', 'address', 40),
    ('Gb', 'capacity', 10),
    ('IOPS', 'iops', 10),
    ('Notes', 'notes', 20)
]

#
# GET LIST OF ALL DEDICATED HARDWARE IN ACCOUNT
#

hardwarelist = client['Account'].getHardware(mask='datacenterName')

for hardware in hardwarelist:

    #if hardware['datacenterName'] != 'Paris 1':
    #        continue

    hardwareid = hardware['id']


    #
    # LOOKUP HARDWARE INFORMATION BY HARDWARE ID
    #

    mask_object = "datacenterName,networkVlans,backendRouters,frontendRouters,backendNetworkComponentCount,backendNetworkComponents,frontendNetworkComponentCount,frontendNetworkComponents,uplinkNetworkComponents"
    hardware = client['Hardware'].getObject(mask=mask_object, id=hardwareid)

    # FIND Index for MGMT Interface and get it's ComponentID Number
    mgmtnetworkcomponent=[]
    for backend in hardware['backendNetworkComponents']:
        if backend['name'] == "mgmt":
            mgmtnetworkcomponent=client['Network_Component'].getObject(mask="router, uplinkComponent",id=backend['id'])
            continue

    # OBTAIN INFORMATION ABOUT PRIVATE (BACKEND) INTERFACES
    backendnetworkcomponents=[]
    for backend in hardware['backendNetworkComponents']:
        if backend['name'] == "eth":
            backendnetworkcomponent=client['Network_Component'].getObject(mask="router, uplinkComponent",id=backend['id'])
            # Get trunked vlans
            backendnetworkcomponent['trunkedvlans'] = client['Network_Component'].getNetworkVlanTrunks(mask='networkVlan', id=backendnetworkcomponent['uplinkComponent']['id'])
            backendnetworkcomponents.append(backendnetworkcomponent)

    # FIND INFORMATION ABOUT PUBLIC (FRONTEND) INTERFACES
    frontendnetworkcomponents=[]
    for frontend in hardware['frontendNetworkComponents']:
        if frontend['name'] == "eth":
            frontendnetworkcomponent=client['Network_Component'].getObject(mask="router, uplinkComponent",id=frontend['id'])
            # Get trunked vlans
            frontendnetworkcomponent['trunkedvlans'] = client['Network_Component'].getNetworkVlanTrunks(mask='networkVlan', id=frontendnetworkcomponent['uplinkComponent']['id'])
            frontendnetworkcomponents.append(frontendnetworkcomponent)



    print(
        "__________________________________________________________________________________________________________________")
    print()
    print("Hostname        : %s" % (hardware['fullyQualifiedDomainName']))
    print("Datacenter      : %s" % (hardware['datacenterName']))
    print("Serial #        : %s" % (hardware['manufacturerSerialNumber']))
    print(
        "__________________________________________________________________________________________________________________")


    #
    # POPULATE TABLE WITH FRONTEND DATA
    #

    print()
    print("FRONTEND NETWORK")
    data = []
    network = {}
    for frontendnetworkcomponent in frontendnetworkcomponents:
        network={}
        network['interface'] = "%s%s" % (frontendnetworkcomponent['name'], frontendnetworkcomponent['port'])
        network['mac'] = frontendnetworkcomponent['macAddress']
        if 'primaryIpAddress' in frontendnetworkcomponent:
            network['primaryIpAddress'] = frontendnetworkcomponent['primaryIpAddress']
        network['speed'] = frontendnetworkcomponent['speed']
        network['status'] = frontendnetworkcomponent['status']
        network['switch'] = frontendnetworkcomponent['uplinkComponent']['hardware']['hostname']
        network['router'] = frontendnetworkcomponent['router']['hostname']
        network['router_mfg'] = frontendnetworkcomponent['router']['hardwareChassis']['manufacturer']
        network['router_ip'] = frontendnetworkcomponent['router']['primaryIpAddress']
        if len(hardware['networkVlans']) > 1:
            network['vlan'] = hardware['networkVlans'][1]['vlanNumber']
            if 'name' in hardware['networkVlans'][1].keys(): network['vlanName'] = hardware['networkVlans'][0]['name']
        data.append(network)
    print(TablePrinter(networkFormat, ul='=')(data))

    #
    # POPULATE TABLE WITH BACKEND DATA
    #

    #print (json.dumps(backendnetworkcomponents,indent=4))
    interfacedata = []
    trunkdata= []
    for backendnetworkcomponent in backendnetworkcomponents:
        network={}
        network['interface'] = "%s%s" % (backendnetworkcomponent['name'], backendnetworkcomponent['port'])
        network['mac'] = backendnetworkcomponent['macAddress']
        if 'primaryIpAddress' in backendnetworkcomponent:
                network['primaryIpAddress'] = backendnetworkcomponent['primaryIpAddress']
        network['speed'] = backendnetworkcomponent['speed']
        network['status'] = backendnetworkcomponent['status']
        network['vlan'] = hardware['networkVlans'][0]['vlanNumber']
        if 'name' in hardware['networkVlans'][0].keys(): network['vlanName'] = hardware['networkVlans'][0]['name']
        network['switch'] = backendnetworkcomponent['uplinkComponent']['hardware']['hostname']
        network['router'] = backendnetworkcomponent['router']['hostname']
        network['router_mfg'] =backendnetworkcomponent['router']['hardwareChassis']['manufacturer']
        network['router_ip'] = backendnetworkcomponent['router']['primaryIpAddress']
        interfacedata.append(network)
        for trunk in backendnetworkcomponent['trunkedvlans']:
            trunkedvlan = {}
            trunkedvlan['interface'] = network['interface']
            trunkedvlan['vlanNumber'] = trunk['networkVlan']['vlanNumber']
            if 'name' in trunk['networkVlan'].keys(): trunkedvlan['vlanName'] = trunk['networkVlan']['name']
            trunkdata.append(trunkedvlan)

    print()
    print("BACKEND NETWORK INTERFACE(S)")
    print(TablePrinter(networkFormat, ul='=')(interfacedata))
    print()
    print("TAGGED VLANS BY INTERFACE")
    print(TablePrinter(trunkFormat, ul='=')(trunkdata))

    #
    # POPULATE TABLE WITH MGMT DATA
    #
    print()
    print("MGMT NETWORK")
    data = []
    network = {}

    network['mac'] = mgmtnetworkcomponent['ipmiMacAddress']
    network['primaryIpAddress'] = mgmtnetworkcomponent['ipmiIpAddress']
    network['speed'] = mgmtnetworkcomponent['speed']
    network['status'] = mgmtnetworkcomponent['status']
    network['vlan'] = hardware['networkVlans'][0]['vlanNumber']
    if 'name' in hardware['networkVlans'][0].keys(): network['vlanName'] = hardware['networkVlans'][0]['name']
    network['switch'] = mgmtnetworkcomponent['uplinkComponent']['hardware']['hostname']
    network['router'] = mgmtnetworkcomponent['router']['hostname']
    network['router_mfg'] =mgmtnetworkcomponent['router']['hardwareChassis']['manufacturer']
    network['router_ip'] = mgmtnetworkcomponent['router']['primaryIpAddress']
    data.append(network)
    print(TablePrinter(networkFormat, ul='=')(data))
    print()

    #
    # GET NETWORK STORAGE
    #
    storagealloc = client['Hardware'].getAllowedNetworkStorage(mask="iops",id=hardwareid)
    data = []
    for storage in storagealloc:
        storagerow = {}
        storagerow['type'] = storage['nasType']
        storagerow['address'] = storage['serviceResourceBackendIpAddress']
        storagerow['capacity'] = storage['capacityGb']
        storagerow['iops'] = storage['iops']
        if 'notes' in storage.keys(): storagerow['notes'] = storage['notes']
        data.append(storagerow)
    print("NETWORK STORAGE AUTHORIZED")
    print(TablePrinter(storageFormat, ul='=')(data))
    print("")

    #
    # POPULATE TABLE WITH COMPONENT DATA
    #
    result = client['Hardware'].getComponents(id=hardwareid)
    data = []
    for device in result:
        hwdevice = {}
        hwdevice['devicetype'] = \
        device['hardwareComponentModel']['hardwareGenericComponentModel']['hardwareComponentType']['type']
        hwdevice['manufacturer'] = device['hardwareComponentModel']['manufacturer']
        hwdevice['name'] = device['hardwareComponentModel']['name']
        hwdevice['description'] = device['hardwareComponentModel']['hardwareGenericComponentModel']['description']
        hwdevice['modifydate'] = device['modifyDate']
        if 'serialNumber' in device.keys(): hwdevice['serialnumber'] = device['serialNumber']
        data.append(hwdevice)
    print(TablePrinter(serverFormat, ul='=')(data))

    print(
        "__________________________________________________________________________________________________________________")
    print()
    print()
