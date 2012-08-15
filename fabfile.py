from fabric.api import local, run, sudo, cd, env, hide
from fabric.contrib.console import confirm
from fabric.contrib import django
from fabric.context_managers import settings as fab_settings

import os, sys, shutil

# needed to push vcweb.settings onto the path.
sys.path.append(os.path.abspath('.'))

# default env configuration
env.python = 'python'
env.project_name = 'vcweb'
env.deploy_user = 'apache'
env.deploy_group = 'commons'
env.virtualenv_path = "%s/.virtualenvs/%s" % (os.getenv("HOME"), env['project_name'])
#env.virtualenv_path = '/opt/virtualenvs/%(project_name)s' % env
env.deploy_path = '/opt/'
# default to current working directory
env.project_path = os.path.dirname(__file__)
env.hosts = ['localhost']
env.hg_url = 'https://bitbucket.org/virtualcommons/vcweb'
env.apache = 'httpd'
env.applist = ['core', 'forestry', 'boundaries', 'lighterprints']
env.apps = ' '.join(env.applist)

# django integration for access to settings, etc.
django.project(env.project_name)


"""
this currently only works for sqlite3 development database.  do it by hand with
postgres a few times to figure out what to automate.
"""
syncdb_commands = [
        '%(python)s manage.py syncdb --noinput' % env,
        '%(python)s manage.py migrate' % env,
        '%(python)s manage.py loaddata slovakia' % env,
        ]

def shellp():
    local("{python} manage.py shell_plus".format(python=env.python), capture=False)

def shell():
    local("{python} manage.py shell".format(python=env.python), capture=False)

def syncdb(**kwargs):
    with cd(env.project_path):
        from vcweb import settings as vcweb_settings
        if os.path.exists(vcweb_settings.DATA_DIR):
            shutil.rmtree(vcweb_settings.DATA_DIR)
        os.mkdir(vcweb_settings.DATA_DIR)
        _virtualenv(local, *syncdb_commands, **kwargs)


def setup_virtualenv():
    """ Setup a fresh virtualenv """
    try:
	os.makedirs("%(virtualenv_path)s" % env)
    except OSError:
	pass
    local('virtualenv -p %(python)s --no-site-packages %(virtualenv_path)s' % env)

def clear_rabbitmq_db():
    with fab_settings(warn_only=True):
        sudo_chain(["rabbitmqctl %s" % cmd for cmd in ['stop_app', 'reset', 'start_app']])

def setup_rabbitmq():
    from vcweb import settings as vcweb_settings
    clear_rabbitmq_db()
    with fab_settings(warn_only=True):
        sudo("rabbitmqctl delete_user %s" % vcweb_settings.BROKER_USER, pty=True)
    sudo("rabbitmqctl add_user %s %s" % (vcweb_settings.BROKER_USER, vcweb_settings.BROKER_PASSWORD), pty=True)
    with fab_settings(warn_only=True):
        sudo("rabbitmqctl delete_vhost %s" % vcweb_settings.BROKER_VHOST, pty=True)
    sudo("rabbitmqctl add_vhost %s" % vcweb_settings.BROKER_VHOST, pty=True)
# figure out what the appropriate rabbitmq perms are here.
    sudo('rabbitmqctl set_permissions -p %s %s ".*" ".*" ".*"' % (vcweb_settings.BROKER_VHOST, vcweb_settings.BROKER_USER), pty=True)

def _virtualenv(executor, *commands, **kwargs):
    """ source the virtualenv before executing this command """
    env.command = ' && '.join(commands)
    if os.path.exists(env.virtualenv_path):
        return executor('. %(virtualenv_path)s/bin/activate && %(command)s' % env, **kwargs)
    else:
        return executor(env.command, **kwargs)

def pip():
    ''' looks for requirements.pip in the django project directory '''
    _virtualenv(local, 'pip install -r %(project_path)s/vcweb/requirements.pip' % env)
    # install bootstrap forms from github
    _virtualenv(local, 'pip install -e git+git://github.com/earle/django-bootstrap.git#egg=bootstrap')
    #with cd(env.virtualenv_path):
    #    sudo_chain('chgrp -R %(deploy_group)s .' % env, 'chmod -R g+rw' % env, pty=True)

def host_type():
    run('uname -a')

def test():
    '''
    runs tests on this local codebase, not the deployed codebase
    '''
    with cd(env.project_path):
        _virtualenv(local, '%(python)s manage.py test %(apps)s' % env)

def sockjs(ip="127.0.0.1", port=None):
    from vcweb import settings as vcweb_settings
    if port is None:
        port = vcweb_settings.WEBSOCKET_PORT
    _virtualenv(local, "{python} vcweb/sockjs.py {port}".format(python=env.python, port=port), capture=False)

def tornadio(ip="127.0.0.1", port=None):
    from vcweb import settings as vcweb_settings
    if port is None:
        port = vcweb_settings.WEBSOCKET_PORT
    _virtualenv(local, "{python} vcweb/vcwebio.py {port}".format(python=env.python, port=port), capture=False)


def server(ip="127.0.0.1", port=8000):
    local("{python} manage.py runserver {ip}:{port}".format(python=env.python, **locals()), capture=False)

def push():
    local('hg push ssh://hg@bitbucket.org/virtualcommons/vcweb')

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

def staticg():
    local('%(python)s manage.py generate_static_dajaxice > static/js/dajaxice.core.js' % env)
    local('%(python)s manage.py collectstatic' % env)

def setup():
    setup_virtualenv()
    #sudo('hg clone %(hg_url)s %(deploy_path)s' % env, pty=True, user=env.deploy_user)
    #sudo_chain('chown -R %(deploy_user)s:%(deploy_group)s %(deploy_path)s' % env,
    #        'chmod -R ug+rw %(deploy_path)s' % env,
    #        'find %(deploy_path)s -type d -exec chmod ug+x {} \;' % env,
    #        pty=True)
    pip()

def _restart_command():
    return 'service %(apache)s restart' % env

def restart():
    sudo(_restart_command(), pty=True)

def sudo_chain(*commands, **kwargs):
    sudo(' && '.join(commands), **kwargs)

def deploy():
    from vcweb import settings as vcweb_settings
    """ deploys to an already setup environment """
    env.project_path = env.deploy_path + env.project_name
    push()
    if confirm("Deploy to %(hosts)s ?" % env):
        with cd(env.project_path):
            sudo_chain('hg pull && hg up -C',
                    'chmod -R g+w logs',
                    user=env.deploy_user, pty=True)
            env.static_root = vcweb_settings.STATIC_ROOT
            _virtualenv(run,'%(python)s manage.py collectstatic' % env)
            sudo_chain('chmod -R ug+rw .',
                    'find %(static_root)s -type d -exec chmod a+x {} \;' % env,
                    'find . -type d -exec chmod ug+x {} \;',
                    'chown -R %(deploy_user)s:%(deploy_group)s . %(static_root)s' % env,
                    _restart_command(),
                    pty=True)
