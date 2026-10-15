import { useEffect, useState, useRef } from 'react'
import {
  Brain,
  Loader2,
  Plus,
  Send,
  PawPrint,
  AlertTriangle,
  CheckCircle2,
  Clock,
  X,
} from 'lucide-react'
import { API_BASE } from '../App'
import { useToast } from '../components/Toast'

const inputClass =
  'w-full rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-sm text-white placeholder:text-text-secondary focus:border-primary focus:outline-none'

const TRIAGE_COLORS = {
  emergency: 'bg-red-500/10 text-red-400 border border-red-500/30',
  urgent: 'bg-amber-500/10 text-amber-400 border border-amber-500/30',
  watch: 'bg-blue-500/10 text-blue-400 border border-blue-500/30',
  routine: 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/30',
}

const QUICK_QUESTIONS = [
  'My dog is vomiting, what should I do?',
  'How much should I feed my cat daily?',
  'When is my dog’s next vaccination due?',
  'My cat is hiding and not eating, is this normal?',
  'What are common toxic foods for pets?',
  'How often should I walk my dog?',
]

export default function Expert() {
  const toast = useToast()
  const [pets, setPets] = useState([])
  const [selectedPetId, setSelectedPetId] = useState('')
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [streaming, setStreaming] = useState(false)
  const [triage, setTriage] = useState(null)
  const eventSourceRef = useRef(null)

  // Load pets
  useEffect(() => {
    let cancelled = false
    async function loadPets() {
      try {
        const res = await fetch(`${API_BASE}/api/petcare/pets`)
        if (!res.ok) throw new Error(`Request failed with status ${res.status}`)
        const data = await res.json()
        if (!cancelled) {
          setPets(data)
          if (data.length > 0 && !selectedPetId) setSelectedPetId(String(data[0].id))
        }
      } catch (err) {
        if (!cancelled) toast.error('Failed to load pets', err.message)
      }
    }
    loadPets()
    return () => { cancelled = true }
  }, [])

  const petName = (id) => {
    const pet = pets.find((p) => String(p.id) === String(id))
    return pet ? pet.name : 'Pet'
  }

  const petSpecies = (id) => {
    const pet = pets.find((p) => String(p.id) === String(id))
    return pet ? pet.species : ''
  }

  const sendMessage = async (e) => {
    e.preventDefault()
    if (!input.trim() || !selectedPetId) return
    if (loading || streaming) return

    const question = input.trim()
    setInput('')
    setLoading(true)

    // Add user message
    const userMsg = { id: Date.now(), role: 'user', content: question }
    setMessages(prev => [...prev, userMsg])

    // Reset streaming state
    setStreaming(false)
    setTriage(null)

    try {
      // Use the streaming SSE endpoint
      const res = await fetch(`${API_BASE}/api/petcare/expert/chat/stream`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          question,
          pet_id: parseInt(selectedPetId),
          conversation_id: Date.now(),
        }),
      })

      if (!res.ok) throw new Error(`Request failed with status ${res.status}`)

      const reader = res.body.getReader()
      const decoder = new TextDecoder()
      let assistantContent = ''
      let assistantTriage = null
      let assistantTopics = []
      let assistantDisclaimer = ''

      const assistantMsg = {
        id: Date.now() + 1,
        role: 'assistant',
        content: '',
        streaming: true,
      }
      setMessages(prev => [...prev, assistantMsg])
      setStreaming(true)

      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        const chunk = decoder.decode(value, { stream: true })
        const lines = chunk.split('\n').filter(l => l.trim())
        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const parsed = JSON.parse(line.slice(6))
              if (parsed.type === 'token') {
                assistantContent += parsed.content
                setMessages(prev =>
                  prev.map(m =>
                    m.id === assistantMsg.id
                      ? { ...m, content: assistantContent }
                      : m
                  )
                )
              } else if (parsed.type === 'done') {
                assistantTriage = parsed.triage
                assistantTopics = parsed.topics
                assistantDisclaimer = parsed.disclaimer
              }
            } catch {
              // ignore parse errors on partial lines
            }
          }
        }
      }

      setTriage(assistantTriage)
      setMessages(prev =>
        prev.map(m =>
          m.id === assistantMsg.id
            ? {
                ...m,
                streaming: false,
                triage: assistantTriage,
                topics: assistantTopics,
                disclaimer: assistantDisclaimer,
              }
            : m
        )
      )
    } catch (err) {
      toast.error('Expert advice failed', err.message)
      // Remove the incomplete assistant message
      setMessages(prev => prev.filter(m => m.id !== assistantMsg?.id))
    } finally {
      setLoading(false)
      setStreaming(false)
    }
  }

  const stopStreaming = () => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close()
      eventSourceRef.current = null
    }
    setStreaming(false)
    setLoading(false)
  }

  const triageLabel = {
    emergency: 'EMERGENCY',
    urgent: 'URGENT',
    watch: 'WATCH',
    routine: 'ROUTINE',
  }

  const clearChat = () => {
    setMessages([])
    setTriage(null)
    stopStreaming()
  }

  if (!pets.length) {
    return (
      <div className="glass-panel rounded-xl p-8 text-center">
        <Brain className="mx-auto h-12 w-12 text-primary" />
        <h2 className="mt-4 text-xl font-bold gradient-text">Pet Care Expert</h2>
        <p className="mt-2 text-sm text-text-secondary">
          Add a pet on the Pets page to start getting care advice.
        </p>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <header className="glass-panel-solid rounded-xl p-6">
        <div className="flex items-center gap-3">
          <Brain className="h-8 w-8 text-primary" />
          <h1 className="font-display text-3xl font-bold gradient-text">Pet Care Expert</h1>
        </div>
        <p className="mt-2 text-text-secondary">
          AI-powered pet care advice with triage. Select a pet for personalized guidance.
        </p>
      </header>

      {/* Quick questions */}
      <div className="flex flex-wrap gap-2">
        {QUICK_QUESTIONS.map((q, i) => (
          <button
            key={i}
            onClick={() => setInput(q)}
            className="rounded-lg px-3 py-1.5 text-xs bg-white/5 border border-white/10 text-text-secondary hover:bg-primary/20 hover:text-primary transition-colors"
          >
            {q}
          </button>
        ))}
      </div>

      <div className="grid lg:grid-cols-3 gap-6">
        {/* Pet selector + triage */}
        <div className="lg:col-span-3 glass-panel rounded-xl p-5">
          <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4">
            <div>
              <label className="mb-1 block text-sm text-muted">Pet</label>
              <select
                className={inputClass}
                value={selectedPetId}
                onChange={e => setSelectedPetId(e.target.value)}
              >
                {pets.map(pet => (
                  <option key={pet.id} value={pet.id} className="bg-neutral-900">
                    {pet.name} ({pet.species})
                  </option>
                ))}
              </select>
            </div>
            {triage && (
              <div className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-semibold ${TRIAGE_COLORS[triage.level]}`}>
                <span>{triageLabel[triage.level]}</span>
                {triage.matched_symptoms.length > 0 && (
                  <span className="text-text-muted">({triage.matched_symptoms.join(', ')})</span>
                )}
                {triage.prompt_vet && (
                  <span className="text-red-400">See a vet</span>
                )}
              </div>
            )}
          </div>
        </div>

        {/* Chat area */}
        <div className="lg:col-span-3 glass-panel rounded-xl p-5 flex flex-col h-[600px]">
          <div className="flex-1 overflow-y-auto pr-2 space-y-4 mb-4">
            {messages.length === 0 && (
              <div className="flex flex-col items-center justify-center py-20 text-center">
                <Brain className="h-12 w-12 text-text-muted" />
                <p className="mt-3 text-text-sm text-text-secondary">
                  Ask me anything about your pet’s health, feeding, vaccinations, or care.
                </p>
              </div>
            )}
            {messages.map(msg => (
              <div
                key={msg.id}
                className={`flex gap-3 ${
                  msg.role === 'user' ? 'justify-end' : 'justify-start'
                }`}
              >
                <div
                  className={`max-w-[85%] p-3 rounded-2xl ${
                    msg.role === 'user'
                      ? 'bg-primary text-white rounded-tr-none'
                      : 'bg-white/5 text-white rounded-tl-none'
                  }`}
                >
                  <div className="whitespace-pre-wrap">{msg.content}</div>
                  {msg.role === 'assistant' && msg.streaming && (
                    <div className="mt-2 flex items-center gap-1">
                      <Loader2 className="h-3 w-3 animate-spin text-primary" />
                      <span className="text-xs text-text-muted">Typing...</span>
                    </div>
                  )}
                  {msg.role === 'assistant' && !msg.streaming && msg.triage && (
                    <div className="mt-3 pt-2 border-t border-white/10 flex items-center gap-2">
                      <span
                        className={`px-2 py-0.5 rounded text-xs font-semibold ${TRIAGE_COLORS[msg.triage.level]}`}
                      >
                        {triageLabel[msg.triage.level]}
                      </span>
                      {msg.topics.length > 0 && (
                        <span className="text-xs text-text-muted">
                          • {msg.topics.join(', ')}
                        </span>
                      )}
                    </div>
                  )}
                </div>
                {msg.role === 'user' && (
                  <PawPrint className="h-4 w-4 text-text-muted" />
                )}
                {msg.role === 'assistant' && (
                  <Brain className="h-4 w-4 text-primary" />
                )}
              </div>
            ))}
          </div>

          {/* Input form */}
          <form onSubmit={sendMessage} className="flex gap-2 border-t border-white/10 pt-4">
            <input
              className={`${inputClass} flex-1`}
              value={input}
              onChange={e => setInput(e.target.value)}
              placeholder="Ask about your pet’s health, feeding, vaccinations…"
              disabled={loading || streaming || !selectedPetId}
            />
            <button
              type="submit"
              disabled={!input.trim() || loading || streaming || !selectedPetId}
              className="rounded-lg bg-primary px-4 py-2 text-sm font-medium text-white disabled:opacity-50 transition hover:opacity-90"
            >
              {streaming ? (
                <span className="flex items-center gap-2">
                  <Loader2 className="h-4 w-4 animate-spin" />
                  <X onClick={stopStreaming} className="h-4 w-4 cursor-pointer hover:text-red-400" />
                </span>
              ) : (
                <Send className="h-4 w-4" />
              )}
            </button>
          </form>
          {triage && (
            <div className="mt-3 p-3 rounded-lg bg-black/20 text-xs text-text-secondary">
              <p className="mb-1"><strong>Disclaimer:</strong> {messages.find(m => m.role === 'assistant' && !m.streaming)?.disclaimer || ''}</p>
            </div>
          )}
        </div>
      </div>

      {/* Warning disclaimer */}
      <div className="glass-panel rounded-xl p-4 border border-amber-500/30 bg-amber-500/10">
        <AlertTriangle className="h-4 w-4 text-amber-400 mr-2" />
        <span className="text-xs text-amber-300">
          General pet-care education only — not a diagnosis. Always confirm with your veterinarian.
          In an emergency, contact your vet immediately.
        </span>
      </div>
    </div>
  )
}
