# Create_Bulk_Users.py
import pandas as pd
from time import time
from itertools import chain
from random import seed, choice, sample
import sys, getopt, socket, SoftLayer, json, string, configparser, os, argparse, codecs


def initializeSoftLayerAPI():
    ## READ CommandLine Arguments and load configuration file
    parser = argparse.ArgumentParser(description="Create accont creates user account under Parent Account.")
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


# DEFINE password generator function
def mkpasswd(length=10, digits=2, upper=1, lower=2, special=1):
    """Create a random password

    Create a random password with the specified length and no. of
    digit, upper and lower case letters.

    :param length: Maximum no. of characters in the password
    :type length: int

    :param digits: Minimum no. of digits in the password
    :type digits: int

    :param upper: Minimum no. of upper case letters in the password
    :type upper: int

    :param lower: Minimum no. of lower case letters in the password
    :type lower: int

    :param special: Minimum no. of lower case letters in the password
    :type special: int

    :returns: A random password with the above constaints
    :rtype: str
    """

    seed(time())

    lowercase = string.ascii_lowercase
    uppercase = string.ascii_uppercase
    letters = "{0:s}{1:s}".format(lowercase, uppercase)
    specialchars = "_-|@?!~#$%^&*(){}[]+="

    password = list(
        chain(
            (choice(uppercase) for _ in range(upper)),
            (choice(specialchars) for _ in range(special)),
            (choice(lowercase) for _ in range(lower)),
            (choice(string.digits) for _ in range(digits)),
            (choice(letters) for _ in range((length - special - digits - upper - lower)))
        )
    )

    return "".join(sample(password, len(password)))


#
# Get APIKEY from config.ini & initialize SoftLayer API
#

client = initializeSoftLayerAPI()

## Prompt user forFile to use
userlist=input("Filename of userlist to create: ")

# Always display all the columns
pd.set_option('display.width', 5000)
pd.set_option('display.max_columns', 60)

wb = Workbook(userlist)
data = Range('A1').table.value
users = pd.DataFrame(data[1:], columns=data[0])

## LOOKUP USERIDS IN ACCOUNT
ObjectMask="id, username"
users = client['Account'].getUsers(mask=ObjectMask)

parent = input("Select the Parent Owner: ")

parentid=0
for user in users:
    if user['username'] == parent:
        parentid = user['id']

if parentid == 0:
    print ("Parent User not found.")
else:
    # PROCEED WITH USERID GENERATION
    print ("ID's will be created under %s (%s)" % (parent,parentid))
    suffix = input("Userid Suffix to use (ie. @class123): ")
    print ()
    for user in user_file:
        email=user['Email']
        name=user['Name']
        phone='0000000000'
        emailprefix=email[0:email.rfind("@")]
        NewUserName = emailprefix+suffix
        firstname=name[0:name.rfind(" ")]
        lastname=name[name.rfind(" ")+1:]
        password = mkpasswd() # Generate random password
        vpn_password = password # Set VPN password the same
        template_user = {
            'parentId': parentid,
            'username': NewUserName,
            'firstName':  firstname,
            'lastName': lastname,
            'email': email,
            'officePhone': phone,
            'permissionSystemVersion': 2,
            'userStatusId': 1001,
            'secondaryPasswordTimeoutDays': 90,
            'secondaryLoginRequiredFlag': '',
            }

        #---------------------------------------------
        # SET PERMISSIONS FOR NEW CHILD ACCOUNT
        # Permissions can not be greater than ParentID has
        #---------------------------------------------

Super_User = [
        {'name': 'View cPanel', 'keyName': 'VIEW_CPANEL', 'key': 'SO_1'}
        {'name': 'View Plesk', 'keyName': 'VIEW_PLESK', 'key': 'SO_2'},
        {'name': 'View Helm', 'keyName': 'VIEW_HELM', 'key': 'SO_3'},
        {'name': 'View Urchin', 'keyName': 'VIEW_URCHIN', 'key': 'SO_4'},
        {'name': 'Add Storage (StorageLayer)', 'keyName': 'ADD_SERVICE_STORAGE', 'key': 'A_10'},
        {'name': 'add / edit user', 'keyName': 'USER_MANAGE', 'key': 'A_0'},
        {'name': 'add server', 'keyName': 'SERVER_ADD', 'key': 'XX_1'},
        {'name': 'view account summary', 'keyName': 'ACCOUNT_SUMMARY_VIEW', 'key': 'A_1'},
        {'name': 'edit company', 'keyName': 'COMPANY_EDIT', 'key': 'A_2'},
        {'name': 'Update Payment Details', 'keyName': 'UPDATE_PAYMENT_DETAILS', 'key': 'A_3'},
        {'name': 'Submit One-time Payments', 'keyName': 'ONE_TIME_PAYMENTS', 'key': 'A_4'},
        {'name': 'Upgrade Server', 'keyName': 'SERVER_UPGRADE', 'key': 'A_5'},
        {'name': 'Cancel Server', 'keyName': 'SERVER_CANCEL', 'key': 'A_6'},
        {'name': 'Add Services', 'keyName': 'SERVICE_ADD', 'key': 'A_7'},
        {'name': 'Upgrade Services', 'keyName': 'SERVICE_UPGRADE', 'key': 'A_8'},
        {'name': 'Cancel Services', 'keyName': 'SERVICE_CANCEL', 'key': 'A_9'},
        {'name': 'bandwidth', 'keyName': 'BANDWIDTH_MANAGE', 'key': 'B_1'},
        {'name': 'Manage DNS', 'keyName': 'DNS_MANAGE', 'key': 'DNS_1'},
        {'name': 'forums', 'keyName': 'FORUM_ACCESS', 'key': 'F_1'},
        {'name': 'View Hardware', 'keyName': 'HARDWARE_VIEW', 'key': 'H_1'},
        {'name': 'IPMI', 'keyName': 'REMOTE_MANAGEMENT', 'key': 'H_2'},
        {'name': 'Monitoring', 'keyName': 'MONITORING_MANAGE', 'key': 'H_3'},
        {'name': 'OS Reloads', 'keyName': 'SERVER_RELOAD', 'key': 'H_4'},
        {'name': 'View licenses', 'keyName': 'LICENSE_VIEW', 'key': 'H_5'},
        {'name': 'Add Ips', 'keyName': 'IP_ADD', 'key': 'H_6'},
        {'name': 'Manage lockbox', 'keyName': 'LOCKBOX_MANAGE', 'key': 'NAS_1'},
        {'name': 'Manage NAS', 'keyName': 'NAS_MANAGE', 'key': 'NAS_2'},
        {'name': 'ssl vpn', 'keyName': 'SSL_VPN_ENABLED', 'key': 'PI_1'},
        {'name': 'Manage Port Control', 'keyName': 'PORT_CONTROL', 'key': 'PO_1'},
        {'name': 'Upgrade Port', 'keyName': 'PORT_UPGRADE', 'key': 'PU_2'},
        {'name': 'Security', 'keyName': 'SECURITY_MANAGE', 'key': 'SE_1'},
        {'name': 'View Tickets', 'keyName': 'TICKET_VIEW', 'key': 'T_1'},
        {'name': 'Search Tickets', 'keyName': 'TICKET_SEARCH', 'key': 'T_2'},
        {'name': 'Manage Load Balancers', 'keyName': 'LOADBALANCER_MANAGE', 'key': 'LBS_1'},
        {'name': 'Hardware Firewall', 'keyName': 'FIREWALL_MANAGE', 'key': 'SE_2'},
        {'name': 'Software Firewall', 'keyName': 'SOFTWARE_FIREWALL_MANAGE', 'key': 'SE_3'},
        {'name': 'Antivirus / Spyware', 'keyName': 'ANTI_MALWARE_MANAGE', 'key': 'SE_4'},
        {'name': 'Host IDS', 'keyName': 'HOST_ID_MANAGE', 'key': 'SE_6'},
        {'name': 'Vulnerability Scanning ', 'keyName': 'VULN_SCAN_MANAGE', 'key': 'SE_7'},
        {'name': 'Manage StorageLayer Notification Subscribers', 'keyName': 'NTF_SUBSCRIBER_MANAGE', 'key': 'NTF_1'},
        {'name': 'Network VLAN Spanning', 'keyName': 'NETWORK_VLAN_SPANNING', 'key': 'NET_2'},
        {'name': 'Manage CDN Account', 'keyName': 'CDN_ACCOUNT_MANAGE', 'key': 'CDN_1'},
        {'name': 'CDN File Manage', 'keyName': 'CDN_FILE_MANAGE', 'key': 'CDN_2'},
        {'name': 'View CDN Bandwidth', 'keyName': 'CDN_BANDWIDTH_VIEW', 'key': 'CDN_3'},
        {'name': 'Manage network routes', 'keyName': 'NETWORK_ROUTE_MANAGE', 'key': 'NET_1'},
        {'name': 'View CloudLayer Computing Instances', 'keyName': 'VIRTUAL_GUEST_VIEW', 'key': 'VG_1'},
        {'name': 'Reset customer portal password', 'keyName': 'RESET_PORTAL_PASSWORD', 'key': 'A_12'},
        {'name': 'Cloude Instance upgrade', 'keyName': 'INSTANCE_UPGRADE', 'key': 'A_11'},
        {'name': 'Hostname', 'keyName': 'HOSTNAME_EDIT', 'key': 'H_7'},
        {'name': 'View Tickets by Hardware Access', 'keyName': 'TICKET_VIEW_BY_HARDWARE', 'key': 'T_4'},
        {'name': 'View Tickets by Computing Instance Access', 'keyName': 'TICKET_VIEW_BY_VIRTUAL_GUEST', 'key': 'T_5'},
        {'name': 'IPSEC Network Tunnel', 'keyName': 'NETWORK_TUNNEL_MANAGE', 'key': 'NET_3'},
        {'name': 'Manage Queue Service', 'keyName': 'QUEUE_MANAGE', 'key': 'SO_6'},
        {'name': 'Manage Provisioning Scripts', 'keyName': 'CUSTOMER_POST_PROVISION_SCRIPT_MANAGEMENT', 'key': 'SO_8'},
        {'name': 'Request Compliance Report', 'keyName': 'REQUEST_COMPLIANCE_REPORT', 'key': 'COM_1'},
        {'name': 'Manage E-mail Delivery Service', 'keyName': 'NETWORK_MESSAGE_DELIVERY_MANAGE', 'key': 'NET_4'},
        {'name': 'View Event Log', 'keyName': 'USER_EVENT_LOG_VIEW', 'key': 'A_15'},
        {'name': 'Manage Network Gateways', 'keyName': 'GATEWAY_MANAGE', 'key': 'GTW_1'},
        {'name': 'Access all hardware', 'keyName': 'ACCESS_ALL_HARDWARE', 'key': 'ALL_1'},
        {'name': 'Access all guests', 'keyName': 'ACCESS_ALL_GUEST', 'key': 'ALL_2'},
        {'name': 'Manage VPN', 'keyName': 'VPN_MANAGE', 'key': 'VPN_1'},
        {'name': 'View QuantaStor', 'keyName': 'VIEW_QUANTASTOR', 'key': 'SO_7'},
        {'name': 'Physically Access a Datacenter', 'keyName': 'DATACENTER_ACCESS', 'key': 'DA_1'},
        {'name': "Physically Access a Customer's Colo Cage", 'keyName': 'DATACENTER_ROOM_ACCESS', 'key': 'DA_2'},
        {'name': 'Manage SSH Keys', 'keyName': 'CUSTOMER_SSH_KEY_MANAGEMENT', 'key': 'SE_10'},
        {'name': 'View All Tickets', 'keyName': 'TICKET_VIEW_ALL', 'key': 'T_6'},
        {'name': 'Add Tickets', 'keyName': 'TICKET_ADD', 'key': 'T_7'},
        {'name': 'Edit Tickets', 'keyName': 'TICKET_EDIT', 'key': 'T_8'},
        {'name': 'Manage Firewall Rules', 'keyName': 'FIREWALL_RULE_MANAGE', 'key': 'FW_1'},
        {'name': 'Manage Public Images', 'keyName': 'PUBLIC_IMAGE_MANAGE', 'key': 'I_1'},
        {'name': 'View Certificates (SSL)', 'keyName': 'SECURITY_CERTIFICATE_VIEW', 'key': 'SE_8'},
        {'name': 'Manage Certificates (SSL)', 'keyName': 'SECURITY_CERTIFICATE_MANAGE', 'key': 'SE_9'},
        {'name': 'Manage Scaling Groups', 'keyName': 'SCALE_GROUP_MANAGE', 'key': 'SG_1'}]

Network_User = [
        {'name': 'view account summary', 'keyName': 'ACCOUNT_SUMMARY_VIEW', 'key': 'A_1'},
        {'name': 'bandwidth', 'keyName': 'BANDWIDTH_MANAGE', 'key': 'B_1'},
        {'name': 'forums', 'keyName': 'FORUM_ACCESS', 'key': 'F_1'},
        {'name': 'View Hardware', 'keyName': 'HARDWARE_VIEW', 'key': 'H_1'},
        {'name': 'IPMI', 'keyName': 'REMOTE_MANAGEMENT', 'key': 'H_2'},
        {'name': 'Monitoring', 'keyName': 'MONITORING_MANAGE', 'key': 'H_3'},
        {'name': 'Add Ips', 'keyName': 'IP_ADD', 'key': 'H_6'},
        {'name': 'ssl vpn', 'keyName': 'SSL_VPN_ENABLED', 'key': 'PI_1'},
        {'name': 'Manage Port Control', 'keyName': 'PORT_CONTROL', 'key': 'PO_1'},
        {'name': 'Upgrade Port', 'keyName': 'PORT_UPGRADE', 'key': 'PU_2'},
        {'name': 'View Tickets', 'keyName': 'TICKET_VIEW', 'key': 'T_1'},
        {'name': 'Search Tickets', 'keyName': 'TICKET_SEARCH', 'key': 'T_2'},
        {'name': 'Manage Load Balancers', 'keyName': 'LOADBALANCER_MANAGE', 'key': 'LBS_1'},
        {'name': 'Hardware Firewall', 'keyName': 'FIREWALL_MANAGE', 'key': 'SE_2'},
        {'name': 'Network VLAN Spanning', 'keyName': 'NETWORK_VLAN_SPANNING', 'key': 'NET_2'},
        {'name': 'Manage network routes', 'keyName': 'NETWORK_ROUTE_MANAGE', 'key': 'NET_1'},
        {'name': 'View Tickets by Hardware Access', 'keyName': 'TICKET_VIEW_BY_HARDWARE', 'key': 'T_4'},
        {'name': 'View Tickets by Computing Instance Access', 'keyName': 'TICKET_VIEW_BY_VIRTUAL_GUEST', 'key': 'T_5'},
        {'name': 'IPSEC Network Tunnel', 'keyName': 'NETWORK_TUNNEL_MANAGE', 'key': 'NET_3'},
        {'name': 'Manage Network Gateways', 'keyName': 'GATEWAY_MANAGE', 'key': 'GTW_1'},
        {'name': 'Manage VPN', 'keyName': 'VPN_MANAGE', 'key': 'VPN_1'},
        {'name': 'Add Tickets', 'keyName': 'TICKET_ADD', 'key': 'T_7'},
        {'name': 'Edit Tickets', 'keyName': 'TICKET_EDIT', 'key': 'T_8'},
        {'name': 'Manage Firewall Rules', 'keyName': 'FIREWALL_RULE_MANAGE', 'key': 'FW_1'}]

ViewOnly_User = [
        {'name': 'View cPanel', 'keyName': 'VIEW_CPANEL', 'key': 'SO_1'}
        {'name': 'View Plesk', 'keyName': 'VIEW_PLESK', 'key': 'SO_2'},
        {'name': 'View Helm', 'keyName': 'VIEW_HELM', 'key': 'SO_3'},
        {'name': 'View Urchin', 'keyName': 'VIEW_URCHIN', 'key': 'SO_4'},
        {'name': 'view account summary', 'keyName': 'ACCOUNT_SUMMARY_VIEW', 'key': 'A_1'},
        {'name': 'bandwidth', 'keyName': 'BANDWIDTH_MANAGE', 'key': 'B_1'},
        {'name': 'View licenses', 'keyName': 'LICENSE_VIEW', 'key': 'H_5'},
        {'name': 'Add Ips', 'keyName': 'IP_ADD', 'key': 'H_6'},
        {'name': 'View Tickets', 'keyName': 'TICKET_VIEW', 'key': 'T_1'},
        {'name': 'View CDN Bandwidth', 'keyName': 'CDN_BANDWIDTH_VIEW', 'key': 'CDN_3'},
        {'name': 'View CloudLayer Computing Instances', 'keyName': 'VIRTUAL_GUEST_VIEW', 'key': 'VG_1'},
        {'name': 'View Tickets by Hardware Access', 'keyName': 'TICKET_VIEW_BY_HARDWARE', 'key': 'T_4'},
        {'name': 'View Tickets by Computing Instance Access', 'keyName': 'TICKET_VIEW_BY_VIRTUAL_GUEST', 'key': 'T_5'},
        {'name': 'View All Tickets', 'keyName': 'TICKET_VIEW_ALL', 'key': 'T_6'},
        {'name': 'View Certificates (SSL)', 'keyName': 'SECURITY_CERTIFICATE_VIEW', 'key': 'SE_8'}]



        #---------------------------------------------
        # Write Record to file (before creating so password not lost
        #---------------------------------------------
        row={'name': name, 'email': email, "newusername": NewUserName, "password": password}
        csvwriter.writerow(row)
        print (row)
        
        #---------------------------------------------
        # Create New Child User ID
        #---------------------------------------------
        try:
            new_user = client['User_Customer'].createObject(template_user, password, vpn_password)
        except SoftLayer.SoftLayerAPIError as e:
            print("Error: %s, %s" % (e.faultCode, e.faultString))
            out_file.close()
            user_file.close()
            quit()
           
        #---------------------------------------------
        #Get new userid number which was created
        #---------------------------------------------
        userid = new_user['id']

        #---------------------------------------------
        # Give SSL VPN Access to new USERID
        # Note: Won't work if you specify flag oninitial create
        #---------------------------------------------
        template_user = {
            'sslVpnAllowedFlag': True,
            }
        result = client['User_Customer'].editObject(template_user,id=userid)

        #---------------------------------------------
        # SET BULK PERMISSIONS OF NEW USER
        #---------------------------------------------
        result = client['User_Customer'].addBulkPortalPermission(bulkpermission, id = userid)

        #---------------------------------------------
        # Put USER under new parent
        # Note: Won't work if you specify flag oninitial create
        #---------------------------------------------

        template_user = {
            'parentId': parentid,
            }

        result = client['User_Customer'].editObject(template_user,id=userid)


    out_file.close()
    user_file.close()

