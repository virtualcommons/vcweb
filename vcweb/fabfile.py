from fabric.api import run, local, sudo, cd, env, require
from fabric.decorators import hosts
from fabric.contrib.console import confirm

""" Default Configuration """
env.python = 'python2.6'
env.project_name = 'vcweb'
env.virtualenv_path = '/opt/virtualenvs/%(project_name)s' % env
env.deploy_path = '/opt/webapps/virtualcommons/'
env.project_path = env.deploy_path + env.project_name

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

def virtualenv():
    """ Setup a fresh virtualenv """
    run('virtualenv -p %(python)s --no-site-packages %(virtualenv_path)s;' % env)

def _virtualenv(command, use_django_path=False):
    """ source the virtualenv before executing this command """
    #env.command = '%s/%s' % (env.project_path, command) if use_django_path else command
    env.command = command
    run('source %(virtualenv_path)s/bin/activate && %(command)s' % env)

def pip():
    with cd(env.project_path):
        _virtualenv('pip install -E %(virtualenv_path)s -r %(project_path)s/requirements.pip' % env)

def host_type():
    run('uname -a')

def test():
    env.hosts = ['localhost']
    with cd(env.project_path):
        _virtualenv('%(python)s manage.py test' % env)

def server(ip="149.169.203.115", port=8080):
    local("./manage.py runserver {ip}:{port}".format(**locals()), capture=False)

def push():
    local('hg push')

@hosts('dev.commons.asu.edu')
def dev():
    pass

@hosts('vcweb.asu.edu')
def prod():
    pass

@hosts('localhost')
def loc():
    pass

def deploy():
    push()
    if confirm("Deploy to %s ?" % (loc.hosts or dev.hosts or prod.hosts)):
        with cd(env.project_path):
            run('hg pull')
            run('hg up')
            sudo('chmod -R ug+rw .', pty=True)
            sudo('find . -type d -exec chmod ug+x {} \;', pty=True)
            sudo('service httpd restart', pty=True)
