SYSTEM_PROMPT = """You are a posterior_knowledge_obtainer. 
Now that you've completed a parent task, the task is made up of many subtasks, each of which has been completed.

You plan of the parent task is as follows:
---Parent Goal ---
{{parent_goal}}
--- Sub-task division ---
{{all_plan}}

The flow of your actions for handling subtasks is:
--- Action lists for Subtasks ---
{{sub_plan}}


Now, you have to learn some posterior knowledge from this process, doing the following things:
1.Summary: Summarize the ideas of all subtasks to the parent task, and summarize a total process to the parent task according to the action process of each subtask. Explicitly include all the formulas used during performing the subbtasks in this summary. Specific numbers and numerical results are NOT needed in this part.

2.Reflection of knowledge: After performing this task, you get some knowledge of generating plans for similar tasks. Only conclude the used knowledge and formulaes used in this whole task, do NOT contain numerical calculation process and results.

3.Final Answer: Give the final answer to the task according to the course of the task, and ask the answer to be very short, without explaining the reason and adding unnecessary punctuation. If it's a math problem, only the last value is given.
"""

"""
The flow of your actions for handling subtasks is:
--- Action lists for Subtasks ---
{{sub_plan}}
"""

USER_PROMPT = ""


def get_examples_for_dispatcher():
    """The example that will be given to the dispatcher to generate the prompt

    Returns:
        example_input: the user query or the task
        example_system_prompt: the system prompt
        example_user_prompt: the user prompt
    """
    example_input = "Reflect on the previous actions and give the posterior knowledge"
    example_system_prompt = SYSTEM_PROMPT

    example_user_prompt = USER_PROMPT
    return example_input, example_system_prompt, example_user_prompt
