```python
# 1. 初始执行  
print("\n--- 正在进行初始尝试 ---")  
initial_prompt = self.prompts["initial"].format(task=input_text)  
initial_result = self._get_llm_response(initial_prompt, **kwargs)  
self.memory.add_record("execution", initial_result)

```

第一段意思是用字典方式把promot 里面"initial"的部分提出来
然后作为input调用大模型等待回复，再作为执行（"execution"）的部分加入memory供后面查看

```python

# 2. 迭代循环：反思与优化  
for i in range(self.max_iterations):  
    print(f"\n--- 第 {i+1}/{self.max_iterations} 轮迭代 ---")  
  
    # a. 反思  
    print("\n-> 正在进行反思...")  
    last_result = self.memory.get_last_execution()  
    reflect_prompt = self.prompts["reflect"].format(  
        task=input_text,  
        content=last_result  
    )  
    feedback = self._get_llm_response(reflect_prompt, **kwargs)  
    self.memory.add_record("reflection", feedback)  
  
    # b. 检查是否需要停止  
    if "无需改进" in feedback or "no need for improvement" in feedback.lower():  
        print("\n✅ 反思认为结果已无需改进，任务完成。")  
        break  
  
    # c. 优化  
    print("\n-> 正在进行优化...")  
    refine_prompt = self.prompts["refine"].format(  
        task=input_text,  
        last_attempt=last_result,  
        feedback=feedback  
    )  
    refined_result = self._get_llm_response(refine_prompt, **kwargs)  
    self.memory.add_record("execution", refined_result)  
  
final_result = self.memory.get_last_execution()  
print(f"\n--- 任务完成 ---\n最终结果:\n{final_result}")


```

第二部分是reflection 循环的部分
外面套一个大for用来保障不会超出最大步数，内使用print i+1来展示到底是第几轮迭代

反思part：将目前的最近一次execution取出，用format字典方法，提取prompt中对于reflection当要求，task为input_text，content为最近一次的execution，组成reflection prompt的全部。
将reflection prompt投入，得到feedback，并将其一并加入memory。

判断feedback里面是否有“无需改进”或者“no need for improvement”，使用.lower()避免大小写问题。如果里面有这种字样，直接掐停。

如果没有，进入优化阶段。将"refine"的提示词从prompt中取出，使用format插入input_text，上一次的execution结果，feedback，并且将refine prompt投入llm得到结果，将其加入execution部分。

for结束后，将最后一次execution结果作为final_result，print出来
（remind：{}表达式是f- string的写法，使用时要在双引号外的开头加一个f）


```python

self.add_message(Message(input_text, "user"))  
self.add_message(Message(final_result, "assistant"))  
  
return final_result

```

保存 input 和final_result 到message内并返回