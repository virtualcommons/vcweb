from django.db import models
from django.template.defaultfilters import slugify
from vcweb.core.models import (ExperimentMetadata, Experiment, Participant)

class Session(models.Model):
    name = models.CharField(max_length=200)
    slug = models.SlugField(blank=True)
    start_date = models.DateField(auto_now=False)
    end_date = models.DateField(auto_now=False)
    experiment = models.ForeignKey(Experiment, blank=True, null=True)
    participant = models.ManyToManyField(Participant)

    class Meta:
        verbose_name_plural = 'sessions'
        ordering = ['start_date']

    def __unicode__(self):
        return self.title

    def save(self, *args, **kwargs):
        self.slug = slugify(self.title)
        return super(Session, self).save(*args, **kwargs)

    @models.permalink
    def get_absolute_url(self):
        return ('session_detail', [self.slug])
    @models.permalink
    def get_update_url(self):
        return ('session_update', [self.slug])
    @models.permalink
    def get_delete_url(self):
        return ('session_delete', [self.slug])

    


    # def get_experiment_metadata(self):
    #     return ExperimentMetadata.objects.get(all)