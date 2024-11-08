from llama_index.llms.azure_openai import AzureOpenAI
from llama_index.embeddings.azure_openai import AzureOpenAIEmbedding
from llama_index.core import VectorStoreIndex, SimpleDirectoryReader
from llama_index.core.schema import BaseNode, TextNode
from llama_index.core.schema import TextNode, NodeRelationship, RelatedNodeInfo
from openai import AzureOpenAI
from llama_index.core.vector_stores import (
    MetadataFilter,
    MetadataFilters,
    FilterOperator,
)
from llama_index.core import StorageContext, load_index_from_storage

try:
    from .imagination_engine import imagination
except ImportError:
    from imagination_engine import imagination
try:
    from XAgent.config import CONFIG
except ImportError:
    from config import CONFIG

# TODO
# pip install llama-index-llms-azure-openai,pip install llama-index-embeddings-azure-openai,pip install llama-index
# pip install llama-index-vector-stores-postgres

keys = CONFIG["api_keys"]["embedding"][0]
api_key = keys["api_key"]
azure_endpoint = keys["api_base"]
api_version = keys["api_version"]


# Clear the current directory (CONFIG["save_dir"]) for initializing MemoryDB

def MemoryDB_clear():
    import os, shutil

    save_dir = CONFIG["save_dir"]
    if os.path.exists(save_dir):
        print("Clearing MemoryDB")
        shutil.rmtree(save_dir)
    os.makedirs(save_dir)



def format_dict(input_dict, index, status):
    output_str = f"[The Start of {status} Task {index}]\n"
    for key, value in input_dict.items():
        output_str += f"[{key}]: {value},\n"
    output_str = (
        output_str[:-2] + f"\n[The End of {status} Task {index}]\n\n"
    )  
    return output_str


class MemoryDB:
    def __init__(self, insert_mode=True, init_mode=False):
        self.insert_mode = insert_mode
        self.embed_model = AzureOpenAIEmbedding(
            api_key=api_key,
            deployment_name="text-embedding-ada-002",
            azure_endpoint=azure_endpoint,
            api_version=api_version,
            model="text-embedding-ada-002",
        )
        self.save_dir = CONFIG["save_dir"]
        self.pool_id = CONFIG.pool_id

        self.index_list = []
        self.save_dir_list = [
            "./storage_chemmc_sample",
            "./storage_quan_sample",
            "./storage_matter_sample_gpt35",
            "./storage_atkins_sample_gpt35",
        ]
        ## for global use

        # for dir in self.save_dir_list:
        #     storage_context = StorageContext.from_defaults(persist_dir=dir)
        #     # load index
        #     index = load_index_from_storage(
        #         storage_context,
        #         embed_model=self.embed_model,
        #     )
        #     self.index_list.append(index)

        if init_mode:
            MemoryDB_clear()
            self.index = VectorStoreIndex(nodes=[], embed_model=self.embed_model)
            print("MemoryDB FIRST init finished")
        else:
            try:
                storage_context = StorageContext.from_defaults(
                    persist_dir=self.save_dir
                )
                # load index
                self.index = load_index_from_storage(
                    storage_context,
                    embed_model=self.embed_model,
                )
                print("MemoryDB read from config storage success")
            except Exception as e:
                print(e)
                print("MemoryDB read from config storage failed, init new index")
                MemoryDB_clear()
                self.index = VectorStoreIndex(nodes=[], embed_model=self.embed_model)
                print("MemoryDB FIRST init finished")

    def insert_father_node(
        self,
        uuid: str,
        goal: str,
        action_list: str,
        namespace="",
        reflex="",
        task_id="",
        level=0,
        childs_id=[],
    ):
        print(f"for task_Id:{task_id} , childs_id:{childs_id}")
        if not self.insert_mode:
            return

        new_node = TextNode(
            text=goal,
            id_=uuid + "-" + task_id,
            metadata={
                "goal": goal,
                "action": action_list,
                "reflex": reflex,
                "pool": self.pool_id,
                "tree_id": uuid,
                "task_id": task_id,
                "level": level,
                "status": namespace,
                # "subject": subject,
            },
        )
        RelatedList = []
        for id in childs_id:
            RelatedList.append(RelatedNodeInfo(node_id=id))

        new_node.relationships[NodeRelationship.CHILD] = RelatedList

        try:
            self.index.insert_nodes([new_node])
        except Exception as e:
            print(e)
            print("Warning: Fail to insert father node", goal)

    def get_subject(self, query: str):
        """
        ask chatgpt to get subject for the goal
        """
        subjects = CONFIG.subjects
        prompt = f"Given the question '{query}', please select the most relevant subject from the following list: {subjects}.Please return only one element in the list without explaining the reason and adding extra punctuation and spaces.If you don't think the issue belongs to any of the subject in the list, return 'None'."
        message_text = [
            {
                "role": "system",
                "content": "You are an AI assistant that helps people with text classification.",
            },
            {"role": "user", "content": prompt},
        ]

        client = AzureOpenAI(
            api_key=api_key,
            api_version=api_version,
            azure_endpoint=azure_endpoint,
        )

        response = client.chat.completions.create(
            model="GPT-35-Turbo-16k", messages=message_text
        )
        response = response.choices[0].message.content
        if response in subjects:
            return response
        else:
            return None

    def insert_sentence(
        self,
        uuid: str,
        goal: str,
        action_list: str,
        namespace="",
        reflex="",
        task_id="",
        level=0,
    ):
        """
        traj structure:
        id(uuid+task_id), there is a conflict issue, the latter generated one will overwrite the former (the refined one is better)
        goal
        parent_id
        level (atomic task is marked as 0)
        status (SUCCESS/FAIL)
        reflex
        pool_id (memory pool id)
        action_list
        uuid: id of this task tree
        """
        
        if not self.insert_mode:
            return

        new_node = TextNode(
            text=goal,
            id_=uuid + "-" + task_id,
            metadata={
                "goal": goal,
                "action": action_list,
                "reflex": reflex,
                "pool": self.pool_id,
                "tree_id": uuid,
                "task_id": task_id,
                "level": level,
                "status": namespace,
                # "subject": subject,
            },
        )
        try:
            self.index.insert_nodes([new_node])

        except Exception as e:
            print(e)
            print("Warning: Fail to insert", goal)

    def search_similar_sentences(
        self, query_sentence: str, namespace="", level=0, top_k=3
    ):
        """
        Search rule: Search within the memory pool of the same level, retrieve the top_K, and return values above the threshold.

        """
        filters = MetadataFilters(
            filters=[
                MetadataFilter(
                    key="status",
                    value=namespace,
                    operator=FilterOperator.EQ,
                ),
                MetadataFilter(
                    key="level",
                    value=level,
                    operator=FilterOperator.EQ,
                ),
            ]
        )

        retriever = self.index.as_retriever(similarity_top_k=top_k, filters=filters)

        try:
            res = retriever.retrieve(query_sentence)
            # print(res)
            ans = []
            for node in res:
                if node.get_score(node) > CONFIG["traj_score_threshold"]:
                    dict_node = node.to_dict()
                    if (
                        "--- Similar tasks ---"
                        in dict_node["node"]["metadata"]["action"]
                    ):
                        break
                    ans.append(node.to_dict())
            return ans
        except Exception as e:
            print(e)
            print("Warning: Fail to search similar sentences")

    def search_from_index(self, query_sentence: str, index, namespace="", top_k=3):
        """
        Search rule: Search within the memory pool of the same level, retrieve the top_K, and return values above the threshold.
        """
        filters = MetadataFilters(
            filters=[
                MetadataFilter(
                    key="status",
                    value=namespace,
                    operator=FilterOperator.EQ,
                ),
            ]
        )

        retriever = index.as_retriever(similarity_top_k=top_k, filters=filters)

        try:
            res = retriever.retrieve(query_sentence)
            # print(res)
            ans = []
            for node in res:
                if node.get_score(node) > CONFIG["traj_score_threshold"]:
                    ans.append([node.get_score(node), node.to_dict()])
            return ans
        except Exception as e:
            print(e)
            print("Warning: Fail to search similar sentences")

    def search_from_global(self, query_sentence: str, namespace="", top_k=3):
        res = []
        for index in self.index_list:
            res_one = self.search_from_index(query_sentence, index, namespace, top_k)
            res.extend(res_one)
        sorted_res = sorted(res, key=lambda x: x[0], reverse=True)
        res = sorted_res[:top_k]
        res = [x[1] for x in res]
        prompt = []

        if namespace == "SUCCESS":

            for traj in res:
                prompt.append(
                    {
                        "GOAL": traj["node"]["metadata"]["goal"],
                        "ACTION": traj["node"]["metadata"]["action"],
                    }
                )
        else:
            for traj in res:
                prompt.append(
                    {
                        "GOAL": traj["node"]["metadata"]["goal"],
                        "ACTION": traj["node"]["metadata"]["action"],
                        # "REFLEX": traj["node"]["metadata"]["reflex"],
                    }
                )

        str = ""
        for index, p in enumerate(prompt):
            str += format_dict(p, index, namespace)

        return str

    def calculate_similar_rate(self, goal_list):
        # calculate the average similarity rate of the goals in the list
        res = []
        for goal in goal_list:
            now_res = []
            temp = self.search_similar_sentences(
                goal, "SUCCESS", 0, top_k=CONFIG.exec_topk
            )
            for t in temp:
                now_res.append(t["score"])
            if len(now_res) != 0:
                new_average = sum(now_res) / len(now_res)
            else:
                new_average = 0
            res.append(new_average)

        return res

    def search_from_hierarchical(self, query_sentence: str, namespace="", top_k=3):
        res = []
        # search from each level
        for level in range(4):
            res_level = self.search_similar_sentences(
                query_sentence, namespace, level=level, top_k=top_k
            )
            res.extend(res_level)

            if len(res) >= top_k:
                break
        # print(res[:top_k])

        res = res[:top_k]

        if CONFIG.image:
            # calculate max and average
            score_list = []
            for t in res:
                score_list.append(t["score"])
            
            if len(score_list) == 0:
                average = 0
            else:
                average = sum(score_list) / len(score_list)
            print(average)
            
            # The similarity is low, it requires association.
            if average < CONFIG.imagination_threshold:
                
                for i in range(3):
                    topic = self.get_subject(query_sentence)
                    if topic != None:
                        break
                print(f"imagination!!!! topic is {topic}")
                return imagination(topic, res, top_k)

        prompt = []

        if namespace == "SUCCESS":

            for traj in res:
                prompt.append(
                    {
                        "GOAL": traj["node"]["metadata"]["goal"],
                        "ACTION": traj["node"]["metadata"]["action"],
                    }
                )
        else:
            for traj in res:
                prompt.append(
                    {
                        "GOAL": traj["node"]["metadata"]["goal"],
                        "ACTION": traj["node"]["metadata"]["action"],
                        # "REFLEX": traj["node"]["metadata"]["reflex"],
                    }
                )

        str = ""
        for index, p in enumerate(prompt):
            str += format_dict(p, index, namespace)

        return str

    def search_nodes(self, query_text):
        return self.retriever.retrieve(
            query_text,
        )

    def save_vector(self):
        self.index.storage_context.persist(persist_dir=self.save_dir)


# FOR TESTING
if __name__ == "__main__":
    DB = MemoryDB(init_mode=False)

    query_text = "Calculate the number of moles of nitrogen gas"

    result_node = DB.search_from_hierarchical(query_text, "SUCCESS", 3)
    print(result_node)
