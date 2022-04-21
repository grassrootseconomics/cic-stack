# standard imports
import json

# external imports
from cic_types.condiments import MetadataPointer

# local imports
from cic_ussd.cache import cache_data_key, get_cached_data
from cic_ussd.state_machine.logic.tokens import (is_valid_token_selection,
                                                 process_token_selection,
                                                 set_selected_active_token)
from cic_ussd.account.tokens import get_cached_token_data_list


# test imports


def test_is_valid_token_selection(activated_account,
                                  cache_token_data_list,
                                  cache_token_symbol_list,
                                  cached_ussd_session,
                                  init_cache,
                                  init_database):
    cached_token_data_list = get_cached_token_data_list(activated_account.blockchain_address)
    ussd_session = get_cached_data(cached_ussd_session.external_session_id)
    ussd_session = json.loads(ussd_session)
    ussd_session['data'] = {'account_tokens_list': cached_token_data_list}
    state_machine_data = ('GFT', ussd_session, activated_account, init_database)
    assert is_valid_token_selection(state_machine_data) is True
    state_machine_data = ('1', ussd_session, activated_account, init_database)
    assert is_valid_token_selection(state_machine_data) is True
    state_machine_data = ('3', ussd_session, activated_account, init_database)
    assert is_valid_token_selection(state_machine_data) is False


def test_process_token_selection(activated_account,
                                 cache_token_data_list,
                                 cache_token_symbol_list,
                                 cached_ussd_session,
                                 celery_session_worker,
                                 init_cache,
                                 init_database):
    cached_token_data_list = get_cached_token_data_list(activated_account.blockchain_address)
    ussd_session = get_cached_data(cached_ussd_session.external_session_id)
    ussd_session = json.loads(ussd_session)
    ussd_session['data'] = {'account_tokens_list': cached_token_data_list}
    state_machine_data = ('GFT', ussd_session, activated_account, init_database)
    process_token_selection(state_machine_data)
    ussd_session = get_cached_data(cached_ussd_session.external_session_id)
    ussd_session = json.loads(ussd_session)
    assert ussd_session.get('data').get('selected_token').get('symbol') == 'GFT'


def test_set_selected_active_token(activated_account,
                                   cache_token_data_list,
                                   cache_token_symbol_list,
                                   cached_ussd_session,
                                   init_cache,
                                   init_database):
    cached_token_data_list = get_cached_token_data_list(activated_account.blockchain_address)
    ussd_session = get_cached_data(cached_ussd_session.external_session_id)
    ussd_session = json.loads(ussd_session)
    ussd_session['data'] = {'selected_token': cached_token_data_list[0]}
    state_machine_data = ('GFT', ussd_session, activated_account, init_database)
    set_selected_active_token(state_machine_data)
    identifier = bytes.fromhex(activated_account.blockchain_address)
    key = cache_data_key(identifier=identifier, salt=MetadataPointer.TOKEN_ACTIVE)
    active_token = get_cached_data(key)
    assert active_token == 'GFT'
