import os
import sys

from invoke import task

# NB: assumes containerized execution
sys.path.append('/code/')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vcweb.settings.dev')

def dj(c, subcommand, **kwargs):
    """
    Run a Django manage.py subcommand.
    """
    c.run(
        'python3 /code/manage.py {subcommand} --settings {project_conf}'.format(
            subcommand=subcommand,
            project_conf=os.environ['DJANGO_SETTINGS_MODULE']
        ),
        **kwargs
    )


@task(aliases=['sh'])
def shell(c, print_sql=False):
    flags = "--ipython{}".format('--print-sql' if print_sql else '')
    c.run("./manage.py shell_plus {}".format(flags), pty=True)


@task
def test(c, tests='', coverage=True):
    coverage_omit_patterns = ('templates/*', 'settings/*', 'migrations/*', 'wsgi.py', 'management/*', 'tasks.py', 'apps.py')
    coverage_src_patterns = ('vcweb/core', 'vcweb/experiment')
    if coverage:
        ignored = ['*{0}*'.format(ignored_pkg) for ignored_pkg in coverage_omit_patterns]
        test_command = "coverage run --source={0} --omit={1}".format(','.join(coverage_src_patterns),
                                                                     ','.join(ignored))
    else:
        test_command = 'python3'
    c.run("{test_command} manage.py test {tests}".format(tests=tests, test_command=test_command),
          env={'DJANGO_SETTINGS_MODULE': 'vcweb.settings.dev'})
