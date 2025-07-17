# 吴奇峰第四次作业
在暑期集训的第四次作业中，我选择了作业3，直接基于 暑期集训-2025-homework-3 中的任务，自己构造数据，训练模型来实现更好的格式控制

## 一、数据构建
我使用了开源的DebugBench数据集：https://huggingface.co/datasets/Rtian/DebugBench

数据集的每个样本包含：有bug的代码，错误类型，正确代码等。

为了达到训练 code agent 的目的，训练数据应有的格式为
```
{
    "system": system_prompt,
    "user": query,
    "output": "<think> 思考过程 </think> <AGENT> \n python_tool_call"
}

```
或
```
{
    "system": system_prompt,
    "user": query,
    "output": "<think> 思考过程 </think> <EDIT> \n editor_tool_call"
}
```

两种模式下，工具调用需要的参数只有原始代码（和正确代码）。因此，需要合成的只有query和思考过程。

### 1，Query构建
#### AGENT相关Query
我在网页端要求大模型生成了一部分Query中的描述部分，从中人工挑选出合理的部分。
（在此之前曾经尝试在本地推理，为有bug的代码补全Query，但是生成的质量不是很好）

在代码中，我先随机选取一个描述，再在后面拼上数据集中有bug的代码，作为完整Query
#### EDIT相关Query
这部分Query需要包含错误的信息，我直接使用了原数据集中的错误类别和子类型，进行合并，作为错误信息提示，后面拼接上代码

### 2，思考过程构建

通过设计合理的prompt，要求Qwen3-32B大模型针对一个Query，在两种模式中选择。在<\/think>后，要求模型仅给出<|AGENT|>或<|EDIT|>以及选择的理由。

之后，我比较模型给出的选择和当前Query的设定的类别，若一致，则认为当前Query和think具有合理性，予以保留，在此基础上拼接模型回复部分，构建完整的训练数据

## 二、模型训练
使用llamafactory训练，训练时加入新的token，<|AGENT|>和<|EDIT|>。方法为全量监督微调

由于计算资源限制（只申请到了3张显卡），训练对象是Qwen3-1.7B，数据量是1200多条。

训练数据示例
```json
  {
    "instrution": "我不确定这段代码的实现是否正确，请验证并指出问题。\n\n\n\nclass Solution:\n    def maximumNumber(self, num: str, change: List[int]) -> str:\n        num = list(num)\n        on = False \n     for i, ch in enumerate(num): \n         x = int(ch)\n         if x < change[x]: \n              on = True\n              num[i] = str(change[x])\n         elif x > change[x] and on: break\n    return \"\".join(num)\n",
    "input": "",
    "output": "<think>用户请求验证代码的正确性并指出潜在问题，但未明确说明具体错误表现或需要直接修改代码。此场景需要调试和分析代码逻辑是否符合预期，例如检查循环终止条件、替换规则是否正确等，因此适用代理模式。</think><|AGENT|>\n{\"name\": \"python\", \"arguments\": {\"code\": \"\\nclass Solution:\\n    def maximumNumber(self, num: str, change: List[int]) -> str:\\n        num = list(num)\\n        on = False \\n     for i, ch in enumerate(num): \\n         x = int(ch)\\n         if x < change[x]: \\n              on = True\\n              num[i] = str(change[x])\\n         elif x > change[x] and on: break\\n    return \\\"\\\".join(num)\\n\"}}",
    "system": "你是 Github Copilot 系统的主控模型……"
  }
```

### 损失函数图像
不是很平滑，但可以下降到很低的水平。

![alt text](image-1.png)


## 三、效果检验
使用作业三给出的10条query进行简单测试。

初始Qwen3-1.7B的效果很差
![alt text](image.png)

训练后，可以通过所有测试，并且模型对代码本身而非模式选择的思考得到了有效抑制

一个输出示例为
```json
  {
    "Query": "报错信息：SyntaxError: invalid syntax\n修复这个条件判断\n\ndef check_grade(score):\n    if score >= 90\n        return 'A'\n    elif score >= 80:\n        return 'B'\n    else:\n        return 'C'",
    "Output": "<think>用户直接指出了语法错误（invalid syntax），并且代码片段中存在明显的语法错误：if score >= 90后缺少冒号。这是一个直接的代码修改需求，无需调试分析，应使用编辑模式。</think><|EDIT|>\n{\"name\": \"editor\", \"arguments\": {\"original_code\": \"\\ndef check_grade(score):\\n    if score >= 90\\n        return 'A'\\n    elif score >= 80:\\n        return 'B'\\n    else:\\n        return 'C'\", \"modified_code\": \"def check_grade(score):\\n    if score >= 90:\\n        return 'A'\\n    elif score >= 80:\\n        return 'B'\\n    else:\\n        return 'C'\"}}"
  }
```
