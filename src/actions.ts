/**
 * Printer actions run the plugin's own slash command as the local user, never an HTTP route: the
 * command goes through the plugin's owner check like any typed `/home3d ...`, so the screen can do
 * nothing a person at the keyboard could not.
 *
 * - A chat is focused: `slash.exec` in it, and the command's reply is the result.
 * - No chat (the usual case on the Workshop page itself): `slash.exec` in the screen's own hidden session
 *   (`session.create` with a fixed title and `hidden: true`; the gateway hands back the same session for the
 *   same title, so it is made once and never shows in the sidebar). Still a local slash command: the
 *   plugin's owner check decides, exactly as for a typed one.
 * - That fails too: seat `/home3d ...` in the message box for the person to send (they press Enter).
 * - No message box answers either: say which command to send.
 */

export interface ActionHost {
  request: <T>(method: string, params?: unknown) => Promise<T>
  state?: { focusedSessionId?: { get: () => string | null } }
  composer?: {
    insertText?: (sessionId: string | null, text: string, opts?: { mode?: 'block' | 'inline' | 'prefix' }) => Promise<boolean>
  }
}

export type ActionOutcome =
  | { kind: 'ran'; ok: boolean; text: string }
  | { kind: 'seated'; ok: true; text: string }
  | { kind: 'manual'; ok: false; text: string }
  | { kind: 'failed'; ok: false; text: string }

/** Only `home3d ...` commands leave this screen. */
export function cleanCommand(command: string): string {
  const trimmed = command.trim()
  if (/[\n\r\t;&|`$<>]/.test(trimmed)) throw new Error(`not a workshop command: ${command}`)
  const c = trimmed.replace(/^\/+/, '').replace(/ +/g, ' ')
  if (!/^home3d( |$)/.test(c)) throw new Error(`not a workshop command: ${command}`)
  return c
}

/**
 * The plugin ends the reply of every action subcommand (approve start|clear|resume, stop, pause, collected)
 * with one line: `[home3d:ok]` or `[home3d:not_done:<code>]` (home3d/commands.py, `result_marker`).
 * `readReply` splits it off; a reply without it (an older plugin) falls back to the wording.
 */
const MARKER = /(?:^|\n)[ \t]*\[home3d:(ok|not_done)(?::([a-z0-9_]+))?\][ \t]*$/

export function readReply(text: string): { ok: boolean; code: string; text: string; marked: boolean } {
  const m = MARKER.exec(text)
  if (!m) return { ok: !replyLooksRefused(text), code: '', text: text.trim(), marked: false }
  const ok = m[1] === 'ok'
  return { ok, code: ok ? 'ok' : m[2] || 'not_done', text: text.slice(0, m.index).trim(), marked: true }
}

/** Fallback for a reply without the marker: it reads as a refusal when it starts with refusal wording. */
export function replyLooksRefused(text: string): boolean {
  return /^\s*(?:\S+\s+)?(not done|refused|cannot|can't|error|failed|no such|unknown|only the owner|nothing is printing|usage)/i.test(text)
}

const errText = (e: unknown) => (e instanceof Error ? e.message : String(e ?? 'unknown error'))

type SlashReply = { output?: string; warning?: string } | null

function ranOutcome(r: SlashReply): ActionOutcome {
  const raw = [r?.output, r?.warning].filter(s => typeof s === 'string' && s.trim()).join('\n').trim()
  if (!raw) return { kind: 'ran', ok: true, text: 'Done. The command sent no reply.' }
  const reply = readReply(raw)
  return { kind: 'ran', ok: reply.ok, text: reply.text || (reply.ok ? 'Done.' : 'Not done.') }
}

/** Title of the screen's own hidden session (the gateway resolves a title to the same session every time). */
export const WORKSHOP_SESSION_TITLE = 'Workshop actions (home-3d-workshop)'
let ownSession: string | null = null

/** The runtime id of the screen's hidden session, made on first use; null when the gateway will not make one. */
export async function workshopSession(host: ActionHost): Promise<string | null> {
  if (ownSession) return ownSession
  try {
    const r = await host.request<{ session_id?: string } | null>('session.create', { title: WORKSHOP_SESSION_TITLE, hidden: true })
    ownSession = typeof r?.session_id === 'string' && r.session_id ? r.session_id : null
  } catch {
    ownSession = null
  }
  return ownSession
}

/** Tests: forget the cached session id. */
export function resetWorkshopSession(): void {
  ownSession = null
}

export async function runCommand(host: ActionHost, command: string): Promise<ActionOutcome> {
  let c: string
  try {
    c = cleanCommand(command)
  } catch (e) {
    return { kind: 'failed', ok: false, text: errText(e) }
  }
  let sid: string | null = null
  try {
    sid = host.state?.focusedSessionId?.get() ?? null
  } catch {
    sid = null
  }
  if (sid) {
    try {
      return ranOutcome(await host.request<SlashReply>('slash.exec', { session_id: sid, command: c }))
    } catch (e) {
      return { kind: 'failed', ok: false, text: `The command did not run: ${errText(e)}` }
    }
  }
  const own = await workshopSession(host)
  if (own) {
    try {
      return ranOutcome(await host.request<SlashReply>('slash.exec', { session_id: own, command: c }))
    } catch (e) {
      ownSession = null // a gateway restart drops the runtime id: the next press asks again
      if (!host.composer?.insertText) return { kind: 'failed', ok: false, text: `The command did not run: ${errText(e)}` }
    }
  }
  try {
    const seated = await host.composer?.insertText?.(null, `/${c}`, { mode: 'prefix' })
    if (seated) {
      return { kind: 'seated', ok: true, text: `No chat is open here, so /${c} is waiting in the message box. Press Enter there to send it.` }
    }
  } catch {
    /* fall through to the manual line */
  }
  return { kind: 'manual', ok: false, text: `No chat is open here. Open a chat with the printer and send /${c}` }
}
