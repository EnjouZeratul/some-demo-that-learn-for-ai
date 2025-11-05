import re
import asyncio
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel
import uvicorn
from agent_demo import agent, cost_tracker, log_handler, TRACK_COSTS
from typing import Optional, List
import json
import os
from datetime import datetime
import tempfile
import io

app = FastAPI(title="AI Agent API", version="1.0.0")

# 配置CORS，让前端能够正常访问
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Next.js默认端口
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 内存中存储对话历史 - 生产环境建议使用Redis或数据库
conversation_history = []

# 用于跟踪每个会话的成本基线
session_baselines = {}
current_session_id = "default"

class ChatRequest(BaseModel):
    query: str
    session_id: Optional[str] = "default"  # 支持多会话

class ChatResponse(BaseModel):
    response: str
    thinking_process: Optional[str] = None
    cost: Optional[dict] = None
    timestamp: str = None
    session_id: str = "default"

class ConversationHistory(BaseModel):
    messages: List[dict]
    total_cost: Optional[dict] = None

def extract_content_from_error(error_msg: str) -> str:
    """
    从LangChain的错误信息中提取实际的AI回复内容。
    有时候AI不按ReAct格式输出，LangChain会报错，但回复内容还是有用的。
    """
    # 尝试各种可能的格式提取内容
    if '`' in error_msg:
        # 匹配反引号包裹的内容
        pattern = r'`([^`]+(?:`[^`]*`[^`]+)*)`'
        matches = re.findall(pattern, error_msg)
        if matches:
            return max(matches, key=len)  # 返回最长的匹配
    
    if '"' in error_msg:
        # 匹配双引号包裹的内容
        pattern = r'"([^"]+)"'
        matches = re.findall(pattern, error_msg)
        if matches:
            return matches[-1]  # 通常最后一个是完整内容
    
    if ':' in error_msg:
        # 提取冒号后的所有内容
        parts = error_msg.split(':', 1)
        if len(parts) > 1:
            return parts[1].strip()
    
    # 实在提取不出来就返回整个错误信息
    return error_msg

def get_session_baseline(session_id: str) -> dict:
    """获取或创建会话的成本基线"""
    if session_id not in session_baselines:
        session_baselines[session_id] = {
            'input': cost_tracker.total_input_tokens,
            'output': cost_tracker.total_output_tokens,
            'cost': cost_tracker.total_cost
        }
    return session_baselines[session_id]

@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    主要的对话接口。处理用户输入，调用Agent，返回回复和成本信息。
    """
    try:
        # 清空上次的思考日志
        log_handler.reset()
        
        # 获取这个会话的基线成本
        session_baseline = get_session_baseline(request.session_id)
        
        # 记录本次调用前的token数（用于计算增量）
        before_tokens = {
            'input': cost_tracker.total_input_tokens,
            'output': cost_tracker.total_output_tokens,
            'cost': cost_tracker.total_cost
        }
        
        result = None
        thinking_log = None
        
        try:
            # 调用Agent处理用户请求
            agent_result = agent.invoke({"input": request.query})
            result = agent_result.get("output", "")
            thinking_log = log_handler.get_full_log()
            
        except Exception as e:
            error_msg = str(e)
            
            # 处理Agent输出格式错误的情况
            if "Could not parse LLM output:" in error_msg:
                # AI直接回答了，没有按照ReAct格式
                content_start = error_msg.find('`')
                content_end = error_msg.rfind('`')
                if content_start != -1 and content_end != -1 and content_start < content_end:
                    result = error_msg[content_start + 1:content_end]
                else:
                    result = extract_content_from_error(error_msg)
                
                thinking_log = log_handler.get_full_log() or "Agent直接给出答案，未使用ReAct思考链"
            else:
                # 其他错误直接抛出
                raise
        
        # 生成时间戳
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # 构建响应数据
        response_data = {
            "response": result or "未能获取有效回复",
            "thinking_process": thinking_log,
            "timestamp": timestamp,
            "session_id": request.session_id
        }
        
        # 计算本次调用的成本（增量计算，避免累加）
        if TRACK_COSTS:
            # 计算相对于会话开始的总成本
            session_cost = {
                "input_tokens": cost_tracker.total_input_tokens - session_baseline['input'],
                "output_tokens": cost_tracker.total_output_tokens - session_baseline['output'],
                "total_cost": f"¥{cost_tracker.total_cost - session_baseline['cost']:.4f}"
            }
            
            # 计算本次调用的增量成本
            this_call_cost = {
                "input_tokens": cost_tracker.total_input_tokens - before_tokens['input'],
                "output_tokens": cost_tracker.total_output_tokens - before_tokens['output'],
                "total_cost": f"¥{cost_tracker.total_cost - before_tokens['cost']:.4f}"
            }
            
            # 只返回本次调用的成本
            response_data["cost"] = this_call_cost
        
        # 保存到对话历史
        conversation_history.append({
            "query": request.query,
            "response": result,
            "thinking_process": thinking_log,
            "cost": response_data.get("cost"),
            "timestamp": timestamp,
            "session_id": request.session_id
        })
        
        return ChatResponse(**response_data)
        
    except Exception as e:
        # 详细的错误处理，方便调试
        import traceback
        error_trace = traceback.format_exc()
        print(f"错误详情: {error_trace}")  # 服务器端日志
        
        raise HTTPException(
            status_code=500, 
            detail=f"服务器处理请求时出错: {str(e)}"
        )

@app.get("/history")
async def get_history(session_id: str = "default"):
    """
    获取指定会话的对话历史，包括总成本统计
    """
    # 过滤出当前会话的历史
    session_messages = [
        msg for msg in conversation_history 
        if msg.get("session_id", "default") == session_id
    ]
    
    # 计算这个会话的总成本
    total_cost = {
        "input_tokens": 0,
        "output_tokens": 0,
        "total_cost": 0.0
    }
    
    for conv in session_messages:
        if conv.get("cost"):
            cost = conv["cost"]
            total_cost["input_tokens"] += cost.get("input_tokens", 0)
            total_cost["output_tokens"] += cost.get("output_tokens", 0)
            # 解析成本字符串并累加
            cost_str = cost.get("total_cost", "¥0.0000")
            cost_value = float(cost_str.replace("¥", ""))
            total_cost["total_cost"] += cost_value
    
    total_cost["total_cost"] = f"¥{total_cost['total_cost']:.4f}"
    
    return {
        "messages": session_messages,
        "total_cost": total_cost if session_messages else None,
        "message_count": len(session_messages)
    }

@app.post("/clear")
async def clear_history(session_id: Optional[str] = None):
    """
    清除对话历史。如果提供session_id只清除特定会话，否则清除所有
    """
    global conversation_history
    
    if session_id:
        # 只清除特定会话
        conversation_history = [
            msg for msg in conversation_history 
            if msg.get("session_id", "default") != session_id
        ]
        # 重置该会话的成本基线
        if session_id in session_baselines:
            session_baselines[session_id] = {
                'input': cost_tracker.total_input_tokens,
                'output': cost_tracker.total_output_tokens,
                'cost': cost_tracker.total_cost
            }
        return {"message": f"会话 {session_id} 的历史已清除"}
    else:
        # 清除所有历史
        conversation_history = []
        session_baselines.clear()
        return {"message": "所有对话历史已清除"}

@app.get("/download-logs")
async def download_logs(format: str = "json"):
    """
    下载对话日志，支持JSON和Markdown格式
    """
    timestamp_str = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    if format.lower() == "markdown":
        # 生成Markdown格式的日志
        md_content = f"# AI Agent 对话记录\n\n"
        md_content += f"导出时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        
        for i, conv in enumerate(conversation_history, 1):
            md_content += f"## 对话 {i}\n"
            md_content += f"**时间**: {conv.get('timestamp', '未知')}\n\n"
            md_content += f"**用户**: {conv.get('query', '')}\n\n"
            md_content += f"**AI**: {conv.get('response', '')}\n\n"
            
            if conv.get('cost'):
                cost = conv['cost']
                md_content += f"**成本**: {cost.get('total_cost', '¥0')} "
                md_content += f"(输入: {cost.get('input_tokens', 0)} tokens, "
                md_content += f"输出: {cost.get('output_tokens', 0)} tokens)\n\n"
            
            if conv.get('thinking_process'):
                md_content += "<details>\n<summary>思考过程</summary>\n\n```\n"
                md_content += conv['thinking_process']
                md_content += "\n```\n</details>\n\n"
            
            md_content += "---\n\n"
        
        # 返回Markdown文件
        return StreamingResponse(
            io.StringIO(md_content),
            media_type="text/markdown",
            headers={
                "Content-Disposition": f"attachment; filename=agent_log_{timestamp_str}.md"
            }
        )
    
    else:
        # JSON格式（默认）
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False, encoding='utf-8') as tmp:
            log_data = {
                "export_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "total_conversations": len(conversation_history),
                "conversations": conversation_history,
                "sessions": list(session_baselines.keys())
            }
            
            # 添加总成本统计
            total_cost = {"input_tokens": 0, "output_tokens": 0, "total_cost": 0.0}
            for conv in conversation_history:
                if conv.get("cost"):
                    cost = conv["cost"]
                    total_cost["input_tokens"] += cost.get("input_tokens", 0)
                    total_cost["output_tokens"] += cost.get("output_tokens", 0)
                    cost_str = cost.get("total_cost", "¥0.0000")
                    cost_value = float(cost_str.replace("¥", ""))
                    total_cost["total_cost"] += cost_value
            
            total_cost["total_cost"] = f"¥{total_cost['total_cost']:.4f}"
            log_data["total_cost"] = total_cost
            
            json.dump(log_data, tmp, ensure_ascii=False, indent=2)
            temp_name = tmp.name
        
        # 60秒后自动清理临时文件
        async def cleanup():
            await asyncio.sleep(60)
            try:
                os.unlink(temp_name)
            except:
                pass
        
        asyncio.create_task(cleanup())
        
        return FileResponse(
            temp_name,
            filename=f"agent_log_{timestamp_str}.json",
            media_type='application/json'
        )

@app.post("/reset-session")
async def reset_session(session_id: str = "default"):
    """
    重置特定会话的成本基线，用于开始新的计费周期
    """
    session_baselines[session_id] = {
        'input': cost_tracker.total_input_tokens,
        'output': cost_tracker.total_output_tokens,
        'cost': cost_tracker.total_cost
    }
    return {"message": f"会话 {session_id} 的成本计数已重置"}

@app.get("/health")
async def health():
    """
    健康检查端点，显示服务状态
    """
    return {
        "status": "ok",
        "tools_enabled": True,
        "tracking_costs": TRACK_COSTS,
        "conversations_count": len(conversation_history),
        "active_sessions": len(session_baselines),
        "uptime": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }

@app.get("/stats")
async def get_stats():
    """
    获取使用统计信息
    """
    # 计算各种统计数据
    total_queries = len(conversation_history)
    unique_sessions = len(set(msg.get("session_id", "default") for msg in conversation_history))
    
    # 计算平均响应长度
    avg_response_length = 0
    if conversation_history:
        total_length = sum(len(msg.get("response", "")) for msg in conversation_history)
        avg_response_length = total_length // total_queries
    
    # 计算总成本
    total_cost_value = 0.0
    for conv in conversation_history:
        if conv.get("cost"):
            cost_str = conv["cost"].get("total_cost", "¥0.0000")
            total_cost_value += float(cost_str.replace("¥", ""))
    
    return {
        "total_queries": total_queries,
        "unique_sessions": unique_sessions,
        "average_response_length": avg_response_length,
        "total_cost": f"¥{total_cost_value:.4f}",
        "cost_tracking_enabled": TRACK_COSTS
    }

if __name__ == "__main__":
    print("🚀 启动AI Agent API服务器...")
    print(f"💰 成本追踪: {'✅ 已开启' if TRACK_COSTS else '❌ 已关闭'}")
    print(f"🌐 API地址: http://localhost:8000")
    print(f"📊 健康检查: http://localhost:8000/health")
    print(f"📥 下载日志: http://localhost:8000/download-logs")
    print("-" * 50)
    
    # 使用reload=True在开发时支持热重载
    uvicorn.run("api_server:app", host="0.0.0.0", port=8000, reload=True)

