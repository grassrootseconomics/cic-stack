# standard imports
import logging
import urllib.parse
import urllib.error
import urllib.request
import json

# external imports
import celery
from cic_types.processor import generate_metadata_pointer

logg = logging.getLogger().getChild(__name__)

celery_app = celery.current_app


class MetadataTask(celery.Task):

    meta_host = None
    meta_port = None
    meta_path = ''
    meta_ssl = False
    autoretry_for = (
            urllib.error.HTTPError,
            )
    retry_kwargs = {
        'countdown': 3,
        'max_retries': 100,
            }

    @classmethod
    def meta_url(self):
        scheme = 'http'
        if self.meta_ssl:
            scheme += s
        url = urllib.parse.urlparse('{}://{}:{}/{}'.format(scheme, self.meta_host, self.meta_port, self.meta_path))
        return urllib.parse.urlunparse(url)

@celery_app.task(bind=True, base=MetadataTask)
def resolve_phone(self, phone):
    identifier = generate_metadata_pointer(phone.encode('utf-8'), 'cic.phone')
    url = urllib.parse.urljoin(self.meta_url(), identifier)
    logg.debug('attempt getting phone pointer at {}'.format(url))
    r = urllib.request.urlopen(url)
    address = json.load(r)
    logg.debug('address {} for phone {}'.format(address, phone))


@celery_app.task(bind=True, base=MetadataTask)
def transfer_opening_balance(self, phone, address):
    pass

