__author__ = 'jonhall'
## List powerstate for VirtualServers in Datacenter

## BUILD CSV FILE FOR USE WITH PowerOffVirtualServers & PowerOnVirtualServers
## FIELDS CREATED: ORDER, ID, HOSTNAME, WAIT
## ORDER = Order of PowerOff/PowerOn.  Set Sequentially by VSI ID.  Modify to requirements.
## ID = VSI ID
## fullyQualifiedDomainName = SL fullyQualifiedDomainName (IF VSI PRESENT ONLY USED FOR DISPLAY PURPOSES)
## WAIT = Set to Zero by Script, # of second to wait after powering on or off VM before moving to next VM.  Modify as needed
## Example csv file created
## Order,id,fullyQualifiedDomainName,wait
## 1,13405579,centos02.ibmsldemo.com,60
## 2,13405577,centos01.ibmsldemo.com,30
## 3,13405581,centos03.ibmsldemo.com,30

import SoftLayer, configparser, argparse, csv

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
parser = argparse.ArgumentParser(description="List powerstate for VirtualServers in Datacenter")
parser.add_argument("-u", "--username", help="SoftLayer API Username")
parser.add_argument("-k", "--apikey", help="SoftLayer APIKEY")
parser.add_argument("-c", "--config", help="config.ini file to load")
parser.add_argument("-d", "--datacenter", help="Filter by Datacenter")
parser.add_argument("-o", "--output", help="serverfile to create")

args = parser.parse_args()

client = initializeSoftLayerAPI(args.username, args.apikey, args.config)

if args.datacenter == None:
    virtualServerFilter={}
else:
    virtualServerFilter={'virtualGuests': {'datacenter': {'name': {'operation': args.datacenter}}}}
    datacenter=args.datacenter

if args.output == None:
    outputname = input("Output filename:")
else:
    outputname = args.output


## OPEN CSV FILE UP FOR WRITING
outfile = open(outputname, 'w')
csvwriter = csv.writer(outfile, delimiter='\t', quotechar='"', quoting=csv.QUOTE_ALL)
fieldnames = ['order', 'id', 'fullyQualifiedDomainName', 'wait']
csvwriter = csv.DictWriter(outfile, delimiter=',', fieldnames=fieldnames)
csvwriter.writerow(dict((fn, fn) for fn in fieldnames))

# CREATE API FILTER TO FILTER

virtualServers = client['Account'].getVirtualGuests(mask='id,fullyQualifiedDomainName,datacenter.name',filter=virtualServerFilter)

print ('{:<10} {:<20}'.format("ID", "fullyQualifiedDomainName"))
print ('{:<10} {:<20}'.format("==========", "================"))

order=0
for server in virtualServers:
    order=order+1
    print("{:<10} {:<20}".format(server['id'], server['fullyQualifiedDomainName']))
    row = {'order': order,
           'id': server['id'],
           'fullyQualifiedDomainName': server['fullyQualifiedDomainName'],
           'wait': 0
          }
    csvwriter.writerow(row)
outfile.close()