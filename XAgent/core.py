"""XAgent Core Components"""

import abc
from datetime import datetime
import os
import uuid

from XAgent.memory_db_plan import PlanMemoryDB
from colorama import Fore
from XAgent.agent.dispatcher import XAgentDispatcher
from XAgent.agent import (
    PlanGenerateAgent,
    PlanRefineAgent,
    ToolAgent,
    ReflectAgent,
    FatherReflectAgent,
    SimpleAgent,
    PlanVerifyAgent,
)
from XAgent.function_handler import FunctionHandler
from XAgent.utils import TaskSaveItem

from XAgent.memory_db import MemoryDB
from XAgent.workflow.base_query import AutoGPTQuery, BaseQuery

from XAgent.loggers.logs import Logger


class XAgentParam(metaclass=abc.ABCMeta):
    """
    XAgent Param
    """

    def __init__(
        self, config=None, query: BaseQuery = None, newly_created: bool = True
    ) -> None:
        self.config = config
        self.query = query
        self.newly_created = newly_created

    def build_query(self, query: dict):
        """
        build query
        """
        self.query = AutoGPTQuery(**query)

    def build_config(self, config):
        """
        build config
        """
        self.config = config


class XAgentCoreComponents(metaclass=abc.ABCMeta):
    """
    XAgent Core Components
    Components:
        logger: Logging
        recorder: Running recorder
        toolserver_interface: Tool server interface
        function_handler: Function handler
        working_memory_function: Working memory
        agent_dispatcher: Agent dispatcher
        vector_db_interface: Vector database interface
        interaction: Interaction

    All components in the component set are globally unique.
    """

    global_recorder = None

    def __init__(self) -> None:
        self.interaction = None
        self.client_id = None
        self.logger = None
        self.recorder = None
        self.toolserver_interface = None
        self.function_handler = None
        self.tool_functions_description_list = []
        self.function_list = []
        self.working_memory_function = None
        self.agent_dispatcher = None
        self.vector_db_interface = None
        self.base_dir = ""
        self.extract_dir = ""
        self.available_agents = [
            PlanGenerateAgent,
            PlanRefineAgent,
            ToolAgent,
            ReflectAgent,
            FatherReflectAgent,
            SimpleAgent,
            PlanVerifyAgent,
        ]
        self.client_id = uuid.uuid4().hex
        self.date_str = datetime.now().strftime("%Y-%m-%d")

    def register_logger(self):
        """
        register a logger to the core components
        """

        self.base_dir = os.path.join(
            os.path.join("Xagent", "localstorage", "interact_records"),
            self.date_str,
            self.client_id,
        )
        if not os.path.exists(self.base_dir):
            os.makedirs(self.base_dir, exist_ok=True)

        self.extract_dir = os.path.join(self.base_dir, "workspace")
        if not os.path.exists(self.extract_dir):
            os.makedirs(self.extract_dir, exist_ok=True)

        self.log_dir = os.path.join(
            os.path.join("Xagent", "localstorage", "interact_records"),
            self.date_str,
            self.client_id,
        )
        self.logger = Logger(log_dir=self.log_dir, log_file=f"interact.log")

    def register_agent_dispatcher(self, param: XAgentParam):
        """
        register a agent dispatcher to the core components
        """
        self.logger.info("register agent dispatcher")
        self.agent_dispatcher = XAgentDispatcher(
            param.config, enable=False, logger=self.logger
        )
        for agent in self.available_agents:
            self.agent_dispatcher.regist_agent(agent)

    def register_function_handler(self, config):
        """
        register a function handler to the core components
        """
        self.logger.info("register function handler")
        self.function_handler = FunctionHandler(
            config=config,
            logger=self.logger,
        )

    def register_vector_db_interface(self, insert_mode, init_mode):
        """
        register a vector db interface to the core components
        """
        self.logger.info(
            f"for vector_db insert_mode: {insert_mode}, init_mode: {init_mode}",
        )
        self.vector_db_interface = MemoryDB(
            insert_mode=insert_mode, init_mode=init_mode
        )
        pass

    def register_all(self, param: XAgentParam, insert_mode, init_mode):
        """
        register all components to the core components
        """
        self.register_logger()
        self.register_agent_dispatcher(param=param)
        self.register_function_handler(param.config)
        self.register_vector_db_interface(insert_mode=insert_mode, init_mode=init_mode)

    def build(self, param: XAgentParam, insert_mode, init_mode):
        """
        start all components
        """
        self.register_all(param, insert_mode, init_mode)
        self.logger.info("build all components, done!")

    def start(self):
        """
        start all components
        """
        self.logger.info("start all components")

    def close(self):
        """
        close all components
        """

    def print_task_save_items(
        self,
        item: TaskSaveItem,
    ) -> None:

        self.logger.typewriter_log(f"Task Name:", Fore.YELLOW, f"{item.name}")
        self.logger.typewriter_log(f"Task Goal:", Fore.YELLOW, f"{item.goal}")
        self.logger.typewriter_log(
            f"Task Prior-Criticism:", Fore.YELLOW, f"{item.prior_plan_criticism}"
        )
        if len(item.posterior_plan_reflection) > 0:
            self.logger.typewriter_log(f"Task Posterior-Criticism:", Fore.YELLOW)
            for line in item.posterior_plan_reflection:
                line = line.lstrip("- ")
                self.logger.typewriter_log("- ", Fore.GREEN, line.strip())
        if len(item.milestones) > 0:
            self.logger.typewriter_log(
                f"Task Milestones:",
                Fore.YELLOW,
            )
            for line in item.milestones:
                line = line.lstrip("- ")
                self.logger.typewriter_log("- ", Fore.GREEN, line.strip())
        # if len(item.expected_tools) > 0:
        #     logger.typewriter_log(
        #         f"Expected Tools:", Fore.YELLOW,
        #     )
        #     for line in item.expected_tools:
        #         line = f"{line['tool_name']}: {line['reason']}".lstrip("- ")
        #         logger.typewriter_log("- ", Fore.GREEN, line.strip())
        if len(item.tool_reflection) > 0:
            self.logger.typewriter_log(
                f"Posterior Tool Reflections:",
                Fore.YELLOW,
            )
            for line in item.tool_reflection:
                line = f"{line['target_tool_name']}: {line['reflection']}".lstrip("- ")
                self.logger.typewriter_log("- ", Fore.GREEN, line.strip())

        self.logger.typewriter_log(f"Task Status:", Fore.YELLOW, f"{item.status.name}")
        if item.action_list_summary != "":
            self.logger.typewriter_log(
                f"Action Summary:", Fore.YELLOW, f"{item.action_list_summary}"
            )

    def print_assistant_thoughts(
        self,
        # ai_name: object,
        assistant_reply_json_valid: object,
        speak_mode: bool = False,
    ) -> None:
        assistant_thoughts_reasoning = None
        assistant_thoughts_plan = None
        assistant_thoughts_speak = None
        assistant_thoughts_criticism = None

        assistant_thoughts = assistant_reply_json_valid.get("thoughts", {})
        assistant_thoughts = assistant_thoughts.get("properties", {})
        assistant_thoughts_text = assistant_thoughts.get("thought")
        if assistant_thoughts:
            assistant_thoughts_reasoning = assistant_thoughts.get("reasoning")
            assistant_thoughts_plan = assistant_thoughts.get("plan")
            assistant_thoughts_criticism = assistant_thoughts.get("criticism")
        if assistant_thoughts_text is not None and assistant_thoughts_text != "":
            self.logger.typewriter_log(
                f"THOUGHTS:", Fore.YELLOW, f"{assistant_thoughts_text}"
            )
        if (
            assistant_thoughts_reasoning is not None
            and assistant_thoughts_reasoning != ""
        ):
            self.logger.typewriter_log(
                "REASONING:", Fore.YELLOW, f"{assistant_thoughts_reasoning}"
            )

        if assistant_thoughts_plan is not None and len(assistant_thoughts_plan) > 0:
            self.logger.typewriter_log("PLAN:", Fore.YELLOW, "")
            # If it's a list, join it into a string
            if isinstance(assistant_thoughts_plan, list):
                assistant_thoughts_plan = "\n".join(assistant_thoughts_plan)
            elif isinstance(assistant_thoughts_plan, dict):
                assistant_thoughts_plan = str(assistant_thoughts_plan)

            # Split the input_string using the newline character and dashes
            lines = assistant_thoughts_plan.split("\n")
            for line in lines:
                line = line.lstrip("- ")
                self.logger.typewriter_log("- ", Fore.GREEN, line.strip())

        if (
            assistant_thoughts_criticism is not None
            and assistant_thoughts_criticism != ""
        ):
            self.logger.typewriter_log(
                "CRITICISM:", Fore.YELLOW, f"{assistant_thoughts_criticism}"
            )
        return {
            "thoughts": assistant_thoughts_text,
            "reasoning": assistant_thoughts_reasoning,
            "plan": assistant_thoughts_plan,
            "criticism": assistant_thoughts_criticism,
            "node_id": uuid.uuid4().hex,
        }
