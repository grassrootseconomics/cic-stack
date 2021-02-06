# standard import
import os
import logging
import urllib
import json

# third-party imports
# this must be included for the package to be recognized as a tasks package
import celery

celery_app = celery.current_app
# export external celery task modules
from .foo import log_it_plz
from .ussd import persist_session_to_db
from .callback_handler import process_account_creation_callback
