import datetime
import threading
import time

from insulin import Insulin
from timezone import MST

#############################################################
#  Define the three important variables for controlling 
#  glucose levels using an insulin pump
#
#  Insulin to Carb: ratio of units of insulin to carbs
#  Basal Rate: units of insulin per hour
#  Correction: adjustment to boluses based on glucose level
#
#  Pump settings are listed in a text document
#############################################################
class InsulinPump:

	def __init__(self):
		## user controllable variables
		self.insulin_to_carb = []
		self.basal_rate = []
		self.correction = []

		self.getPumpSettings()

		## insulin usage variables
		self.insulin_on_board = []

		self.clear = threading.Thread( target=self.clearOldInjections )
		self.clear.setDaemon(True)
		self.clear.start()


	def getPumpSettings(self):
		f = open("pump_settings.txt",'r')

		itc_next = False
		basal_next = False
		correction_next = False

		for line in f:
			line = line.strip("\n")
			if line=="ItC":
				itc_next = True
				continue
			elif line=="Basal":
				itc_next = False
				basal_next = True
				continue
			elif line=="Correction":
				basal_next = False
				correction_next = True
				continue

			if itc_next == True:
				s = list(map(int,line.split(",")))
				self.insulin_to_carb.append([datetime.time(s[0],s[1],s[2]),s[3]]) 
			elif basal_next == True:
				s = list(map(float,line.split(",")))
				self.basal_rate.append([datetime.time(int(s[0]),int(s[1]),int(s[2])),s[3]]) 
			elif correction_next == True:
				s = list(map(int,line.split(",")))
				self.correction.append([datetime.time(s[0],s[1],s[2]),s[3],s[4],s[5]]) 

		f.close()

	
	## Methods to get insulin pump settings
	def getCurrentInsulinToCarb(self,current_time):
		for i in range(1,len(self.insulin_to_carb)):
			if current_time < self.insulin_to_carb[i][0]:
				return self.insulin_to_carb[i-1][1]
		return self.insulin_to_carb[len(self.insulin_to_carb)-1][1]

	def getCurrentBasal(self,current_time):
		for i in range(1,len(self.basal_rate)):
			if current_time < self.basal_rate[i][0]:
				return self.basal_rate[i-1][1]
		return self.basal_rate[len(self.basal_rate)-1][1]

	def getCurrentCorrection(self,current_time):
		for i in range(1,len(self.correction)):
			if current_time < self.correction[i][0]:
				return self.correction[i-1][1:4]
		return self.correction[len(self.correction)-1][1:4]

	## Methods dealing with boluses
	def bolus(self, start_time, units):
		self.insulin_on_board.append( Insulin(start_time,units) )

	def getTotalInsulinOnBoard(self):
		total = 0
		for injections in self.insulin_on_board:
			total += injections.getUnits()
		return total

	def clearOldInjections(self):
		while(True):
			current_time = datetime.datetime.now(MST())

			old_injections = []
			for injections in self.insulin_on_board:
				if( current_time > injections.getEndTime() ):
					old_injections.append(injections)

			for old in old_injections:
				self.insulin_on_board.remove(old)

			time.sleep(10)