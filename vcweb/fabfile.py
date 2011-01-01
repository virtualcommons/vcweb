from fabric.api import run, local

def host_type():
    run('uname -s')

def test():
    local('./manage.py test', capture=False)

def syncdb():
    local('test -f vcweb.db && rm vcweb.db', capture=False)
    local('./manage.py syncdb --noinput', capture=False)
    local('./manage.py loaddata test_users_participants', capture=False)
    local('./manage.py loaddata forestry_test_data', capture=False)
