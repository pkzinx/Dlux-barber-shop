import { useEffect, useState } from 'react'
import Head from 'next/head'
import { registerAppointmentPush, listenForegroundMessages } from '@/utils/push'

export default function PushTestPage() {
  const [appointmentId, setAppointmentId] = useState('')
  const [log, setLog] = useState<string[]>([])
  const [sending, setSending] = useState(false)

  useEffect(() => {
    listenForegroundMessages((payload) => {
      setLog((l) => [
        `Mensagem recebida: ${payload?.notification?.title || ''} - ${payload?.notification?.body || ''}`,
        ...l,
      ])
    })
  }, [])

  async function handleRegister() {
    if (!appointmentId) {
      alert('Informe o ID do agendamento')
      return
    }
    const ok = await registerAppointmentPush(appointmentId)
    setLog((l) => [ok ? `Token registrado e associado ao agendamento ${appointmentId}.` : 'Falha ao registrar token.', ...l])
  }

  async function handleSendTest() {
    if (!appointmentId) {
      alert('Informe o ID do agendamento')
      return
    }
    setSending(true)
    try {
      const resp = await fetch(`/api/appointments/${appointmentId}/notify_test/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ appointmentId, title: 'Dlux Barbearia', body: 'Teste de notificação' }),
      })
      const json = await resp.json().catch(() => ({}))
      const statusLine = `HTTP ${resp.status}${resp.statusText ? ' ' + resp.statusText : ''}`
      if (resp.ok) {
        setLog((l) => [`Envio OK (${statusLine}): ${JSON.stringify(json)}`, ...l])
      } else {
        const detail = (json && (json.detail || json.error)) || 'Falha no envio'
        setLog((l) => [`Envio ERRO (${statusLine}): ${detail}`, ...l])
      }
    } catch (e: any) {
      setLog((l) => [`Erro: ${e?.message || e}`, ...l])
    } finally {
      setSending(false)
    }
  }

  return (
    <div style={{ padding: 24, fontFamily: 'sans-serif' }}>
      <Head>
        <title>Teste de Push - Dlux Barbearia</title>
      </Head>
      <h1>Teste de Notificação Push</h1>
      <p>Use esta página para registrar seu dispositivo e enviar uma notificação de teste.</p>
      <label style={{ display: 'block', marginBottom: 8 }}>
        ID do agendamento
        <input
          value={appointmentId}
          onChange={(e) => setAppointmentId(e.target.value)}
          placeholder="Ex.: 1"
          style={{ marginLeft: 12, padding: 6 }}
        />
      </label>
      <div style={{ display: 'flex', gap: 12, marginBottom: 16 }}>
        <button onClick={handleRegister}>Registrar Token & Assinar</button>
        <button onClick={handleSendTest} disabled={sending}>Enviar Push de Teste</button>
      </div>
      <div>
        <h3>Logs</h3>
        <ul>
          {log.map((l, idx) => (
            <li key={idx}>{l}</li>
          ))}
        </ul>
      </div>
    </div>
  )
}