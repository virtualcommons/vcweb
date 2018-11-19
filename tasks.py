import os
import pathlib
import sys

from invoke import task

from vcweb.core.utils import confirm

# NB: assumes containerized execution
sys.path.append('/code/')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vcweb.settings.dev')
from django.conf import settings

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


@task(aliases=['init'])
def run_migrations(ctx, clean=False, initial=False):
    if clean:
        ctx.run('find vcweb -name 00*.py -delete -print')
    dj(ctx, 'makemigrations --noinput')
    migrate_command = 'migrate --noinput'
    if initial:
        migrate_command += ' --fake-initial'
    dj(ctx, migrate_command)


@task(aliases=['ddb'])
def drop_db(ctx, database=None, create=False):
    db_config = get_database_settings(database)
    create_pgpass_file(ctx)
    set_connection_limit = 'psql -h {db_host} -c "alter database {db_name} connection limit 1;" -w {db_name} {db_user}'.format(
        **db_config)
    terminate_backend = 'psql -h {db_host} -c "select pg_terminate_backend(pid) from pg_stat_activity where pid <> pg_backend_pid() and datname=\'{db_name}\'" -w {db_name} {db_user}'.format(
        **db_config)
    dropdb = 'dropdb -w --if-exists -e {db_name} -U {db_user} -h {db_host}'.format(**db_config)
    check_if_database_exists = 'psql template1 -tA -U {db_user} -h {db_host} -c "select 1 from pg_database where datname=\'{db_name}\'"'.format(
        **db_config)
    if ctx.run(check_if_database_exists, echo=True).stdout.strip():
        ctx.run(set_connection_limit, echo=True, warn=True)
        ctx.run(terminate_backend, echo=True, warn=True)
        ctx.run(dropdb, echo=True)

    if create:
        ctx.run('createdb -w {db_name} -U {db_user} -h {db_host}'.format(**db_config), echo=True)


@task(aliases=['sh'])
def shell(c, print_sql=False):
    flags = "--ipython{}".format('--print-sql' if print_sql else '')
    c.run("./manage.py shell_plus {}".format(flags), pty=True)


@task
def test(ctx, tests='', coverage=True):
    coverage_omit_patterns = ('templates/*', 'settings/*', 'migrations/*', 'wsgi.py', 'management/*', 'tasks.py', 'apps.py')
    coverage_src_patterns = ('vcweb/core', 'vcweb/experiment')
    if coverage:
        ignored = ['*{0}*'.format(ignored_pkg) for ignored_pkg in coverage_omit_patterns]
        test_command = "coverage run --source={0} --omit={1}".format(','.join(coverage_src_patterns),
                                                                     ','.join(ignored))
    else:
        test_command = 'python3'
    ctx.run("{test_command} manage.py test {tests}".format(tests=tests, test_command=test_command),
            env={'DJANGO_SETTINGS_MODULE': 'vcweb.settings.dev'})


@task(aliases=['rfd'])
def restore_from_dump(ctx, target_database=None, dumpfile='database.sql', force=False, migrate=True, clean=False):
    db_config = get_database_settings(target_database)
    dumpfile_path = pathlib.Path(dumpfile)
    if dumpfile.endswith('.sql') and dumpfile_path.is_file():
        if not force:
            confirm("This will destroy the database and try to reload it from a dumpfile {0}. Continue? (y/n) ".format(
                dumpfile))
        drop_db(ctx, database=target_database, create=True)
        ctx.run('psql -w -q -h db {db_name} {db_user} < {dumpfile}'.format(dumpfile=dumpfile, **db_config), echo=True)
    elif dumpfile.endswith('.sql.gz') and dumpfile_path.is_file():
        if not force:
            confirm("This will destroy the database and try to reload it from a dumpfile {0}. Continue? (y/n) ".format(
                dumpfile))
        drop_db(ctx, database=target_database, create=True)
        ctx.run('zcat {dumpfile} | psql -w -q -h db {db_name} {db_user}'.format(dumpfile=dumpfile, **db_config), echo=True)
    if migrate:
        run_migrations(ctx, clean=clean, initial=True)


def get_database_settings(db_key=None):
    if db_key is None:
        db_key = 'default'
    return dict(
        db_name=settings.DATABASES[db_key]['NAME'],
        db_host=settings.DATABASES[db_key]['HOST'],
        db_user=settings.DATABASES[db_key]['USER'],
        db_password=settings.DATABASES[db_key]['PASSWORD']
    )


@task(aliases=['dbsh'])
def db_shell(ctx, db_key=None):
    """Open a pgcli shell to the database"""
    ctx.run('pgcli -h {db_host} -d {db_name} -U {db_user}'.format(**get_database_settings(db_key)), pty=True)


@task(aliases=['pgpass'])
def create_pgpass_file(ctx, force=False):
    db_config = get_database_settings()
    pgpass_path = os.path.join(os.path.expanduser('~'), '.pgpass')
    if os.path.isfile(pgpass_path) and not force:
        return
    with open(pgpass_path, 'w+') as pgpass:
        pgpass.write('db:*:*:{db_user}:{db_password}\n'.format(**db_config))
        ctx.run('chmod 0600 ~/.pgpass')


@task(aliases=['b'])
def backup(ctx):
    create_pgpass_file(ctx)
    ctx.run('autopostgresqlbackup')


@task
def prepare(ctx):
    dj(ctx, 'collectstatic --noinput')
