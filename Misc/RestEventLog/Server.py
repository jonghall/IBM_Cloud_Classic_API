import sys, time,  SoftLayer, os, json
from datetime import datetime
import pytz
from flask import Flask, jsonify, request

app = Flask(__name__)
port = os.getenv('VCAP_APP_PORT', '5000')
@app.route('/vms/<id>/<user>/<key>', methods=['GET'])
def get_power_on(id,user,key):
	client = SoftLayer.Client(username=user, api_key=key)
	events = client['Event_Log'].getAllObjects(filter={'objectId': {'operation':id},'eventName': {'operation': 'Power On'}})
	eventdate = datetime.now(pytz.UTC)
	powerOnDate = datetime.now(pytz.UTC)
	found=0
	for event in events:
		if event['eventName']=="Power On":
			eventdate = event["eventCreateDate"]
			eventdate = eventdate[0:29]+eventdate[-2:]
			eventdate = datetime.strptime(eventdate, "%Y-%m-%dT%H:%M:%S.%f%z")
			if eventdate<powerOnDate:
				powerOnDate = eventdate
				found=1

	if found==1: 
		return jsonify({'powerOn':powerOnDate})
	else:
		return jsonify({'powerOn':'notAvailable'})

@app.route('/vmsarray/<user>/<key>', methods=['POST'])
def get_array_power_on(user,key):
	client = SoftLayer.Client(username=user, api_key=key)
	serverlist = request.get_json()
	responseArray={}
	for server in serverlist:
		events = client['Event_Log'].getAllObjects(filter={'objectId': {'operation':server['id']},'eventName': {'operation': 'Power On'}})
		eventdate = datetime.now(pytz.UTC)
		powerOnDate = datetime.now(pytz.UTC)
		found=0
		for event in events:
			if event['eventName']=="Power On":
				eventdate = event["eventCreateDate"]
				eventdate = eventdate[0:29]+eventdate[-2:]
				eventdate = datetime.strptime(eventdate, "%Y-%m-%dT%H:%M:%S.%f%z")
				if eventdate<powerOnDate:
					powerOnDate = eventdate
					found=1
		if found==1:
			responseArray[server['id']]=powerOnDate
		else:
			responseArray[server['id']]='notAvailable'
	return jsonify(responseArray)

if __name__ == '__main__':
	app.debug = True.
	
	app.run(host='0.0.0.0',port=int(port))




            