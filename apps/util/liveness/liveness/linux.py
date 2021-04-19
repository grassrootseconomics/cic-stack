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


def load(check_strs, namespace=default_namespace, rundir='/run', *args, **kwargs):

    if namespace == None:
        import socket
        namespace = socket.gethostname()

    logg.info('pid ' + str(pid))

    checks = []
    for m in check_strs:
        logg.debug('added liveness check: {}'.format(str(m)))
        module = importlib.import_module(m)
        checks.append(module)

    for check in checks:
        r = check.health(args, kwargs)
        if r == False:
            raise RuntimeError('liveness check {} failed'.format(str(check)))
        logg.info('liveness check passed: {}'.format(str(check)))

    app_rundir = os.path.join(rundir, namespace)
    os.makedirs(app_rundir) # should not already exist
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
    os.unlink(os.path.join(app_rundir, 'error'))
