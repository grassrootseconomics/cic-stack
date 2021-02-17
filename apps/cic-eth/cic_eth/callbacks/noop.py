import celery

celery_app = celery.current_app
logg = celery_app.log.get_default_logger()


@celery_app.task(bind=True)
def noop(self, result, param, status_code):
    """A noop callback for task chains executed by external api methods. Logs the callback arguments.

    :param result: Task context object (on error) or return value of previous task (on success)
    :type result: Varies
    :param param: Static value passed from api caller
    :type param: Varies
    :param status_code: 0 on success, any other value is error
    :type status_code: int
    :returns: True
    :rtype: bool
    """
    logg.info('noop callback {} {} {}'.format(result, param, status_code))
    return result
