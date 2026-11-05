/* AEGIS Web Edition: faithful JavaScript translation of aegis/security.py.
   Uses built-in Web Crypto only. No network requests or third-party scripts.
   A vault secret must be supplied independently; this module does not decrypt
   desktop .aegis backups or claim to be a desktop vault replacement. */
(function (root) {
  'use strict';
  const enc = new TextEncoder();
  const VERSION = 'aegis-derive-v1';
  const GROUPS = ['ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz',
    '0123456789', '!@#$%^&*()-_=+[]{};:,.?'];
  const ALPHABET = GROUPS.join('');
  const subtle = () => {
    const result = globalThis.crypto && globalThis.crypto.subtle;
    if (!result) throw new Error('Web Crypto is unavailable. Open this page in a modern browser on a secure origin.');
    return result;
  };
  function concat(...arrays) {
    const out = new Uint8Array(arrays.reduce((n, a) => n + a.length, 0));
    let offset = 0;
    for (const a of arrays) {out.set(a, offset); offset += a.length;}
    return out;
  }
  function u32(n) {
    const a = new Uint8Array(4);
    new DataView(a.buffer).setUint32(0, n, false);
    return a;
  }
  function u64(n) {
    const a = new Uint8Array(8);
    new DataView(a.buffer).setBigUint64(0, BigInt(n), false);
    return a;
  }
  function hexToBytes(s) {
    if (typeof s !== 'string' || !/^(?:[0-9a-fA-F]{2})+$/.test(s))
      throw new Error('Enter a valid hexadecimal secret with an even number of characters.');
    return Uint8Array.from(s.match(/.{2}/g), h => parseInt(h, 16));
  }
  function bytesToHex(bytes) {
    return Array.from(bytes, b => b.toString(16).padStart(2, '0')).join('');
  }
  async function importHmac(rawKey) {
    return subtle().importKey('raw', rawKey, {name:'HMAC', hash:'SHA-256'}, false, ['sign']);
  }
  async function hmac(key, message) {
    return new Uint8Array(await subtle().sign('HMAC', key, message));
  }
  async function sample(key, alphabet, state) {
    const n = alphabet.length;
    const limit = 256 - (256 % n);
    while (true) {
      const block = await hmac(key, u64(state.count));
      state.count += 1n;
      for (const b of block) {
        if (b < limit) return alphabet[b % n];
      }
    }
  }
  /** Produces identical output to Python aegis.security.generate_password() for
      the same phrase, account, length, private-secret bytes and revision.
      The private secret is a separate 32-byte+ value, not the master passphrase. */
  async function generatePassword(memorable, account, length, privateSecret, revision = 1) {
    if (typeof memorable !== 'string' || memorable.length < 1)
      throw new Error('Enter a memorable phrase.');
    if (typeof account !== 'string' || !account.trim())
      throw new Error('Enter an account or website.');
    if (!Number.isInteger(length) || length < 12 || length > 128)
      throw new Error('Choose a password length between 12 and 128.');
    if (!(privateSecret instanceof Uint8Array) || privateSecret.length < 32)
      throw new Error('Enter a private secret containing at least 32 bytes.');
    if (!Number.isInteger(revision) || revision < 1 || revision > 999999)
      throw new Error('Choose a password version between 1 and 999999.');
    const identifier = enc.encode(account.trim().toLowerCase());
    const context = concat(enc.encode(VERSION), new Uint8Array([0]),
      u32(identifier.length), identifier, u32(revision));
    const pbkdf2Key = await subtle().importKey('raw', enc.encode(memorable), 'PBKDF2', false, ['deriveBits']);
    const material = new Uint8Array(await subtle().deriveBits({name:'PBKDF2',
      hash:'SHA-256', salt:concat(privateSecret, context), iterations:310000}, pbkdf2Key, 256));
    const materialKey = await importHmac(material);
    const seed = await hmac(materialKey, enc.encode('aegis-output-v1'));
    const seedKey = await importHmac(seed);
    const state = {count:0n};
    const chars = [];
    for (const group of GROUPS) chars.push(await sample(seedKey, group, state));
    while (chars.length < length) chars.push(await sample(seedKey, ALPHABET, state));
    const prefix = enc.encode('shuffle');
    for (let i = chars.length - 1; i > 0; i--) {
      const limit = 4294967296 - (4294967296 % (i + 1));
      let value;
      do {
        const digest = await hmac(seedKey, concat(prefix, u64(state.count)));
        state.count += 1n;
        value = new DataView(digest.buffer, digest.byteOffset, 4).getUint32(0, false);
      } while (value >= limit);
      const j = value % (i + 1);
      [chars[i], chars[j]] = [chars[j], chars[i]];
    }
    return chars.join('');
  }
  const api = Object.freeze({generatePassword, hexToBytes, bytesToHex, GROUPS, VERSION});
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  if (root) root.AegisEngine = api;
})(typeof window !== 'undefined' ? window : null);
