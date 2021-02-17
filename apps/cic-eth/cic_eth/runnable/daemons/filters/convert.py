
#__convert_log_hash = '0x7154b38b5dd31bb3122436a96d4e09aba5b323ae1fd580025fab55074334c095' # keccak256(Conversion(address,address,address,uint256,uint256,address)

#def parse_convert_log(w3, entry):
#    data = entry.data[2:]
#    from_amount = int(data[:64], 16)
#    to_amount = int(data[64:128], 16)
#    holder_address_hex_raw = '0x' + data[-40:]
#    holder_address_hex = w3.toChecksumAddress(holder_address_hex_raw)
#    o = {
#            'from_amount': from_amount,
#            'to_amount': to_amount,
#            'holder_address': holder_address_hex
#            }
#    logg.debug('parsed convert log {}'.format(o))
#    return o


#def convert_filter(w3, tx, rcpt, chain_spec):
#    destination_token_address = None
#    recipient_address = None
#    amount = 0
#    for l in rcpt['logs']:
#        event_topic_hex = l['topics'][0].hex()
#        if event_topic_hex == __convert_log_hash:
#            tx_hash_hex = tx['hash'].hex()
#            try:
#                convert_transfer = TxConvertTransfer.get(tx_hash_hex)
#            except UnknownConvertError:
#                logg.warning('skipping unknown convert tx {}'.format(tx_hash_hex))
#                continue
#            if convert_transfer.transfer_tx_hash != None:
#                logg.warning('convert tx {} cache record already has transfer hash {}, skipping'.format(tx_hash_hex, convert_transfer.transfer_hash))
#                continue
#            recipient_address = convert_transfer.recipient_address
#            logg.debug('found convert event {} recipient'.format(tx_hash_hex, recipient_address))
#            r = parse_convert_log(l)
#            destination_token_address = l['topics'][3][-20:]
#
#    if destination_token_address == zero_address or destination_token_address == None:
#        return None
#
#    destination_token_address_hex = destination_token_address.hex()
#    s = celery.signature(
#            'cic_eth.eth.bancor.transfer_converted',
#            [
#                [{
#                    'address': w3.toChecksumAddress(destination_token_address_hex),
#                    }],
#                r['holder_address'],
#                recipient_address,
#                r['to_amount'],
#                tx_hash_hex,
#                str(chain_spec),
#                ],
#                queue=queue,
#            )
#    logg.info('sending tx signature {}'.format(s))
#    t = s.apply_async()
#    logg.debug('submitted transfer after convert task uuid {} {}'.format(t, t.successful()))
#    return t
