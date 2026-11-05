/* AEGIS Web Edition interface. No analytics, networking or persistent storage. */
(function () {
  'use strict';
  const $ = id => document.getElementById(id);
  const engine = window.AegisEngine;
  const el = {
    account:$('account'),phrase:$('phrase'),length:$('length'),version:$('version'),
    output:$('output'),status:$('status'),generate:$('generate'),copy:$('copy'),
    save:$('save'),secret:$('secret'),reveal:$('reveal'),slash:$('slash')
  };
  let last = '';
  let privateKey = null;
  let busy = false;
  function say(message, error = false) {
    el.status.textContent = message;
    el.status.classList.toggle('error', error);
  }
  function invalidate() {
    last = '';
    el.output.replaceChildren();
    const span = document.createElement('span');
    span.className='placeholder';
    span.textContent='Your password will appear here';
    el.output.append(span);
    el.copy.disabled = true;
    el.save.disabled = true;
  }
  function freshKey() {
    if (!globalThis.crypto || !crypto.getRandomValues)
      throw new Error('This browser cannot create a secure session key.');
    const bytes = new Uint8Array(32);
    crypto.getRandomValues(bytes);
    privateKey = bytes;
    el.secret.value = engine.bytesToHex(bytes);
    invalidate();
    say('A new session key is ready. Save it privately if you need to recreate passwords.');
  }
  function readNumber(field, min, max, title) {
    const text = field.value.trim();
    if (!/^\d+$/.test(text)) throw new Error(`${title} must be a whole number.`);
    const v = Number(text);
    if (!Number.isSafeInteger(v) || v < min || v > max)
      throw new Error(`${title} must be between ${min} and ${max}.`);
    return v;
  }
  function changeNumber(field, delta, min, max) {
    const original = Number(field.value);
    const start = Number.isFinite(original) ? original : min;
    field.value = String(Math.min(max, Math.max(min, start + delta)));
    invalidate();
  }
  $('less-length').addEventListener('click', () => changeNumber(el.length,-1,12,128));
  $('more-length').addEventListener('click', () => changeNumber(el.length,1,12,128));
  $('less-version').addEventListener('click', () => changeNumber(el.version,-1,1,999999));
  $('more-version').addEventListener('click', () => changeNumber(el.version,1,1,999999));
  $('rotate').addEventListener('click', () => {
    changeNumber(el.version,1,1,999999);
    say('Version changed. Update the password on the website after generating it.');
  });
  for (const field of [el.account,el.phrase,el.length,el.version]) field.addEventListener('input', invalidate);
  $('phrase-help').addEventListener('click', () => toggleHelp('phrase-help','phrase-detail'));
  $('version-help').addEventListener('click', () => toggleHelp('version-help','version-detail'));
  function toggleHelp(buttonId, detailId) {
    const body = $(detailId), button = $(buttonId);
    body.hidden = !body.hidden;
    button.setAttribute('aria-expanded',String(!body.hidden));
  }
  el.reveal.addEventListener('click', () => {
    const show = el.phrase.type === 'password';
    el.phrase.type = show ? 'text' : 'password';
    el.slash.hidden = !show;
    el.reveal.setAttribute('aria-pressed', String(show));
    el.reveal.setAttribute('aria-label', show ? 'Hide memorable phrase' : 'Show memorable phrase');
    el.phrase.focus();
  });
  $('show-key').addEventListener('click', () => {
    const show = el.secret.type === 'password';
    el.secret.type = show ? 'text' : 'password';
    $('show-key').textContent = show ? 'Hide key' : 'Show key';
  });
  $('new-key').addEventListener('click', () => {
    if (!window.confirm('Create a new key? Existing passwords will change unless you have saved your old key.')) return;
    try {freshKey();} catch (err) {say(err.message, true);}
  });
  $('apply-key').addEventListener('click', () => {
    try {
      const bytes = engine.hexToBytes(el.secret.value.trim());
      if (bytes.length < 32) throw new Error('Enter at least 64 hexadecimal characters.');
      privateKey = bytes;
      el.secret.value = engine.bytesToHex(bytes);
      invalidate();
      say('Session key updated. Passwords will now use this key.');
    } catch(err) {say(err.message,true);}
  });
  // Editing the key does not silently modify the key in use. Apply it explicitly.
  el.secret.addEventListener('input', () => say('Select Use entered key to apply your key.'));
  $('sample').addEventListener('click', () => {
    el.account.value = 'example.com';
    el.phrase.value = 'Silver kites drift above the orchard';
    el.phrase.type = 'password';
    el.reveal.setAttribute('aria-pressed','false');
    el.reveal.setAttribute('aria-label','Show memorable phrase');
    el.slash.hidden = true;
    el.length.value = '24';
    el.version.value = '1';
    // Explicit fixed public TEST key: never for real accounts.
    privateKey = Uint8Array.from({length:32}, (_, i) => i);
    el.secret.value = engine.bytesToHex(privateKey);
    invalidate();
    say('Example loaded with a public test key. Do not use this example for a real account.');
  });
  el.generate.addEventListener('click', async () => {
    if (busy) return;
    try {
      if (!privateKey) throw new Error('Create or enter a session key first.');
      const account = el.account.value, memorable = el.phrase.value;
      const length = readNumber(el.length,12,128,'Password length');
      const version = readNumber(el.version,1,999999,'Password version');
      busy = true;
      el.generate.disabled = true;
      el.generate.textContent = 'Generating…';
      say('Generating password locally…');
      // Take a snapshot, discard output if any input changes while generating.
      const key = privateKey;
      const result = await engine.generatePassword(memorable,account,length,key,version);
      if (account !== el.account.value || memorable !== el.phrase.value ||
          String(length) !== el.length.value.trim() || String(version) !== el.version.value.trim() ||
          key !== privateKey) {
        invalidate();say('The inputs changed. Generate again.');return;
      }
      last = result;
      el.output.textContent = last;
      el.copy.disabled = false;
      el.save.disabled = false;
      say('Password ready. Use the same details and session key to recreate it.');
    } catch(err) {invalidate();say(err.message || 'Could not generate the password.',true);}
    finally {busy=false;el.generate.disabled=false;el.generate.textContent='Generate password';}
  });
  async function copyText(text) {
    if (navigator.clipboard && navigator.clipboard.writeText) {
      try {await navigator.clipboard.writeText(text);return true;} catch(_e) {/* fallback */}
    }
    const textarea = document.createElement('textarea');
    textarea.value=text; textarea.setAttribute('readonly','');
    textarea.style.position='fixed';textarea.style.opacity='0';
    document.body.append(textarea); textarea.select();
    let ok = false;
    try {ok=document.execCommand('copy');} catch(_e) {}
    textarea.remove();return ok;
  }
  el.copy.addEventListener('click', async () => {
    if (!last) return;
    const ok = await copyText(last);
    say(ok ? 'Password copied. Clear it from your clipboard after use.' : 'Copy was blocked. Select and copy the password manually.', !ok);
  });
  $('copy-key').addEventListener('click', async () => {
    if (!privateKey) return;
    const ok = await copyText(engine.bytesToHex(privateKey));
    say(ok ? 'Session key copied. Keep it private.' : 'Copy was blocked. Show the key and copy it manually.', !ok);
  });
  el.save.addEventListener('click', () => {
    if (!last) return;
    if (!window.confirm('This saves your password as an unencrypted text file. Continue?')) return;
    const name = el.account.value.trim().toLowerCase().replace(/[^a-z0-9.-]/g,'_').slice(0,70) || 'account';
    const blob = new Blob([`AEGIS password for ${el.account.value.trim()}\n${last}\n`],{type:'text/plain;charset=utf-8'});
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement('a');
    anchor.href=url;anchor.download=`AEGIS-${name}.txt`;
    document.body.append(anchor);anchor.click();anchor.remove();
    setTimeout(() => URL.revokeObjectURL(url),1000);
    say('Text file saved. It is not encrypted.');
  });
  window.addEventListener('pagehide', () => {invalidate();el.phrase.value='';});
  try {freshKey();} catch(err) {say(err.message,true);}
})();
