import os
import sys

from invoke import task

# NB: assumes containerized execution
sys.path.append('/code/')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vcweb.settings.dev')

def dj(ctx, subcommand, **kwargs):
    """
    Run a Django manage.py subcommand.
    """
    ctx.run(
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
