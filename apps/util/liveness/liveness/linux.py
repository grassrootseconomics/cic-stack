# standard imports
import importlib
import sys
import os
import logging

logg = logging.getLogger().getChild(__name__)

pid = os.getpid()

default_namespace = os.environ.get('LIVENESS_UNIT_NAME')
if default_namespace == None:
    import socket
    default_namespace = socket.gethostname()


def check_by_module(checks, *args, **kwargs):
    for check in checks:
        r = check.health(args, kwargs)
        if r == False:
            raise RuntimeError('liveness check {} failed'.format(str(check)))
        logg.info('liveness check passed: {}'.format(str(check)))


def check_by_string(check_strs, *args, **kwargs):
    checks = []
    for m in check_strs:
        logg.debug('added liveness check: {}'.format(str(m)))
        module = importlib.import_module(m)
        checks.append(module)
    return check_by_module(checks, args, kwargs)
   

def load(check_strs, namespace=default_namespace, rundir='/run', *args, **kwargs):

    if namespace == None:
        import socket
        namespace = socket.gethostname()

    check_by_string(check_strs)

    logg.info('pid ' + str(pid))

    app_rundir = os.path.join(rundir, namespace)
    os.makedirs(app_rundir, exist_ok=True) # should not already exist
    f = open(os.path.join(app_rundir, 'pid'), 'w')
    f.write(str(pid))
    f.close()


def set(error=0, namespace=default_namespace, rundir='/run'):
    app_rundir = os.path.join(rundir, namespace)
    f = open(os.path.join(app_rundir, 'error'), 'w')
    f.write(str(error))
    f.close()


def reset(namespace=default_namespace, rundir='/run'):
    app_rundir = os.path.join(rundir, namespace)
    os.unlink(os.path.join(app_rundir, 'pid'))
    os.unlink(os.path.join(app_rundir, 'error'))
