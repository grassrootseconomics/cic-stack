# standard import

# third-party imports
# this must be included for the package to be recognized as a tasks package
import celery

celery_app = celery.current_app
# export external celery task modules
from .logger import *
from .ussd_session import *
from .callback_handler import *
from .metadata import *
from .notifications import *
from .processor import *
