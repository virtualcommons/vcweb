from fabric.api import local, run, sudo, cd, env, hide
from fabric.contrib.console import confirm
from fabric.contrib import django

import os, sys

# needed to push vcweb.settings onto the path.
sys.path.append(os.path.abspath('..'))

# default env configuration
env.python = 'python2.6'
env.project_name = 'vcweb'
env.deploy_user = 'apache'
env.deploy_group = 'commons'
env.virtualenv_path = '/opt/virtualenvs/%(project_name)s' % env
env.deploy_path = '/opt/webapps/virtualcommons/'
# default to current working directory 
env.project_path = os.path.dirname(__file__)
env.hosts = ['localhost']
env.hg_url = 'http://virtualcommons.hg.sourceforge.net:8000/hgroot/virtualcommons/virtualcommons'
env.apache = 'httpd'
env.applist = ['core', 'forestry']
env.apps = ' '.join(env.applist)

# django integration for access to settings, etc.
django.project(env.project_name)

"""
this currently only works for sqlite3 development database.  do it by hand with
postgres a few times to figure out what to automate, probably with south?
"""
syncdb_commands = ['(test -f vcweb.db && rm -f vcweb.db) || true',
        '%(python)s manage.py syncdb --noinput' % env,
        '%(python)s manage.py loaddata test_users_participants' % env,
        '%(python)s manage.py loaddata forestry_test_data' % env]

def shell():
    local("{python} manage.py shell".format(python=env.python), capture=False)

def syncdb(**kwargs):
    with cd(env.project_path):
        _virtualenv(*syncdb_commands, **kwargs)


def setup_virtualenv():
    """ Setup a fresh virtualenv """
    run('virtualenv -p %(python)s --no-site-packages %(virtualenv_path)s;' % env)

def clear_rabbitmq_db():
    from fabric.context_managers import settings
    with settings(warn_only=True):
        sudo_chain(["rabbitmqctl %s" % cmd for cmd in ['stop_app', 'reset', 'start_app']])

def setup_rabbitmq():
    from vcweb import settings
    from fabric.context_managers import settings as fab_settings
    clear_rabbitmq_db()
    with fab_settings(warn_only=True):
        sudo("rabbitmqctl delete_user %s" % settings.BROKER_USER, pty=True)
    sudo("rabbitmqctl add_user %s %s" % (settings.BROKER_USER, settings.BROKER_PASSWORD), pty=True)
    with fab_settings(warn_only=True):
        sudo("rabbitmqctl delete_vhost %s" % settings.BROKER_VHOST, pty=True)
    sudo("rabbitmqctl add_vhost %s" % settings.BROKER_VHOST, pty=True)
# figure out what the appropriate rabbitmq perms are here.
    sudo('rabbitmqctl set_permissions -p %s %s ".*" ".*" ".*"' % (settings.BROKER_VHOST, settings.BROKER_USER), pty=True)

def _virtualenv(*commands, **kwargs):
    """ source the virtualenv before executing this command """
    env.command = ' && '.join(commands)
    return run('source %(virtualenv_path)s/bin/activate && %(command)s' % env, **kwargs)

def pip():
    ''' looks for requirements.pip in the django project directory '''
    _virtualenv('pip install -E %(virtualenv_path)s -r %(project_path)s/requirements.pip' % env)
    with cd(env.virtualenv_path):
        sudo_chain('chgrp -R %(deploy_group)s .' % env, 'chmod -R g+rw' % env, pty=True)

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

def server(ip="149.169.203.115", port=8000):
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
    sudo_chain('chown -R %(deploy_user)s:%(deploy_group)s %(deploy_path)s' % env,  
            'chmod -R ug+rw %(deploy_path)s' % env, 
            'find %(deploy_path)s -type d -exec chmod ug+x {} \;' % env,
            pty=True)
    pip()

def _restart_command():
    return 'service %(apache)s restart' % env

def restart():
    sudo(_restart_command(), pty=True)

def sudo_chain(*commands, **kwargs):
    sudo(' && '.join(commands), **kwargs)

def deploy():
    """ deploys to an already setup environment """
    env.project_path = env.deploy_path + env.project_name
    push()
    if confirm("Deploy to %(hosts)s ?" % env):
        with cd(env.project_path):
            sudo('hg pull && hg up', user=env.deploy_user, pty=True)
            if confirm("syncdb?"):
                syncdb()
            sudo_chain('chmod -R ug+rw .',
                    'find . -type d -exec chmod ug+x {} \;',
                    'chown -R %(deploy_user)s:%(deploy_group)s .' % env,
                    _restart_command(),
                    pty=True)
