"use client"
import { useState, useEffect } from 'react'

interface Message {
  role: 'user' | 'assistant'
  content: string
  thinking?: string
  cost?: {
    input_tokens: number
    output_tokens: number
    total_cost: string
  }
  timestamp?: string
}

export default function Home() {
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [streamingMessage, setStreamingMessage] = useState('')
  const [currentTool, setCurrentTool] = useState('')

  // 从localStorage加载历史
  useEffect(() => {
    const saved = localStorage.getItem('chat-history')
    if (saved) {
      try {
        setMessages(JSON.parse(saved))
      } catch (e) {
        console.error('Failed to load chat history:', e)
      }
    }
  }, [])

  // 保存到localStorage
  useEffect(() => {
    if (messages.length > 0) {
      localStorage.setItem('chat-history', JSON.stringify(messages))
    }
  }, [messages])

  // 打字机效果
  const typeWriter = async (text: string) => {
    if (text.includes('Action:') || text.includes('使用') || text.includes('调用')) {
      const toolMatch = text.match(/Action: (\w+)/)
      if (toolMatch) {
        setCurrentTool(toolMatch[1])
        await new Promise(resolve => setTimeout(resolve, 1000))
        setCurrentTool('')
      }
    }

    for (let i = 0; i <= text.length; i++) {
      setStreamingMessage(text.slice(0, i))
      await new Promise(resolve => setTimeout(resolve, 20))
    }
  }

  const sendMessage = async () => {
    if (!input.trim() || loading) return

    const userMessage: Message = { role: 'user', content: input }
    setMessages(prev => [...prev, userMessage])
    setInput('')
    setLoading(true)
    setStreamingMessage('')

    try {
      const res = await fetch('http://localhost:8000/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: input })  // 修正字段名
      })
      
      const data = await res.json()
      
      // 流式显示
      await typeWriter(data.response)  // 修正字段名
      
      const aiMessage: Message = {
        role: 'assistant',
        content: data.response,
        thinking: data.thinking_process,  // 修正字段名
        cost: data.cost,
        timestamp: data.timestamp
      }
      
      setMessages(prev => [...prev, aiMessage])
      setStreamingMessage('')
    } catch (error) {
      setMessages(prev => [...prev, { 
        role: 'assistant', 
        content: '连接失败，请检查API服务器是否在运行' 
      }])
    } finally {
      setLoading(false)
    }
  }

  const clearChat = () => {
    setMessages([])
    localStorage.removeItem('chat-history')
    fetch('http://localhost:8000/clear', { method: 'POST' })
  }

const downloadLogs = async (format: 'json' | 'markdown' = 'json') => {
  try {
    const response = await fetch(`http://localhost:8000/download-logs?format=${format}`)
    const blob = await response.blob()
    const url = window.URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `agent_log_${new Date().toISOString().slice(0,10)}.${format === 'json' ? 'json' : 'md'}`
    a.click()
    window.URL.revokeObjectURL(url)
  } catch (error) {
    console.error('下载失败:', error)
  }
}


  return (
    <div className="max-w-4xl mx-auto p-4">
      <h1 className="text-3xl font-bold mb-6">AI Agent 演示平台</h1>
      
      {/* 功能按钮区 */}
      <div className="flex gap-2 mb-4">
        <button 
          onClick={clearChat}
          className="px-4 py-2 bg-gray-500 text-white rounded hover:bg-gray-600"
        >
          清除对话
        </button>
        <button 
          onClick={() => downloadLogs('json')}
          className="px-4 py-2 bg-green-500 text-white rounded hover:bg-green-600"
        >
          下载日志(JSON)
        </button>
        <button 
          onClick={() => downloadLogs('markdown')}
          className="px-4 py-2 bg-green-500 text-white rounded hover:bg-green-600"
        >
          下载日志(MD)
        </button>
      </div>
      
      <div className="border rounded-lg p-4 h-[500px] overflow-y-auto mb-4 bg-gray-50">
        {messages.map((msg, i) => (
          <div key={i} className={`mb-4 ${msg.role === 'user' ? 'text-right' : ''}`}>
            <div className={`inline-block max-w-[80%] p-3 rounded-lg ${
              msg.role === 'user' ? 'bg-blue-500 text-white' : 'bg-white border'
            }`}>
              <p className="whitespace-pre-wrap">{msg.content}</p>
              {msg.cost && (
                <div className="text-xs mt-2 opacity-70">
                  成本: {msg.cost.total_cost} | Tokens: {msg.cost.input_tokens + msg.cost.output_tokens}
                </div>
              )}
              {msg.timestamp && (
                <div className="text-xs mt-1 opacity-50">
                  {msg.timestamp}
                </div>
              )}
            </div>
            {msg.thinking && (
              <details className="mt-2 text-sm text-gray-600">
                <summary className="cursor-pointer hover:text-gray-800">查看思考过程</summary>
                <pre className="mt-2 p-2 bg-gray-100 rounded text-xs overflow-x-auto whitespace-pre-wrap">
                  {msg.thinking}
                </pre>
              </details>
            )}
          </div>
        ))}
        
        {loading && streamingMessage && (
          <div className="mb-4">
            <div className="inline-block max-w-[80%] p-3 rounded-lg bg-white border">
              <p>{streamingMessage}▊</p>
            </div>
          </div>
        )}
        
        {currentTool && (
          <div className="text-center text-sm text-blue-600 animate-pulse">
            🔧 正在使用 {currentTool} 工具...
          </div>
        )}
        
        {loading && !streamingMessage && (
          <div className="text-center text-gray-500 animate-pulse">Agent思考中...</div>
        )}
      </div>
      
      <div className="flex gap-2">
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyPress={(e) => e.key === 'Enter' && !loading && sendMessage()}
          disabled={loading}
          className="flex-1 p-3 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:bg-gray-100"
          placeholder="输入你的问题..."
        />
        <button 
          onClick={sendMessage}
          disabled={loading}
          className="px-6 py-3 bg-blue-500 text-white rounded-lg hover:bg-blue-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          {loading ? '处理中...' : '发送'}
        </button>
      </div>
      
      {/* 状态栏 */}
      <div className="mt-4 text-sm text-gray-500 flex justify-between">
        <span>对话数: {messages.length}</span>
        <span>API状态: 
          <span className="inline-block w-2 h-2 bg-green-500 rounded-full ml-1"></span>
        </span>
      </div>
    </div>
  )
}
