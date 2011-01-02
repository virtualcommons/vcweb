from fabric.api import *
from fabric.contrib.console import confirm

env.hosts = ['dev.commons.asu.edu']

def host_type():
    run('uname -a')

def test():
    local('./manage.py test', capture=False)

def syncdb():
    local('test -f vcweb.db && rm vcweb.db', capture=False)
    local('./manage.py syncdb --noinput', capture=False)
    local('./manage.py loaddata test_users_participants', capture=False)
    local('./manage.py loaddata forestry_test_data', capture=False)

def deploy():
    local('hg push')
    if confirm("Deploy to %s ?" % env.hosts):
        with cd('/opt/webapps/virtualcommons/'):
            run('hg pull')
            run('hg up')
            sudo('find . -type d -exec chmod a+x {} \;', pty=True)
            sudo('chmod -R a+r .', pty=True)
            sudo('service httpd restart', pty=True)
