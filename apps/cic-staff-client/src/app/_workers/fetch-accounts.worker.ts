/// <reference lib="webworker" />

import { Envelope, Syncable, User } from 'cic-client-meta';
import { add0x } from '@src/assets/js/ethtx/hex';
import { personValidation, vcardValidation } from '@app/_helpers/schema-validation';
import * as vCard from 'vcard-parser';

const headers = {
  'x-cic-automerge': 'client',
};

const options = {
  headers,
};

addEventListener('message', async ({ data }) => {
  if (data.addresses instanceof Array) {
    for (const accountAddress of data.addresses) {
      try {
        const account = await getAccountByAddress(accountAddress, data.url, data.token);
        postMessage(account);
      } catch (error) {
        console.log(`ERROR we failed to get account ${accountAddress}`, error);
      }
    }
  }
});

async function getAccountByAddress(
  accountAddress: string,
  metaUrl: string,
  token: string,
): Promise<any> {
  const userKey = await User.toKey(add0x(accountAddress));

  headers['Authorization'] = 'Bearer ' + token;
  const response = await fetch(`${metaUrl}/${userKey}`, options)
    .then((res) => {
      if (res.ok) {
        return res.json();
      } else {
        return Promise.reject({
          status: res.status,
          statusText: res.statusText,
        });
      }
    })
    .catch((error) => {
      throw Error(`${error.status}: ${error.statusText}`);
    });
  const account: Syncable = Envelope.fromJSON(JSON.stringify(response)).unwrap();
  const accountInfo = account.m.data;
  await personValidation(accountInfo);
  accountInfo.vcard = vCard.parse(atob(accountInfo.vcard));
  await vcardValidation(accountInfo.vcard);
  return accountInfo;
}
