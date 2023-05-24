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
from time import strftime
#Authors:
#Dylan Logan

#Master Publisher code for multiple sensors photo triggering
#Periodically polls the sensors in the camera array and takes a picture if a set ratio is met
setup = True 
main = False
take_pic = False
delay = False
initial_setup = True
delay_flag = 0
reinitialize = 0

while setup:
	if initial_setup == True: #runs only one time
		print("Started master multisensor photo sync program")
		photoNum = 1
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
	
		s.bind(('',12345)) #bind the socket to a unused undesignated port
		initial_setup = False
		
	s.settimeout(30) #set a time for the socket to be open for. This is purposefully long in lue of a delay
	sensors_connected = [] #list of all the slaves that connect to the master
	message = "Setup"
	sensors_connected.append([str(IPAddr)])
	publish.single(MQTT_PATH,message,hostname=MQTT_SERVER) #send message see which slave sensors are looking to connect
	s.listen(4) #set socket to take a backlog of 10. increase number if there are more slaves to be connected
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
	
	total_sensors = len(sensors_connected)
	if (total_sensors > 3):
		thresh_pass = floor(2/3*total_sensors) #this creates the threshold to take a picture as two thirds of the total sensors rounding down
		main = True
	elif (total_sensors < 3): #if there is only one slave connected then the script is not run
		print("you dont have enough connected sensors")
	else: #this is the minimum number of sensors to create a usable model therefore it is a special case where all the sensors must detect heat
		thresh_pass = 3
		main = True
	setup = False #changes the setup variable to false so it only runs once
	wait_time = 10 #Want to get many pics of the animal when it comes so wait time is just long enough for sensors to cool down on average
	s.settimeout(10) #sets a new time for reading sensor outputs. shouldnt need to be this high
	break #ends the loop

#run continously until terminated by user
while main:
	print("Resting...")
	pass_flag = 0 #resets flags every loop
	sleep(wait_time)
	print("Starting")
	message = "Info"
	publish.single(MQTT_PATH,message,hostname=MQTT_SERVER) #send message get info about slave sensors

    #put sensor state of master pi in sensor list
	if(pir.motion_detected==True):
		pass_flag +=  1 #increments the pass count if motion is seen on master

    #listen for incoming connections
	s.listen(total_sensors) #now listens for exactly the correct number of sensors 
	print("Socket is listening")

    #get data from slave pis by listening to socket and parse it and add it to sensor list
	for i in range(1,total_sensors):
		try:
			c,addr = s.accept() #accept connections from slave pis
			print('Got connection from', addr)
			receivedInfo = str(c.recv(1024))
			
			if receivedInfo == "True":
				pass_flag += 1

			c.close()
			
			if pass_flag >= thresh_pass:
				take_pic = True

		except socket.timeout:
			total_sensors -=1 #this means a sensor has died
			reinitialize = 20950 #sets cameras so run for a short amount more time then reinitialize and rethreshold
			break #break the loop so no pic is taken as a timeout means the animal is likely past

	#list of all devices and their sensor readings  CAN ADD BACK IN FOR TESTING OR IF INTERESTED 
	#for x in sensorlist:
		#print(x)

    #if ratio is above the threshold, start a photo session
	if(take_pic):
		#Send MQTT message to slaves to take photo and start photo
		date = strftime("%d_%m_%y_")
		message = "Take Synced Photo " + str(photoNum) + ' ' + date
		
		publish.single(MQTT_PATH,message,hostname=MQTT_SERVER)
		ctpath = '/home/pi/cameraTrapPhotos/' + date +'set' + str(photoNum) + '/'
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

		#Take Photo
		camera.capture(ctpath+filename)
		#End of Photo session

		print("Camera 1 photo number "+ str(photoNum) + " taken")
		#go to next photo session
		photoNum = photoNum + 1
		
#		delay = True #tracks that a picture has been taken and that the delay should begin
		take_pic = False #stops the picture taking loop
		delay_flag +=1 
		sleep(6)


	if delay_flag == 10:
		delay = True
		delay_flag = 0
		
	reinitialize +=1 #increment every loop
	if reinitialize == 21000:  #about once a day will reinitialize the list of sensors 
		setup = True
		main = False
	while delay: 
		sleep(45) #Gives the sensors ample time to fully reset if they have just taken 10 pics in a row
			#Long times at high could cause them to continue to falsely read high for longer i.e. cool down
