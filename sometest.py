import run
import json
import json5
import jsonschema
from typing import List
from colorama import Fore
from tenacity import retry, stop_after_attempt

import argparse
from XAgent.agent.base_agent import BaseAgent
from XAgent.utils import RequiredAbilities
from XAgent.message_history import Message
from XAgent.logs import logger
from XAgent.data_structure.node import ToolNode
from XAgent.ai_functions import function_manager, objgenerator
from XAgent.config import CONFIG

SPLIT_PROMPT_SYS = """
You are ChatGPT, a large language model trained by OpenAI, also an excellent prompt evaluator, who is capable of splitting tasks and evaluating the difficulty of tasks which will be solved by other autonomous agents powered by LLM.
"""

SPLIT_PROMPT = """
Now, I have a target task and its solution here: 
task: {{task}}
solution: {{solution}}

And I also have a python environment where agents can write code. (It is also okay not to use them and just use your own knowledge):

Then, split or separate the sentence of the original task to two parts, one is conditions and another is questions.

Below is the format you should follow when you give the answer:

`
CONDITIONS: 

QUESTIONS:

`

"""

SPLIT_PROMPT_2 = """
Now, I have a target task here: 
task: {{task}}

Then, split or separate the sentence of the original task to two parts, one is conditions and another is questions.
All the specified numerical data should be included by the conditions part, instead of the question part.

Below is the format you should follow when you give the answer:

`
CONDITIONS: 

QUESTIONS:

`

"""

REFLECT_PROMPT_SYS = """
You are ChatGPT, a large language model trained by OpenAI, also an excellent answer checker, who is really capable of figuring out whether some conditions and questions separated from the original task are complete and correct.
"""
# The refined question should be independent with each other and totally complete, which means, by using each condition, the question can be solved.
REFLECT_PROMPT = """
Now, I have a task and its corresponding conditions and questions listed below. I need your help to check whether the conditions and questions are correct and exactly fit the original task.

{{tasks}}
{{conditions}}
{{questions}}

You should give me back the conditions and questions refined according to the original task, if you think there is nothing needed to be changed, just output the original conditions and questions.

You do NOT need to give the solutions.

All the specified numerical data should be included by the conditions part, instead of the question part.

Also, the questions should NOT contain something that is not given in the condition.

Your answer should strictly follow the format below. 

`
I think the given conditions and questions fit the original task well / not well. Because ...

REFINED_CONDITIONS:

REFINED_QUESTIONS:

`

"""

SUB_PROMPT_SYS = """
You are an excellent expert who thinks step by step and splits a complex question into several steps.
"""

SUB_PROMPT = """
Given a task's background and its condition:
{{condition}}

Now the question is:
{{question}}

And here is the given solution of this question:
{{solution}}

Please think generally and step by step to divide the question into `N` subtasks according to the given solution.
You must give each task a clear description and every subtask must be designed as a necessary step to the final question.
You should strictly follow the format below:

`
I think the best way to solve the question and my solution is: ...

So I set up subtasks as described below.
TASKS=>
<st> SUBTASK 1: ... <ed>
<st> SUBTASK 2: ... <ed>
...
<st> SUBTASK `N`: ... <ed>
`

"""

SUB_SOL_PROMPT_SYS = """
You are an excellent expert who can think step by step and split a given complex solution of a certain question into several sub-steps according to the given subtasks which is splitted from the original question.
"""

SUB_SOL_PROMPT = """
Given a task's background and its condition:
{{condition}}

Now the question is:
{{question}}

And I have already split the question into the subtasks listed below:
{{subtask}}

And the whole solution to the original whole question is:
{{solution}}

Now, Please think generally and step by step to divide the solution into sub-solutions, which must correspond one-to-one with subtasks. 
You must give each sub-solution a clear description and every sub-solution should be specific and exactly solve the corresponding subtask. 

For example, if there are `N` subtasks, you must generate `N` sub-solutions. And sub-solution 1 should exactly solve subtask 1.

You must generate sub-solutions according to the whole solution given.
If the whole solution is "Not provided", just generate your own suggested solution for each subtask.
Else if the whole solution is provided, your every sub-solution should be a part of the whole solution.
You should strictly follow the format below:

`
I think the relations between subtasks and the whole solution are: ...

So I set up sub-solutions as described below.
SOLUTIONS=>
<st> SUBSOLUTION 1: ... <ed> <st> SUBSOLUTION 2: ... <ed> <st> SUBSOLUTION `N`: ... <ed>
`

"""

SORT_PROMPT_SYS = """
You are ChatGPT, a large language model trained by OpenAI, also an excellent prompt difficulty evaluator, who is capable of sorting a series of tasks according to their difficulty.
"""

SORT_PROMPT = """
Now, I have some tasks (each containing conditions, questions and corresponding solutions) listed below. I need your help to sort these tasks from the easiest one to the most difficult one for an agent to solve, which means you need to put the simpler subtasks in front.
{{tasks}} 

Think carefully and tell me the reason why you think one is easier and another is harder.

You do Not take the temporal relationship into consideration when sorting.

You do NOT need to refine the given solutions.

You do NOT need to follow the origin order of the tasks.

You are FORBIDDEN from changing the description of the tasks given. Just change their order.

Your answer should be a permutation of the `n` tasks. And the id of easier tasks should be placed in front of the harder ones.
For example, if there are 3 tasks, and task 2 is the simplest, task 3 is the hardest.
Then your final output should be "RESULT=>
<st> 2 1 3 <ed>"

Please strictly follow the format below. 
`
I think the difficulty relationship between the tasks are: ...
SO MY ANSWER IS:
RESULT=>
<st> [a permutation] <ed>
`

If there is just 1 subtask, just list it, follow this format:

`
SO MY ANSWER IS:
RESULT=>
<st> 1 <ed>
`

"""


class EnvAgent(BaseAgent):

    abilities = set([])

    def parse(
        self,
        placeholders: dict = {},
        arguments: dict = None,
        functions=None,
        function_call=None,
        stop=None,
        additional_messages: List[Message] = [],
        *args,
        **kwargs,
    ):
        """
        The function is used to parse various arguments and call the generate function with these parsed arguments.

        Args:
            placeholders (dict, optional): Placeholders for the agent's responses.
            arguments(dict, optional): Argument to influence the response of the agent.
            functions (functions, optional): Functions to guide the agent's response.
            function_call (FunctionType, optional): Function called to generate agent's response.
            stop (bool, optional): Flag to stop the induction of the response.
            additional_messages (list, optional): Additional messages to be included in the response.

        Returns:
            object: Response generated by the agent.

        """
        logger.typewriter_log(f"debug:  ", Fore.BLUE, "parsing")
        prompt_messages = self.fill_in_placeholders(placeholders)
        messages = prompt_messages

        # for i in messages:
        #     logger.typewriter_log(f"debug:  ", Fore.BLUE, str(i.raw()))

        if isinstance(messages[0], Message):
            messages = [message.raw() for message in messages]

        logger.typewriter_log(f"debug :  ", Fore.BLUE, "reaching for response.........")
        response = objgenerator.chatcompletion(
            messages=messages,
            functions=functions,
            function_call=function_call,
            stop=stop,
            *args,
            **kwargs,
        )

        # logger.typewriter_log(f"debug response GET!:  ", Fore.BLUE, response)

        return response["choices"][0]["message"]["content"], response["usage"]


def parse_args() -> argparse.Namespace:
    """
    Parse the command line arguments and return them as an argparse.Namespace object.

    Returns:
        argparse.Namespace: An object containing command line arguments and their values.
    """
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--wholetask", type=str, required=True, help="The whole task description."
    )
    parser.add_argument(
        "--wholesolution",
        type=str,
        default="Not provided.",
        help="The whole task solution.",
    )
    return parser.parse_args()


def split_query(q):
    prompt_messages = [
        Message(role="system", content=SPLIT_PROMPT_SYS),
        Message(role="user", content=SPLIT_PROMPT_2),
        Message(role="system", content=REFLECT_PROMPT_SYS),
        Message(role="user", content=REFLECT_PROMPT),
    ]
    max_attempts = 10
    attempts = 0
    success = False
    cond = ""
    ques = ""
    while not success and attempts < max_attempts:
        try:
            agent = EnvAgent(CONFIG, [prompt_messages[0], prompt_messages[1]])
            logger.typewriter_log(f"begin parsing...  ", Fore.YELLOW, "AH?")
            new_message, _ = agent.parse(
                placeholders={
                    "user": {
                        "task": q,
                    }
                },
                schema_validation=False,
            )
            # logger.typewriter_log(f"whole_task:  ", Fore.YELLOW, args.wholetask)
            # logger.typewriter_log(f"GPT35:  ", Fore.YELLOW, new_message)

            agent = EnvAgent(CONFIG, [prompt_messages[2], prompt_messages[3]])
            new_message_conditions = new_message.split("CONDITIONS:")[1].split(
                "QUESTIONS:"
            )[0]
            new_message_questions = new_message.split("QUESTIONS:")[1]

            final_message, _ = agent.parse(
                placeholders={
                    "user": {
                        "tasks": q,
                        "conditions": new_message_conditions,
                        "questions": new_message_questions,
                    }
                },
                schema_validation=False,
            )
            # logger.typewriter_log(f"GPT35-2:  ", Fore.YELLOW, final_message)

            cond = final_message.split("REFINED_CONDITIONS:")[1].split(
                "REFINED_QUESTIONS:"
            )[0]
            ques = final_message.split("REFINED_QUESTIONS:")[1]
            logger.typewriter_log(f"condition:  ", Fore.YELLOW, cond)
            logger.typewriter_log(f"question:  ", Fore.YELLOW, ques)
            success = 1
        except Exception as e:
            print(f"Attempt {attempts + 1}: An error occurred: {e}. Retrying...")
            attempts += 1
    return cond, ques


def env(args=None, whole_task=None, whole_solution=None):
    if args != None:
        if whole_task != None:
            args.wholetask = whole_task
        if whole_solution != None:
            args.wholesolution = whole_solution
    else:
        args = argparse.Namespace()
        args.wholetask = whole_task
        args.wholesolution = whole_solution
    prompt_messages = [
        Message(role="system", content=SPLIT_PROMPT_SYS),
        Message(role="user", content=SPLIT_PROMPT),
        Message(role="system", content=REFLECT_PROMPT_SYS),
        Message(role="user", content=REFLECT_PROMPT),
        Message(role="system", content=SUB_PROMPT_SYS),
        Message(role="user", content=SUB_PROMPT),
        Message(role="system", content=SUB_SOL_PROMPT_SYS),
        Message(role="user", content=SUB_SOL_PROMPT),
        Message(role="system", content=SORT_PROMPT_SYS),
        Message(role="user", content=SORT_PROMPT),
    ]
    max_attempts = 10
    attempts = 0
    success = False
    final_output_tasks = []
    cond = ""
    ques = ""
    subtasks = ""
    while not success and attempts < max_attempts:
        try:
            agent = EnvAgent(CONFIG, [prompt_messages[0], prompt_messages[1]])
            logger.typewriter_log(f"begin parsing...  ", Fore.YELLOW, "AH?")
            new_message, _ = agent.parse(
                placeholders={
                    "user": {
                        "task": args.wholetask,
                        "solution": args.wholesolution,
                    }
                },
                schema_validation=False,
            )
            # logger.typewriter_log(f"whole_task:  ", Fore.YELLOW, args.wholetask)
            # logger.typewriter_log(f"GPT35:  ", Fore.YELLOW, new_message)

            agent = EnvAgent(CONFIG, [prompt_messages[2], prompt_messages[3]])
            new_message_conditions = new_message.split("CONDITIONS:")[1].split(
                "QUESTIONS:"
            )[0]
            new_message_questions = new_message.split("QUESTIONS:")[1]

            final_message, _ = agent.parse(
                placeholders={
                    "user": {
                        "tasks": args.wholetask,
                        "conditions": new_message_conditions,
                        "questions": new_message_questions,
                    }
                },
                schema_validation=False,
            )
            # logger.typewriter_log(f"GPT35-2:  ", Fore.YELLOW, final_message)

            cond = final_message.split("REFINED_CONDITIONS:")[1].split(
                "REFINED_QUESTIONS:"
            )[0]
            ques = final_message.split("REFINED_QUESTIONS:")[1]

            agent = EnvAgent(CONFIG, [prompt_messages[4], prompt_messages[5]])
            final_tasks, _ = agent.parse(
                placeholders={
                    "user": {
                        "condition": cond,
                        "question": ques,
                        "solution": args.wholesolution,
                    }
                },
                schema_validation=False,
            )
            count_sub = final_tasks.count("<ed>")

            subtasks = final_tasks.split("=>")[1]
            logger.typewriter_log(f"GPT35-3:  ", Fore.YELLOW, subtasks)

            assert "=>" in final_tasks, "No task or solution tag"
            assert (
                "<st>" in final_tasks and "<ed>" in final_tasks
            ), "Sorter agent didn't follow <st>...<ed> format"
            assert (
                count_sub == len(final_tasks.split("<st>")) - 1
            ), "number of <st> doesn't match the amount of subtasks"

            for i in range(len(final_tasks.split("<st>")) - 1):
                final_output_tasks.append(final_tasks.split("<ed>")[i].split(":")[-1])

            assert "" not in final_output_tasks[0].split(
                "..."
            ), "Failed to generate plan"

            for i in range(len(final_tasks.split("<st>")) - 1):
                final_output_tasks[i] = (
                    "CONDITIONS: " + cond + "\n" + "QUESTION: " + final_output_tasks[i]
                )

            success = True

        except AssertionError as e:
            print(f"AssertionError on attempt {attempts + 1}: {e}. Retrying...")
            attempts += 1
        except Exception as e:
            print(f"Attempt {attempts + 1}: An error occurred: {e}. Retrying...")
            attempts += 1

    if not success:
        return ["FAILED BEFORE THE SOLUTION SPLITTING STAGE! "]

    max_attempts = 10
    attempts = 0
    success = False
    final_output_tasks_sorted = []
    count_sub = 0
    while not success and attempts < max_attempts:
        try:
            agent = EnvAgent(CONFIG, [prompt_messages[6], prompt_messages[7]])
            logger.typewriter_log(f"begin parsing...  ", Fore.YELLOW, "AH?")
            new_message, _ = agent.parse(
                placeholders={
                    "user": {
                        "condition": cond,
                        "question": ques,
                        "subtask": subtasks,
                        "solution": args.wholesolution,
                    }
                },
                schema_validation=False,
            )
            # logger.typewriter_log(f"whole_task:  ", Fore.YELLOW, args.wholetask)
            # logger.typewriter_log(f"GPT35:  ", Fore.YELLOW, new_message)

            count_sub_st = new_message.count("<st>")
            count_sub = new_message.count("SUBSOLUTION")

            assert "=>" in new_message, "No task or solution tag"
            assert (
                "<st>" in new_message and "<ed>" in new_message
            ), "Solution split agent didn't follow <st>...<ed> format"
            assert (
                count_sub == count_sub_st
            ), "number of <st> doesn't match the amount of subsolutions"
            assert (
                count_sub == len(final_tasks.split("<st>")) - 1
            ), "number of sub-solutions not match number of subtasks"

            subsolutions = new_message.split("=>")[1]

            logger.typewriter_log(f"sub-solutions:  ", Fore.RED, subsolutions)

            agent = EnvAgent(CONFIG, [prompt_messages[8], prompt_messages[9]])
            for i in range(len(final_tasks.split("<st>")) - 1):
                final_output_tasks[i] = (
                    "task "
                    + str(i + 1)
                    + ": {"
                    + final_output_tasks[i]
                    + "\nSOLUTION:"
                    + new_message.split("<ed>")[i].split(":")[-1]
                    + "}\n<end-of-a-task>\n"
                )

            final_output_tasks_str = ""
            for i in range(len(final_tasks.split("<st>")) - 1):
                final_output_tasks_str = final_output_tasks_str + final_output_tasks[i]

            final_message, _ = agent.parse(
                placeholders={
                    "user": {
                        "tasks": final_output_tasks_str,
                    }
                },
                schema_validation=False,
            )
            # logger.typewriter_log(f"GPT35-2:  ", Fore.YELLOW, final_message)

            assert "=>" in final_message, "No result tag"
            task_sorted = final_message.split("=>")[1]
            logger.typewriter_log(f"sorter:  ", Fore.YELLOW, task_sorted)
            task_sorted_tmp_if = task_sorted
            assert (
                "<st>" in task_sorted and "<ed>" in task_sorted
            ), "Sorter agent didn't follow <st>...<ed> format"
            if "<st> " in task_sorted_tmp_if and " <ed>" in task_sorted_tmp_if:
                task_sorted = [
                    int(i) - 1
                    for i in task_sorted.split("<st>")[1]
                    .split("<ed>")[0]
                    .split(" ")[1:-1]
                ]
            if "<st> " not in task_sorted_tmp_if and " <ed>" not in task_sorted_tmp_if:
                task_sorted = [
                    int(i) - 1
                    for i in task_sorted.split("<st>")[1].split("<ed>")[0].split(" ")[:]
                ]
            if "<st> " not in task_sorted_tmp_if and " <ed>" in task_sorted_tmp_if:
                task_sorted = [
                    int(i) - 1
                    for i in task_sorted.split("<st>")[1]
                    .split("<ed>")[0]
                    .split(" ")[:-1]
                ]
            if "<st> " in task_sorted_tmp_if and " <ed>" not in task_sorted_tmp_if:
                task_sorted = [
                    int(i) - 1
                    for i in task_sorted.split("<st>")[1]
                    .split("<ed>")[0]
                    .split(" ")[1:]
                ]
            count_sub = len(task_sorted)

            assert count_sub == len(
                final_output_tasks
            ), "sorter forget or add some tasks"

            for i in range(len(task_sorted)):
                final_output_tasks_sorted.append(
                    final_output_tasks[task_sorted[i]]
                    .split(": {")[1]
                    .split("}\n<end-of-a-task>\n")[0]
                )

            assert "" not in final_output_tasks_sorted[0].split(
                "..."
            ), "Failed to generate plan"
            assert "" not in final_output_tasks_sorted[-1].split(
                "..."
            ), "Failed to generate plan"
            assert "..." not in final_output_tasks_sorted, "Failed to generate plan"

            logger.typewriter_log(
                f"final answer:  ", Fore.RED, final_output_tasks_sorted
            )

            success = True

        except AssertionError as e:
            print(f"AssertionError on attempt {attempts + 1}: {e}. Retrying...")
            attempts += 1
        except Exception as e:
            print(f"Attempt {attempts + 1}: An error occurred: {e}. Retrying...")
            attempts += 1

    if success:
        final_output_tasks_sorted.append(
            "CONDITIONS: "
            + cond
            + "\n"
            + "QUESTION: "
            + ques
            + "\nSOLUTION:"
            + args.wholesolution
        )
        return final_output_tasks_sorted

    return ["FAILED Sort stage"]


if __name__ == "__main__":
    args = parse_args()
    tasks_and_solutions = env(args)
    tasks = []
    sols = []
    for i in range(len(tasks_and_solutions)):
        tasks.append(tasks_and_solutions[i].split("SOLUTION:")[0])
        sols.append(tasks_and_solutions[i].split("SOLUTION:")[1])

    logger.typewriter_log(f"TASKSSSSSSSSSSSSSSSSSSSSSSSSSSSS:  ", Fore.RED, tasks)
    logger.typewriter_log(f"SOLUTIONSSSSSSSSSSSSSSSSSSSSSSSS:  ", Fore.RED, sols)

    final_answers = []

    for i in tasks:
        final_answers.append(run.run(["--task", i]) + "\n")

    logger.typewriter_log(f"final_answers : ", Fore.RED, final_answers)


##############################################################
#  """
#  README:
#
#  Dont use `env.py` to cut tasks and solutions, use this.
#
#  docker exec sometest.py --wholetask ... --wholesolution ...
#
#  MENTION that whole solution is default "not provided", i originally pass it directly in the code, line 431, `w_solution`, you can change it as you want.
#
#  `tasks` is the subtasks, `sols` is the corresponding solutions. Both are list.
#
#  Evalution on the `run.py`'s result is not given.
#
#  """
###############################################################
"""
EXAMPLE=>
original task:
The change in molar internal energy when $\\mathrm{CaCO}_3(\\mathrm{~s})$ as calcite converts to another form, aragonite, is $+0.21 \\mathrm{~kJ} \\mathrm{~mol}^{-1}$. Calculate the difference between the molar enthalpy and internal energy changes when the pressure is 1.0 bar given that the densities of the polymorphs are $2.71 \\mathrm{~g} \\mathrm{~cm}^{-3}$ and $2.93 \\mathrm{~g} \\mathrm{~cm}^{-3}$, respectively.
whole solution:
The change in enthalpy when the transition occurs is\r\n$$\r\n\\begin{aligned}\r\n\\Delta H_{\\mathrm{m}} & =H_{\\mathrm{m}}(\\text { aragonite })-H_{\\mathrm{m}}(\\text { calcite }) \\\\\r\n& =\\left\\{U_{\\mathrm{m}}(\\mathrm{a})+p V_{\\mathrm{m}}(\\mathrm{a})\\right\\}-\\left\\{U_{\\mathrm{m}}(\\mathrm{c})+p V_{\\mathrm{m}}(\\mathrm{c})\\right\\} \\\\\r\n& =\\Delta U_{\\mathrm{m}}+p\\left\\{V_{\\mathrm{m}}(\\mathrm{a})-V_{\\mathrm{m}}(\\mathrm{c})\\right\\}\r\n\\end{aligned}\r\n$$\r\nwhere a denotes aragonite and c calcite. It follows by substituting $V_{\\mathrm{m}}=M / \\rho$ that\r\n$$\r\n\\Delta H_{\\mathrm{m}}-\\Delta U_{\\mathrm{m}}=p M\\left(\\frac{1}{\\rho(\\mathrm{a})}-\\frac{1}{\\rho(\\mathrm{c})}\\right)\r\n$$\r\nSubstitution of the data, using $M=100 \\mathrm{~g} \\mathrm{~mol}^{-1}$, gives\r\n$$\r\n\\begin{aligned}\r\n\\Delta H_{\\mathrm{m}}-\\Delta U_{\\mathrm{m}} & =\\left(1.0 \\times 10^5 \\mathrm{~Pa}\\right) \\times\\left(100 \\mathrm{~g} \\mathrm{~mol}^{-1}\\right) \\times\\left(\\frac{1}{2.93 \\mathrm{~g} \\mathrm{~cm}^{-3}}-\\frac{1}{2.71 \\mathrm{~g} \\mathrm{~cm}^{-3}}\\right) \\\\\r\n& =-2.8 \\times 10^5 \\mathrm{~Pa} \\mathrm{~cm}{ }^3 \\mathrm{~mol}^{-1}=-0.28 \\mathrm{~Pa} \\mathrm{~m}^3 \\mathrm{~mol}^{-1}\r\n\\end{aligned}\r\n$$

DIVIDED:
Calculate the change in molar enthalpy, $\Delta H_{\mathrm{m}}$, when the transition occurs. 
SOLUTION: $\Delta H_{\mathrm{m}}=H_{\mathrm{m}}(\text { aragonite })-H_{\mathrm{m}}(\text { calcite })$. 

Substitute the given values and calculate the difference between $\Delta H_{\mathrm{m}}$ and $\Delta U_{\mathrm{m}}$. 
SOLUTION: $\Delta H_{\mathrm{m}}-\Delta U_{\mathrm{m}}=\left(1.0 \times 10^5 \mathrm{~Pa}\right) \times\left(100 \mathrm{~g} \mathrm{~mol}^{-1}\right) \times\left(\frac{1}{2.93 \mathrm{~g} \mathrm{~cm}^{-3}}-\frac{1}{2.71 \mathrm{~g} \mathrm{~cm}^{-3}}\right)=-0.28 \mathrm{~Pa} \mathrm{~m}^3 \mathrm{~mol}^{-1}$. 

Use the given formula to express $\Delta H_{\mathrm{m}}$ in terms of molar internal energy change, $\Delta U_{\mathrm{m}}$, and pressure, $p$. 
SOLUTION: $\Delta H_{\mathrm{m}}=\Delta U_{\mathrm{m}}+p\left\{V_{\mathrm{m}}(\mathrm{a})-V_{\mathrm{m}}(\mathrm{c})\right\}$. 

Substitute the formula for molar volume, $V_{\mathrm{m}}=M / \rho$, in the previous expression of $\Delta H_{\mathrm{m}}$ to obtain the expression in terms of densities, $\rho(\mathrm{a})$ and $\rho(\mathrm{c})$. 
SOLUTION: $\Delta H_{\mathrm{m}}-\Delta U_{\mathrm{m}}=p M\left(\frac{1}{\rho(\mathrm{a})}-\frac{1}{\rho(\mathrm{c})}\right)$.
"""
