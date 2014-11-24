##
## Account Bare Metal Configuration Report
## Pass username & apikey to script

import sys,getopt,socket,SoftLayer,json,string


client = SoftLayer.Client(username= sys.argv[1], api_key = sys.argv[2])


#
# FORMAT TABLE                
#
class TablePrinter(object):
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
        super(TablePrinter,self).__init__()
        self.fmt   = str(sep).join('{lb}{0}:{1}{rb}'.format(key, width, lb='{', rb='}') for heading,key,width in fmt)
        self.head  = {key:heading for heading,key,width in fmt}
        self.ul    = {key:str(ul)*width for heading,key,width in fmt} if ul else None
        self.width = {key:width for heading,key,width in fmt}

    def row(self, data):
        return self.fmt.format(**{ k:str(data.get(k,''))[:w] for k,w in self.width.items() })

    def __call__(self, dataList):
        _r = self.row
        res = [_r(data) for data in dataList]
        res.insert(0, _r(self.head))
        if self.ul:
            res.insert(1, _r(self.ul))
        return '\n'.join(res)

#
# BUILD TABLES
#
networkFormat = [
        ('MAC ',              'mac',                    17),
        ('IpAddress',         'primaryIpAddress',       16),
        ('speed',             'speed',                  5),
        ('status',            'status',                 10),
        ('Vlan',              'vlan',                   5),
        ('Vlan Name',         'vlanName',               20),
        ('Router',            'router',                 30),
    ]


serverFormat = [
        ('Type   ',       'devicetype',        15),
        ('Manufacturer',  'manufacturer',      15),
        ('Name',          'name',              20),
        ('Description',   'description',       30),
        ('Modify Date',   'modifydate',        25),
        ('Serial Number', 'serialnumber',      15)
    ]

trunkFormat = [
        ('VlanID',          'vlanid',                8),
        ('VlanNumber',    'vlanNumber',             10),
        ('VlanName',      'vlanName',               20)
    ]



#
# GET LIST OF ALL DEDICATED HARDWARE IN ACCOUNT
#

hardwarelist =client['Account'].getHardware(mask='datacenterName')

for hardware in hardwarelist:

    #if hardware['datacenterName'] != 'Paris 1':
    #        continue
                
    hardwareid = hardware['id']
    
    
    #
    # LOOKUP HARDWARE INFORMATION BY HARDWARE ID
    #
    
    mask_object="datacenterName,networkVlans,backendRouters,frontendRouters,backendNetworkComponentCount,backendNetworkComponents,frontendNetworkComponentCount,frontendNetworkComponents,uplinkNetworkComponents"
    hardware = client['Hardware'].getObject(mask=mask_object, id = hardwareid)

    # FIND Index for MGMT Interface and get it's ComponentID Number
    index=0
    mgmtindex=0
    for backend in hardware['backendNetworkComponents']:
        if backend['name'] == "mgmt":
            mgmtindex=index
            mgmtcomponentid=backend['id']
            continue
        index=index+1

    # FIND Private Index & COmponentID Number
    index=0
    privateindex=0
    for backend in hardware['backendNetworkComponents']:
        if backend['name'] == "eth" and 'primaryIpAddress' in backend.keys():
            privateindex=index
            privatenetworkcomponentid=backend['id']
            continue
        index=index+1
        
    # FIND Public Index & COmponentID Number
    index=0
    publicindex=0
    for frontend in hardware['frontendNetworkComponents']:
        if frontend['name'] == "eth" and 'primaryIpAddress' in frontend.keys():
            publicindex=index
            publiccomponentid=frontend['id']
            continue
        index=index+1

            
    # Get VLAN Trunks for network_compondent ID
    network = client['Network_Component'].getObject(mask='uplinkComponent', id=privatenetworkcomponentid)
    trunks = client['Network_Component'].getNetworkVlanTrunks(mask='networkVlan', id=network['uplinkComponent']['id'])
 
    print ("__________________________________________________________________________________________________________________")
    print ()
    print ("Hostname        : %s" % (hardware['fullyQualifiedDomainName']))
    print ("Datacenter      : %s" % (hardware['datacenterName']))
    print ("Serial #        : %s" % (hardware['manufacturerSerialNumber']))
    print ("__________________________________________________________________________________________________________________")


    #
    # POPULATE TABLE WITH FRONTEND DATA
    #
  
    print ()
    print ("FRONTEND NETWORK")
    data=[]
    network={}
    network['mac']=hardware['frontendNetworkComponents'][publicindex]['macAddress']
    if 'primaryIpAddress' in hardware['frontendNetworkComponents'][publicindex].keys(): network['primaryIpAddress']=hardware['frontendNetworkComponents'][publicindex]['primaryIpAddress']
    network['speed']=hardware['frontendNetworkComponents'][publicindex]['speed']
    network['status']=hardware['frontendNetworkComponents'][publicindex]['status']
    network['router']=hardware['frontendRouters'][publicindex]['fullyQualifiedDomainName']
    if len(hardware['networkVlans'])>1:
        network['vlan']=hardware['networkVlans'][1]['vlanNumber']
        if 'name' in hardware['networkVlans'][1].keys(): network['vlanName']=hardware['networkVlans'][0]['name']
    data.append(network)
    print( TablePrinter(networkFormat, ul='=')(data)) 

    #
    # POPULATE TABLE WITH BACKEND DATA
    #
    print ()
    print ("BACKEND NETWORK")
    data=[]
    network={}
    network['mac']=hardware['backendNetworkComponents'][privateindex]['macAddress']
    network['primaryIpAddress']=hardware['backendNetworkComponents'][privateindex]['primaryIpAddress']
    network['speed']=hardware['backendNetworkComponents'][privateindex]['speed']
    network['status']=hardware['backendNetworkComponents'][privateindex]['status']
    network['vlan']=hardware['networkVlans'][0]['vlanNumber']
    if 'name' in hardware['networkVlans'][0].keys(): network['vlanName']=hardware['networkVlans'][0]['name']
    network['router']=hardware['backendRouters'][0]['fullyQualifiedDomainName']
    data.append(network)
    print( TablePrinter(networkFormat, ul='=')(data))     

    #
    # PRINT TRUNKED VLANS
    #
    
    print ()
    print ("TRUNKED/TAGGED VLANS")
    data=[]
    for trunk in trunks:
        trunkedvlan={}
        trunkedvlan['vlanid']=trunk['networkVlan']['id']
        trunkedvlan['vlanNumber']=trunk['networkVlan']['vlanNumber']
        if 'name' in trunk['networkVlan'].keys(): trunkedvlan['vlanName']=trunk['networkVlan']['name']
        data.append(trunkedvlan)
    print( TablePrinter(trunkFormat, ul='=')(data)) 
    
    #
    # POPULATE TABLE WITH MGMT DATA
    #
    print ()
    print ("MGMT NETWORK")
    data=[]
    network={}
    network['mac']=hardware['backendNetworkComponents'][mgmtindex]['ipmiMacAddress']
    network['primaryIpAddress']=hardware['networkManagementIpAddress']
    network['speed']=hardware['backendNetworkComponents'][mgmtindex]['speed']
    network['status']=hardware['backendNetworkComponents'][mgmtindex]['status']
    network['vlan']=hardware['networkVlans'][0]['vlanNumber']
    if 'name' in hardware['networkVlans'][0].keys(): network['vlanName']=hardware['networkVlans'][0]['name']
    network['router']=hardware['backendRouters'][0]['fullyQualifiedDomainName']
    data.append(network)
    print( TablePrinter(networkFormat, ul='=')(data))     

    print ()

    result = client['Hardware'].getComponents(id = hardwareid)
    

    #
    # POPULATE TABLE WITH COMPONENT DATA
    #
    data=[]
    for device in result:
        hwdevice={}
        hwdevice['devicetype']=device['hardwareComponentModel']['hardwareGenericComponentModel']['hardwareComponentType']['type']
        hwdevice['manufacturer']=device['hardwareComponentModel']['manufacturer']
        hwdevice['name']=device['hardwareComponentModel']['name']
        hwdevice['description']=device['hardwareComponentModel']['hardwareGenericComponentModel']['description']
        hwdevice['modifydate']=device['modifyDate']
        if 'serialNumber' in device.keys(): hwdevice['serialnumber']=device['serialNumber']                                                                                                                      
        data.append(hwdevice)

    #
    # PRINT DATA TABLE
    #
    
    print( TablePrinter(serverFormat, ul='=')(data) )
    print ("__________________________________________________________________________________________________________________")
    print ()
    print ()
