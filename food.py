import datetime

class Food:

	def __init__(self,start_time,carbs):
		self.start_time = start_time
		self.end_time = start_time + datetime.timedelta(hours=1,minutes=0)
		self.carbs = carbs

	def getStartTime(self):
		return self.start_time

	def getEndTime(self):
		return self.end_time

	def getCarbs(self):
		return self.carbs