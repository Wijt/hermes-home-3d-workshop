// Printer actions run the plugin's slash command as the local user; the one-WebGL-view slot; reading a
// home3d_design tool call for the inline card.
import assert from 'node:assert/strict'
import { test } from 'node:test'

import { cleanCommand, readReply, replyLooksRefused, resetWorkshopSession, runCommand, WORKSHOP_SESSION_TITLE } from '../../src/actions.ts'
import { callFacts, findVersion, isLeadPicture, readDesignCall } from '../../src/design-result.ts'
import { createViewSlot } from '../../src/slot.ts'

function fakeHost({ session = null, reply = { output: 'OK' }, seat = false, fail = null, own = null, execFail = null } = {}) {
  resetWorkshopSession()
  const calls = []
  return {
    calls,
    state: { focusedSessionId: { get: () => session } },
    request: async (method, params) => {
      calls.push(['request', method, params])
      if (fail) throw new Error(fail)
      if (method === 'session.create') {
        if (!own) throw new Error('no model configured')
        return { session_id: own, stored_session_id: own }
      }
      if (execFail) throw new Error(execFail)
      return reply
    },
    composer: {
      insertText: async (sid, text, opts) => {
        calls.push(['insertText', sid, text, opts])
        return seat
      }
    }
  }
}

test('with a focused chat the command runs through slash.exec and its reply is the result', async () => {
  const host = fakeHost({ session: 's1', reply: { output: 'Started "Name tag".', warning: '' } })
  const r = await runCommand(host, '/home3d approve start 12')
  assert.deepEqual(host.calls, [['request', 'slash.exec', { session_id: 's1', command: 'home3d approve start 12' }]])
  assert.deepEqual(r, { kind: 'ran', ok: true, text: 'Started "Name tag".' })
})

test('a refusal from the plugin is shown as not done', async () => {
  const host = fakeHost({ session: 's1', reply: { output: 'Not done: Cannot start: queue item 999 not found.' } })
  const r = await runCommand(host, 'home3d approve start 999')
  assert.equal(r.kind, 'ran')
  assert.equal(r.ok, false)
  assert.equal(replyLooksRefused('⛔ Refused: owner only'), true)
  assert.equal(replyLooksRefused('Started the print.'), false)
})

test('without a chat the command runs in the screen\'s own hidden session, made once', async () => {
  const host = fakeHost({ own: 'w1', reply: { output: 'Started #5 "Key tag".' } })
  const r = await runCommand(host, 'home3d approve start 5')
  assert.deepEqual(r, { kind: 'ran', ok: true, text: 'Started #5 "Key tag".' })
  await runCommand(host, 'home3d pause')
  assert.deepEqual(host.calls, [
    ['request', 'session.create', { title: WORKSHOP_SESSION_TITLE, hidden: true }],
    ['request', 'slash.exec', { session_id: 'w1', command: 'home3d approve start 5' }],
    ['request', 'slash.exec', { session_id: 'w1', command: 'home3d pause' }]
  ])
})

test('a lost hidden session is asked for again on the next press', async () => {
  const host = fakeHost({ own: 'w1', execFail: 'unknown session', seat: true })
  const r = await runCommand(host, 'home3d stop')
  assert.equal(r.kind, 'seated')
  await runCommand(host, 'home3d stop')
  assert.equal(host.calls.filter(c => c[1] === 'session.create').length, 2)
})

test('without a chat or a hidden session the command is seated in the message box for the person to send', async () => {
  const host = fakeHost({ seat: true })
  const r = await runCommand(host, 'home3d stop')
  assert.deepEqual(host.calls, [
    ['request', 'session.create', { title: WORKSHOP_SESSION_TITLE, hidden: true }],
    ['insertText', null, '/home3d stop', { mode: 'prefix' }]
  ])
  assert.equal(r.kind, 'seated')
  assert.match(r.text, /Press Enter/)
})

test('without a chat or a message box, it says which command to send', async () => {
  const host = fakeHost({ seat: false })
  const r = await runCommand(host, 'home3d pause')
  assert.equal(r.kind, 'manual')
  assert.match(r.text, /send \/home3d pause$/)
})

test('a failing gateway call is reported, not thrown', async () => {
  const r = await runCommand(fakeHost({ session: 's1', fail: 'socket closed' }), 'home3d stop')
  assert.equal(r.kind, 'failed')
  assert.match(r.text, /socket closed/)
})

test('only plain home3d commands leave the screen', async () => {
  assert.equal(cleanCommand('  /home3d   collected 4 '), 'home3d collected 4')
  for (const bad of ['rm -rf /', 'home3dx stop', 'home3d stop; ls', 'home3d stop\nhome3d pause', 'home3d $(id)']) {
    assert.throws(() => cleanCommand(bad))
  }
  const host = fakeHost({ session: 's1' })
  const r = await runCommand(host, 'help')
  assert.equal(r.kind, 'failed')
  assert.equal(host.calls.length, 0)
})

test('one live 3D view at a time', () => {
  const slot = createViewSlot()
  const seen = []
  slot.subscribe(h => seen.push(h))
  slot.claim('hero')
  slot.claim('design')
  slot.release('hero') // no longer the holder: nothing changes
  assert.equal(slot.holder(), 'design')
  slot.release('design')
  assert.equal(slot.holder(), null)
  assert.deepEqual(seen, ['hero', 'design', null])
})

const RENDER = {
  ok: true,
  name: 'rail-bracket',
  version: 2,
  size_mm: [40, 30, 35],
  volume_cm3: 9.6,
  est_grams_max: 11.9,
  fits_build_volume: true,
  warnings: ['a', 'b', 'c', 'd'],
  previews: ['/d/rail-bracket_v2_iso.png', '/d/rail-bracket_v2_top.png'],
  media: ['MEDIA:/d/rail-bracket_v2_iso.png', 'MEDIA:/d/rail-bracket_v2_top.png'],
  stl_path: '/d/rail-bracket_v2.stl'
}

test('a home3d_design result is read live or from history (JSON string)', () => {
  for (const result of [RENDER, JSON.stringify(RENDER)]) {
    const c = readDesignCall(result, { action: 'render', name: 'rail bracket' })
    assert.equal(c.slug, 'rail-bracket')
    assert.equal(c.version, 2)
    assert.equal(c.warnings.length, 3)
    assert.deepEqual(callFacts(c), ['40 × 30 × 35 mm', 'about 12 g'])
    assert.equal(isLeadPicture(c, '/d/rail-bracket_v2_iso.png'), true)
    assert.equal(isLeadPicture(c, '/d/rail-bracket_v2_top.png'), false)
    assert.equal(isLeadPicture(c, '/elsewhere.png'), true)
  }
  assert.equal(readDesignCall({ ok: false, code: 'no_openscad' }, {}), null)
  assert.equal(readDesignCall({ ok: true, name: 'x' }, {}), null)
  assert.equal(readDesignCall('not json', {}), null)
})

test('the card finds the version STL in the overview', () => {
  const designs = [{ slug: 'rail-bracket', title: 'Rail bracket', versions: [{ version: 1, stl: 'a.stl', previews: [], facts: {}, note: '' }, { version: 2, stl: 'b.stl', previews: [], facts: {}, note: '' }] }]
  assert.equal(findVersion(designs, 'Rail-Bracket', 2).stl, 'b.stl')
  assert.equal(findVersion(designs, 'rail-bracket', 3), null)
  assert.equal(findVersion(designs, 'other', 1), null)
})

test('the reply marker decides success or refusal and is not shown', async () => {
  const ok = await runCommand(fakeHost({ session: 's1', reply: { output: '⏸️ Paused "Key tag" (Owner (local)). Resume: /home3d approve resume\n[home3d:ok]' } }), 'home3d pause')
  assert.deepEqual(ok, { kind: 'ran', ok: true, text: '⏸️ Paused "Key tag" (Owner (local)). Resume: /home3d approve resume' })
  const no = await runCommand(fakeHost({ session: 's1', reply: { output: 'Started? no: the gate said the plate is unknown.\n[home3d:not_done:gate]' } }), 'home3d approve start 3')
  assert.equal(no.ok, false)
  assert.equal(no.text, 'Started? no: the gate said the plate is unknown.')
  assert.deepEqual(readReply('📦 "a coaster" marked collected (Mum).\n[home3d:ok]'), { ok: true, code: 'ok', text: '📦 "a coaster" marked collected (Mum).', marked: true })
  assert.deepEqual(readReply('Only the owner and the people in the household list can mark a part collected.\n[home3d:not_done:collected_unknown]'),
    { ok: false, code: 'collected_unknown', text: 'Only the owner and the people in the household list can mark a part collected.', marked: true })
  // the marker wins over wording that looks like the other answer
  assert.equal(readReply('Cannot believe it: started.\n[home3d:ok]').ok, true)
  assert.equal(readReply('Nothing is printing, so no command was sent.\n[home3d:not_done:nothing_printing]').code, 'nothing_printing')
  // an older plugin without the marker: the wording decides
  assert.equal(readReply('Nothing is printing, so no command was sent.').ok, false)
  assert.equal(readReply('Started #5 "Key tag".').marked, false)
})
