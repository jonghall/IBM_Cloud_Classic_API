#
# ADD SOFTLAYER FIREWALL RULE EXAMPLE
#
import sys, socket, SoftLayer, json, configparser, argparse, csv

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
        client = SoftLayer.Client(username=user, api_key=key)
    return client


## READ CommandLine Arguments and load configuration file
parser = argparse.ArgumentParser(description="Add a Firewall Rule to SoftLayer Firewall")
parser.add_argument("-u", "--username", help="SoftLayer API Username")
parser.add_argument("-k", "--apikey", help="SoftLayer APIKEY")
parser.add_argument("-c", "--config", help="config.ini file to load")
parser.add_argument("-v", "--hostname", help="Hostname of VSI to add rule")

args = parser.parse_args()

if args.hostname == None:
    hostlookup = input("Add firewall rules for host: ")
else:
    hostlookup=args.hostname

client = initializeSoftLayerAPI(args.username, args.apikey, args.config)


## GET LIST OF HOSTNAMES & CORRESPONDING VIRTUAL ID
vsis = client['Account'].getVirtualGuests(mask="id,fullyQualifiedDomainName")

## FIND VIRTUAL ID FOR HOST
parentid=0
for vsi in vsis:
    if vsi['fullyQualifiedDomainName'] == hostlookup:
        vsiid = vsi['id']

        ## GET FIREWALL ID FOR THIS HOST
        result = client['Virtual_Guest'].getFirewallServiceComponent(id = vsiid)
        firewall = result['id']

        ## GET COUNT OF EXISTING RULES FOR HOST
        rules = client['Network_Component_Firewall'].GetRules(id = firewall)
        next_rule = len(rules) + 1

        ## POPULATE FIREWALL RULES INTO OBJECT
        newRule = {
            'action': 'permit',
            'destinationIpAddress': '198.11.194.154',
            'destinationIpSubnetMask': '255.255.255.255',
            'sourceIpAddress': 'any',
            'sourceIpSubnetMask': 'any',
            'protocol': 'tcp',
            'destinationPortRangeStart': 25,
            'destinationPortRangeEnd': 25,
            'orderValue': next_rule,
               }

        rules.append(newRule)

        request_template = {
           'networkComponentFirewallId': firewall,
           'rules': rules
               }

        ## SUBMIT FIREWALL RULE UPDATE REQUEST
        result = client['Network_Firewall_Update_Request'].createObject(request_template, id=firewall)
        print (json.dumps(result,indent=4))
