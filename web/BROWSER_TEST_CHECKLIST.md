# Browser test checklist

- [ ] Open `AEGIS_Web_Edition.html` by double-clicking it in Edge or Chrome.
- [ ] Confirm the dark theme and layout work at 100% and 125% Windows display scale.
- [ ] Click **Try an example**, then **Generate password**. It should match the first JSON test vector.
- [ ] Show and hide the memorable phrase with the eye.
- [ ] Check the info icons on the phrase and version fields.
- [ ] Test length +/- and version +/-; generation changes with version.
- [ ] Test Copy (permission permitting) and Save .txt (with plaintext warning).
- [ ] Verify that changing any field clears the old generated output.
- [ ] Reload: a new private browser key is created (previous passwords no longer match).
- [ ] Import the public test key `000102...1f` via **Use entered key** and verify the same sample output.
- [ ] Disconnect the internet and verify generation still works.
- [ ] Check keyboard tab order, button focus and screen reader labels.
- [ ] Do not use actual desktop vault keys or real passwords during testing.
