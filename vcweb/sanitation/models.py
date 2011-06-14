from django.db import models

# Create your models here.

#    @property
def consent_url(self):
	return "/%s/consent" % self.get_absolute_url()

 #   @property
def survey_url(self):
	return "/%s/survey" % self.get_absolute_url()

  #@property
def quiz_url(self):
	return "/%s/quiz" % self.get_absolute_url()

#  @property
def play_url(self):
	return "/%s/play" % self.get_absolute_url()

 # @property
def instructions_url(self):
	return "/%s/instructions" % self.get_absolute_url()
