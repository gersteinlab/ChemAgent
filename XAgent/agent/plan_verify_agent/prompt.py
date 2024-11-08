SYSTEM_PROMPT = """You're an expert professor who is very proficient in chemistry, and now you want to check whether a step of a chemistry problem has gone wrong.

This chemistry question is: {{question}}

We broke down this chemistry problem into a number of steps to solve, each of which was a subtask. The split is as follows:
{{all_plan}}

"""
USER_PROMPT = """The subtasks you need to complete are:
{{subplan}}

The reasoning and answer you receive are:
[Response START]
{{response}}
[Response END]

Check your response very carefully. Please check whether the subtask has completed all the milestones of the subtask, whether the answers given are the objectives of the task, whether the constants involved in the reasoning process are correct, whether there are logical errors, whether the unit conversion is correct and whether there are calculation errors, Whether there is an error in the formula. 

You should give me back the **Formulae retrieval:** , **Reasoning/calculation process:** and **Answer conclusion:**  refined according to the original response, if you think there is nothing needed to be changed, just output the original **Formulae retrieval:** , **Reasoning/calculation process:** and **Answer conclusion:**.
Your answer should strictly follow the format below. 
**Refined Formulae retrieval:**

**Refined Reasoning/calculation process:** 

**Refined Answer conclusion:** 
[answer]: ```{Refined PYTHON CODE}``` 


"""






def get_examples_for_dispatcher():
    """The example that will be given to the dispatcher to generate the prompt

    Returns:
        example_input: the user query or the task
        example_system_prompt: the system prompt
        example_user_prompt: the user prompt
    """
    example_input = ""
    example_system_prompt = SYSTEM_PROMPT
    example_user_prompt = USER_PROMPT
    return example_input, example_system_prompt, example_user_prompt
