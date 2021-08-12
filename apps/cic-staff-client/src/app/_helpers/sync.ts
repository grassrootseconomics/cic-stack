import { ArgPair, Syncable } from 'cic-client-meta';
import * as Automerge from 'automerge';

export function updateSyncable(
  changes: Array<ArgPair>,
  changesDescription: string,
  syncable: Syncable
): any {
  syncable.m = Automerge.change(syncable.m, changesDescription, (m) => {
    changes.forEach((c) => {
      const path = c.k.split('.');
      let target = m['data'];
      while (path.length > 1) {
        const part = path.shift();
        target = target[part];
      }
      try {
        target[path[0]] = c.v;
      } catch (error) {
        if (
          !error.message.includes(
            'Cannot assign an object that already belongs to an Automerge document.'
          )
        ) {
          throw new Error(error);
        }
      }
    });
    m['timestamp'] = Math.floor(Date.now() / 1000);
  });
}
