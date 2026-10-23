import {empty, validate} from './model.mjs';
import {openRemote,readRemote,updateRemote} from './remote-store.mjs';
export {initializeSource,commitSource} from './remote-store.mjs';
export async function openWorkspace(){
  const params=new URLSearchParams(location.search);
  if(params.has('workspace')||params.get('local')==='1'){const name=params.get('workspace');const db=await openStore(name?`ci-package-test-workbench:${name}`:undefined);db.info={mode:'local-preview',initialized:true};return db;}
  return openRemote();
}

export function openStore(name = 'ci-package-test-workbench') {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open(name, 1);
    request.onupgradeneeded = () => request.result.createObjectStore('state');
    request.onerror = () => reject(request.error);
    request.onblocked = () => reject(new Error('Database upgrade blocked; close other workbench tabs'));
    request.onsuccess = () => resolve(request.result);
  });
}
export function read(db) {
  if(db.remote)return readRemote(db);
  return new Promise((resolve, reject) => {
    const tx = db.transaction('state', 'readonly'); const request = tx.objectStore('state').get('workspace');
    let state;
    request.onsuccess = () => { state = request.result ?? empty(); };
    tx.oncomplete = () => { try { resolve(validate(state)); } catch (error) { reject(error); } };
    tx.onabort = () => reject(tx.error ?? new Error('Read aborted'));
  });
}
export function update(db, expectedRevision, action) {
  if(db.remote)return updateRemote(db,expectedRevision,action);
  return new Promise((resolve, reject) => {
    const tx = db.transaction('state', 'readwrite'); const store = tx.objectStore('state');
    const request = store.get('workspace'); let result; let failure;
    request.onsuccess = () => {
      try {
        const current = validate(request.result ?? empty());
        if (current.revision !== expectedRevision) throw new Error('Another tab changed the data. Reload and review before saving.');
        result = validate(action(current));
        if (result !== current) {
          if (result.revision !== current.revision + 1) throw new Error('Invalid update revision');
          store.put(result, 'workspace');
        }
      } catch (error) { failure = error; tx.abort(); }
    };
    tx.oncomplete = () => resolve(result);
    tx.onabort = () => reject(failure ?? tx.error ?? new Error('Save aborted; previous data retained'));
  });
}
