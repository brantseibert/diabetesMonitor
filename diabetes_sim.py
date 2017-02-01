import time
import datetime
import random
import json
import sys
import getopt
import os
from AWSIoTPythonSDK.MQTTLib import AWSIoTMQTTClient

from insulin_pump import InsulinPump
from human_body import HumanBody
from aws_interface import aws_initialize
from timezone import MST


#####################################################################
## Command line help information
#####################################################################
# Usage
usageInfo = """
Usage:

python diabetes_sim.py -e <endpoint> -r <rootCAFilePath> -C <CognitoIdentityPoolID>


Type "python diabetes_sim.py -h" for available options.

"""
# Help info
helpInfo = """
-e, --endpoint
	Your AWS IoT custom endpoint
-r, --rootCA
	Root CA file path
-C, --CognitoIdentityPoolID
	Your AWS Cognito Identity Pool ID
-h, --help
	Help information

"""

#############################################
## Variables used to simulate glucose levels
#############################################
USERNAME = ""

## Time between steps (minutes)
D_TIME = 5

## Steps per hour
STEPS = 60/D_TIME

## Simulated glucose level (mg/dL)
glucose = 120
## Delta glucose level  (mg/dL/h)
#  should roughly be 0 for perfect control
D_GLUCOSE = 50
## Max glucose level, the level where a correction 
#  should be applied (mg/dL)
MAX_GLUCOSE = 300
## Min glucose level, the level where food should 
#  be eaten (mg/dL)
MIN_GLUCOSE = 50

## Delta bolus, the rate at which all bolus injections
#  affects current glucose levels (mg/dL/h)
d_bolus = 0
## Delta basal, the rate at which basal injections
#  affects current glucose levels (mg/dL/h)
d_basal = 0
## Delta glucose level per unit of insulin (mg/dL/h/units)
D_GTOI = -27

## Delta Carbs, the rate at which all the food eaten will
#  affect current glucose levels (mg/dL/h)
d_carbs = 0
## Delta glucose level per carbs (mg/dL/h/g)
D_GTOC = 4


#####################################################
## Meal Schedules 
#####################################################
MIN_BREAKFAST = datetime.time(7,30,0)
MAX_BREAKFAST = datetime.time(9,30,0)
breakfast = 0.1
breakfast_ate = False

MIN_LUNCH = datetime.time(12,0,0)
MAX_LUNCH = datetime.time(14,0,0)
lunch = 0.1
lunch_ate = False

MIN_DINNER = datetime.time(17,30,0)
MAX_DINNER = datetime.time(20,0,0)
dinner = 0.2
dinner_ate = False

MIN_SNACK = datetime.time(21,30,0)
MAX_SNACK = datetime.time(22,0,0)
snack = 0.05
snack_ate = False

correction_given = False
correction_end = datetime.datetime.now(MST())

def isBreakfast(current_time):
	if( MIN_BREAKFAST <= current_time and current_time <= MAX_BREAKFAST ):
		return True
	return False

def isLunch(current_time):	
	if( MIN_LUNCH <= current_time and current_time <= MAX_LUNCH ):
		return True
	return False

def isDinner(current_time):
	if( MIN_DINNER <= current_time and current_time <= MAX_DINNER ):
		return True
	return False

def isSnack(current_time):
	if( MIN_SNACK <= current_time and current_time <= MAX_SNACK ):
		return True
	return False

## Grab a user defined username so that the data being sent 
#  can be unique to each instance
def getUsername():
		try:
				with open('username.txt') as f:
						return f.readline()
		except IOError:
				f = open('username.txt', 'w')
				name = raw_input('Enter patient name: ')
				f.write(name)
				f.close()
				return name

def randomItC(file):
	file.write("ItC\n")
	num_itc = random.randint(1,3)
	file.write("0,0,0,"+str(random.randint(6,9))+"\n")
	time_division = 24/num_itc
	for i in range(0,num_itc):
		hour = random.randint(time_division*i,time_division*(i+1)-1)
		minute = random.choice([0,15,30,45])
		itc = random.randint(6,9)
		file.write(str(hour)+","+str(minute)+",0,"+str(itc)+"\n")

def randomBasal(file):
	file.write("Basal\n")
	num_basal = random.randint(3,6)
	file.write("0,0,0,"+str(round(0.5*random.random()+1,2))+"\n")
	time_division = 24/num_basal
	for i in range(0,num_basal):
		hour = random.randint(time_division*i,time_division*(i+1)-1)
		minute = random.choice([0,15,30,45])
		basal = round(0.5*random.random()+1,2)
		file.write(str(hour)+","+str(minute)+",0,"+str(basal)+"\n")

def randomCorrection(file):
	file.write("Correction\n")
	num_correction = random.randint(1,3)
	file.write("0,0,0,"+str(random.randint(30,50))+","+str(random.randint(110,130))+","+str(random.randint(25,35))+"\n")
	time_division = 24/num_correction
	for i in range(0,num_correction):
		hour = random.randint(time_division*i,time_division*(i+1)-1)
		minute = random.choice([0,15,30,45])
		ratio = str(random.randint(30,50))
		base = str(random.randint(110,130))
		margin = str(random.randint(25,35))
		file.write(str(hour)+","+str(minute)+",0,"+str(ratio)+","+str(base)+","+str(margin)+"\n")


def randomizePumpSettings():
	if not os.path.isfile('pump_settings.txt'):
		f = open('pump_settings.txt', 'w')
		randomItC(f)
		randomBasal(f)
		randomCorrection(f)

## Determine a random value of carbs between minCarbs and MaxCarbs
#  Determine the dosgae for the meal 
#  Determine the correction for the current glucose
#  If a correction had been previously given, don't correct again
def eatFood(hb,ip,minCarbs,maxCarbs,insulin_to_carb,correction):
	meal = random.randint(minCarbs,maxCarbs)
	hb.eat(current_datetime,meal)
	meal_dose = meal/(1.0*insulin_to_carb)
	correction_difference = last_glucose-correction[1]
	correction_dose = correction_difference/(1.0*correction[0]) if abs(correction_difference)>correction[2] else 0
	correction_dose = correction_dose if not correction_given else 0
	ip.bolus(current_datetime,meal_dose+correction_dose)

	return (meal_dose+correction_dose), meal

		
if __name__ == '__main__':
	# Read in command-line parameters
	host = ""
	rootCAPath = ""
	cognitoIdentityPoolID = ""
	try:
		opts, args = getopt.getopt(sys.argv[1:], "he:r:C:", ["help", "endpoint=", "rootCA=", "CognitoIdentityPoolID="])
		if len(opts) == 0:
			raise getopt.GetoptError("No input parameters!")
		for opt, arg in opts:
			if opt in ("-h", "--help"):
				print(helpInfo)
				exit(0)
			if opt in ("-e", "--endpoint"):
				host = arg
			if opt in ("-r", "--rootCA"):
				rootCAPath = arg
			if opt in ("-C", "--CognitoIdentityPoolID"):
				cognitoIdentityPoolID = arg
	except getopt.GetoptError:
		print(usageInfo)
		exit(1)

	USERNAME = getUsername()
	print( "Starting Diabetes Monitor for patient: " + USERNAME )

	randomizePumpSettings()

	# aws_client = aws_initialize(USERNAME,host,rootCAPath,cognitoIdentityPoolID)
	# ip = InsulinPump()
	# hb = HumanBody()

	# while(True):

	# 	insulin_usage = 0
	# 	carbs_ate = 0
				
	# 	last_glucose = glucose

	# 	current_datetime = datetime.datetime.now(MST())

	# 	## Modify Glucose based on current values
	# 	# Get current insulin and carbs on board and
	# 	# the current basal rate
	# 	carbs = hb.getTotalCarbsOnBoard()
	# 	bolus = ip.getTotalInsulinOnBoard()
	# 	basal = ip.getCurrentBasal(current_datetime.time())
	# 	correction = ip.getCurrentCorrection(current_datetime.time())
	# 	insulin_to_carb = ip.getCurrentInsulinToCarb(current_datetime.time())

	# 	# Convert those to delta glucose values for a 
	# 	# 5 minute interval 
	# 	d_carbs = carbs*D_GTOC/STEPS
	# 	d_bolus = bolus*D_GTOI/STEPS
	# 	d_basal = basal*D_GTOI/STEPS

	# 	# Calculate the newest glucose measurement
	# 	glucose = last_glucose + D_GLUCOSE/STEPS + d_carbs + d_bolus + d_basal

	# 	## First thing to consider is if the patient has reached the 
	# 	#  max or min glucose level. If the max is reached, a bolus is given.
	# 	#  If the min is reached a snack of 15 carbs will be eaten.
	# 	if( last_glucose > MAX_GLUCOSE and not correction_given ):
	# 		correction_difference = last_glucose-correction[1]
	# 		correction_dose = correction_difference/correction[0] if abs(correction_difference)>correction[2] else 0
	# 		ip.bolus(current_datetime,correction_dose)
	# 		insulin_usage = correction_dose

	# 		correction_given = True
	# 		correction_end = current_datetime + datetime.timedelta(hours=1,minutes=30)

	# 	elif( last_glucose < MIN_GLUCOSE and not correction_given ):
	# 		hb.eat(current_datetime,15)
	# 		carbs_ate = 15

	# 		correction_given = True
	# 		correction_end = current_datetime + datetime.timedelta(minutes=15)
	# 	## Otherwise determine if the patient will eat some food
	# 	#  Outside of a snack, there will be a linearly
	# 	#  increasing chance of eating in the time window
	# 	#  to a max of 90%
	# 	elif( isBreakfast(current_datetime.time()) and not breakfast_ate ):
	# 		snack_ate = False
	# 		if(random.random()<breakfast):
	# 			insulin_usage, carbs_ate = eatFood(hb,ip,30,50,insulin_to_carb,correction)

	# 			breakfast = 0.1
	# 			breakfast_ate = True
	# 		else:
	# 			breakfast += 0.8/(120/D_TIME)
	# 	elif( isLunch(current_datetime.time()) and not lunch_ate ):
	# 		breakfast_ate = False
	# 		if(random.random()<lunch):
	# 			insulin_usage, carbs_ate = eatFood(hb,ip,50,80,insulin_to_carb,correction)

	# 			lunch = 0.1
	# 			lunch_ate = True
	# 		else:
	# 			lunch += 0.8/(120/D_TIME)
	# 	elif( isDinner(current_datetime.time()) and not dinner_ate):
	# 		lunch_ate = False
	# 		if(random.random()<dinner):
	# 			insulin_usage, carbs_ate = eatFood(hb,ip,40,100,insulin_to_carb,correction)

	# 			dinner = 0.2
	# 			dinner_ate = True
	# 		else:
	# 			dinner += 0.7/(180/D_TIME)
	# 	elif( isSnack(current_datetime.time()) and not snack_ate ):
	# 		dinner_ate = False
	# 		if(random.random()<snack):
	# 			insulin_usage, carbs_ate = eatFood(hb,ip,15,30,insulin_to_carb,correction)

	# 			snack = 0.05
	# 			snack_ate = True
	# 		else:
	# 			snack += 0.15/(30/D_TIME)
	# 	elif( current_datetime > correction_end ):
	# 		correction_given = False

	# 	data = [{ USERNAME : { 'Glucose' : last_glucose, 'Insulin' : insulin_usage, 'Carbs' : carbs_ate, 'Date' : current_datetime.strftime("%Y-%m-%d %H:%M:%S") } }]
	# 	json_data = json.dumps(data)

	# 	try:
	# 		aws_client.connect()
	# 	except ValueError:
	# 		print("Websocket Handshake Error occurred, reinitializing aws client")
	# 		aws_client = aws_initialize(USERNAME,host,rootCAPath,cognitoIdentityPoolID)
	# 		aws_client.connect()
	# 	time.sleep(2)
	# 	aws_client.publish("Ascentti/DiabetesMonitor",json_data,1)
	# 	time.sleep(2)
	# 	aws_client.disconnect()

	# 	time.sleep(D_TIME*60-4)

	
