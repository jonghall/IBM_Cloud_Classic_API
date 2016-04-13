import SoftLayer
import simplejson, time
from datetime import datetime, timedelta, tzinfo
from SoftLayer import VSManager, NetworkManager, ImageManager, Client

class SoftLayerVirtual:

    def __init__(self, client):
        self.Client = client

    def getImageTemplateGuid(self, imageName):
        imgManager = ImageManager(self.Client)
        images = imgManager.list_private_images(name=imageName)
        if len(images) == 1:
            return images[0]['globalIdentifier']
        else:
            return None

    def getVlanIdFromName(self, datacenter, vlan):
        nwManager = NetworkManager(self.Client)
        vlans = nwManager.list_vlans(datacenter=datacenter, vlan_number=vlan, mask='id')
        if len(vlans) == 1:
            return vlans[0]['id']
        else:
            return None

    def orderServer(self, counter, hostname, domain, cpus, memory, localDisk, private, hourly, datacenter, osCode, privateVlan, nicSpeed, dedicated, templateGuid, postInstallUrl, tag):
        uniqueHostname = hostname + "-" + str(counter)

        sshKeys = []
        disks = [100]

        if (osCode != None and osCode != ''):
            templateGuid = ''
        else:
            osCode = ''
            disks = [] # Blank out disks since it will use the template

        vsManager = VSManager(self.Client)
        instance = vsManager.create_instance(
            hostname = uniqueHostname,
            domain = domain,
            cpus = cpus,
            memory = memory,
            hourly = hourly,
            datacenter = datacenter,
            os_code = osCode,
            image_id = templateGuid,
            local_disk = localDisk,
            disks = disks,
            ssh_keys = sshKeys,
            nic_speed = nicSpeed,
            private = private,
            private_vlan = privateVlan,
            dedicated = dedicated,
            post_uri = postInstallUrl,
            tags = tag)

        return instance


    def provisionServers(self, quantity, hostname, domain, cpus, memory, localDisk, private, hourly, datacenter, osCode, privateVlan, nicSpeed, dedicated, templateGuid, postInstallUrl, tag):
        print 'Begin Provisioning: ' + time.strftime('%Y-%m-%d %I:%M:%S %Z')

        startTime = datetime.now()
        serverIds = []
        counter = 1
        completed = False

        if ',' in tag:
            tag = tag.split(',')[0]

        while counter <= quantity:
            createdInstance = self.orderServer(counter, hostname, domain, cpus, memory, localDisk, private, hourly, datacenter, osCode, privateVlan, nicSpeed, dedicated, templateGuid, postInstallUrl, tag)
            createdId = createdInstance['id']
            print 'Built Server: ' + str(createdId)
            serverIds.append(createdId)
            counter += 1

        
        vsManager = VSManager(self.Client)
        print 'Waiting for provisioning completion'
        while completed == False:
            time.sleep(10)

            exit = True
            for serverId in serverIds:
                time.sleep(1)
                instance = vsManager.get_instance(serverId)
                if 'activeTransaction' in instance.keys():
                    activeTransaction = instance['activeTransaction']['transactionStatus']['name']
                    if activeTransaction != 'SERVICE_SETUP':
                        exit = False

            if exit == True:
                completed = True

        print 'Sleeping for 1 minute before power off'
        time.sleep(60)

        # Power Off servers
        for serverId in serverIds:
            print 'Powering off: ' + str(serverId)
            time.sleep(1)
            self.Client['Virtual_Guest'].powerOff(id=serverId)

        time.sleep(60)
        print 'Completed Provisioning: ' + time.strftime('%Y-%m-%d %I:%M:%S %Z')
