import run
from typing import List
from colorama import Fore

import argparse
from XAgent.agent.base_agent import BaseAgent
from XAgent.utils import RequiredAbilities
from XAgent.message_history import Message
from XAgent.logs import logger

from XAgent.ai_functions import function_manager, objgenerator
from XAgent.config import CONFIG


SPLIT_PROMPT = """You are ChatGPT, a large language model trained by OpenAI, also an excellent prompt evaluater, who is capable of splitting tasks and evaluating the difficulty of tasks which will be solved by other autonomous agents powered by LLM.

Now, I have a target task and its solution here: 
task: {{task}}
solution: {{solution}}

And I also have a tool list (It is also okay not to use them and just use your own knowledge):
- A FileSystemEnv to read and write files (text, code, markdown, latex...), always write down detailed content as it will help further actions. 
- A python notebook to execute python code. Always follow python coding rules. Contains libs like numpy, pandas, matplotlib, sklearn, etc.
- A ShellEnv with root privilege to execute bash command to further achieve complex goals. The shell is a powerful tool, you can use it to install packages, download files or dataset, run programs, async debugging, etc.

First, please evaluate whether this is a successful solution or not, you simply choose one from "success" and "failure" .

Then, evaluate the difficulty of this given task and determine how many steps you need to solve it. Be confident! If you think one step is already enough, it is totally okay and preferred. The total number of sub-tasks is recorded as `N` .

Finally, please generate `N` sub-tasks and their solutions according to the original task and solution, I have the following requirements: 
1. the difficulty of the `N` sub-tasks should be from low to high, and there is a clear distinction in the difficulty of solving. 
2. Your subtasks and their solutions should choose ones with clear answers that are easy to evaluate.
3. You need to have a deep understanding of the target task I gave, the generated sub-task has a strong relationship with the target task, you can decompose the target task.
4. Don't add new knowledge points to the subtasks you generate, and don't let the difficulty of the subtasks you generate involve the understanding of concepts that are not mentioned in the target task. 
5. The hardest task should be similar in difficulty to the target task.
6. If the solution to the given task is "None", you just need to generate subtasks and create your own each corresponding solutions.

KEEP the <st> and <ed> note in the answer.
Below is the format you should follow when you give the answer:

`
WHOLE STATUS: success / failure
I think there are `N` subtasks contained in the main task, and they are listed below.
TASKS=>
<st> SUBTASK 1: ... <ed>
<st> SUBTASK 2: ... <ed>
...
<st> SUBTASK `N`: ... <ed>

SOLUTIONS=>
<st> SOLUTION 1: ... <ed>
<st> SOLUTION 2: ... <ed>
...
<st> SOLUTION `N`: ... <ed>
`

"""

SORT_PROMPT = """You are ChatGPT, a large language model trained by OpenAI, also an excellent prompt difficulty evaulater, who is capable of sorting a series of tasks according to their difficulty.

Now, I have some tasks listed below, I need your help to sort these tasks from the easiest one to most difficult one for an agent to solve, which means you need to put the simpler subtasks in front.

{{tasks}} 

Think carefully and tell me the reason why you think one is easier and another is harder.

You do Not take the temporal relationship into consideration when sorting.

You do NOT need to give the solutions.

You do NOT need to follow the origin order of the tasks.

Please stricylt follow the format below. Replace the "?" character with subtasks' integer ids. 
KEEP the <st> and <ed> note in the answer.

`
I think the difficulty relationship between the tasks are: ...
SO MY ANSWER IS:
<st> SUBTASK ? : ... <ed>
<st> SUBTASK ? : ... <ed>
...
<st> SUBTASK ? : ... <ed>
`

If there is just 1 subtask, just list it, follow this format:

`
<st> SUBTASK 1 : ... <ed>
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

        for i in messages:
            logger.typewriter_log(f"debug:  ", Fore.BLUE, str(i.raw()))

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
    return parser.parse_args()


def env(args, whole_task=None, whole_solution="Not provided."):
    if whole_task != None:
        args.wholetask = whole_task
    prompt_messages = [
        Message(role="assistant", content=SPLIT_PROMPT),
        Message(role="assistant", content=SORT_PROMPT),
    ]
    max_attempts = 10
    attempts = 0
    success = False
    final_tasks = []
    while not success and attempts < max_attempts:
        try:
            final_tasks = []
            agent = EnvAgent(CONFIG, [prompt_messages[0]])
            logger.typewriter_log(f"begin parsing...  ", Fore.YELLOW, "AH?")
            new_message, _ = agent.parse(
                placeholders={
                    "assistant": {
                        "task": args.wholetask,
                        "solution": whole_solution,
                    }
                },
                schema_validation=False,
            )
            # logger.typewriter_log(f"whole_task:  ", Fore.YELLOW, args.wholetask)
            # logger.typewriter_log(f"GPT35:  ", Fore.YELLOW, new_message)
            count_sub_1 = new_message.count("SUBTASK")

            agent = EnvAgent(CONFIG, [prompt_messages[1]])
            assert (
                "TASKS=>" in new_message and "SOLUTIONS=>" in new_message
            ), "No task or solution tag"
            new_message_task = new_message.split("TASKS=>")[1].split("SOLUTIONS=>")[0]
            final_message, _ = agent.parse(
                placeholders={"assistant": {"tasks": new_message_task}},
                schema_validation=False,
            )
            # logger.typewriter_log(f"GPT35-2:  ", Fore.YELLOW, final_message)
            count_sub_2 = final_message.count("SUBTASK")

            assert count_sub_1 == count_sub_2, "Sorter agent forget some sub_tasks"
            assert (
                "<st>" in final_message and "<ed>" in final_message
            ), "Sorter agent didn't follow <st>...<ed> format"
            assert (
                count_sub_2 == len(final_message.split("<st>")) - 1
            ), "number of <st> doesn't match the amount of subtasks"

            for i in range(len(final_message.split("<st>")) - 1):
                final_tasks.append(final_message.split("<ed>")[i].split(":")[-1])

            success = True

        except AssertionError as e:
            print(f"AssertionError on attempt {attempts + 1}: {e}. Retrying...")
            attempts += 1
        except Exception as e:
            print(f"Attempt {attempts + 1}: An error occurred: {e}. Retrying...")
            attempts += 1
    if success:
        return final_tasks
    return []


if __name__ == "__main__":
    args = parse_args()
    tasks = env(args)
    logger.typewriter_log(f"TASKSSSSSSSSSSSSSSSSSSSSSSSSSSSS:\n\n\n  ", Fore.RED, tasks)
    for i in tasks:
        run.run(["--task", i])
