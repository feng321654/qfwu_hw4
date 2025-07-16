system_prompt="""请根据用户请求选择以下两种工作模式之一，严格按照对应格式输出：
**注意，你只需要做出选择并给出理由**
<模式说明>
1. 代理模式（<|AGENT|>）：
   适用场景：需要调试、分析代码问题，并给出修改建议或修复方案。
2. 编辑模式（<|EDIT|>）：
   适用场景：用户请求直接修改代码，或者已经给出代码的问题，无需分析或调试环节。
</模式说明>

<任务>
1. 首先明确说明你选择的模式（必须且只能选择一种）
2. 给出你选择的思考过程
</任务>

<示例>
输入：请修复这段Python代码中的bug：[代码片段]
"输出": "<|AGENT|>\n用户没有直接告诉我 BUG 是什么，所以我需要先调试代码再进行分析，我应该使用代理模式进行尝试"
</示例>
"""

tools = [
    {
        "type": "function",
        "function": {
            "name": "python",
            "description": "Execute Python code for debugging and analysis",
            "parameters": {
                "type": "object",
                "properties": {
                    "code": {
                        "type": "string",
                        "description": "Python code to execute"
                    }
                },
                "required": ["code"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "editor",
            "description": "Edit and merge code by comparing original and modified versions",
            "parameters": {
                "type": "object",
                "properties": {
                    "original_code": {
                        "type": "string",
                        "description": "Original code before modification"
                    },
                    "modified_code": {
                        "type": "string",
                        "description": "Modified code after fixing"
                    }
                },
                "required": ["original_code", "modified_code"]
            }
        }
    }
]

train_prompt="""你是 Github Copilot 系统的主控模型。你的任务是根据用户输入和任务内容，自动识别并切换两种工作模式：

1. 代理模式（<|AGENT|>）
适用场景：需要调试、分析代码问题，并给出修改建议或修复方案。
工作流程：
使用 代码执行器（python） 工具来运行、调试、分析代码或验证想法。

2. 编辑模式（<|EDIT|>）
适用场景：用户请求直接修改代码，或者已经给出代码的问题，无需分析或调试环节。
工作流程：
直接根据任务要求修改代码。
只使用 代码编辑器（editor） 工具进行原始代码与修改后代码的合并和替换。

# 工具描述\n{}""".format(tools)+"""\n# 在使用工具时，你必须遵循工具描述，并通过JSON格式实现对工具的调用，具体格式为{\"name\": <function-name>, \"arguments\": <args-json-object>}

总体要求
自动根据任务内容和用户意图选择模式。
在代理模式下，在</think>后生成<|AGENT|>，并用 python 工具分析、验证
在编辑模式下，在</think>后生成<|EDIT|>直接用 editor 工具修改代码，不使用 python。
工具调用要符合上述流程规范，输出应清晰、准确，便于用户理解和采纳"""

from vllm import LLM, SamplingParams
from transformers import AutoTokenizer
import json
model_name = "Qwen3-32B"

tokenizer = AutoTokenizer.from_pretrained(model_name)

with open('processed_data/query.json') as f:
    data_list=json.load(f)
prompts=[]
for data in data_list:
    messages = [{"role": "system", "content": system_prompt},{"role":"user","content":f"用户请求：{data['query']}"}]
    prompt = tokenizer.apply_chat_template(
        messages,
        tokenize=False,
        add_generation_prompt=True,
        enable_thinking=True
    )
    prompts.append(prompt)

llm = LLM(model=model_name,tensor_parallel_size=2)
sampling_params = SamplingParams(
    temperature=0.6,
    top_p=0.9,
    max_tokens=2048,
)
outputs = llm.generate(prompts, sampling_params)

train_data_list=[]
for data, output in zip(data_list, outputs):
    generated_text = output.outputs[0].text
    with open('123,txt','w') as f:
        f.write(generated_text)
    if '</think>' not in generated_text:
        continue
    answer=generated_text.split("</think>")[-1]
    new_data={}
    if "<|AGENT|>" in answer and data['label']=='agent' and '\n' in answer:
        think=answer.split('\n')[-1].strip()
        python_call=json.dumps({"name": "python", "arguments": {"code": data['buggy_code']}})
        new_output=f"<think>{think}</think><|AGENT|>\n{python_call}"
    elif "<|EDIT|>" in answer and data['label']=='edit' and '\n' in answer:
        think=answer.split('\n')[-1].strip()
        edit_call=json.dumps({"name": "editor","arguments": {"original_code": data['buggy_code'],"modified_code": data['solution']}})
        new_output=f"<think>{think}</think><|EDIT|>\n{edit_call}"
    else:
        continue
    train_data_list.append(
        {
            "instruction":data['query'],
            "input":"",
            "output":new_output,
            "system": train_prompt
        }
    )
    with open('processed_data/train.json','w') as f:
        json.dump(train_data_list,f,ensure_ascii=False,indent=2)
