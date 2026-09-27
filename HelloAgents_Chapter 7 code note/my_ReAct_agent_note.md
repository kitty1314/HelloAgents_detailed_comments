可以把 `run()` 理解成一个“导演”循环：Python 不负责思考，它负责把当前局面交给 LLM、读懂 LLM 的决定、执行决定，再把结果交回给 LLM。

整体数据流是：

```
用户问题
  ↓
构建提示词（问题 + 工具说明 + 历史）
  ↓
LLM 输出一段文本：Thought + Action
  ↓
Python 解析出 Thought、Action
  ↓
Action 是 Finish？→ 返回答案
Action 是工具？→ 执行工具，得到 Observation
  ↓
把 Action/Observation 加进历史，回到开头进行下一轮
```

例如用户问：

> “北京今天的天气怎么样？”

第一轮会这样执行。

```
self.current_history = []
current_step = 0
```

每次 `run()` 从空的 ReAct 过程历史开始，避免上一次问题的工具结果干扰这一次。

`while current_step < self.max_steps:` 是循环安全阀：最多执行 5 步，防止模型反复调用工具、无限消耗 API 费用。

---

### 1. 构建提示词

```
tools_desc = self.tool_registry.get_tools_description()
history_str = "\n".join(self.current_history)

prompt = self.prompt_template.format(
    tools=tools_desc,
    question=input_text,
    history=history_str
)
```

这一部分并没有调用模型，只是在把模板中的三个“空位”填好：

```
{tools}    → 当前可用工具，例如 search、calculator
{question} → 用户问题
{history}  → 之前行动过什么、工具返回了什么
```

第一轮的 `history` 是空的，所以模型看到的大意是：

```
可用工具：
- search: 搜索网页信息

问题：北京今天的天气怎么样？

执行历史：空

请输出 Thought 和 Action。
```

第二轮时，`history` 已经有了搜索结果，模型才知道“我已经搜过了”，可以据此继续思考或结束任务。

---

### 2. 调用 LLM

```
messages = [{"role": "user", "content": prompt}]
response_text = self.llm.invoke(messages, **kwargs)
```

这里才真正把提示词发给模型。

模型通常会返回一整段普通字符串，例如：

```
Thought: 这是实时天气信息，我需要搜索。
Action: search[北京今天天气]
```

注意：此时 `Thought`、`Action` 还只是字符串中的两行文本；Python 还不知道它们分别是什么。

---

### 3. 解析 LLM 输出

```
thought, action = self._parse_output(response_text)
```

`_parse_output()` 用正则表达式从模型返回的整段文字里提取：

```
thought = "这是实时天气信息，我需要搜索。"
action = "search[北京今天天气]"
```

也就是说：

```
response_text  # 原始整段回复
```

变成：

```
thought        # 模型的理由
action         # 模型要求程序做的事
```

`Thought` 的主要用途是让人观察模型为什么作出这个决定；`Action` 才是 Python 接下来要执行的指令。

顺带一提：你贴的这版 `run()` 中，`thought` 被解析出来了，但没有保存或打印；因此它对后续流程实际上没有作用。更完整的写法常会加上：

```
self.current_history.append(f"Thought: {thought}")
```

这样下一轮模型也能看到自己上一轮的推理过程。

---

### 4. 判断是否已经完成

```
if action and action.startswith("Finish"):
    final_answer = self._parse_action_input(action)
    ...
    return final_answer
```

如果模型已经拿到足够信息，就会输出：

```
Thought: 已经从搜索结果获得天气信息。
Action: Finish[北京今天晴，最高温 20°C。]
```

Python 此时不需要调用工具，而是从 `Finish[...]` 中取出最终回答并 `return` 给用户。循环结束。

---

### 5. 如果没完成，就执行工具

模型若输出：

```
Action: search[北京今天天气]
```

代码会拆解它：

```
tool_name, tool_input = self._parse_action(action)
```

得到：

```
tool_name = "search"
tool_input = "北京今天天气"
```

接着执行真实工具：

```
observation = self.tool_registry.execute_tool(tool_name, tool_input)
```

假设搜索工具返回：

```
北京今日晴，最高温 20°C，最低温 9°C。
```

这就是 **Observation（观察结果）**：不是 LLM 自己猜的，而是外部工具执行后返回给它的新信息。

然后存入历史：

```
self.current_history.append(f"Action: {action}")
self.current_history.append(f"Observation: {observation}")
```

下一轮的提示词就会包含：

```
Action: search[北京今天天气]
Observation: 北京今日晴，最高温 20°C，最低温 9°C。
```

模型第二轮看到这个结果后，通常会输出：

```
Thought: 已经获得天气信息，可以回答用户。
Action: Finish[北京今天晴，最高温 20°C，最低温 9°C。]
```

于是流程结束。

---

因此，三个概念的分工是：

|名称|谁产生|含义|
|---|---|---|
|Thought|LLM|“我为什么要这样做”|
|Action|LLM|“程序接下来请做什么”|
|Observation|工具/程序|“工具实际执行后得到什么”|

而 `run()` 就是反复执行这个规则：**让 LLM 决策 → 程序执行 → 把真实结果反馈给 LLM**。