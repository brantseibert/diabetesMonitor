import time
import datetime
import random
import json
from AWSIoTPythonSDK.MQTTLib import AWSIoTMQTTClient

from insulin_pump import InsulinPump
from human_body import HumanBody
from aws_interface import aws_initialize
from timezone import MST

#############################################
## Variables used to simulate glucose levels
#############################################
FILENAME = "username.txt"
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


def getUsername():
        try:
                with open(FILENAME) as f:
                        return f.readline()
        except IOError:
                f = open(FILENAME, 'w')
                name = raw_input('Enter patient name: ')
                f.write(name)
                f.close()
                return name

        
if __name__ == '__main__':

        USERNAME = getUsername()
        print( USERNAME )

	aws_client = aws_initialize()
	ip = InsulinPump()
	hb = HumanBody()

	while(True):

                insulin_usage = 0
                carbs_ate = 0
                
		last_glucose = glucose

		current_datetime = datetime.datetime.now(MST())

		## Modify Glucose based on current values
		# Get current insulin and carbs on board and
		# the current basal rate
		carbs = hb.getTotalCarbsOnBoard()
		bolus = ip.getTotalInsulinOnBoard()
		basal = ip.getCurrentBasal(current_datetime.time())
		correction = ip.getCurrentCorrection(current_datetime.time())
		insulin_to_carb = ip.getCurrentInsulinToCarb(current_datetime.time())

		# Convert those to delta glucose values for a 
		# 5 minute interval 
		d_carbs = carbs*D_GTOC/STEPS
		d_bolus = bolus*D_GTOI/STEPS
		d_basal = basal*D_GTOI/STEPS

		# Calculate the newest glucose measurement
		glucose = last_glucose + D_GLUCOSE/STEPS + d_carbs + d_bolus + d_basal

		## First thing to consider is if the patient has reached the 
		#  max or min glucose level. If the max is reached, a bolus is given.
		#  If the min is reached a snack of 15 carbs will be eaten.
		if( last_glucose > MAX_GLUCOSE and not correction_given ):
			correction_difference = last_glucose-correction[1]
			correction_dose = correction_difference/correction[0] if abs(correction_difference)>correction[2] else 0
			ip.bolus(current_datetime,correction_dose)

			#with open(FILENAME,"a") as file:
			#	file.write("A correction does was given\n")
			#	file.write("Insulin,\t" + current_datetime.strftime("%Y-%m-%d %H:%M:%S") + ",\t" + str(correction_dose) + "\n")
			#aws_client.publish("Ascentti/DiabetesMonitor","Insulin,\t" + current_datetime.strftime("%Y-%m-%d %H:%M:%S") + ",\t" + str(correction_dose) + "\n",1)
			insulin_usage = correction_dose

			correction_given = True
			correction_end = current_datetime + datetime.timedelta(hours=1,minutes=30)

		elif( last_glucose < MIN_GLUCOSE and not correction_given ):
			hb.eat(current_datetime,15)

			#with open(FILENAME,"a") as file:
			#	file.write("A snack was eaten for a low blood sugar\n")
			#	file.write("Meal,\t\t" + current_datetime.strftime("%Y-%m-%d %H:%M:%S") +",\t15\n")
			#aws_client.publish("Ascentti/DiabetesMonitor","Meal,\t\t" + current_datetime.strftime("%Y-%m-%d %H:%M:%S") +",\t15\n",1)
			carbs_ate = 15

			correction_given = True
			correction_end = current_datetime + datetime.timedelta(minutes=15)
		## Then determine if the patient will eat some food
		#  Outside of a snack, there will be a linearly
		#  increasing chance of eating in the time window
		#  to a max of 90%
		elif( isBreakfast(current_datetime.time()) and not breakfast_ate ):
			snack_ate = False
			if(random.random()<breakfast):
				meal = random.randint(30,50)
				hb.eat(current_datetime,meal)
				meal_dose = meal/insulin_to_carb
				correction_difference = last_glucose-correction[1]
				correction_dose = correction_difference/correction[0] if abs(correction_difference)>correction[2] else 0
				correction_dose = correction_dose if not correction_given else 0
				ip.bolus(current_datetime,meal_dose+correction_dose)

				#with open(FILENAME,"a") as file:
				#	file.write("Breakfast has been eaten\n")
				#	file.write("Insulin,\t" + current_datetime.strftime("%Y-%m-%d %H:%M:%S") + ",\t" + str(meal_dose+correction_dose) + "\n" )
				#	file.write("Meal,\t\t" + current_datetime.strftime("%Y-%m-%d %H:%M:%S") + ",\t" + str(meal) + "\n")
				#aws_client.publish("Ascentti/DiabetesMonitor","Insulin,\t" + current_datetime.strftime("%Y-%m-%d %H:%M:%S") + ",\t" + str(meal_dose+correction_dose) + "\n",1)
				#aws_client.publish("Ascentti/DiabetesMonitor","Meal,\t\t" + current_datetime.strftime("%Y-%m-%d %H:%M:%S") + ",\t" + str(meal) + "\n",1)
				insulin_usage = meal_dose+correction_does
				carbs_ate = meal


				breakfast = 0.1
				breakfast_ate = True
			else:
				breakfast += 0.8/(120/D_TIME)
		elif( isLunch(current_datetime.time()) and not lunch_ate ):
			breakfast_ate = False
			if(random.random()<lunch):
				meal = random.randint(50,80)
				hb.eat(current_datetime,meal)
				meal_dose = meal/insulin_to_carb
				correction_difference = last_glucose-correction[1]
				correction_dose = correction_difference/correction[0] if abs(correction_difference)>correction[2] else 0
				correction_dose = correction_dose if not correction_given else 0
				ip.bolus(current_datetime,meal_dose+correction_dose)

				#with open(FILENAME,"a") as file:
				#	file.write("Lunch has been eaten\n")
				#	file.write("Insulin,\t" + current_datetime.strftime("%Y-%m-%d %H:%M:%S") + ",\t" + str(meal_dose+correction_dose) + "\n" )
				#	file.write("Meal,\t\t" + current_datetime.strftime("%Y-%m-%d %H:%M:%S") + ",\t" + str(meal) + "\n")
				#aws_client.publish("Ascentti/DiabetesMonitor","Insulin,\t" + current_datetime.strftime("%Y-%m-%d %H:%M:%S") + ",\t" + str(meal_dose+correction_dose) + "\n",1)
				#aws_client.publish("Ascentti/DiabetesMonitor","Meal,\t\t" + current_datetime.strftime("%Y-%m-%d %H:%M:%S") + ",\t" + str(meal) + "\n",1)
				insulin_usage = meal_dose+correction_does
				carbs_ate = meal

				lunch = 0.1
				lunch_ate = True
			else:
				lunch += 0.8/(120/D_TIME)
		elif( isDinner(current_datetime.time()) and not dinner_ate):
			lunch_ate = False
			if(random.random()<dinner):
				meal = random.randint(40,100)
				hb.eat(current_datetime,meal)
				meal_dose = meal/insulin_to_carb
				correction_difference = last_glucose-correction[1]
				correction_dose = correction_difference/correction[0] if abs(correction_difference)>correction[2] else 0
				correction_dose = correction_dose if not correction_given else 0
				ip.bolus(current_datetime,meal_dose+correction_dose)

				#with open(FILENAME,"a") as file:
				#	file.write("Dinner has been eaten\n")
				#	file.write("Insulin,\t" + current_datetime.strftime("%Y-%m-%d %H:%M:%S") + ",\t" + str(meal_dose+correction_dose) + "\n" )
				#	file.write("Meal,\t\t" + current_datetime.strftime("%Y-%m-%d %H:%M:%S") + ",\t" + str(meal) + "\n")
				#aws_client.publish("Ascentti/DiabetesMonitor","Insulin,\t" + current_datetime.strftime("%Y-%m-%d %H:%M:%S") + ",\t" + str(meal_dose+correction_dose) + "\n",1)
				#aws_client.publish("Ascentti/DiabetesMonitor","Meal,\t\t" + current_datetime.strftime("%Y-%m-%d %H:%M:%S") + ",\t" + str(meal) + "\n",1)
				insulin_usage = meal_dose+correction_does
				carbs_ate = meal

				dinner = 0.2
				dinner_ate = True
			else:
				dinner += 0.7/(180/D_TIME)
		elif( isSnack(current_datetime.time()) and not snack_ate ):
			dinner_ate = False
			if(random.random()<snack):
				meal = random.randint(15,30)
				hb.eat(current_datetime,meal)
				meal_dose = meal/insulin_to_carb
				correction_difference = last_glucose-correction[1]
				correction_dose = correction_difference/correction[0] if abs(correction_difference)>correction[2] else 0
				correction_dose = correction_dose if not correction_given else 0
				ip.bolus(current_datetime,meal_dose+correction_dose)

				#with open(FILENAME,"a") as file:
				#	file.write("A late night snack has been eaten\n")
				#	file.write("Insulin,\t" + current_datetime.strftime("%Y-%m-%d %H:%M:%S") + ",\t" + str(meal_dose+correction_dose) + "\n")
				#	file.write("Meal,\t\t" + current_datetime.strftime("%Y-%m-%d %H:%M:%S") + ",\t" + str(meal) + "\n")
				#aws_client.publish("Ascentti/DiabetesMonitor","Insulin,\t" + current_datetime.strftime("%Y-%m-%d %H:%M:%S") + ",\t" + str(meal_dose+correction_dose) + "\n",1)
				#aws_client.publish("Ascentti/DiabetesMonitor","Meal,\t\t" + current_datetime.strftime("%Y-%m-%d %H:%M:%S") + ",\t" + str(meal) + "\n",1)
				insulin_usage = meal_dose+correction_does
				carbs_ate = meal

				snack = 0.05
				snack_ate = True
			else:
				snack += 0.15/(30/D_TIME)
		elif( current_datetime > correction_end ):
			correction_given = False

		#with open(FILENAME,"a") as file:
		#	file.write("Glucose,\t" + current_datetime.strftime("%Y-%m-%d %H:%M:%S") + ",\t" + str(last_glucose) + "\n")
		#aws_client.publish("Ascentti/DiabetesMonitor","Glucose,\t" + current_datetime.strftime("%Y-%m-%d %H:%M:%S") + ",\t" + str(last_glucose) + "\n",1)

                data = [{ USERNAME : { 'Glucose' : last_glucose, 'Insulin' : insulin_usage, 'Carbs' : carbs_ate, 'Date' : current_datetime.strftime("%Y-%m-%d %H:%M:%S") } }]
                json_data = json.dumps(data)

                aws_client.publish("Ascentti/DiabetesMonitor",json_data,1)

		time.sleep(D_TIME*60)

	
