import transformers
print("Transformers version:", transformers.__version__)
from datasets import load_dataset
from transformers import AutoTokenizer, AutoModelForCausalLM, TrainingArguments, Trainer
from peft import LoraConfig, get_peft_model

# 1. 选择基座模型
model_name = "gpt2-medium"  # 345M 参数，显存友好
tokenizer = AutoTokenizer.from_pretrained(model_name)
tokenizer.pad_token = tokenizer.eos_token  # GPT2 没有 pad_token，需要手动指定

model = AutoModelForCausalLM.from_pretrained(model_name)

# 2. 配置 LoRA
lora_config = LoraConfig(
    r=8,
    lora_alpha=16,
    target_modules=["c_attn"],  # GPT2 的注意力层
    lora_dropout=0.05,
    task_type="CAUSAL_LM"
)
model = get_peft_model(model, lora_config)

# 3. 加载数据集（HuggingFace 的 wikitext 小样本）
raw_dataset = load_dataset("wikitext", "wikitext-2-raw-v1")

# 划分训练集和验证集（取很小一部分，快速跑通进行测试 不过我的小破电脑也不太行 跑了半天 桌子都可以煎牛排了）
dataset = raw_dataset["train"].train_test_split(test_size=0.005)

def tokenize(batch):
    tokens = tokenizer(batch["text"], truncation=True, padding="max_length", max_length=128)
    # Trainer 需要 labels 字段
    tokens["labels"] = tokens["input_ids"].copy()
    return tokens

train_dataset = dataset["train"].map(tokenize, batched=True, remove_columns=["text"])
eval_dataset = dataset["test"].map(tokenize, batched=True, remove_columns=["text"])

# 4. 训练参数
training_args = TrainingArguments(
    output_dir="./outputs",
    per_device_train_batch_size=2,
    gradient_accumulation_steps=4,
    num_train_epochs=1,
    learning_rate=2e-4,
    logging_dir="./logs",
    save_strategy="epoch",
    fp16=True,
    logging_steps=10,
    eval_strategy="epoch"  # 用 eval_strategy 替代 evaluation_strategy
)

# 5. Trainer
trainer = Trainer(
    model=model,
    args=training_args,
    train_dataset=train_dataset,
    eval_dataset=eval_dataset
)

# 6. 开始训练
trainer.train()
