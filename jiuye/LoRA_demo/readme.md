 **运行方式** 

使用conda或者Windows自带的PowerShell在项目根目录下执行： 

```powershell
conda activate D:\jiuye\environments\lora_env
cd D:\jiuye\LoRA_demo
python lora_demo.py 
```

```powershell
python inference.py
```

（基于最近一次训练的模型权重进行测试对话，可以在代码中修改对话输入以及指定使用的checkpoint。）

（需要在代码中配置训练数据。本demo使用HuggingFace的wikitext小样本作为示例。可自定义训练检查点保存频率（如每500步保存一次）。训练后的模型权重默认保存在`./outputs/checkpoint-XXXX`目录下。）



 **How to Run** 

Using conda or Windows PowerShell, execute from the project root directory: 

```PowerShell
conda activate D:\jiuye\environments\lora_env
cd D:\jiuye\LoRA_demo
python lora_demo.py
```

```PowerShell
python inference.py
```

(Tests dialogue based on the most recent trained model weights. You can modify the dialogue input and specify which checkpoint to use in the code.)

(Training data needs to be configured in the code. This demo uses HuggingFace's wikitext small sample as an example. You can customize checkpoint saving frequency (e.g., save every 500 steps). Trained model weights are saved by default in `./outputs/checkpoint-XXXX` directory.)



