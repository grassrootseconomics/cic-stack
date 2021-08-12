# standard import

# third-party imports
import celery

# export external celery task modules
from .callback_handler import *
from .metadata import *
from .notifications import *
from .processor import *
from .ussd_session import *

celery_app = celery.current_app
