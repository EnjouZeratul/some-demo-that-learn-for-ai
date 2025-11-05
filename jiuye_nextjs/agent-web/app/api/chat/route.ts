export async function POST(request: Request) {
  const { message } = await request.json()
  
  try {
    const response = await fetch('http://127.0.0.1:8000/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query: message })
    })
    
    if (!response.ok) {
      const error = await response.text()
      console.error('Python API error:', error)
      throw new Error(error)
    }
    
    const data = await response.json()
    
    return Response.json({ 
      reply: data.response,
      thinking: data.thinking_process,
      cost: data.cost
    })
  } catch (error) {
    console.error('Chat API error:', error)
    return Response.json({ 
      reply: `错误: ${error instanceof Error ? error.message : '未知错误'}` 
    }, { status: 500 })
  }
}
