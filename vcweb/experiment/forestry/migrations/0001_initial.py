# -*- coding: utf-8 -*-
from south.v2 import SchemaMigration


class Migration(SchemaMigration):

    def forwards(self, orm):
        from django.core.management import call_command
        call_command("loaddata", "forestry_experiment_metadata.json")
        pass

    def backwards(self, orm):
        pass

    models = {
        
    }

    complete_apps = ['forestry']
