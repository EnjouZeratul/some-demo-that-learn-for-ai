​	

​	我希望以后可以参与制作真正的AI的项目，不过在一定程度上来看不积跬步无以至千里，我打算先尝试逐步从现有的各种体系先学起来。



​	A dream of making true AI has begun. Maybe it seems far away now, and we can't see it in this demo yet. But I hope and believe the wait won't be much longer. 



​	这个项目只是一个普通的用于学习如何进行基本的API调用以及RAG，Lora微调，agent工具调用，Eval，多模态的项目。每个模块单独做一个demo进行练习，后续可能尝试整合进入一个web框架或者整合为应用程序，或者先验证是否可以完成更多整合，例如模型训练等，然后再进行总体整合，试试能不能后续持续更新内容。



​	This project is a simple learning project for practicing basic API calls, RAG, LoRA fine-tuning, agent tool calling, Eval, and multimodality. Each module has its own separate demo for practice. Future plans may include integrating into a web framework or application, or first validating whether more integrations are possible (like model training), then proceeding with overall integration to see if continuous content updates are feasible. 



​	主要是基于deep seek API 以及langchain 框架，react推理模式等。
LLM层: DeepSeek API (via OpenAI client) 
向量数据库: FAISS (轻量本地) 
Embeddings: HuggingFace本地模型 (sentence-transformers) 
文档处理: PyPDFLoader, DirectoryLoader 
Agent工具: Wikipedia, DDGS搜索, 自定义Python/计算器 
辅助: python-dotenv环境管理, datetime日志



Primarily based on DeepSeek API and LangChain framework, ReAct reasoning mode, etc.

- LLM Layer: DeepSeek API (via OpenAI client)
- Vector Database: FAISS (lightweight local)
- Embeddings: HuggingFace local models (sentence-transformers)
- Document Processing: PyPDFLoader, DirectoryLoader
- Agent Tools: Wikipedia, DDGS search, custom Python/calculator
- Utilities: python-dotenv environment management, datetime logging



**每个demo文件夹需要单独创建一个.env文件中加入DEEPSEEK_API_KEY=sk-？？？？？**** 

**来放置你拥有的deep seek API** （计划在未来更新为支持多种模型的API）



**Each demo folder requires creating a separate .env file with DEEPSEEK_API_KEY=sk-??????**

**to store your deep seek API key**（future will not only deep seek api）



​	我会把每个demo的conda依赖环境导出为文件（environment.yml）放入对应的每个demo的文件夹中  你们可以使用（ `conda env create -f environment.yml` ）配置在自己喜欢的文件夹内 只要运行的时候找得到就行了，每个项目中的readme第一行代码是用于打开对应的环境，我在此处写的是我的环境位置，如果你们有变动，则以自己配置的环境位置为准。



​	I'll export each demo's conda environment dependencies as a file (environment.yml) and place it in the corresponding demo folder. You can use `conda env create -f environment.yml` to configure it in your preferred location - as long as it's findable when running. The first line of code in each project's readme is for activating the corresponding environment. I've written my environment location here, but if yours differs, use your own configured environment path. 



​	每个项目有单独的readme来告知如何运行。



​	a demo have a readme that tell how to run.



​	最后更新于2025/11/4



​	Last updated: 2025/11/4 



**开头（接近2025.10.22）**
	创建RAGdemo，分别创建单PDF文件检索分析对话以及多文件检索分析对话，faiss向量库生成使用huggingface开源处下载的Embedding本地模型（因为我使用的deep seekAPI不支持Embeddings接口调用）
	创建LORADEMO，训练下载到本地的gpt2-medium模型（如果你喜欢别的模型可以在代码中修改下载的模型），可以根据需求更换训练的模型，每次训练结果在outputs生成为checkpoint-XXXX文件夹。



**began (around 2025.10.22)** 

​	Created RAG demo with separate single PDF file retrieval analysis dialogue and multi-file retrieval analysis dialogue. FAISS vector database generation uses locally downloaded Embedding models from HuggingFace open source (since the DeepSeek API I'm using doesn't support Embeddings interface calls). 

​	Created LORA DEMO to train the locally downloaded gpt2-medium model (you can modify the code to download other models if preferred). The training model can be changed based on requirements. Each training result generates a checkpoint-XXXX folder in outputs. 



**2025.10.27**
	去除每个demo各自的依赖库，改为在项目主目录全局配置整合后的依赖库。
我失败了，在多个demo的情况下使用统一依赖库是很容易触发依赖版本和兼容冲突的选择，我决定改为依赖目录依然放在主目录，但是在其内部分离不同demo的依赖环境，如果后续有空再把确定可以共享的依赖放在主目录环境配置目录的通用文件夹。

​	创建agent_demo，因为方便所以放置再RAG_demo文件夹内。用于练习工具调用。
不行，不能犯懒。借用RAG的依赖环境会导致兼容问题，以及受限于RAG的依赖环境（怕破坏RAG可运行的自身依赖环境） 导致不能进行激进的依赖环境更新。 我还是单独分离agentdemo吧。



**2025.10.27** 

​	Removed individual dependency libraries for each demo, switching to globally configured integrated dependencies in the project main directory. 

​	I failed - using unified dependencies across multiple demos easily triggers dependency version and compatibility conflicts. I've decided to keep the dependency directory in the main folder but separate different demo dependency environments within it. If time permits later, I'll move confirmed shareable dependencies to a common folder in the main directory's environment configuration.

​	Created agent_demo, initially placed in RAG_demo folder for convenience. Used for practicing tool calling. 

​	No, can't be lazy. Borrowing RAG's dependency environment causes compatibility issues and limits aggressive dependency updates (to avoid breaking RAG's working environment). I'll separate agent_demo after all.



**2025.11.4**

​	尝试将RAG合并入AGENT，发现环境依赖冲突严重，为保持环境独立性以及稳定性，RAG查询和Agent分析采用分离架构。继续保持独立。

​	最近学的内容就大概先做这一些吧，下一步我打算学习一下next.js，巩固一下node.js，研究研究WEB或者全栈的内容。



**2025.11.4**

​	 Attempted to merge RAG into AGENT but encountered severe environment dependency conflicts. To maintain environment independence and stability, RAG queries and Agent analysis adopt a separated architecture. Continuing to keep them independent. 

​	That's about it for what I've learned recently. Next, I plan to study Next.js, consolidate  node.js knowledge, and research web or full-stack development. 