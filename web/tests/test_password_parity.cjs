/* Run: node tests/test_password_parity.cjs */
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const engine = require('../web/engine.js');
const vectors = JSON.parse(fs.readFileSync(path.join(__dirname,'python_vectors.json'),'utf8'));
async function main() {
  for (const v of vectors) {
    const args = [v.memorable, v.account, v.length, engine.hexToBytes(v.secret_hex), v.revision];
    const output = await engine.generatePassword(...args);
    assert.equal(output, v.expected, `Python/JS mismatch: ${v.case}`);
    assert.equal(await engine.generatePassword(...args), output, `${v.case} not deterministic`);
    assert.equal(output.length, v.length);
    for (const group of engine.GROUPS) assert.ok([...output].some(ch => group.includes(ch)), `${v.case} missing class`);
    console.log('PASS', v.case);
  }
  const s = new Uint8Array(32);
  await assert.rejects(engine.generatePassword('phrase','',24,s,1),/account/i);
  await assert.rejects(engine.generatePassword('', 'a',24,s,1),/memorable/i);
  await assert.rejects(engine.generatePassword('phrase','a',10,s,1),/length/i);
  await assert.rejects(engine.generatePassword('phrase','a',24,new Uint8Array(31),1),/secret/i);
  await assert.rejects(engine.generatePassword('phrase','a',24,s,0),/version/i);
  assert.equal(engine.bytesToHex(engine.hexToBytes('aA12ff')),'aa12ff');
  console.log(`Passed ${vectors.length} cross-language parity cases and input validation checks.`);
}
main().catch(e=>{console.error(e);process.exitCode=1});
