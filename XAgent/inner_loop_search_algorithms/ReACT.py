import json

from colorama import Fore
from XAgent.config import CONFIG
from XAgent.agent.base_agent import BaseAgent
from XAgent.agent.summarize import summarize_action, summarize_plan
from XAgent.core import XAgentCoreComponents
from XAgent.data_structure.node import ToolNode
from XAgent.data_structure.tree import TaskSearchTree
from XAgent.inner_loop_search_algorithms.base_search import BaseSearchMethod
from XAgent.message_history import Message
from XAgent.utils import SearchMethodStatusCode, ToolCallStatusCode
from XAgent.agent.simple_agent.post_process import exec_code, extract_code
from .score import evaluate_res, understand
from .wiki_search import search_from_concept

NOW_SUBTASK_PROMPT = """

"""

# add tool prompt

PYTHON_PROMPT = """[answer]: ```{PYTHON CODE}```
Your answer should be a piece of python code which solves the current question.
Encase your code within triple backticks for clarity.
You must end your code with printing all the result and their units.
Make sure the code can be successfully run without any input.
Be precise.The answer should be accurate, choose the appropriate units, and prohibit the use of round functions to round off and lose the results.
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

# Print the result
print("The value of beta is:", beta, "cm^(-1)")
```


"""

SIMPLE_PROMPT = """[answer]:\\boxed{[ANSWER]}.
Summarize a short text summary of the answer if it is a text answer, and a specific numerical value if it is a scientific question.The answer will be displayed to the user and processed by subsequent subtasks, so it must contain enough information to help subsequent subtasks proceed smoothly. At the same time, the answer needs to complete the goals and all milestones of the current processing subtask.
Please add units in your answer.The format of the answer is "[answer]:\\boxed{[ANSWER]}."

"""


def make_message(now_node: ToolNode, max_length, config, now_dealing_task):
    """
    Function to generate messages for each node.

    Args:
        now_node: The current ToolNode instance.
        task_handler: Handler of the tasks.
        max_length: Maximum length of the subtask chain.
        config: The configuration settings.

    Returns:
        The sequence of messages for the current node.

    """

    if CONFIG.enable_summary:
        terminal_task_info = summarize_plan(now_dealing_task.to_json())
    else:
        terminal_task_info = json.dumps(
            now_dealing_task.to_json(), indent=2, ensure_ascii=False
        )

    message_sequence = []

    now_subtask_prompt = f'''Now you will perform the following subtask:\n"""\n{terminal_task_info}\n"""\n'''
    message_sequence.append(Message("user", now_subtask_prompt))
    action_process = now_node.process

    if config.enable_summary:
        action_process = summarize_action(action_process, terminal_task_info)
    user_prompt = f"""The following steps have been performed (you have already done the following and the current file contents are shown below):\n
    {action_process}
    """
    message_sequence.append(Message("user", user_prompt))
    return message_sequence


class ReACTChainSearch(BaseSearchMethod):
    """
    Class for ReACT chain search. It performs chain based searches for tasks.
    """

    def __init__(self, xagent_core_components: XAgentCoreComponents, tool):
        """
        xagent_core_components: XAgentCoreComponents object, used to initialize ReACTChainSearch object
        Initializes ReACTChainSearch object. It maintains a list of trees to represent
        the processed tasks.
        """
        super().__init__()

        self.tree_list = []
        self.finish_node = None
        self.tool = tool
        if "python" in tool:
            self.tool_prompt = PYTHON_PROMPT
        else:
            self.tool_prompt = SIMPLE_PROMPT

        self.xagent_core_components = xagent_core_components
        self.vector_db = xagent_core_components.vector_db_interface

    def run(
        self,
        config,
        agent: BaseAgent,
        arguments,
        functions,
        task_id,
        now_dealing_task,
        plan_agent,
        max_try=1,
        max_answer=1,
    ):
        """
        Runs the chain search task.

        Args:
            config: Configuration for the search.
            agent: Base agent responsible for chain search.
            arguments: Arguments for the current task to be handled.
            functions: The available functions for use by agent.
            task_id: ID of the current task.
            max_try: Maximum number of attempts.
            max_answer: Maximum number of answers to be received

        Returns:
            None
        Raises:
            None
        """

        for _attempt_id in range(max_try):
            return self.generate_chain(
                config,
                agent,
                arguments,
                functions,
                task_id,
                now_dealing_task,
                plan_agent,
            )

    def get_finish_node(self):
        """
        Function to retrieve the finished node in the task tree.

        Returns:
            The finished node.
        """
        return self.finish_node

    def generate_chain(
        self,
        config,
        agent: BaseAgent,
        arguments,
        functions,
        task_id,
        now_dealing_task,
        plan_agent,
    ):
        """
        Run the chain search task.

        Args:
            config: Configuration for the search.
            agent: Base agent responsible for chain search.
            arguments: Arguments for the current task to be handled.
            functions: The available functions for use by agent.
            task_id: ID of the current task.

        Returns:
            None.
        Raises:
            None.
        """

        # search similar trial
        search_goal = now_dealing_task.data.goal

        success_prompt = self.vector_db.search_from_hierarchical(
            search_goal, namespace="SUCCESS", top_k=CONFIG.exec_topk
        )
        fail_prompt = ""

        print("success_similar_lists:", success_prompt)
        # print("fail_similar_lists:", fail_prompt)

        # success_prompt = fail_prompt = []
        all_plan = plan_agent.latest_plan.to_json()

        if config.enable_summary:
            all_plan = summarize_plan(all_plan)
        else:
            all_plan = json.dumps(all_plan, indent=2, ensure_ascii=False)
        print("all_plan for now task:")
        print(all_plan)

        # web_search
        additional_prompt = ""
        if CONFIG.web_search:

            additional_prompt = search_from_concept(now_dealing_task.data.goal)

        max_confidence = 0
        final_res = final_ans = "None"
        for i in range(3):

            response, ans = agent.parse(
                placeholders={
                    "system": {"all_plan": all_plan},
                    "user": {
                        "subtask_id": now_dealing_task.get_subtask_id(to_str=True),
                        "subtask_goal": now_dealing_task.data.goal,
                        "milestones": str(now_dealing_task.data.milestones),
                        "success_prompt": success_prompt,
                        # "fail_prompt": fail_prompt,
                        "tool_prompt": self.tool_prompt,
                        "additional_prompt": additional_prompt,
                    },
                },
                arguments=arguments,
                functions=[self.tool],
                function_call=None,
            )
            print(f"______ans:{ans}_______\n")
            if not CONFIG.score:
                break
            if ans != "None":

                conf = evaluate_res(
                    now_dealing_task.data.goal,
                    str(now_dealing_task.data.milestones),
                    response
                    + "\nWe executed the generated python code and got the answer: "
                    + ans,
                )
                if conf >= max_confidence:
                    final_res, final_ans = response, ans
                    max_confidence = conf

            if i == 2:
                response, ans = final_res, final_ans

        if ans != "None":
            now_dealing_task.data.response = response
        else:
            now_dealing_task.data.response = "None"

        print("++++++++++++++++++++")
        print(response)
        print("++++++++++++++++++++")

        if self.tool == "python" and ans != "None":
            print("________python_code___________")
            code = extract_code(response)
            print(code)
            now_dealing_task.data.thoughts = (
                "This Python code solves the problem.\n" + code
            )

        else:
            now_dealing_task.data.thoughts = response
        print("--------answer-----------")
        print(ans)
        print("-------------------\n")

        now_dealing_task.data.answer = ans

        if CONFIG.refine:

            if ans == None or ans == "" or ans == "None":
                self.need_for_plan_refine = True
            else:
                self.need_for_plan_refine = False
        return ans

    def to_json(self):
        """
        Placeholder function to convert ReACTChainSearch object to JSON.

        Currently not implemented.

        Returns:
            None
        """
        pass

    def is_include_pictures(self, using_tools):

        tool_name = (
            using_tools.get("tool_name", "") if isinstance(using_tools, dict) else ""
        )
        tool_output = (
            using_tools.get("tool_output", {}) if isinstance(using_tools, dict) else ""
        )
        if tool_name == "PythonNotebook_execute_cell":
            for output in tool_output:
                if isinstance(output, dict) and "file_name" in output:
                    return True
        return False
