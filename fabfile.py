from fabric.api import local, run, sudo, cd, env, lcd, execute, hosts, roles
from fabric.context_managers import prefix
from fabric.contrib import django
from fabric.contrib.console import confirm
from fabric.contrib.project import rsync_project
import sys
import os
import shutil
import logging

logger = logging.getLogger(__name__)

# default to current working directory
env.project_path = os.path.dirname(__file__)
# needed to push vcweb.settings onto the path.
sys.path.append(os.path.abspath(env.project_path))

# default env configuration
env.roledefs = {
    'test': ['localhost'],
    'dev': ['www.thevirtualcommons.org'],
    'staging': ['www.thevirtualcommons.org'],
    'prod': ['vcweb.asu.edu'],
}
env.python = 'python'
env.project_name = 'vcweb'
env.deploy_user = 'apache'
env.deploy_group = 'commons'
env.database = 'default'
env.deploy_path = '/opt/'
env.hg_url = 'https://bitbucket.org/virtualcommons/vcweb'
env.apache = 'httpd'
# FIXME: use django conf INSTALLED_APPS to introspect instead, similar to
# experiment_urls
env.docs_path = os.path.join(env.project_path, 'docs')
env.test_fixtures = ' '.join(['forestry_experiment_metadata', 'lighterprints_experiment_metadata',
                              'activities', 'bound_experiment_metadata', 'bound_parameters'])
env.virtualenv_path = '%s/.virtualenvs/%s' % (
    os.getenv('HOME'), env.project_name)

# django integration for access to settings, etc.
django.project(env.project_name)
from django.conf import settings as vcweb_settings


"""
this currently only works for sqlite3 development database.  do it by hand with
postgres a few times to figure out what to automate.
"""
syncdb_commands = [
    '%(python)s manage.py syncdb --noinput --database=%(database)s' % env,
    '%(python)s manage.py migrate' % env,
]


@hosts('csid@commons.asu.edu')
def docs(api_path='/home/csid/public_html/api/vcweb'):
    with lcd(env.docs_path):
        local("/usr/bin/make html")
        rsync_project(api_path, 'build/html/')
    with cd(api_path):
        run('find . -type d -exec chmod a+rx {} \; && chmod -R a+r .')


def testdata():
    syncdb()
    with cd(env.project_path):
        _virtualenv(
            local, '%(python)s manage.py loaddata %(test_fixtures)s' % env)


def migrate():
    local("%(python)s manage.py migrate" % env, capture=False)


def clean_update():
    local("hg pull && hg up -C")


def cu():
    execute(clean_update)
    execute(migrate)


def psh():
    local("%(python)s manage.py shell_plus" % env, capture=False)


def shell():
    local("%(python)s manage.py shell" % env, capture=False)


def syncdb(**kwargs):
    with cd(env.project_path):
        if os.path.exists(vcweb_settings.DATA_DIR):
            shutil.rmtree(vcweb_settings.DATA_DIR)
        os.mkdir(vcweb_settings.DATA_DIR)
        _virtualenv(local, *syncdb_commands, **kwargs)


def _virtualenv(executor, *commands, **kwargs):
    """ source the virtualenv before executing this command """
    env.command = ' && '.join(commands)
    with prefix('. %(virtualenv_path)s/bin/activate' % env):
        executor('%(command)s' % env, **kwargs)
    """
    if os.path.exists(env.virtualenv_path):
    return executor('. %(virtualenv_path)s/bin/activate && %(command)s' % env, **kwargs)
    else:
    return executor(env.command, **kwargs)
"""


def host_type():
    run('uname -a')


def coverage():
    execute(test, coverage=True)
    local('coverage html --omit=*test*,*settings*,*migrations*,*fabfile*,*wsgi*')


def test(name=None, coverage=False):
    if name is not None:
        env.apps = name
    else:
        apps = ['vcweb.core'] + vcweb_settings.EXPERIMENTS
        env.apps = ' '.join(apps)

    if coverage:
        env.python = "coverage run --source='.' --omit=*test*,*settings*,*migrations*,*fabfile*,*wsgi*"
    local('%(python)s manage.py test %(apps)s' % env)


def sockjs(ip="127.0.0.1", port=None):
    if port is None:
        port = vcweb_settings.WEBSOCKET_PORT
    _virtualenv(
        local, "{python} vcweb/vcweb-sockjs.py {port}".format(python=env.python, port=port), capture=False)


def tornadio(ip="127.0.0.1", port=None):
    if port is None:
        port = vcweb_settings.WEBSOCKET_PORT
    _virtualenv(
        local, "{python} vcweb/vcwebio.py {port}".format(python=env.python, port=port), capture=False)


def ssl(ip='127.0.0.1', port=8443):
    local("{python} manage.py runsslserver {ip}:{port}".format(
        python=env.python, **locals()), capture=False)


def server(ip="127.0.0.1", port=8000):
    local("{python} manage.py runserver {ip}:{port}".format(
        python=env.python, **locals()), capture=False)


@roles('dev')
def dev():
    execute(deploy)


@roles('prod')
def prod():
    execute(deploy)


@roles('test')
def setup_postgres():
    local("psql -c 'create role %(db_user)s CREATEDB;'" % env)
    local("psql -c 'create database %(db_name)s;' -U %(db_user)s" % env)


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
    """ deploy to an already setup environment """
    env.project_path = env.deploy_path + env.project_name
    if confirm("Deploy to %(roles)s ?" % env):
        with cd(env.project_path):
            sudo_chain(
                'hg pull && hg up -C',
                'hg id -n > build-id.txt',
                'chmod g+s logs',
                'chmod -R g+rw logs/',
                user=env.deploy_user, pty=True)
            env.static_root = vcweb_settings.STATIC_ROOT
            _virtualenv(run, '%(python)s manage.py collectstatic' % env)
            _virtualenv(run, '%(python)s manage.py installtasks' % env)
            sudo_chain(
                'chmod -R ug+rw .',
                'find %(static_root)s -type d -exec chmod a+x {} \;' % env,
                'find %(static_root)s -type f -exec chmod a+r {} \;' % env,
                'find . -type d -exec chmod ug+x {} \;',
                'chown -R %(deploy_user)s:%(deploy_group)s . %(static_root)s' % env,
                _restart_command(),
                pty=True)
