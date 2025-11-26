**2025/11/10**

### 环境配置

**下载并安装 Racket**

 访问 https://download.racket-lang.org/ 下载安装包 

 安装到 `D:\TA\Racket` 保持环境独立 （你可以选择自己喜欢的安装目录 只要找得到就好）

**V S Code 配置**

安装 Magic Racket 扩展

打开文件夹 `D:\TA\consciousness-kernel_Racket_20251110` 

项目结构：

```
consciousness-kernel_Racket_20251110/
├── core/          # 核心逻辑引擎
├── rules/         # 可修改规则集
├── logs/          # 运行日志
└── README.md
```

 **运行步骤** 

```
# PowerShell 中验证安装

racket --version
或者D:\TA\Racket\racket.exe --version
```

（**①**如果racket --version**报错**但是D:\TA\Racket\racket.exe --version不报错，

​	你可能需要配置一下racket的全局PATH，但是基于项目的独立性我不建议这么做，反之我建议以下两种方案 ：

​	方案一（对应后续运行方法二）：你可以直接使用我的**run.bat文件**，但是需要注意**如果**你之前**自定义**了racket的安装目录，你需要在run.bat中**重新定向**到你的racket.exe，而非直接使用我的目录。

​	方案二（对应后续运行方法三）无需改动或增加run.bat，直接使用后续运行的第三种方法）

```
# 运行核心程序（如果你不用VSCODE运行程序 例如VSCODE仅用于编写代码 那么直接用单独的power shell运行程序也可以）

cd D:\TA\consciousness-kernel_Racket_20251110\core

# 方法一

racket seed.rkt
```

**如果你存在①报错，则不运行racket seed.rkt，而是换为以下二者之一：**

```
# 方法二
.\run.bat seed.rkt
```

```
# 方法三 （如果你自定义了目录记得把D:\TA\Racket\racket.exe重定向为你自己安装的racket位置）
D:\TA\Racket\racket.exe seed.rkt
```



## 方法四（不使用VSCODE也无需power shell和run.bat）

直接运行DrRacket.exe 然后在里面打开seed.rkt文件run就可以了



**25/11/27新增内容**

运行D:\TA\consciousness-kernel_Racket_20251110的setup.bat来配置依赖

延续之前的风格 你需要在core文件夹创建.env文件  格式：`DEEPSEEK_API_KEY=你的密钥` 。

### 运行记录

2025/11/10 - v0.1

- 成功运行基础core
- 实现概念学习和状态追踪
- 时间戳：1762770991

OS：其实本质上就是个极简demo，还没什么东西做出来。删掉了。

2025/11/26

尝试了许多方案但是发现算力不足以及反馈等过于机械化难以达到满意水平，或许我应该学习更多线性代数、概率论，信息论的内容，再进行开发足够完美的模型架构。

我决定先改为制作以DEEPSEEKAPI为基础的记忆模型，使得其可以高于LLM的常规水平，相当于多了本地仓库以及一定的自我分析进行参考，从而为后续对话产生优势效果 。

2025/11/27

经过修改需要运行D:\TA\consciousness-kernel_Racket_20251110的setup.bat来增加依赖

```powershell
v1.0 实用转型
- 转向：基于DeepSeek API的记忆增强系统
- 实现功能：
  * 智能记忆存储与检索
  * 每10次对话自动分析提取行为规则
  * 成本追踪（¥/对话）
  * 规则即时生效
  
### 当前能力
- 记忆关键词自动标注
- 基于历史的上下文增强
- 自主学习并应用对话模式
- 完整持久化（重启不丢失）

### 技术亮点
- Reasoner模型高效规则提取（33字符响应）
- 中文格式规则解析
- 渐进式系统改进
```



