import paho.mqtt.publish as publish
from picamera import PiCamera
from time import sleep
import time
from gpiozero import MotionSensor
import socket
import datetime
import os
import shutil
import commands

#Authors:
#Dylan Logan

#Master Publisher code for multiple sensors photo triggering
#Periodically polls the sensors in the camera array and takes a picture if a set ratio is met
setup = true 
main = false

while setup
	print("Started master multisensor photo sync program")

	MQTT_SERVER = "localhost" #master Pi IP address
	MQTT_PATH = "test" #topic name for MQTT
	path = '/home/pi/cameraTrapPhotos/'
	pir = MotionSensor(4) #use motion sensor
	camera = PiCamera() #use camera
	access_rights = 0o777

	#create a directory if one does not exist for the camera trap photos
	if(os.path.isdir(path)==False):
		os.mkdir(path,access_rights)
	#else, remove all photos and photo sets currently in the directory
	else:
		for fname in os.listdir(path):
			shutil.rmtree(path+fname)

	IPAddr = commands.getoutput("hostname -I") #get Pi's own IP address
	
	#set socket for listening to slave pis
	s = socket.socket()
	s.settimeout(30) #set a time for the socket to be open for. This is purposefully long in lue of a delay
	s.bind(('',12345)) #bind the socket to a unused undesignated port
	
	sensors_connected = [] #list of all the slaves that connect to the master
	message = "Setup"
	sensors_connected.append([str(IPAddr)])
	publish.single(MQTT_PATH,message,hostname=MQTT_SERVER) #send message see which slave sensors are looking to connect
	s.listen(10) #set socket to take a backlog of 10. increase number if there are more slaves to be connected
	print("Socket is listening for setup")
	
	while True:
		try:
			c,addr = s.accept() #accept connections from slave pis
			print('Got connection from', addr)
			receivedIP = str(c.recv(1024))
			sensors_connected.append([receivedIP])
			c.close()

		except socket.timeout:
			break
	
	total_sensors = len(sensors_connested)
	if (total_sensors > 3):
		thresh_pass = floor(2/3*total_sensors) #this creates the threshold to take a picture as two thirds of the total sensors rounding down
		thresh_fail = (ceil(1/3*total_sensors)) + 1 #this sets a fail flag
	threshold = 0.67 #threshold for taking photo, percent of sensors that need to be true to take a photo, configurable
	photoNum = 1 #current set/photo number
	delay = 30 #amount of time in seconds to rest after a photo session (should be greater than 30 seconds)



	
	main = true
	setup = false
	break

#run continously until terminated by user
while True:
	sensorlist = [] #list of all devices by their ip addresses and their sensor readings
	print("Resting...")
	sleep(delay)
	print("Starting")
	message = "Info"
	publish.single(MQTT_PATH,message,hostname=MQTT_SERVER) #send message get info about slave sensors

    #put sensor state of master pi in sensor list
	if(pir.motion_detected==True):
		sensorlist.append([str(IPAddr).rstrip(),str(True)])
	else:
		sensorlist.append([str(IPAddr).rstrip(),str(False)])

    #listen for incoming connections
	s.listen(5)
	print("Socket is listening")

    #get data from slave pis by listening to socket and parse it and add it to sensor list
	while True:
		try:
			c,addr = s.accept() #accept connections from slave pis
			print('Got connection from', addr)
			receivedInfo = str(c.recv(1024))

            #parse data and add it to the sensor list
			splitInfo = receivedInfo.split()
			receivedIP = splitInfo[0]
			receivedSensor = splitInfo[1]
			sensorlist.append([receivedIP,receivedSensor])
			c.close()

		except socket.timeout:
			break

	#list of all devices and their sensor readings
	for x in sensorlist:
		print(x)

    #calculate percentage of sensors that show true
	numSensors = float(0)
	numTrue = float(0)
	for i, element in enumerate(sensorlist):
		numSensors = numSensors + 1
		if element[1] == "True":
			numTrue = numTrue + 1
	ratio = numTrue/numSensors
	print("ratio: " + str(ratio))

    #if ratio is above the threshold, start a photo session
	if(ratio>threshold):
		#Send MQTT message to slaves to take photo and start photo
		message = "Take Synced Photo " + str(photoNum)
		publish.single(MQTT_PATH,message,hostname=MQTT_SERVER)
		ctpath = '/home/pi/cameraTrapPhotos/set' + str(photoNum) +  '/'
		access_rights = 0o777 #permissions for directory
        #make directory for current photo session
		try:
			os.mkdir(ctpath,access_rights)
		except OSError:
			print("creation of the directory %s failed" % ctpath)
		else:
			print("successfully created the directory %s" % ctpath)

        #set camera and file parameters
		filename = 'set'+str(photoNum)+'_camera1.jpg'
		camera.resolution=(3280,2464)
		camera.shutter_speed = 30000

		#Take Photo
		camera.capture(ctpath+filename)
		#End of Photo session

		print("Camera 1 photo number "+ str(photoNum) + " taken")
		#go to next photo session
		photoNum = photoNum + 1
