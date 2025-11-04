import os
import datetime
from dotenv import load_dotenv
from openai import OpenAI
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import HuggingFaceEmbeddings

# 读取 .env 文件
load_dotenv()

# 初始化 DeepSeek 客户端
client = OpenAI(
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    base_url="https://api.deepseek.com"
)
if not os.getenv("DEEPSEEK_API_KEY"):
    raise ValueError("请在.env文件中设置DEEPSEEK_API_KEY")


# 加载 PDF 文档
loader = PyPDFLoader("data/sample.pdf")
documents = loader.load()

# 切分文档
text_splitter = RecursiveCharacterTextSplitter(chunk_size=800, chunk_overlap=100)
docs = text_splitter.split_documents(documents)

# 使用本地 HuggingFace Embedding 模型
embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")

# 构建向量索引
vectorstore = FAISS.from_documents(docs, embeddings)

# 定义一个函数，用 DeepSeek 回答问题，并统计 token 消耗
def ask_llm(prompt: str):
    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=[{"role": "user", "content": prompt}],
        stream=False
    )

    # 默认值
    input_tokens = output_tokens = total_tokens = 0
    cost = 0.0

    # 统计 token 消耗
    usage = response.usage
    if usage:
        input_tokens = usage.prompt_tokens
        output_tokens = usage.completion_tokens
        total_tokens = usage.total_tokens
        cost = input_tokens/1e6*2 + output_tokens/1e6*3  # 按 DeepSeek 价格估算
        print(f"[统计] 输入tokens={input_tokens}, 输出tokens={output_tokens}, 总tokens={total_tokens}, 约花费={cost:.6f}元")

    answer = response.choices[0].message.content
    return answer, input_tokens, output_tokens, total_tokens, cost

# 循环问答
print("RAG Demo 已启动，输入 exit 退出")
while True:
    query = input("请输入问题: ")
    if query.lower() in ["exit", "quit"]:
        break

    # 检索相关文档
    docs = vectorstore.similarity_search(query, k=3)
    context = "\n".join([d.page_content for d in docs])
    prompt = f"以下是相关文档内容：\n{context}\n\n请根据这些内容回答问题：{query}"

    # 调用 LLM
    answer, input_tokens, output_tokens, total_tokens, cost = ask_llm(prompt)

    # === 日志记录 ===
    with open("logs.txt", "a", encoding="utf-8") as f:
        f.write("==== 新的一次问答 ====\n")
        f.write(f"时间: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"问题: {query}\n")
        f.write(f"回答: {answer}\n")
        f.write(f"输入tokens: {input_tokens}, 输出tokens: {output_tokens}, 总tokens: {total_tokens}, 费用估算: {cost:.6f}元\n\n")

    # 控制台输出
    print("回答:", answer)
