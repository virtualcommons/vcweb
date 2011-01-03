from fabric.api import run, local, sudo, cd, env
from fabric.decorators import hosts
from fabric.contrib.console import confirm


syncdb_commands = ['(test -f vcweb.db && rm vcweb.db) || true', 
        './manage.py syncdb --noinput', 
        './manage.py loaddata test_users_participants', 
        './manage.py loaddata forestry_test_data' ]

def syncdb():
    for command in syncdb_commands:
        local(command, capture=False)

@hosts('dev.commons.asu.edu', 'localhost')
def host_type():
    run('uname -a')

def test():
    local('./manage.py test', capture=False)


def server(ip="149.169.203.115", port=8080):
    local("./manage.py runserver {ip}:{port}".format(**locals()), capture=False)

def push():
    local('hg push')

@hosts('dev.commons.asu.edu')
def dev():
    deploy()

@hosts('vcweb.asu.edu')
def prod():
    deploy()

def deploy():
    test()
    push()
    if confirm("Deploy to %s ?" % (dev.hosts or prod.hosts)):
        with cd('/opt/webapps/virtualcommons/'):
            run('hg pull')
            run('hg up')
            with cd('/opt/webapps/virtualcommons/vcweb'):
                run('touch django.wsgi')
                for command in syncdb_commands:
                    run(command)
            sudo('chmod -R ug+rw .', pty=True)
            sudo('find . -type d -exec chmod ug+x {} \;', pty=True)
            sudo('chown -R alllee:commons .', pty=True)
            sudo('service httpd restart', pty=True)
