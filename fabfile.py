from fabric.api import local, sudo, cd, env, lcd, execute, hosts, roles, task
from fabric.context_managers import prefix
from fabric.contrib.console import confirm
from fabric.contrib import django
from fabric.contrib.project import rsync_project
import sys
import os
import logging

logger = logging.getLogger(__name__)

# default to current working directory
env.project_path = os.path.dirname(__file__)
# needed to push vcweb.settings onto the path.
sys.path.append(os.path.abspath(env.project_path))

# default env configuration
env.roledefs = {
    'localhost': ['localhost'],
    'staging': ['vcweb-dev.asu.edu'],
    'prod': ['vcweb.asu.edu'],
}
env.python = 'python'
env.project_name = 'vcweb'
env.project_conf = 'vcweb.settings'
env.deploy_user = 'vcweb'
env.deploy_group = 'vcweb'
env.database = 'default'
env.deploy_parent_dir = '/opt/'
env.hg_url = 'https://bitbucket.org/virtualcommons/vcweb'
env.git_url = 'https://github.com/virtualcommons/vcweb.git'
env.services = 'nginx redis supervisord'
# FIXME: use django conf INSTALLED_APPS to introspect instead, similar to
# experiment_urls
env.docs_path = os.path.join(env.project_path, 'docs')
env.test_fixtures = ' '.join(['forestry_experiment_metadata', 'lighterprints_experiment_metadata',
                              'activities', 'bound_experiment_metadata', 'bound_parameters'])
env.virtualenv = 'vcweb'
env.virtualenv_path = '%s/.virtualenvs/%s' % (os.getenv('HOME'), env.project_name)
env.ignored_coverage = ('test', 'settings', 'migrations', 'fabfile', 'wsgi',
                        'broker', 'irrigation', 'commands', 'sanitation', 'vcweb-sockjs', 'sockjs-redis')
env.branches = {
    'prod': {
        'hg': 'stable',
        'git': 'master'
    },
    'staging': {
        'hg': 'default',
        'git': 'develop',
    }
}
env.vcs = 'git'
env.vcs_commands = {
    'hg': 'hg pull && hg up -C %(branch)s',
    'git': 'export GIT_WORK_TREE=%(deploy_dir)s && git checkout -f %(branch)s && git pull',
}

# django integration for access to settings, etc.
django.project(env.project_name)
from django.conf import settings as vcweb_settings


@hosts('vcweb-dev.asu.edu')
@task
def docs(remote_path='/home/www/dev.commons.asu.edu/vcweb/'):
    with lcd(env.docs_path):
        local("/usr/bin/make html")
        rsync_project(local_dir='build/html/', remote_dir=os.path.join(remote_path, 'apidocs'), delete=True)
    execute(coverage)
    rsync_project(local_dir='htmlcov/', remote_dir=os.path.join(remote_path, 'coverage'), delete=True)
    with cd(remote_path):
        sudo('find . -type d -exec chmod a+rx {} \; && chmod -R a+r . && chown -R alllee:commons .')


@task
def sh():
    dj('shell_plus')


def dj(command, **kwargs):
    """
    Run a Django manage.py command on the server.
    """
    _virtualenv(local,
                'python manage.py {dj_command} --settings {project_conf}'.format(dj_command=command, **env), **kwargs)


def _virtualenv(executor, *commands, **kwargs):
    """ source the virtualenv before executing this command """
    command = ' && '.join(commands)
    with prefix('. %(virtualenv_path)s/bin/activate' % env):
        executor(command, **kwargs)


@roles('localhost')
@task
def coverage():
    execute(test, coverage=True)
    ignored = ['*{0}*'.format(ignored_pkg) for ignored_pkg in env.ignored_coverage]
    local('coverage html --omit=' + ','.join(ignored))


@roles('localhost')
@task
def test(name=None, coverage=False):
    if name is not None:
        env.apps = name
    else:
        env.apps = ' '.join(vcweb_settings.VCWEB_APPS)
    if coverage:
        ignored = ['*{0}*'.format(ignored_pkg) for ignored_pkg in env.ignored_coverage]
        env.python = "coverage run --source='.' --omit=" + ','.join(ignored)
    local('%(python)s manage.py test %(apps)s' % env)


@task
def sockjs(port=None):
    if port is None:
        port = vcweb_settings.WEBSOCKET_PORT
    _virtualenv(local, "{python} vcweb/sockjs-redis.py {port}".format(python=env.python, port=port), capture=False)


@task
def ssl(ip='127.0.0.1', port=8443):
    dj('runsslserver {ip}:{port}'.format(ip=ip, port=port), capture=False)


@task
def server(ip="127.0.0.1", port=8000):
    dj('runserver {ip}:{port}'.format(ip=ip, port=port), capture=False)


@task
def dev():
    execute(staging)


@roles('staging')
@task
def staging():
    execute(deploy, env.branches['staging'])


@roles('prod')
@task
def prod():
    execute(deploy, env.branches['prod'])


@roles('localhost')
@task
def setup_postgres():
    local("psql -c 'create role %(db_user)s CREATEDB;'" % env)
    local("psql -c 'create database %(db_name)s;' -U %(db_user)s" % env)


def _restart_command(systemd=True):
    """
    FIXME: look into less drastic ways to reload the app and sockjs servers
    """
    if systemd:
        cmd = 'systemctl restart %(services)s && systemctl status -l %(services)s'
    else:
        cmd = ' && '.join(['service %s restart' % service for service in env.services.split()])
    return cmd % env


@roles('localhost')
@task
def clean():
    with cd(env.project_path):
        sudo('find . -name "*.pyc" -delete -print')
        sudo('rm -rvf htmlcov')
        sudo('rm -rvf docs/build')


@task
def restart():
    sudo(_restart_command(), pty=True)


def sudo_chain(*commands, **kwargs):
    sudo(' && '.join(commands), **kwargs)


def deploy(vcs_branch_dict):
    """ deploy to an already setup environment """
    env.deploy_dir = env.deploy_parent_dir + env.project_name
    vcs = env.vcs
    env.branch = vcs_branch_dict[vcs]
    env.vcs_command = env.vcs_commands[vcs] % env
    if confirm("Deploying '%(branch)s' branch to host %(host)s : \n\r %(vcs_command)s\nContinue? " % env):
        with cd(env.deploy_dir):
            sudo_chain(
                env.vcs_command,
                'chmod g+s logs',
                'chmod -R g+rw logs/',
                user=env.deploy_user, pty=True)
            env.static_root = vcweb_settings.STATIC_ROOT
            if confirm("Update pip dependencies?"):
                _virtualenv(sudo, 'pip install -Ur requirements.txt', user=env.deploy_user)
            if confirm("Update cron?"):
                _virtualenv(sudo, '%(python)s manage.py installtasks' % env, user=env.deploy_user)
            if confirm("Run database migrations?"):
                _virtualenv(sudo, '%(python)s manage.py migrate' % env, user=env.deploy_user)
            _virtualenv(sudo, '%(python)s manage.py collectstatic' % env, user=env.deploy_user)
            sudo_chain(
                'chmod -R ug+rw .',
                'find %(static_root)s %(virtualenv_path)s -type d -exec chmod a+x {} \;' % env,
                'find %(static_root)s %(virtualenv_path)s -type f -exec chmod a+r {} \;' % env,
                'find . -type d -exec chmod ug+x {} \;',
                'chown -R %(deploy_user)s:%(deploy_group)s . %(static_root)s %(virtualenv_path)s' % env,
                _restart_command(),
                pty=True)
