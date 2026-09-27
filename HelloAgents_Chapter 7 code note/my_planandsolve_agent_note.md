
import ast

DEFAULT_PLANNER_PROMPT = """
你是一个顶级的AI规划专家。你的任务是将用户提出的复杂问题分解成一个由多个简单步骤组成的行动计划。
请确保计划中的每个步骤都是一个独立的、可执行的子任务，并且严格按照逻辑顺序排列。
你的输出必须是一个Python列表，其中每个元素都是一个描述子任务的字符串。

问题: {question}

请严格按照以下格式输出你的计划:
```python
["步骤1", "步骤2", "步骤3", ...]
```
"""

# 默认执行器提示词模板
DEFAULT_EXECUTOR_PROMPT = """
你是一位顶级的AI执行专家。你的任务是严格按照给定的计划，一步步地解决问题。
你将收到原始问题、完整的计划、以及到目前为止已经完成的步骤和结果。
请你专注于解决"当前步骤"，并仅输出该步骤的最终答案，不要输出任何额外的解释或对话。

# 原始问题:
{question}

# 完整计划:
{plan}

# 历史步骤与结果:
{history}

# 当前步骤:
{current_step}

请仅输出针对"当前步骤"的回答:
"""



from hello_agents import PlanAndSolveAgent, HelloAgentsLLM, Config, Message, ToolRegistry

from typing import List, Dict, Any, Optional



class Planner:
    def __init__(self,llm_client: HelloAgentsLLM,prompt_template: Optional[str] = DEFAULT_PLANNER_PROMPT):
        self.llm_client = llm_client
        self.prompt_template = DEFAULT_PLANNER_PROMPT

    """和reflection一个逻辑，先用format把question放入prompt，然后再用invoke方法调用"""
    def plan(self,question:str, **kwargs) -> List[str]:
        """
          生成执行计划

          Args:
              question: 要解决的问题
              **kwargs: LLM调用参数

          Returns:
              步骤列表
          """

        plan_text = self.prompt_template.format(question=question)
        messages = [{"role": "user", "content": plan_text}]
        print("--- 正在生成计划 ---")
        plan_result = self.llm_client.invoke(messages, **kwargs)
        print("--- 计划已生成 ---")

        try:
            """用try-catch方法做错误处理，因为提示词里已经要求```python["步骤1", "步骤2", "步骤3", ...]  
            的输出格式，所以用split("```python")以```python为分隔切开，得到：
            [
                "\n计划如下：\n\n",
                '\n["搜索相关资料", "整理重点", "生成答案"]\n```\n'
            ]
            
            取 [1]，就是取 Python 代码块开始标记后面的内容：
            '\n["搜索相关资料", "整理重点", "生成答案"]\n```\n'
            
            接着：
                .split("```")[0]
                再按结束标记 ``` 切开，只取前半段：
                '\n["搜索相关资料", "整理重点", "生成答案"]\n'
            最后：
                .strip()
                去掉首尾空白和换行，最终：
                plan_str = '["搜索相关资料", "整理重点", "生成答案"]'
                
            注意：
                此时 plan_str 仍然只是一个字符串。
                plan = ast.literal_eval(plan_str)
                把“长得像 Python 列表的字符串”转换为真实列表：
                plan = ["搜索相关资料", "整理重点", "生成答案"]   
            
            return plan if isinstance(plan, list) else [] 确认解析结果真的是列表：
                - 是列表：返回 plan；
                - 不是列表：返回空列表 []。
            """
            plan_str = plan_result.split("```python")[1].split("```")[0].strip()
            plan = ast.literal_eval(plan_str)
            return plan if isinstance(plan, list) else []

            """
            异常处理
                IndexError：LLM 没输出 ```python，所以 [1] 不存在；
                SyntaxError：代码块里的内容不是合法 Python 列表；
                ValueError：内容无法转换为字面量。
            """

        except (ValueError, SyntaxError, IndexError) as e:
            print(f"❌ 解析计划时出错: {e}")
            print(f"原始响应: {plan_result}")
            return []
        except Exception as e:
            print(f"❌ 解析计划时发生未知错误: {e}")
            return []

class Executor:
    def __init__(self,llm_client: HelloAgentsLLM,prompt_template: Optional[str] = DEFAULT_EXECUTOR_PROMPT):
        self.llm_client = llm_client
        self.prompt_template = prompt_template if prompt_template else DEFAULT_EXECUTOR_PROMPT
    """和planner一个逻辑，先用format把# 原始问题:{question} # 完整计划:{plan} # 历史步骤与结果:{history} # 当前步骤:{current_step}放入prompt，然后再用invoke方法调用"""
    def execute(self,question: str, plan: List[str], **kwargs) -> str:
        """
        按计划执行任务

        Args:
            question: 原始问题
            plan: 执行计划
            **kwargs: LLM调用参数

        Returns:
            最终答案
        """
        history = ""
        final_answer = ""

        print("\n--- 正在执行计划 ---")

        """enumerate :Python 的内置函数，遍历序列时，同时给每个元素配上编号。"""
        """len(plan) = plan.length(java)"""

        for i, step in enumerate(plan, 1):
            print(f"\n-> 正在执行步骤 {i}/{len(plan)}: {step}")
            """把所有东西放入prompt"""
            prompt = self.prompt_template.format(
                question=question,
                plan=plan,
                history=history if history else "无",
                current_step=step
            )
            messages = [{"role": "user", "content": prompt}]
            response_text = self.llm_client.invoke(messages, **kwargs) or ""
            """添加history方便后续循环"""
            history += f"步骤 {i}: {step}\n结果: {response_text}\n\n"
            final_answer = response_text
            print(f"✅ 步骤 {i} 已完成，结果: {final_answer}")
        return final_answer





class MyPlanAndSolveAgent(PlanAndSolveAgent):
    def __init__(
            self,
            name: str,
            llm: HelloAgentsLLM,
            system_prompt: Optional[str] = None,
            config: Optional[Config] = None,
            custom_prompts: Optional[Dict[str, str]] = None
    ):
        """
        初始化PlanAndSolveAgent

        Args:
            name: Agent名称
            llm: LLM实例
            system_prompt: 系统提示词
            config: 配置对象
            custom_prompts: 自定义提示词模板 {"planner": "", "executor": ""}
        """
        super().__init__(name, llm, system_prompt, config)
        # 设置提示词模板：用户自定义优先，否则使用默认模板
        if custom_prompts:
            planner_prompt = custom_prompts.get("planner")
            executor_prompt = custom_prompts.get("executor")
        else:
            planner_prompt = None
            executor_prompt = None

        self.planner = Planner(self.llm, planner_prompt)
        self.executor = Executor(self.llm, executor_prompt)

        def run(self,input_text: str,plan,**kwargs) -> str:
            """
                运行Plan and Solve Agent

                Args:
                    input_text: 要解决的问题
                    **kwargs: 其他参数

                Returns:
                    最终答案
                """
            print(f"\n{self.name}开始处理问题{input_text}")

            """1,生成计划"""

            plan_text = self.planner.plan(input_text, **kwargs)
            if not plan_text:
                final_answer = "无法生成有效的行动计划，任务终止。"
                print(f"\n--- 任务终止 ---\n{final_answer}")
                self.add_message(Message(input_text, "user"))
                self.add_message(Message(final_answer, "assistant"))
                return final_answer

            """2.执行计划"""

            final_answer = self.executor.execute(input_text,plan,**kwargs)
            print(f"\n--- 任务完成 ---\n最终答案: {final_answer}")
            self.add_message(Message(input_text, "user"))
            self.add_message(Message(final_answer, "assistant"))
            return final_answer

```
