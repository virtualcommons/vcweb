from fabric.api import local, run, sudo, cd, env, lcd, hosts
from fabric.context_managers import settings as fab_settings
from fabric.contrib import django
from fabric.contrib.console import confirm
from fabric.contrib.project import rsync_project

import os, sys, shutil, logging

logger = logging.getLogger(__name__)

# default to current working directory
env.project_path = os.path.dirname(__file__)
# needed to push vcweb.settings onto the path.
sys.path.append(os.path.abspath(env.project_path))

# default env configuration
env.python = 'python'
env.project_name = 'vcweb'
env.deploy_user = 'apache'
env.deploy_group = 'commons'
env.virtualenv_path = "%s/.virtualenvs/%s" % (os.getenv("HOME"), env['project_name'])
env.database = 'default'
#env.virtualenv_path = '/opt/virtualenvs/%(project_name)s' % env
env.deploy_path = '/opt/'
env.hosts = ['localhost']
env.hg_url = 'https://bitbucket.org/virtualcommons/vcweb'
env.apache = 'httpd'
env.applist = ['core', 'forestry', 'bound', 'lighterprints', 'broker']
env.docs_path = os.path.join(env.project_path, 'docs')
env.remote_docs_path = '/home/csid/public_html/api/vcweb'
env.testdata_fixtures = 'forestry_experiment_metadata lighterprints_experiment_metadata activities bound_experiment_metadata bound_parameters'
env.apps = ' '.join(env.applist)

# django integration for access to settings, etc.
django.project(env.project_name)

"""
this currently only works for sqlite3 development database.  do it by hand with
postgres a few times to figure out what to automate.
"""
syncdb_commands = [
        '%(python)s manage.py syncdb --noinput --database=%(database)s' % env,
        '%(python)s manage.py migrate' % env,
        ]


@hosts('csid@commons.asu.edu')
def docs():
    with lcd(env.docs_path):
        local("/usr/bin/make html")
        rsync_project(env.remote_docs_path, 'build/html/')
    with cd(env.remote_docs_path):
        run('find . -type d -exec chmod a+rx {} \; && chmod -R a+r .')

def testdata():
    syncdb()
    with cd(env.project_path):
        _virtualenv(local, '%(python)s manage.py loaddata %(testdata_fixtures)s' % env)
    
def migrate():
    local("{python} manage.py migrate".format(python=env.python), capture=False)

def clean_update():
    local("hg pull && hg up -C")

def cu():
    clean_update()
    migrate()

def psh():
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
    _virtualenv(local, 'pip install -U -r %(project_path)s/vcweb/requirements.pip' % env)
    #with cd(env.virtualenv_path):
    #    sudo_chain('chgrp -R %(deploy_group)s .' % env, 'chmod -R g+rw' % env, pty=True)

def host_type():
    run('uname -a')

def test(name=None):
    '''
    runs tests on this local codebase, never remote
    run specific tests like fab test:core.ExperimentTest
    '''
    with cd(env.project_path):
        if name is not None:
            env.apps = name
        _virtualenv(local, '%(python)s manage.py test %(apps)s' % env)

def sockjs(ip="127.0.0.1", port=None):
    from vcweb import settings as vcweb_settings
    if port is None:
        port = vcweb_settings.WEBSOCKET_PORT
    _virtualenv(local, "{python} vcweb/vcweb-sockjs.py {port}".format(python=env.python, port=port), capture=False)

def tornadio(ip="127.0.0.1", port=None):
    from vcweb import settings as vcweb_settings
    if port is None:
        port = vcweb_settings.WEBSOCKET_PORT
    _virtualenv(local, "{python} vcweb/vcwebio.py {port}".format(python=env.python, port=port), capture=False)

def server(ip="127.0.0.1", port=8000):
    local("{python} manage.py runserver {ip}:{port}".format(python=env.python, **locals()), capture=False)

def dev():
    env.project_path = env.deploy_path + env.project_name
    env.hosts =['sod51.asu.edu']

def prod():
    env.project_path = env.deploy_path + env.project_name
    env.hosts = ['vcweb.asu.edu']

def loc():
    env.deploy_user = 'alllee'
    env.apache = 'apache2'
    env.hosts = ['localhost']

def collectstatic():
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
    return 'service %(apache)s restart && supervisorctl restart vcweb-sockjs' % env

def clean():
    with cd(env.project_path):
        sudo('find . -name "*.pyc" -delete -print')
        
def restart():
    sudo(_restart_command(), pty=True)

def sudo_chain(*commands, **kwargs):
    sudo(' && '.join(commands), **kwargs)

def deploy():
    from vcweb import settings as vcweb_settings
    """ deploys to an already setup environment """
    if confirm("Deploy to %(hosts)s ?" % env):
        with cd(env.project_path):
            sudo_chain(
                    'hg pull && hg up -C',
                    'chmod g+s logs',
                    'chmod -R g+rw logs/',
                    user=env.deploy_user, pty=True)
            env.static_root = vcweb_settings.STATIC_ROOT
            _virtualenv(run,'%(python)s manage.py collectstatic' % env)
            _virtualenv(run,'%(python)s manage.py installtasks' % env)
            sudo_chain(
                    'chmod -R ug+rw .',
                    'find %(static_root)s -type d -exec chmod a+x {} \;' % env,
                    'find %(static_root)s -type f -exec chmod a+r {} \;' % env,
                    'find . -type d -exec chmod ug+x {} \;',
                    'chown -R %(deploy_user)s:%(deploy_group)s . %(static_root)s' % env,
                    _restart_command(),
                    pty=True)
