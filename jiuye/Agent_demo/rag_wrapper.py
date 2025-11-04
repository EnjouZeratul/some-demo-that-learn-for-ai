#尝试于agent里面加入RAG 为保持环境独立性，RAG查询和Agent分析采用分离架构 故废止

import subprocess
import sys
import os

if __name__ == "__main__":
    query = sys.argv[1]
    
    # 创建干净的环境变量，移除所有Python相关路径
    env = {k: v for k, v in os.environ.items() 
           if not k.startswith(('PYTHON', 'CONDA', 'VIRTUAL'))}
    env['PATH'] = os.environ['PATH']  # 保留系统PATH
    
    # 直接调用rag_env的python
    proc = subprocess.Popen(
        [r"D:\jiuye\environments\rag_env\python.exe", r"D:\jiuye\RAG_demo\rag_multi.py"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding='gbk',
        cwd=r"D:\jiuye\RAG_demo",  # 确保在正确目录
        env=env
    )
    
    # 发送查询并退出
    stdout, stderr = proc.communicate(input=f"{query}\nexit\n")
    
    # 提取回答
    if "回答:" in stdout:
        answer = stdout.split("回答:")[-1].split("可输入")[0].strip()
        print(answer)
    elif stderr:
        print(f"错误: {stderr.strip()}")
    else:
        print("无输出")
