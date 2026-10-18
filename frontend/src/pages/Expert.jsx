import { useEffect, useState, useRef } from 'react'
import {
  Brain,
  Loader2,
  Send,
  Mic,
  Volume2,
  Settings,
  History,
  Sparkles,
  Copy,
  AlertTriangle,
  CheckCircle2,
} from 'lucide-react'
import { API_BASE } from '../App'
import { useToast } from '../components/Toast'

const EXAMPLE_QUESTIONS = [
  "Why is my dog licking his paws?",
  "Is my cat's meow normal?",
  "What does excessive barking mean?",
  "Why is my pet not eating?",
  "How often should I bathe my dog?",
  "My cat is hiding, is that normal?",
]

const initialMessage = {
  id: 0,
  role: 'assistant',
  content:
    "Hello! I'm your pet care expert. I can help with feeding advice, vaccination schedules, behavior questions, and general pet health guidance. What would you like to know about your pet?",
  created_at: new Date().toISOString(),
}

export default function Expert() {
  const toast = useToast()
  const [messages, setMessages] = useState([initialMessage])
  const [input, setInput] = useState('')
  const [isStreaming, setIsStreaming] = useState(false)
  const [streamingContent, setStreamingContent] = useState('')
  const [selectedExample, setSelectedExample] = useState(null)
  const messagesEndRef = useRef(null)

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, streamingContent])

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  const handleExampleClick = (question) => {
    setInput(question)
    setSelectedExample(question)
  }

  const handleInputChange = (e) => {
    setInput(e.target.value)
    setSelectedExample(null)
  }

  const handleSend = async (e) => {
    e.preventDefault()
    const text = input.trim()
    if (!text || isStreaming) return

    const userMessage = {
      id: Date.now(),
      role: 'user',
      content: text,
      created_at: new Date().toISOString(),
    }

    setMessages((prev) => [...prev, userMessage])
    setInput('')
    setIsStreaming(true)
    setStreamingContent('')

    try {
      const response = await fetch(`${API_BASE}/api/petcare/expert/chat/stream`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          question: text,
          pet_id: null,
          conversation_id: null,
        }),
      })

      if (!response.ok) throw new Error(`Request failed: ${response.status}`)

      const reader = response.body?.getReader()
      if (!reader) throw new Error('No response body')

      const decoder = new TextDecoder()

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        const chunk = decoder.decode(value, { stream: true })
        const lines = chunk.split('\n')

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const data = JSON.parse(line.slice(6))
              if (data.type === 'token') {
                setStreamingContent((prev) => prev + data.content)
              } else if (data.type === 'done') {
                setIsStreaming(false)
                setMessages((prev) => [
                  ...prev.filter((m) => m.role !== 'assistant' || m.id !== -1),
                  {
                    id: -1,
                    role: 'assistant',
                    content: streamingContent + data.content,
                    triage: data.triage,
                    topics: data.topics,
                    disclaimer: data.disclaimer,
                    created_at: new Date().toISOString(),
                  },
                ])
                setStreamingContent('')
              }
            } catch {
              // Ignore parse errors
            }
          }
        }
      }
    } catch (err) {
      setIsStreaming(false)
      setStreamingContent('')
      toast.error('Expert chat failed', err.message)
      setMessages((prev) => [
        ...prev.filter((m) => m.role !== 'assistant' || m.id !== -1),
        {
          id: -1,
          role: 'assistant',
          content: "I'm sorry, I couldn't process your question right now. Please try again later.",
        },
      ])
    }
  }

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey && !isStreaming) {
      e.preventDefault()
      handleSend(e)
    }
  }

  const renderMessage = (message) => {
    const isUser = message.role === 'user'
    const isStreaming = message.id === -1 && message.role === 'assistant'

    return (
      <div
        key={message.id}
        className={`flex gap-3 mb-4 ${isUser ? 'flex-row-reverse' : ''}`}
      >
        <div
          className={`w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold ${
            isUser ? 'bg-primary text-white' : 'bg-white/10 text-primary'
          }`}
        >
          {isUser ? 'U' : '🐾'}
        </div>
        <div
          className={`max-w-[80%] p-4 rounded-2xl ${
            isUser
              ? 'bg-primary text-white ml-auto'
              : 'bg-white/5 text-white'
          }`}
        >
          <div className="whitespace-pre-wrap text-sm leading-relaxed">
            {message.role === 'assistant' && message.content ? (
              <>
                {message.content}
                {message.disclaimer && (
                  <div className="mt-3 pt-3 border-t border-white/5 text-xs text-muted italic">
                    {message.disclaimer}
                  </div>
                )}
                {message.topics && message.topics.length > 0 && (
                  <div className="mt-2 flex flex-wrap gap-1">
                    {message.topics.map((topic) => (
                      <span
                        key={topic}
                        className="px-2 py-1 rounded bg-white/10 text-xs text-cyan-300 border border-cyan-500/20"
                      >
                        #{topic}
                      </span>
                    ))}
                  </div>
                )}
                {message.triage && message.triage.level !== 'routine' && (
                  <div className="mt-2 flex items-center gap-1">
                    <AlertTriangle className="w-3 h-3 text-amber-400" />
                    <span className="text-xs text-amber-300 font-medium">
                      {message.triage.level.toUpperCase()} triage
                    </span>
                  </div>
                )}
              </>
            ) : (
              message.content
            )}
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="glass-panel-solid rounded-2xl p-6 mb-6">
        <div className="flex items-center gap-3 mb-4">
          <div className="w-10 h-10 rounded-xl bg-primary/20 flex items-center justify-center">
            <Brain className="w-6 h-6 text-primary" />
          </div>
          <div>
            <h1 className="font-display text-2xl font-bold text-white">Pet Care Expert</h1>
            <p className="text-xs text-text-secondary">
              AI-powered guidance for feeding, health, behavior & more
            </p>
          </div>
        </div>

        {/* Example Questions */}
        <div className="flex flex-wrap gap-2">
          {EXAMPLE_QUESTIONS.map((q) => (
            <button
              key={q}
              onClick={() => handleExampleClick(q)}
              className={`px-3 py-1.5 rounded-full text-xs font-medium transition-all ${
                selectedExample === q
                  ? 'bg-primary text-white'
                  : 'bg-white/5 text-text-secondary hover:bg-white/10 hover:text-white'
              }`}
            >
              {q}
            </button>
          ))}
        </div>
      </div>

      {/* Chat Area */}
      <div className="flex-1 overflow-y-auto p-6">
        <div className="flex flex-col gap-4" ref={messagesEndRef}>
          {messages.map((msg) => (
            <div key={msg.id} className="flex gap-3">
              {msg.role === 'user' ? (
                <></>
              ) : (
                <div className="w-8 h-8 rounded-full bg-white/10 flex items-center justify-center text-primary text-xs font-bold">
                  🐾
                </div>
              )}
              <div
                className={`max-w-[80%] p-4 rounded-2xl ${
                  msg.role === 'user'
                    ? 'bg-primary text-white ml-auto'
                    : 'bg-white/5 text-white'
                }`}
              >
                <div className="whitespace-pre-wrap text-sm leading-relaxed">
                  {msg.content}
                  {msg.role === 'assistant' && msg.disclaimer && (
                    <div className="mt-3 pt-3 border-t border-white/5 text-xs text-muted italic">
                      {msg.disclaimer}
                    </div>
                  )}
                  {msg.role === 'assistant' && msg.topics && msg.topics.length > 0 && (
                    <div className="mt-2 flex flex-wrap gap-1">
                      {msg.topics.map((topic) => (
                        <span
                          key={topic}
                          className="px-2 py-1 rounded bg-white/10 text-xs text-cyan-300 border border-cyan-500/20"
                        >
                          #{topic}
                        </span>
                      ))}
                    </div>
                  )}
                  {msg.role === 'assistant' && msg.triage && msg.triage.level !== 'routine' && (
                    <div className="mt-2 flex items-center gap-1">
                      <AlertTriangle className="w-3 h-3 text-amber-400" />
                      <span className="text-xs text-amber-300 font-medium">
                        {message.triage.level.toUpperCase()} triage
                      </span>
                    </div>
                  )}
                </div>
              </div>
              {msg.role === 'user' ? (
                <div className="w-8 h-8 rounded-full bg-primary flex items-center justify-center text-white text-xs font-bold">
                  U
                </div>
              ) : (
                <></>
              )}
            </div>
          ))}
          {isStreaming && (
            <div className="flex gap-3">
              <div className="w-8 h-8 rounded-full bg-white/10 flex items-center justify-center text-primary text-xs font-bold">
                🐾
              </div>
              <div className="max-w-[80%] bg-white/5 p-4 rounded-2xl text-white animate-pulse">
                <div className="whitespace-pre-wrap text-sm leading-relaxed">
                  {streamingContent}
                  <span className="text-primary animate-pulse">▋</span>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Input Area */}
      <div className="glass-panel-solid p-4 border-t border-white/10">
        <form onSubmit={handleSend} className="flex gap-2">
          <div className="flex-1 relative">
            <input
              type="text"
              value={input}
              onChange={handleInputChange}
              onKeyDown={handleKeyDown}
              disabled={isStreaming}
              placeholder={isStreaming ? 'Assistant is typing...' : "Ask about your pet's health, behavior, or care..."}
              className="w-full rounded-xl px-4 py-3 bg-white/5 border border-white/10 text-white placeholder:text-muted focus:border-primary focus:outline-none transition-colors"
            />
            {!input && !isStreaming && (
              <div className="absolute right-3 top-1/2 -mt-2 text-xs text-muted">
                Press Enter to send
              </div>
            )}
          </div>
          <button
            type="submit"
            disabled={!input.trim() || isStreaming}
            className={`rounded-lg px-6 py-3 text-sm font-medium transition-all ${
              !input.trim() || isStreaming
                ? 'bg-white/10 text-text-muted cursor-not-allowed'
                : 'bg-primary text-white hover:bg-primary/90 hover:shadow-[0_0_20px_rgba(16,185,129,0.4)]'
            }`}
          >
            {isStreaming ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin mr-2" />
                Typing...
              </>
            ) : (
              <>
                <Send className="w-4 h-4 mr-2" />
                Send
              </>
            )}
          </button>
        </form>
        <p className="mt-2 text-xs text-text-muted">
          ⚠️ This is general pet-care education, not a diagnosis. Always confirm with your veterinarian.
        </p>
      </div>
    </div>
  )
}
