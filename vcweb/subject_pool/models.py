from datetime import datetime
from django.contrib.auth.models import User
from django.db import models
from django.utils.translation import ugettext_lazy as _
from vcweb.core.models import AutoDateTimeField


class OstromlabFaqEntry(models.Model):
    question = models.TextField(help_text=_("FAQ Question"))
    answer = models.TextField(help_text=_("FAQ Answer"))
    date_created = models.DateTimeField(default=datetime.now)
    last_modified = AutoDateTimeField(default=datetime.now)
    contributor = models.ForeignKey(User)

    def __unicode__(self):
        return u"%s\n\t%s" % (self.question, self.answer)
