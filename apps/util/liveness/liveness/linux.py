# standard imports
import importlib
import sys
import os
import logging

logg = logging.getLogger().getChild(__name__)

pid = os.getpid()


def load(namespace, check_strs, rundir='/run'):
    logg.info('pid ' + str(pid))

    checks = []
    for m in check_strs:
        logg.debug('added liveness check module {}'.format(str(m)))
        module = importlib.import_module(m)
        checks.append(module)

    for check in checks:
        r = check.health()
        if r == False:
            raise RuntimeError('check {} failed'.format(str(check)))

    app_rundir = os.path.join(rundir, namespace)
    os.makedirs(app_rundir) # should not already exist
    f = open(os.path.join(app_rundir, 'pid'), 'w')
    f.write(str(pid))
    f.close()


def set(namespace, error=0, rundir='/run'):
    app_rundir = os.path.join(rundir, namespace)
    f = open(os.path.join(app_rundir, 'error'), 'w')
    f.write(str(error))
    f.close()


def reset(namespace, rundir='/run'):
    app_rundir = os.path.join(rundir, namespace)
    os.unlink(os.path.join(app_rundir, 'error'))
