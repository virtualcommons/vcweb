from django.conf.urls.defaults import *
'''
Created on Jul 14, 2010

@author: alllee
'''
urlpatterns = patterns('vcweb.core.views',
    ('^$', 'index'),
    (r'list/$', 'list'),
    (r'configure/$', 'configure'),
    (r'')
    
)