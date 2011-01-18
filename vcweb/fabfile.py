from fabric.api import local, run, sudo, cd, env, hide
from fabric.contrib.console import confirm
from fabric.contrib import django

import os

""" Default Configuration """
''' env defaults '''
env.python = 'python2.6'
env.project_name = 'vcweb'
env.deploy_user = 'vcweb'
env.deploy_group = 'commons'
env.virtualenv_path = '/opt/virtualenvs/%(project_name)s' % env
env.deploy_path = '/opt/webapps/virtualcommons/'
''' default to current working directory '''
env.project_path = os.path.dirname(__file__)
env.hosts = ['localhost']
env.hg_url = 'http://virtualcommons.hg.sourceforge.net:8000/hgroot/virtualcommons/virtualcommons'
env.apache = 'httpd'
env.applist = ['core', 'forestry']
env.apps = ' '.join(env.applist)

''' django integration '''
django.project(env.project_name)

"""
currently only works for sqlite3 development database.  Need to do it by hand with postgres a
few times to figure out what to automate.
"""
syncdb_commands = ['(test -f vcweb.db && rm vcweb.db) || true',
        '%(python)s manage.py syncdb --noinput' % env,
        '%(python)s manage.py loaddata test_users_participants' % env,
        '%(python)s manage.py loaddata forestry_test_data' % env]

def syncdb():
    with cd(env.project_path):
        for command in syncdb_commands:
            _virtualenv(command)

def setup_virtualenv():
    """ Setup a fresh virtualenv """
    run('virtualenv -p %(python)s --no-site-packages %(virtualenv_path)s;' % env)

def _virtualenv(command, run_locally=False, **kwargs):
    """ source the virtualenv before executing this command """
    env.command = command
    return run('source %(virtualenv_path)s/bin/activate && %(command)s' % env, **kwargs)
   # if run_locally:
   #     return local('source %(virtualenv_path)s/bin/activate && %(command)s' % env, **kwargs)
   # else:

def pip():
    ''' looks for requirements.pip in the django project directory '''
    _virtualenv('pip install -E %(virtualenv_path)s -r %(project_path)s/requirements.pip' % env)

def host_type():
    run('uname -a')

def test():
    '''
    runs tests on this local codebase, not the deployed codebase
    '''
    with cd(env.project_path):
        with hide('stdout'):
            _virtualenv('%(python)s manage.py test %(apps)s' % env)

def tornado(ip="149.169.203.115", port=8888):
    local("{python} vcweb-tornado.py {port}".format(python=env.python, **locals()), capture=False)

def server(ip="149.169.203.115", port=8080):
    local("{python} manage.py runserver {ip}:{port}".format(python=env.python, **locals()), capture=False)

def celeryd():
    local("%(python)s manage.py celeryd" % env)

def celerybeat():
    local("%(python)s manage.py celerybeat" % env)

def push():
    local('hg push')

def dev():
    env.project_path = env.deploy_path + env.project_name
    env.hosts =['dev.commons.asu.edu']

def prod():
    env.project_path = env.deploy_path + env.project_name
    env.hosts = ['vcweb.asu.edu']

def loc():
    env.deploy_user = 'alllee'
    env.apache = 'apache2'
    env.hosts = ['localhost']

def setup():
    setup_virtualenv()
    sudo('hg clone %(hg_url)s %(deploy_path)s' % env, pty=True, user=env.deploy_user)
    sudo('chown -R %(deploy_user)s:%(deploy_group)s %(deploy_path)s' % env, pty=True)
    sudo('chmod -R ug+rw %(deploy_path)s' % env, pty=True)
    sudo('find %(deploy_path)s -type d -exec chmod ug+x {} \;' % env, pty=True)
    pip()

def restart():
    sudo('service %(apache)s restart' % env, pty=True)

def deploy():
    """ deploys to an already setup environment """
    env.project_path = env.deploy_path + env.project_name
    push()
    if confirm("Deploy to %(hosts)s ?" % env):
        with cd(env.project_path):
            sudo('hg pull', user=env.deploy_user, pty=True)
            sudo('hg up', user=env.deploy_user, pty=True)
            sudo('chmod -R ug+rw .', pty=True)
            sudo('find . -type d -exec chmod ug+x {} \;', pty=True)
            sudo('chown -R %(deploy_user)s:%(deploy_group)s .' % env, pty=True)
            restart()
