from transformers import AutoTokenizer, AutoModelForCausalLM
from peft import PeftModel

base_model = "gpt2-medium"   # 你训练时用的基座
adapter_path = "./outputs/checkpoint-4567"  # 最新的 LoRA 权重

tokenizer = AutoTokenizer.from_pretrained(base_model)
model = AutoModelForCausalLM.from_pretrained(base_model)
model = PeftModel.from_pretrained(model, adapter_path)

prompt = "人工智能的未来是"
inputs = tokenizer(prompt, return_tensors="pt")
outputs = model.generate(**inputs, max_new_tokens=80)
print(tokenizer.decode(outputs[0], skip_special_tokens=True))
