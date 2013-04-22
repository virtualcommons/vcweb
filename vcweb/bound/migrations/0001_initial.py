# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        from django.core.management import call_command
        call_command("loaddata", "bound_experiment_metadata.json")

    def backwards(self, orm):
        pass

    models = {
        
    }

    complete_apps = ['bound']
