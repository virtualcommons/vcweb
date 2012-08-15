# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models
from vcweb.core.models import ExperimentMetadata


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'Activity'
        db.create_table('lighterprints_activity', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(unique=True, max_length=32)),
            ('display_name', self.gf('django.db.models.fields.CharField')(max_length=64, null=True, blank=True)),
            ('summary', self.gf('django.db.models.fields.CharField')(max_length=256)),
            ('description', self.gf('django.db.models.fields.TextField')()),
            ('url', self.gf('django.db.models.fields.URLField')(max_length=200)),
            ('savings', self.gf('django.db.models.fields.DecimalField')(default=0.0, max_digits=5, decimal_places=2)),
            ('points', self.gf('django.db.models.fields.PositiveIntegerField')(default=0)),
            ('available_all_day', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('personal_benefits', self.gf('django.db.models.fields.TextField')(null=True, blank=True)),
            ('level', self.gf('django.db.models.fields.PositiveIntegerField')(default=1)),
            ('group_activity', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('cooldown', self.gf('django.db.models.fields.PositiveIntegerField')(default=1, null=True, blank=True)),
            ('icon', self.gf('django.db.models.fields.files.ImageField')(max_length=100)),
        ))
        db.send_create_signal('lighterprints', ['Activity'])

        # Adding model 'ActivityAvailability'
        db.create_table('lighterprints_activityavailability', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('activity', self.gf('django.db.models.fields.related.ForeignKey')(related_name='availability_set', to=orm['lighterprints.Activity'])),
            ('start_time', self.gf('django.db.models.fields.TimeField')(null=True, blank=True)),
            ('end_time', self.gf('django.db.models.fields.TimeField')(null=True, blank=True)),
        ))
        db.send_create_signal('lighterprints', ['ActivityAvailability'])
        ExperimentMetadata.objects.create(namespace='lighterprints',
                description="A mobile-ready HTML5 experiment / game that educates and examines how groups of people coordinate to reach carbon emission targets.",
                title="Lighter Footprints",
                last_modified="2012-04-02T00:21:45.161",
                date_created="2012-04-02",
                about_url="http://commons.asu.edu",
                )


    def backwards(self, orm):
        # Deleting model 'Activity'
        db.delete_table('lighterprints_activity')

        # Deleting model 'ActivityAvailability'
        db.delete_table('lighterprints_activityavailability')

    models = {
        'lighterprints.activity': {
            'Meta': {'ordering': "['level', 'name']", 'object_name': 'Activity'},
            'available_all_day': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'cooldown': ('django.db.models.fields.PositiveIntegerField', [], {'default': '1', 'null': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {}),
            'display_name': ('django.db.models.fields.CharField', [], {'max_length': '64', 'null': 'True', 'blank': 'True'}),
            'group_activity': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'icon': ('django.db.models.fields.files.ImageField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'level': ('django.db.models.fields.PositiveIntegerField', [], {'default': '1'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '32'}),
            'personal_benefits': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'points': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'}),
            'savings': ('django.db.models.fields.DecimalField', [], {'default': '0.0', 'max_digits': '5', 'decimal_places': '2'}),
            'summary': ('django.db.models.fields.CharField', [], {'max_length': '256'}),
            'url': ('django.db.models.fields.URLField', [], {'max_length': '200'})
        },
        'lighterprints.activityavailability': {
            'Meta': {'ordering': "['activity', 'start_time']", 'object_name': 'ActivityAvailability'},
            'activity': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'availability_set'", 'to': "orm['lighterprints.Activity']"}),
            'end_time': ('django.db.models.fields.TimeField', [], {'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'start_time': ('django.db.models.fields.TimeField', [], {'null': 'True', 'blank': 'True'})
        }
    }

    complete_apps = ['lighterprints']
