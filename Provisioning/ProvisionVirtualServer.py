import sys, getopt, socket, time,  SoftLayer, json, string, configparser, os, argparse


def initializeSoftLayerAPI():
    ## READ CommandLine Arguments and load configuration file
    parser = argparse.ArgumentParser(description="Provisiong single VSI.")
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
        client = SoftLayer.Client(username=args.username, api_key=args.apikey)
    return client


#
# Get APIKEY from config.ini & initialize SoftLayer API
#

client = initializeSoftLayerAPI()



def getDataCenterId(datacenters):
    print ("Datacenter to provision Cloud Compute Instance in: ")
    n=0
    for datacenter in datacenters:
        n=n+1
        print ("%s. %s" % (n, datacenter['template']['datacenter']['name']))
    num = int(input ("Choose: "))
    datacenterid = datacenters[num-1]['template']['datacenter']
    return datacenterid

def getCpus(cpus):
    print ()
    print ("Select the number of starting CPUs: ")
    n=0
    for cpu in cpus:
        n=n+1
        print ("%s. %s - Hourly: %s Monthly %s" % (n,cpu['itemPrice']['item']['description'], cpu['itemPrice']['hourlyRecurringFee'], cpu['itemPrice']['recurringFee']))
    num = int(input ("Choose: "))
    cpus = cpus[num-1]['template']['startCpus']
    return cpus

def getMemory(memory):
    print ()
    print ("Select the Maximum Memory: ")
    n=0
    for mem in memory:
        n=n+1
        print ("%s. %s - Hourly: %s Monthly %s" % (n,mem['itemPrice']['item']['description'], mem['itemPrice']['hourlyRecurringFee'], mem['itemPrice']['recurringFee']))
    num = int(input ("Choose: "))
    startCpus = memory[num-1]['template']['maxMemory']
    return startCpus

def getDisk(disks):
    print ()
    print ("Select block devices for OS: ")
    n=0
    for disk in disks:
        n=n+1
        print ("%s. %s - Hourly: %s Monthly %s" % (n, disk['itemPrice']['item']['description'], disk['itemPrice']['hourlyRecurringFee'], disk['itemPrice']['recurringFee']))
    num = int(input ("Choose: "))
    diskoption = disks[num-1]['template']
    localdisk= disks[num-1]['template']
    return diskoption

def getos(oses):
    print ()
    print ("Select the OS: ")
    n=0
    for os in oses:
        n=n+1
        if 'hourlyRecurringFee' in os.keys():
            print ("%s. %s - Hourly: %s Monthly %s" % (n, os['itemPrice']['item']['description'], os['itemPrice']['hourlyRecurringFee'], os['itemPrice']['recurringFee']))
        else:
            print ("%s. %s - Hourly: NA Monthly %s" % (n, os['itemPrice']['item']['description'], os['itemPrice']['recurringFee']))
    num = int(input ("Choose: "))
    osoption = oses[num-1]['template']['operatingSystemReferenceCode']
    return osoption

###############################################################
# BUILD ORDER                                                 #
###############################################################

#Get CCI Object Options
cci_options = client['Virtual_Guest'].getCreateObjectOptions()

#Prompt & Choose options

datacenter=getDataCenterId(cci_options['datacenters'])
cpus=getCpus(cci_options['processors'])
memory=getMemory(cci_options['memory'])
disk=getDisk(cci_options['blockDevices'])
blockdevice=disk['blockDevices']
localdisk=disk['localDiskFlag']
os=getos(cci_options['operatingSystems'])

# Get Quantity & Populate Hostnames
hostname = input("Hostname: ")
domain = input("Domain: ")

newcci=  {
        "hostname": hostname,
        "domain": domain,
        "datacenter": datacenter,
        "startCpus": cpus,
        "maxMemory": memory,
        "operatingSystemReferenceCode": os,
        "hourlyBillingFlag": True,
        "localDiskFlag": localdisk,
        "prices": [{'id': 32139}]
         }

print ()
print ("Order to be verified:", newcci)
print ()

try:
    verifiedOrder = client['Virtual_Guest'].generateOrderTemplate(newcci)
    print (json.dumps(verifiedOrder, indent=4))
    result = client['Virtual_Guest'].createObject(newcci)
    #print (json.dumps(result, indent=4))
except SoftLayer.SoftLayerAPIError as e:
    print("Error: %s, %s" % (e.faultCode, e.faultString))
    exit()

new_cci_id=result['id']
object_mask = "createDate, provisionDate, activeTransaction"

result = client['Virtual_Guest'].getObject(mask=object_mask, id = new_cci_id)
print ("CCI %s (%s) provisioning initiated at %s." % (hostname, new_cci_id, result['createDate']))
print ("Script will check for completion every 10 seconds.")
print
print (json.dumps(result,indent=4))
while (result['provisionDate']==""):
    time.sleep(10)
    print ("Checking for CCI provisioning completion...")
    result = client['Virtual_Guest'].getObject(mask=object_mask, id = new_cci_id)
    print (json.dumps(result,indent=4))


### Print CCI information

object_mask="id,hostname,domain,startCpus,maxMemory,primaryIpAddress,primaryBackendIpAddress,createDate,provisionDate,activeTransaction"
result=client['Virtual_Guest'].getObject(mask=object_mask, id = new_cci_id)
print ()
print ("Provisioning Complete!")
print ("----------------------")
print ("ID: %s" % (result['id']))
print ("Hostname: %s" % (result['hostname']))
print ("Domain: %s" % (result['domain']))
print ("CPUs: %s" % (result['startCpus']))
print ("Memory: %s" % (result['maxMemory']))
print ("PrimaryIP: %s" % (result['primaryIpAddress']))
print ("BackendIP: %s" % (result['primaryBackendIpAddress']))
print ("CreateDate: %s" % (result['createDate']))
print ("ProvisionedDate: %s" % (result['provisionDate']))


