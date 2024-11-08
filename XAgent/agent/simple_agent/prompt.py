# CONSTRAINTS:
# 1. ~4000 word limit for short term memory. Your short term memory is short, so immediately save important information to files.
# 2. If you are unsure how you previously did something or want to recall past events, thinking about similar events will help you remember.
# 3. No user assistance
# 4. Exclusively use the commands listed in double quotes e.g. "command name"

# RESOURCES:
# 1. Internet access for searches and information gathering.
# 2. Long Term memory management.
# 3. GPT-3.5 powered Agents for delegation of simple tasks.
# 4. File output.


SYSTEM_PROMPT_old = """
A question is divided into many steps, and you will complete one of them. Please provide a clear and step-by-step solution for a scientific problem in the categories of Chemistry, Physics, or Mathematics. The problem will specify the unit of measurement, which should be included in the answer.

--- Plan Overview ---
The query has already been splited into a tree based plan as follows: 
{{all_plan}}
You have already performed some of the subtasks.
"""


SYSTEM_PROMPT = """
A question is divided into many steps, and you will complete one of them. Please provide a clear and step-by-step solution for a scientific problem in the categories of Chemistry, Physics, or Mathematics. The problem will specify the unit of measurement, which should be included in the answer.

For each instance, you need to three things. Firstly, for "formulae retrieval", you need to identify the formulae explicitly and implicitly entailed in the problem context. Then there is a "reasoning/calculation process" where you are required to reason step by step based on the identified formulae and problem context. Finally, conclude the answer. For each problem, the output format should incorporate the following components in the corresponding format:

**Formulae retrieval: **
[Formula 1] (the formula required to solve the problem)
[Formula 2] (the second formula required to solve the problem, if any)
...
[Formula n] (the n-th formula required to solve the problem, if any)

**Reasoning/calculation process:**
[step 1] (the first step for solving this problem)
.....
[step n] (the n-th step for solving the problem, if any)

**Answer conclusion:**
[answer]: ```{PYTHON CODE}``` 


You have been solving a complex task by following a given plan listed below.
--- Plan Overview ---
The complex task has already been splited into a tree based plan as follows: 
{{all_plan}}
You have already performed some of the subtasks.
"""


USER_PROMPT = """
Now, you continue to complete subtasks.Please combine the results of previous tasks to complete the current goal of processing subtasks. Please complete all milestones and give a concise answer that can be efficiently used by subsequent subtasks.
--- Status ---
Current Subtask: {{subtask_id}}
The query: {{subtask_goal}}
Milestones: {{milestones}}
{{additional_prompt}}

Please respond strictly to the format provided. For each instance, you need to three things. 
Firstly, for "formulae retrieval", you need to identify the formulae explicitly and implicitly entailed in the problem context. 
Then there is a "reasoning/calculation process" where you are required to reason step by step based on the identified formulae and problem context, you MUST use 
Finally, conclude the answer by writing a piece of corresponding python code, you MUST use the International System of Units in this stage. 
For each problem, the output format should incorporate the following components in the corresponding format:
**Formulae retrieval: **
[Formula 1] (the formula required to solve the problem)
[Formula 2] (the second formula required to solve the problem, if any)
...
[Formula n] (the n-th formula required to solve the problem, if any)

**Reasoning/calculation process:**
[step 1] (the first step for solving this problem)
.....
[step n] (the n-th step for solving the problem, if any)

**Answer conclusion:**
{{tool_prompt}}

--- Similar tasks ---
The following are the trajectories of tasks that have been dealt with in the past that are similar to this goal, including the successful tasks and their action lists. You can learn form them and use relevant knowledge in their procedure.
{{success_prompt}}

"""


USER_SINGLE_PROMPT = """
Now, solve this problem:
{{query}}

Please respond strictly to the format provided. For each instance, you need to three things. 
Firstly, for "formulae retrieval", you need to identify the formulae explicitly and implicitly entailed in the problem context. 
Then there is a "reasoning/calculation process" where you are required to reason step by step based on the identified formulae and problem context, you MUST use 
Finally, conclude the answer by writing a piece of corresponding python code, you MUST use the International System of Units in this stage. 
For each problem, the output format should incorporate the following components in the corresponding format:
**Formulae retrieval: **
[Formula 1] (the formula required to solve the problem)
[Formula 2] (the second formula required to solve the problem, if any)
...
[Formula n] (the n-th formula required to solve the problem, if any)

**Reasoning/calculation process:**
[step 1] (the first step for solving this problem)
.....
[step n] (the n-th step for solving the problem, if any)

**Answer conclusion:**
[answer]: ```{PYTHON CODE}```


Your answer should be a piece of python code which solves the current question.
Encase your code within triple backticks for clarity.
You must end your code with printing all the result and their units.
Make sure the code can be successfully run without any input.
Be precise.The answer should be accurate, choose the appropriate units, and PROHIBIT the use of round functions to round off and lose the results.
you MUST use the International System of Units in this stage, for example, convert all the volume to {m^3}, and convert pressure to {N/(m^2)}, which is {Pa}.
Make sure the code can be successfully run without any input. And import all the modules that you need to use.

for example, you could response Answer conclusion part like this:
**Answer conclusion:**
[answer]: ```python
import numpy as np

# Value of 2 pi c omega_obs
omega_obs = 1.8133708490380042e+23  # Hz

# Value of D for H35Cl
D = 440.2  # kJ/mol

# Calculate beta
beta = omega_obs * (2 * D)**0.5

# Convert the answer to SI unit
beta = beta * 100 # Convert {cm^(-1)} to {m^(-1)}

# Print the exact result and avoid using round function or format like ".4f"
print("The value of beta is:", beta, "m^(-1)")
```

--- Similar tasks ---
The following are the trajectories of tasks that have been dealt with in the past that are similar to this goal, including the successful tasks and their action lists. You can learn form them and use relevant knowledge in their procedure.
{{success_prompt}}
"""


def get_examples_for_dispatcher():
    """The example that will be given to the dispatcher to generate the prompt

    Returns:
        example_input: the user query or the task
        example_system_prompt: the system prompt
        example_user_prompt: the user prompt
    """
    # example_input = """{\n  "name": "Finding Feasible Examples",\n  "goal": "Find 10 examples that can reach the target number 24 in the 24-points game.",\n  "handler": "subtask 1",\n  "tool_budget": 50,\n  "prior_plan_criticsim": "It may be difficult to come up with examples that are all feasible.",\n  "milestones": [\n    "Identifying appropriate combination of numbers",\n    "Applying mathematical operations",\n    "Verifying the result equals to target number",\n    "Recording feasible examples"\n  ],\n  "expected_tools": [\n    {\n      "tool_name": "analyze_code",\n      "reason": "To ensure all feasible examples meet the rules of the 24-points game"\n    }\n  ],\n  "exceute_status": "TODO"\n}"""
    # TODO
    example_input = ""
    example_system_prompt = SYSTEM_PROMPT
    example_user_prompt = USER_PROMPT
    return example_input, example_system_prompt, example_user_prompt


def get_examples_for_dispatcher_d():
    """The example that will be given to the dispatcher to generate the prompt

    Returns:
        example_input: the user query or the task
        example_system_prompt: the system prompt
        example_user_prompt: the user prompt
    """
    # example_input = """{\n  "name": "Finding Feasible Examples",\n  "goal": "Find 10 examples that can reach the target number 24 in the 24-points game.",\n  "handler": "subtask 1",\n  "tool_budget": 50,\n  "prior_plan_criticsim": "It may be difficult to come up with examples that are all feasible.",\n  "milestones": [\n    "Identifying appropriate combination of numbers",\n    "Applying mathematical operations",\n    "Verifying the result equals to target number",\n    "Recording feasible examples"\n  ],\n  "expected_tools": [\n    {\n      "tool_name": "analyze_code",\n      "reason": "To ensure all feasible examples meet the rules of the 24-points game"\n    }\n  ],\n  "exceute_status": "TODO"\n}"""
    # TODO
    example_input = ""
    example_system_prompt = SYSTEM_PROMPT
    example_user_prompt = USER_SINGLE_PROMPT
    return example_input, example_system_prompt, example_user_prompt
