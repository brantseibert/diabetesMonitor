import datetime

class MST(datetime.tzinfo):
	def utcoffset(self, dt):
		return datetime.timedelta(hours=-7)

	def dst(self, dt):
		return datetime.timedelta(0)