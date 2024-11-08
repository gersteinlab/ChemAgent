import json
import uuid

from colorama import Fore

from XAgent.inner_loop_search_algorithms.ReACT import ReACTChainSearch
from XAgent.agent.summarize import summarize_plan
from XAgent.utils import (
    RequiredAbilities,
    SearchMethodStatusCode,
    TaskSaveItem,
    TaskStatusCode,
)
from XAgent.message_history import Message
from XAgent.ai_functions import function_manager
from XAgent.core import XAgentCoreComponents, XAgentParam
from ..status import StatusEnum
from .plan_exec import Plan, PlanAgent
from .reflection import get_posterior_knowledge, get_father_posterior_knowledge
from ..config import CONFIG as config
from XAgent.agent.simple_agent.post_process import exec_code, extract_code


class TaskHandler:
    """
    Main class for handling tasks within the XAgent system.

    Attributes:
        config: The configuration settings for the task handler.
        function_list: List of available functions for the current task.
        tool_functions_description_list: List of available tool functions description for the current task.
        query: The current task of this agent.
        tool_call_count: Variable for tracking the count of tool calls.
        plan_agent: Instance of PlanAgent class which is used for generating and handling plan for the current task.
        interaction: Instance of XAgentInteraction class for interacting with outer world.
    """

    def __init__(
        self, xagent_param: XAgentParam, xagent_core: XAgentCoreComponents, tool, insert
    ):
        """
        Initializes TaskHandler with the provided input parameters.

        Args:
            xaagent_core (XAgentCoreComponents): Instance of XAgentCoreComponents class.
            xaagent_param (XAgentParam): Instance of XAgentParam class.
        """
        self.tool = tool
        self.insert = insert
        self.xagent_param = xagent_param
        self.config = xagent_param.config
        self.query = self.xagent_param.query
        self.xagent_core = xagent_core
        self.plan_agent = PlanAgent(
            xagent_core_components=self.xagent_core,
            config=self.config,
            query=self.query,
            avaliable_tools_description_list=[],
        )
        self.logger = self.xagent_core.logger
        # self.avaliable_tools_description_list = tool_functions_description_list

        self.agent_dispatcher = self.xagent_core.agent_dispatcher

        self.now_dealing_task = None
        self.vector_db = self.xagent_core.vector_db_interface
        self.final_plan = None
        self.function_list = self.xagent_core.function_list
        self.function_handler = self.xagent_core.function_handler
        self.logger.typewriter_log(
            f"Use tools: {self.tool} ",
            Fore.BLUE,
        )

    def outer_loop(self):
        """
        Executes the main sequence of tasks in the outer loop.

        Raises:
            AssertionError: Raised if a not expected status is encountered while handling the plan.

        Returns:
            None
        """

        self.logger.typewriter_log(
            f"-=-=-=-=-=-=-= BEGIN QUERY SOVLING -=-=-=-=-=-=-=",
            Fore.YELLOW,
            "",
        )
        self.query.log_self()

        gene_sub = 0
        attempts = 0
        subtasks = "None"
        while gene_sub == 0:
            try:
                goal_list, subtasks = self.plan_agent.initial_plan_generation(
                    agent_dispatcher=self.agent_dispatcher
                )

                print(summarize_plan(self.plan_agent.latest_plan.to_json()))

                # print_data = self.plan_agent.latest_plan.to_json()
                # print(print_data)

                self.now_dealing_task = self.plan_agent.latest_plan.children[0]
                gene_sub = 1
            except Exception as e:
                print(f"Attempt {attempts + 1}: An error occurred: {e}. Retrying...\n")
                attempts += 1
                gene_sub = 0
        # workspace_hash_id = ""

        similar_rate_list = self.vector_db.calculate_similar_rate(goal_list)
        print(f"the goal similar rate list is {str(similar_rate_list)}")
       
        # average = sum(similar_rate_list) / len(similar_rate_list)
        average = 1
        if average < self.config.dsolve_threshold:
            print(f"average is {average}, Start dsolve!!!!!!!!!!!!!\n")
            ans, res = self.dsolve(self.query.task)
            return ans, "None", "None", f"dsolve average{str(similar_rate_list)} "

        else:
            print(f"average is {average}, Plan solve!!!!!!!!!!!\n")

        while self.now_dealing_task:
            task_id = self.now_dealing_task.get_subtask_id(to_str=True)

            search_method = self.inner_loop(self.now_dealing_task)


            if self.insert:
                self.posterior_process(self.now_dealing_task)

            self.xagent_core.print_task_save_items(self.now_dealing_task.data)

            # refinement_result = {
            #     "name": self.now_dealing_task.data.name,
            #     "goal": self.now_dealing_task.data.goal,
            #     "prior_plan_criticism": self.now_dealing_task.data.prior_plan_criticism,
            #     "posterior_plan_reflection": self.now_dealing_task.data.posterior_plan_reflection,
            #     "milestones": self.now_dealing_task.data.milestones,
            #     # "expected_tools": self.now_dealing_task.data.expected_tools,
            #     "tool_reflection": self.now_dealing_task.data.tool_reflection,
            #     "action_list_summary": self.now_dealing_task.data.action_list_summary,
            #     "task_id": task_id,
            # }

            if search_method.need_for_plan_refine:

                self.plan_agent.plan_refine_mode(
                    self.now_dealing_task,
                    self.agent_dispatcher,
                )
            else:
                self.logger.typewriter_log(
                    "subtask submitted as no need to refine the plan, continue",
                    Fore.BLUE,
                )

            self.final_plan = self.now_dealing_task
            self.now_dealing_task = Plan.pop_next_subtask(self.now_dealing_task)

            if self.now_dealing_task is None:
                print()
            else:
                current_task_id = self.now_dealing_task.get_subtask_id(to_str=True)
                remaining_subtask = Plan.get_remaining_subtask(self.now_dealing_task)
                subtask_list = []
                for todo_plan in remaining_subtask:
                    raw_data = json.loads(todo_plan.data.raw)
                    raw_data["task_id"] = todo_plan.get_subtask_id(to_str=True)
                    raw_data["inner"] = []
                    raw_data["node_id"] = uuid.uuid4().hex
                    subtask_list.append(raw_data)

        print("Seems It is all done here! wwww~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~")
        print(summarize_plan(self.plan_agent.latest_plan.to_json()))
        self.logger.typewriter_log("ALL Tasks Done", Fore.GREEN)
        # final answer
        final_answer, gained_knowledge = self.father_posterior_process()

        if self.insert:
            self.vector_db.save_vector()
            self.logger.typewriter_log("INSERTED EXEC", Fore.GREEN)

        return (
            final_answer,
            subtasks,
            gained_knowledge,
            f"psolve average {str(similar_rate_list)} ",
        )

    def dsolve(self, query):
        print(query)
        ability_type = RequiredAbilities.simple_search
        example_input, example_system_prompt, example_user_prompt = (
            self.agent_dispatcher.get_examples(ability_type, direct=1)
        )
        prompt_messages = [
            Message(role="system", content=example_system_prompt),
            Message(role="user", content=example_user_prompt),
        ]
        agent = self.agent_dispatcher.build_agent(
            ability_type,
            self.agent_dispatcher.config,
            prompt_messages,
        )

        success_prompt = self.vector_db.search_from_hierarchical(
            query, namespace="SUCCESS", top_k=2
        )

        response, ans = agent.parse(
            placeholders={
                "user": {
                    "query": query,
                    "success_prompt": success_prompt,
                },
            },
            arguments=function_manager.get_function_schema("simple_subtask")[
                "parameters"
            ],
            functions=["python"],
            function_call=None,
        )
        if ans != "None":
            print("________python_code___________")
            code = extract_code(response)
            print(response)
            print(ans)
        else:
            print("dsolve fail!\n")
        return ans, response

    def inner_loop(
        self,
        plan: Plan,
    ):
        """
        Generates search plan and process it for the current task.

        Args:
            plan (Plan): The plan to be processed.

        Raises:
            AssertionError: Raised if a not expected status is encountered while handling the plan.

        Returns:
            ReACTChainSearch: Instance of the search plan.
        """
        task_ids_str = plan.get_subtask_id(to_str=True)
        self.logger.typewriter_log(
            f"-=-=-=-=-=-=-= Performing Task {task_ids_str} ({plan.data.name}): Begin -=-=-=-=-=-=-=",
            Fore.GREEN,
            "",
        )
        self.xagent_core.print_task_save_items(plan.data)

        agent = self.agent_dispatcher.dispatch(
            RequiredAbilities.simple_search,
            json.dumps(plan.data.to_json(), indent=2, ensure_ascii=False),
            # avaliable_tools_description_list=self.avaliable_tools_description_list
        )

        plan.data.status = TaskStatusCode.DOING

        search_method = ReACTChainSearch(
            xagent_core_components=self.xagent_core,
            tool=self.tool,
        )

        arguments = function_manager.get_function_schema("simple_subtask")["parameters"]

        ans = search_method.run(
            config=self.config,
            agent=agent,
            arguments=arguments,
            functions=self.function_handler.intrinsic_tools(
                self.config.enable_ask_human_for_help
            ),
            task_id=task_ids_str,
            now_dealing_task=self.now_dealing_task,
            plan_agent=self.plan_agent,
        )
        if ans == "None":
            plan.data.status = TaskStatusCode.FAIL
            self.logger.typewriter_log(
                f"-=-=-=-=-=-=-= Task {task_ids_str} ({plan.data.name}): Failed -=-=-=-=-=-=-=",
                Fore.RED,
                "",
            )
            return search_method
        # start verify delete this else
        else:
            plan.data.status = TaskStatusCode.SUCCESS
            self.logger.typewriter_log(
                f"-=-=-=-=-=-=-= Task {task_ids_str} ({plan.data.name}): Solved -=-=-=-=-=-=-=",
                Fore.GREEN,
                "",
            )
            return search_method

        # verify!
        # verify_agent = self.agent_dispatcher.dispatch(
        #     RequiredAbilities.verify_refine,
        #     "Rate the current response",
        # )

        # all_plan = self.plan_agent.latest_plan.to_json()

        # if config.enable_summary:
        #     all_plan = summarize_plan(all_plan)
        # else:
        #     all_plan = json.dumps(all_plan, indent=2, ensure_ascii=False)

        # flag = verify_agent.parse(
        #     placeholders={
        #         "system": {"all_plan": all_plan, "question": self.query.task},
        #         "user": {
        #             "subplan": summarize_plan(self.now_dealing_task.to_json()),
        #             "response": self.now_dealing_task.data.thoughts,
        #             "answer": self.now_dealing_task.data.answer,
        #         },
        #     },
        #     arguments=arguments,
        #     functions=[self.tool],
        #     function_call=None,
        #     now_plan=self.now_dealing_task,
        # )

        # if flag:
        #     plan.data.status = TaskStatusCode.SUCCESS
        #     self.logger.typewriter_log(
        #         f"-=-=-=-=-=-=-= Task {task_ids_str} ({plan.data.name}): Solved -=-=-=-=-=-=-=",
        #         Fore.GREEN,
        #         "",
        #     )
        # else:
        #     plan.data.status = TaskStatusCode.FAIL
        #     self.logger.typewriter_log(
        #         f"-=-=-=-=-=-=-= Task {task_ids_str} ({plan.data.name}): Failed -=-=-=-=-=-=-=",
        #         Fore.RED,
        #         "",
        #     )

        return search_method

    # Posterior experience of the smallest unit task
    # Responsible for verifying and inserting memory
    def posterior_process(self, terminal_plan: Plan):
        """
        Performs the post-processing steps on the terminal plan including extraction of posterior knowledge
        and updating the plan data.

        Args:
            terminal_plan (Plan): The terminal plan after completion of all inner loop tasks.

        Returns:
            None
        """

        self.logger.typewriter_log(
            "-=-=-=-=-=-=-= POSTERIOR_PROCESS, working memory, summary, and reflection -=-=-=-=-=-=-=",
            Fore.BLUE,
        )
        posterior_data = get_posterior_knowledge(
            all_plan=self.plan_agent.latest_plan,
            terminal_plan=terminal_plan,
            config=self.config,
            agent_dispatcher=self.agent_dispatcher,
        )

        summary = posterior_data["summary"]

        # TRY:when tool is python , python code is action_list_summary
        if "This Python code" in terminal_plan.data.thoughts:
            terminal_plan.data.action_list_summary = terminal_plan.data.thoughts
        else:
            terminal_plan.data.action_list_summary = summary

        # TO CHANGE:like sample,memory
        if terminal_plan.data.response != "None":
            terminal_plan.data.action_list_summary = terminal_plan.data.response
        else:
            return

        reflex = ""
        if "reflection_of_plan" in posterior_data.keys():
            terminal_plan.data.posterior_plan_reflection = posterior_data[
                "reflection_of_plan"
            ]
            reflex += str(terminal_plan.data.posterior_plan_reflection)

        if "reflection_of_tool" in posterior_data.keys():
            terminal_plan.data.tool_reflection = posterior_data["reflection_of_tool"]
        print(terminal_plan.data.raw)

        # add to vector_db
        save_data = terminal_plan.data

        # id generated by interaction_id
        interaction_id = self.xagent_core.client_id

        # record the action list
        self.vector_db.insert_sentence(
            uuid=interaction_id,
            goal=save_data.goal,
            action_list=save_data.action_list_summary,
            namespace=save_data.status.name,
            reflex=reflex,
            task_id=terminal_plan.get_subtask_id(to_str=True),
            level=0,
        )

        self.logger.typewriter_log(
            f"-=-=-=-=-=-=-= save goal to db SUCCESS-=-=-=-=-=-=-=",
            Fore.BLUE,
        )

        # Insert the plan into vector DB
        # vector_db_interface.insert_sentence(terminal_plan.data.raw)

    def father_posterior_process(self):
        """
        to summury children plan and action_list
        """
        self.logger.typewriter_log(
            "-=-=-=-=-=-=-=FATHER_NODE POSTERIOR_PROCESS, working memory, summary, and reflection -=-=-=-=-=-=-=",
            Fore.BLUE,
        )

        def level_of_task(plan: Plan):
            # if plan is leaf, return 0

            l = 0
            p = plan
            while p.children != []:
                p = p.children[0]
                l = l + 1
            return l

        plan_tree = self.plan_agent.plan.get_inorder_travel(self.plan_agent.latest_plan)
        # Initially in pre-order sequence, after reversing, sorted in ascending order.
        plan_tree.reverse()
        for plan in plan_tree:
            plan_level = level_of_task(plan)
            # Not an atomic task, performing parent node summarization.
            if plan_level > 0 and plan.children != []:
                # If any subtask fails, the parent task fails.
                status = TaskStatusCode.SUCCESS

                for child in plan.children:
                    if child.data.status == TaskStatusCode.FAIL:
                        status = TaskStatusCode.FAIL
                plan.data.status = status

                posterior_data = get_father_posterior_knowledge(
                    plan=plan,
                    config=self.config,
                    agent_dispatcher=self.agent_dispatcher,
                )
                print("posterior_data---------------------------------")
                print(posterior_data)
                summary = posterior_data["summary"]

                plan.data.action_list_summary = summary
                reflex = ""
                if "reflection_of_knowledge" in posterior_data.keys():
                    plan.data.posterior_plan_reflection = posterior_data[
                        "reflection_of_knowledge"
                    ]
                    reflex += str(plan.data.posterior_plan_reflection)

                if "reflection_of_tool" in posterior_data.keys():
                    plan.data.tool_reflection = posterior_data["reflection_of_tool"]
                print("plan.data.raw----------------------------------")
                print(plan.data.raw)

                # add to vector_db
                save_data = plan.data

                interaction_id = self.xagent_core.client_id

                childs_id = []
                for child in plan.children:
                    childs_id.append(
                        interaction_id + "-" + child.get_subtask_id(to_str=True)
                    )
                # TO NONE
                # self.vector_db.insert_father_node(
                #     uuid=interaction_id,
                #     goal=save_data.goal,
                #     action_list=save_data.action_list_summary,
                #     namespace=save_data.status.name,
                #     reflex=reflex,
                #     task_id=plan.get_subtask_id(to_str=True),
                #     level=plan_level,
                #     childs_id=childs_id,
                # )

                self.logger.typewriter_log(
                    f"-=-=-=-=-=-=-= save goal {plan.get_subtask_id(to_str=True)} to db SUCCESS-=-=-=-=-=-=-=",
                    Fore.BLUE,
                )
                # final answer
                final_answer = posterior_data["final_answer"]
                gained_knowledge = posterior_data["reflection_of_knowledge"]
                if final_answer == "" or final_answer == "None":
                    plan_tree = self.plan_agent.plan.get_inorder_travel(
                        self.plan_agent.latest_plan
                    )
                    final_answer = plan_tree[-1].data.answer
                self.logger.typewriter_log(
                    f"FINAL ANSWER :{final_answer}",
                    Fore.RED,
                )
                return final_answer, gained_knowledge
