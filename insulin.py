import datetime

class Insulin:

	def __init__(self,start_time,units):
		self.start_time = start_time
		self.end_time = start_time + datetime.timedelta(hours=1,minutes=30,seconds=0)
		self.units = units

	def getStartTime(self):
		return self.start_time

	def getEndTime(self):
		return self.end_time

	def getUnits(self):
		return self.units