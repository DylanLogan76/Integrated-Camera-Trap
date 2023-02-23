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
setup = True 
main = False

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
		thresh_fail = (ceil(1/3*total_sensors)) + 1 #this sets a fail flag. if this many sensors arent seeing motion we wont take a picture
		main = True
	elif (total_sensors < 3): #if there is only one slave connected then the script is not run
		print("you dont have enough connected sensors")
	else: #this is the minimum number of sensors to create a usable model therefore it is a special case where all the sensors must detect heat
		thresh_pass = 3
		thresh_fail = 1
		main = True
	setup = False #changes the setup variable to false so it only runs once
	delay = 30 #THIS MUST BE SET TO REAL VALUE this is the delay between which we will poll the sensors. 
	            #it was chosen based on approximate diameter of senor array (D) animal speed (V)
	s.settimeout(10) #sets a new time for reading sensor outputs. shouldnt need to be this high
	break #ends the loop

#run continously until terminated by user
while main:
	print("Resting...")
	pass_flag = 0 #resets flags every loop
	fail_flag = 0
	sleep(delay)
	print("Starting")
	message = "Info"
	publish.single(MQTT_PATH,message,hostname=MQTT_SERVER) #send message get info about slave sensors

    #put sensor state of master pi in sensor list
	if(pir.motion_detected==True):
		pass_flag +=  1 #increments the pass count if motion is seen on master
	else:
		fail_flag += 1 #increments the fail count if motion is not seen on master

    #listen for incoming connections
	s.listen(total_sensors) #now listens for exactly the correct number of sensors 
	print("Socket is listening")

    #get data from slave pis by listening to socket and parse it and add it to sensor list
	for i in range(total_sensors):
		try:
			c,addr = s.accept() #accept connections from slave pis
			print('Got connection from', addr)
			receivedInfo = str(c.recv(1024))
			
			if receivedInfo == "True":
				pass_flag += 1
			else:
				fail_flag +=1
			c.close()
			
			if pass_flag >= thresh_pass:
				take_pic = True
				break
			elif fail_flag >= thresh_fail:
				break

		except socket.timeout:
			break

	#list of all devices and their sensor readings  CAN ADD BACK IN FOR TESTING OR IF INTERESTED 
	#for x in sensorlist:
		#print(x)

    #if ratio is above the threshold, start a photo session
	if(take_pic):
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
		
		delay_flag = True #tracks that a picture has been taken and that the delay should begin
		take_pic = False #stops the picture taking loop
		sleep(120) #does nothing for a guaranteed 2 minutes after taking a picture
		s.settimeout(300) #this sets a new timer for 5 mins. This is the max time in the delay loop
		delay_flag = 0
	
	while delay: 
		#this loop polls all the pis in order to check if their PIR signal has changed from high
		#This logic is to stop pictures of the same animal to be taken over and over
		#In order to track this we wait for the first time each sensor outputs a low signal and interpret that
		#as the animal moving away. Once a threshold is met or a specified time has passed we exit the loop
		try:
			message = "Delay"
			publish.single(MQTT_PATH,message,hostname=MQTT_SERVER) #send message get info about slave sensors
			
			if(pir.motion_detected==False) and change == False: #enters this loop the first time the sensors reads false
				change = True
				delay_flag +=1 #adds to the number of sensors that have stopped detecting heat

			s.listen(total_sensors) #now listens for exactly the correct number of sensors 
			print("Socket is listening")
			for i in range(total_sensors)
				c,addr = s.accept() #accept connections from slave pis
				receivedInfo = str(c.recv(1024))
			
				if receivedInfo == "True":
					delay_flag += 1
				c.close()
			
				if delay_flag >= thresh_pass: #uses same threshold as for taking picture to determine if animal has moved
					delay = False
					break
			sleep(10) #only checks the cameras every 10 seconds

		except socket.timeout:
			delay = False
			break
