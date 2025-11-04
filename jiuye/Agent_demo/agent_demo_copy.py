# 用来测试整合RAG的，但是依赖太折磨了，故废止，后续有时间再操作。
import os
import math
import sys
import io
import json
from datetime import datetime
from typing import Dict, Any, Optional
from dotenv import load_dotenv
from langchain.agents import initialize_agent, Tool, AgentType
from langchain_openai import ChatOpenAI
from langchain_community.tools import DuckDuckGoSearchRun, WikipediaQueryRun
from langchain_community.utilities import WikipediaAPIWrapper
# 添加新的搜索包，因为langchain的DuckDuckGo集成已废弃
from ddgs import DDGS  # 不是 from duckduckgo_search import DDGS
from langchain.prompts import PromptTemplate
from langchain_core.callbacks import BaseCallbackHandler
import tiktoken

# 加载环境变量
env_path = os.path.join(os.path.dirname(__file__), ".env")
if not load_dotenv(dotenv_path=env_path):
    print("警告: 未找到 .env 文件")

# 配置
USE_REAL_TOOLS = True
USE_CUSTOM_PROMPT = False
TRACK_COSTS = True

# DeepSeek 定价（2025年10月）
DEEPSEEK_PRICING = {
    "input_cached": 0.2 / 1_000_000,     # 0.2元/百万tokens（缓存命中）
    "input_uncached": 2.0 / 1_000_000,   # 2元/百万tokens（缓存未命中）
    "output": 3.0 / 1_000_000             # 3元/百万tokens
}

class CostTracker(BaseCallbackHandler):
    """追踪API调用成本"""
    def __init__(self):
        self.total_tokens = 0
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        self.total_cost = 0.0
        self.encoding = tiktoken.encoding_for_model("gpt-4")  # DeepSeek兼容
        
    def on_llm_start(self, serialized: Dict[str, Any], prompts: list[str], **kwargs) -> None:
        """LLM调用开始时估算输入tokens"""
        for prompt in prompts:
            self.total_input_tokens += len(self.encoding.encode(prompt))
    
    def on_llm_end(self, response, **kwargs) -> None:
        """LLM调用结束时计算输出tokens和成本"""
        if hasattr(response, 'generations'):
            for generation in response.generations:
                for gen in generation:
                    if hasattr(gen, 'text'):
                        self.total_output_tokens += len(self.encoding.encode(gen.text))
        
        # 计算本次调用成本（假设都是未缓存）
        input_cost = self.total_input_tokens * DEEPSEEK_PRICING["input_uncached"]
        output_cost = self.total_output_tokens * DEEPSEEK_PRICING["output"]
        self.total_cost = input_cost + output_cost
        self.total_tokens = self.total_input_tokens + self.total_output_tokens
    
    def get_summary(self) -> str:
        """获取成本摘要"""
        return f"""
成本统计（DeepSeek 2025年10月定价）:
- 输入 tokens: {self.total_input_tokens:,}
- 输出 tokens: {self.total_output_tokens:,}
- 总 tokens: {self.total_tokens:,}
- 预估成本: ¥{self.total_cost:.4f}
"""

cost_tracker = CostTracker() if TRACK_COSTS else None
class LoggingCallbackHandler(BaseCallbackHandler):
    """记录Agent思考过程"""
    def __init__(self):
        self.logs = []
    
    def on_chain_start(self, serialized, inputs, **kwargs):
        self.logs.append(f"Question: {inputs.get('input', '')}")
    
    def on_llm_start(self, serialized, prompts, **kwargs):
        if prompts and "Thought:" in prompts[0]:
            self.logs.append("=== Agent思考过程 ===")
    
    def on_llm_end(self, response, **kwargs):
        if hasattr(response, 'generations'):
            text = response.generations[0][0].text
            if text:
                self.logs.append(text.strip())
    
    def get_full_log(self):
        return "\n".join(self.logs)
    
    def reset(self):
        self.logs = []

log_handler = LoggingCallbackHandler()

def get_api_config():
    """运行时获取API配置"""
    api_key = os.getenv("DEEPSEEK_API_KEY")
    if not api_key:
        raise ValueError("请在 .env 中设置 DEEPSEEK_API_KEY")
    return {
        "api_key": api_key,
        "base_url": os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")
    }

# ========== 模拟工具 ==========
def fake_search(query: str) -> str:
    return f"[模拟搜索] 关于'{query}'的结果：这是模拟数据"

def fake_calculator(expression: str) -> str:
    return f"[模拟计算] {expression} = 42"

# ========== 真实工具 ==========
# 删除原来的 safe_search 修正一下 因为原来的单源搜索太容易出现搜索不到结果等问题了
def safe_search(query: str) -> str:
    """多源搜索，带缓存和降级"""
    if not hasattr(safe_search, 'cache'):
        safe_search.cache = {}
    
    if query in safe_search.cache:
        return f"[缓存] {safe_search.cache[query]}"
    
    # 使用新的ddgs包替代废弃的DuckDuckGoSearchRun
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query.strip(), max_results=3))
            if results:
                # 检查结果相关性
                relevant = any(word in str(results).lower() 
                             for word in query.lower().split() 
                             if len(word) > 2)
                
                if relevant:
                    # 组合前2个结果
                    result = "\n".join([r['body'] for r in results[:2]])
                    safe_search.cache[query] = result
                    return result
                else:
                    # 结果不相关，提示AI可以换个方式
                    return f"搜索'{query}'返回了不相关结果。建议：1)尝试英文（若英文不行则其他语言也可以尝试 按照语言使用率从高到低顺序尝试）关键词 2)使用更具体的搜索词 3)换个表述方式"
    except Exception as e:
        pass
    
    return f"搜索暂时失败。建议：1)用英文（若英文不行则其他语言也可以尝试 按照语言使用率从高到低顺序尝试）重试 2)简化搜索词 3)访问: https://www.google.com/search?q={query.replace(' ', '+')}"



def safe_wikipedia(query: str) -> str:
    """包装Wikipedia工具，确保返回有效结果"""
    try:
        result = wikipedia.run(query)
        if not result or result == "No good Wikipedia Search Result was found":
            return f"Wikipedia未找到关于 '{query}' 的页面。请尝试英文（若英文不行则其他语言也可以尝试 按照语言使用率从高到低顺序尝试）搜索或更通用的关键词。"
        return result
    except Exception as e:
        return f"Wikipedia查询出错: {type(e).__name__}: {e}"

# search_tool = DuckDuckGoSearchRun() if USE_REAL_TOOLS else None  # 废弃，不再使用
wikipedia = WikipediaQueryRun(api_wrapper=WikipediaAPIWrapper()) if USE_REAL_TOOLS else None

# 自定义 Python REPL 实现
class SafePythonREPL:
    """安全的Python代码执行环境"""
    def run(self, code: str) -> str:
        try:
            # 清理代码块标记
            code = code.strip()
            if code.startswith('```python'):
                code = code[9:]
            if code.startswith('```'):
                code = code[3:]
            if code.endswith('```'):
                code = code[:-3]
            code = code.strip()
            
            old_stdout = sys.stdout
            sys.stdout = io.StringIO()
            
            # 创建受限但功能丰富的执行环境
            exec_globals = {
                '__builtins__': {
                    'print': print, 'range': range, 'len': len, 'sum': sum,
                    'min': min, 'max': max, 'abs': abs, 'round': round,
                    'sorted': sorted, 'list': list, 'dict': dict, 'set': set,
                    'tuple': tuple, 'str': str, 'int': int, 'float': float,
                    'bool': bool, 'enumerate': enumerate, 'zip': zip,
                    'map': map, 'filter': filter, 'any': any, 'all': all,
                },
                'math': math,
            }
            
            # 支持变量赋值和多行代码
            exec(code, exec_globals)
            output = sys.stdout.getvalue()
            
            # 如果没有print输出，尝试eval最后一行
            if not output:
                lines = code.strip().split('\n')
                if lines and not any(keyword in lines[-1] for keyword in ['=', 'def', 'class', 'import', 'for', 'while', 'if']):
                    try:
                        result = eval(lines[-1], exec_globals)
                        if result is not None:
                            output = str(result)
                    except:
                        pass
            
            return output if output else "代码执行成功（无输出）"
            
        except Exception as e:
            return f"执行错误: {type(e).__name__}: {e}"
        finally:
            sys.stdout = old_stdout

python_repl = SafePythonREPL() if USE_REAL_TOOLS else None

def real_calculator(expression: str) -> str:
    """安全的数学计算器"""
    try:
        allowed_names = {k: v for k, v in math.__dict__.items() if not k.startswith("__")}
        allowed_names.update({"abs": abs, "round": round, "sum": sum, "min": min, "max": max})
        code = compile(expression, "<string>", "eval")
        result = eval(code, {"__builtins__": {}}, allowed_names)
        return str(result)
    except Exception as e:
        return f"计算错误: {type(e).__name__}: {e}"

def get_current_time(format: str = "") -> str:
    """获取当前时间，确保总是返回有效结果"""
    try:
        if not format:
            format = "%Y-%m-%d %H:%M:%S"
        return datetime.now().strftime(format)
    except:
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
# def search_knowledge_base(query: str) -> str:
#     """搜索本地知识库"""
#     import subprocess
    
#     result = subprocess.run(
#         [r"D:\jiuye\environments\rag_env\python.exe", r"D:\jiuye\Agent_demo\rag_wrapper.py", query],
#         capture_output=True,
#         text=True,
#         encoding='gbk'
#     )
    
#     return result.stdout if result.returncode == 0 else f"查询失败: {result.stderr}"






# ========== 构建工具列表 ==========
if USE_REAL_TOOLS:
    tools = [
    Tool(name="Search", func=safe_search, description="搜索网络"),
    Tool(name="Wiki", func=safe_wikipedia, description="查Wikipedia"),
    Tool(name="Calc", func=real_calculator, description="数学计算"),
    Tool(name="Time", func=get_current_time, description="Get current time. Leave empty for default format"),
    Tool(name="Python", func=python_repl.run, description="执行Python"),
    # Tool(name="KnowledgeBase", func=search_knowledge_base, description="搜索本地知识库文档（PDF、TXT、MD、代码文件等）")
    ]
else:
    tools = [
        Tool(name="Search", func=fake_search, description="搜索信息（模拟）"),
        Tool(name="Calculator", func=fake_calculator, description="数学计算（模拟）"),
    ]

# ========== 初始化 LLM ==========
try:
    config = get_api_config()
    callbacks = [cost_tracker, log_handler] if TRACK_COSTS else [log_handler]
    llm = ChatOpenAI(
        api_key=config["api_key"],
        base_url=config["base_url"],
        model="deepseek-chat",
        temperature=0,
        callbacks=callbacks
    )
except ValueError as e:
    print(f"配置错误: {e}")
    exit(1)

# ========== 自定义 Prompt (可选) ==========
def get_custom_prompt():
    """返回自定义的ReAct prompt模板"""
    return PromptTemplate(
        template="""你是一个智能助手。你可以使用以下工具来帮助回答问题：

{tools}

请严格使用以下格式：

Question: 需要回答的输入问题
Thought: 你应该思考要做什么
Action: 要采取的动作，必须是 [{tool_names}] 之一
Action Input: 动作的输入
Observation: 动作的结果
... (这个 Thought/Action/Action Input/Observation 可以重复多次)
Thought: 我现在知道最终答案了
Final Answer: 对原始输入问题的最终答案

重要：等待每个Action的实际Observation结果，不要自己编造！

开始！

Question: {input}
Thought: {agent_scratchpad}""",
        input_variables=["tools", "tool_names", "input", "agent_scratchpad"]
    )

# ========== 初始化 Agent ==========
agent_kwargs = {}
if USE_CUSTOM_PROMPT:
    agent_kwargs["prompt"] = get_custom_prompt()
    print("使用自定义 ReAct Prompt")
else:
    print("使用默认 ReAct Prompt")

agent = initialize_agent(
    tools,
    llm,
    agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
    verbose=True,
    max_iterations=3,
    early_stopping_method="generate",
    agent_kwargs=agent_kwargs,
    handle_parsing_errors=True
)

# 可选：查看实际使用的prompt
def show_prompt():
    """显示当前使用的prompt模板"""
    print("\n当前Prompt模板:")
    print("-" * 50)
    print(agent.agent.llm_chain.prompt.template)
    print("-" * 50)

if USE_CUSTOM_PROMPT:
    show_prompt()

# ========== 测试功能 ==========
def run_tests():
    """运行预定义测试"""
    test_queries = [
        "现在几点了？",
        "计算 123 * 456 + 789",
        "搜索一下2024年诺贝尔物理学奖获得者",
        "在Wikipedia查询人工智能的历史",
        "用Python计算前10个斐波那契数",
    ]
    
    for query in test_queries:
        print(f"\n{'='*50}\n问题: {query}\n{'-'*50}")
        try:
            result = agent.invoke({"input": query})["output"]  # 不是 agent.run(query)
            print(f"\n最终答案: {result}")
            # 日志记录
            with open("agent_logs.txt", "a", encoding="utf-8") as f:
                f.write(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"问题: {query}\n")
                f.write(f"回答: {result}\n")
                f.write(f"完整过程:\n{log_handler.get_full_log()}\n")
                log_handler.reset()
                if TRACK_COSTS:
                    f.write(cost_tracker.get_summary())
                f.write("\n" + "="*50 + "\n")
        except Exception as e:
            print(f"错误: {type(e).__name__}: {e}")
        
        if TRACK_COSTS:
            print(cost_tracker.get_summary())

def interactive_mode():
    """交互式模式"""
    print(f"Available tools: {[t.name for t in tools]}")
    print(f"\n{'='*50}")
    print(f"Agent 交互模式")
    print(f"配置: {'真实工具' if USE_REAL_TOOLS else '模拟工具'} | {'自定义Prompt' if USE_CUSTOM_PROMPT else '默认Prompt'}")
    print(f"成本追踪: {'开启' if TRACK_COSTS else '关闭'}")
    print("命令: 'exit/quit' 退出 | 'show prompt' 查看prompt | 'test' 运行测试 | 'cost' 查看成本")
    print(f"{'='*50}\n")
    
    while True:
        try:
            user_input = input("\n请输入问题: ").strip()
            
            # 特殊命令
            if user_input.lower() in ['exit', 'quit', 'q']:
                print("退出程序")
                if TRACK_COSTS:
                    print("\n总计" + cost_tracker.get_summary())
                break
            elif user_input.lower() == 'show prompt':
                show_prompt()
                continue
            elif user_input.lower() == 'test':
                run_tests()
                continue
            elif user_input.lower() == 'cost' and TRACK_COSTS:
                print(cost_tracker.get_summary())
                continue
            elif not user_input:
                continue
                
            print(f"\n{'-'*50}")
            result = agent.invoke({"input": user_input})["output"]  # 注意是user_input不是query,run方法已经不能用了 改为invoke。
            print(f"\n最终答案: {result}")
            # 日志记录
            with open("agent_logs.txt", "a", encoding="utf-8") as f:
                f.write(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"问题: {user_input}\n")
                f.write(f"回答: {result}\n")
                f.write(f"完整过程:\n{log_handler.get_full_log()}\n")
                log_handler.reset()
                if TRACK_COSTS:
                    f.write(cost_tracker.get_summary())
                f.write("\n" + "="*50 + "\n")

            if TRACK_COSTS:
                print(cost_tracker.get_summary())
            
        except KeyboardInterrupt:
            print("\n\n检测到中断，退出程序")
            if TRACK_COSTS:
                print("\n总计" + cost_tracker.get_summary())
            break
        except Exception as e:
            print(f"错误: {type(e).__name__}: {e}")
            import traceback
            if os.getenv("DEBUG", "").lower() == "true":
                traceback.print_exc()

if __name__ == "__main__":
    if len(sys.argv) > 1:
        if sys.argv[1] == "test":
            run_tests()
        elif sys.argv[1] == "custom":
            USE_CUSTOM_PROMPT = True
            print("启用自定义Prompt模式")
            interactive_mode()
    else:
        interactive_mode()
