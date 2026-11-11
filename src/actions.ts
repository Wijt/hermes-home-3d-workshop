/**
 * Printer actions run the plugin's own slash command as the local user, never an HTTP route: the
 * command goes through the plugin's owner check like any typed `/home3d ...`, so the screen can do
 * nothing a person at the keyboard could not.
 *
 * - A chat is focused: `slash.exec` in it, and the command's reply is the result.
 * - No chat: seat `/home3d ...` in the message box for the person to send (they see it and press Enter).
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

/** A reply reads as a refusal when it starts with the plugin's "Not done" / "Refused" wording. */
export function replyLooksRefused(text: string): boolean {
  return /^\s*(?:\S+\s+)?(not done|refused|cannot|can't|error|failed|no such|unknown)/i.test(text)
}

const errText = (e: unknown) => (e instanceof Error ? e.message : String(e ?? 'unknown error'))

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
      const r = await host.request<{ output?: string; warning?: string } | null>('slash.exec', { session_id: sid, command: c })
      const text = [r?.output, r?.warning].filter(s => typeof s === 'string' && s.trim()).join('\n').trim()
      const shown = text || 'Done. The command sent no reply.'
      return { kind: 'ran', ok: !replyLooksRefused(shown), text: shown }
    } catch (e) {
      return { kind: 'failed', ok: false, text: `The command did not run: ${errText(e)}` }
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
