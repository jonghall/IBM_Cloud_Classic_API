#
# Remove a Trunked VLAN from Server
#
import SoftLayer
import sys,getopt,socket,json,string


client = SoftLayer.Client(username= sys.argv[1], api_key = sys.argv[2])


# Lookup Hostname
fullyQualifiedDomainName = input("fully qualified Domain name: ")
hardwarelist =client['Account'].getHardware()

for hardware in hardwarelist:
    if hardware['fullyQualifiedDomainName'] == fullyQualifiedDomainName:
        hardwareid=hardware['id']
        continue    

mask_object="networkVlans,uplinkNetworkComponents"
hardware = client['Hardware'].getObject(mask=mask_object, id = hardwareid)

# Get Tunked VLAN details & remove

try:
    # FIND uplink network Index Number
    index=0
    for uplink in hardware['uplinkNetworkComponents']:
        if uplink['name'] == "eth" and 'primaryIpAddress' in uplink.keys():
                uplinkid=uplink['id']
                continue

    # Get Network Component ID for Uplink
    network = client['Network_Component'].getObject(mask='uplinkComponent', id=uplinkid)

    networkcomponentid=network['id']
    uplinkcomponentid=network['uplinkComponent']['id']

    # Get VLAN Trunks for network_compondent ID
    trunks = client['Network_Component'].getNetworkVlanTrunks(mask='networkVlan', id=uplinkcomponentid)
    
    trunkindex=0
    for trunk in trunks:
        trunkindex=trunkindex+1
        print ("VLAN Trunk #%s: %s (%s)" % (trunkindex, trunk['networkVlan']['name'],trunk['networkVlan']['vlanNumber']))

    vlantrunknum = int(input("VLAN Trunk # to remove: "))
          
    vlanid = [trunks[vlantrunknum-1]['networkVlan']]
    vlanNumber = [trunks[vlantrunknum-1]['networkVlan']['vlanNumber']]


    print ("Removing vlan %s trunk for device %s." % (vlanNumber, fullyQualifiedDomainName))

    # Remove Selected VLAN from trunk using network component.  Trunk is actually removed from uplink
    result = client['Network_Component'].removeNetworkVlanTrunks(vlanid, id=networkcomponentid)
    print (json.dumps(result, indent=4))

    
except SoftLayer.SoftLayerAPIError as e:
    print("Error: %s, %s" % (e.faultCode, e.faultString))

