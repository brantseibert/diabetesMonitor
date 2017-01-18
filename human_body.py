import datetime
import threading
import time

from food import Food
from timezone import MST

class HumanBody:

	def __init__(self):
		## insulin usage variables
		self.carbs_on_board = []

		self.clear = threading.Thread( target=self.clearOldCarbs )
		self.clear.setDaemon(True)
		self.clear.start()

	## Methods dealing with boluses
	def eat(self, start_time, carbs):
		self.carbs_on_board.append( Food(start_time,carbs) )

	def getTotalCarbsOnBoard(self):
		total = 0
		for meals in self.carbs_on_board:
			total += meals.getCarbs()
		return total

	def clearOldCarbs(self):
		while(True):
			current_time = datetime.datetime.now(MST())

			old_meals = []
			for meals in self.carbs_on_board:
				if( current_time > meals.getEndTime() ):
					old_meals.append(meals)

			for old in old_meals:
				self.carbs_on_board.remove(old)

			time.sleep(10)