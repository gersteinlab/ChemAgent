from llama_index.llms.azure_openai import AzureOpenAI
from llama_index.embeddings.azure_openai import AzureOpenAIEmbedding
from llama_index.core import VectorStoreIndex, SimpleDirectoryReader
from llama_index.core.schema import BaseNode, TextNode

from llama_index.core.vector_stores import (
    MetadataFilter,
    MetadataFilters,
    FilterOperator,
)
from llama_index.core import StorageContext, load_index_from_storage


try:
    from XAgent.config import CONFIG
except ImportError:
    from config import CONFIG

# TODO


keys = CONFIG["api_keys"]["embedding"][0]
api_key = keys["api_key"]
azure_endpoint = keys["api_base"]
api_version = keys["api_version"]


def format_dict(input_dict, index):
    output_str = f"[The Start of Similar Task Decomposition {index}]\n"
    for key, value in input_dict.items():
        output_str += f"[{key}]: {value},\n"
    output_str = (
        output_str[:-2] + f"\n[The End of Similar Task Decomposition {index}]\n\n"
    )  # remove the last comma and add a new line
    return output_str


def make_subtasks_readable(subtasks):
    readable_subtasks = ""
    # subtasks = eval(str(subtasks))
    for idx, i in enumerate(subtasks):
        subtask = subtasks[idx]
        readable_subtasks += (
            "SUBTASK " + str(idx) + ": " + subtask["subtask name"] + "\n"
        )
        readable_subtasks += "  GOAL: " + subtask["goal"]["goal"] + "\n"
        readable_subtasks += (
            "  THOUGHT: " + subtask["goal"]["criticism"] + "\n  MILESTONES: "
        )
        for j in subtask["milestones"]:
            readable_subtasks += "--" + j + "  "
        readable_subtasks += "\n"
    return readable_subtasks


def MemoryDB_clear():
    import os, shutil

    save_dir = CONFIG["plan_save_dir"]
    if os.path.exists(save_dir):
        print("Clearing PlanMemoryDB")
        shutil.rmtree(save_dir)
    os.makedirs(save_dir)


class PlanMemoryDB:
    def __init__(self, insert_mode=True, init_mode=False):
        self.insert_mode = insert_mode
        self.embed_model = AzureOpenAIEmbedding(
            api_key=api_key,
            deployment_name="text-embedding-ada-002",
            azure_endpoint=azure_endpoint,
            api_version=api_version,
            model="text-embedding-ada-002",
        )
        self.save_dir = CONFIG["plan_save_dir"]
        self.pool_id = CONFIG.pool_id

        if init_mode:
            MemoryDB_clear()
            self.index = VectorStoreIndex(nodes=[], embed_model=self.embed_model)
            print("PlanMemoryDB FIRST init finished")
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
                print("PlanMemoryDB read from config storage success")
            except Exception as e:
                print(e)
                print("MemoryDB read from config storage failed, init new index")
                MemoryDB_clear()
                self.index = VectorStoreIndex(nodes=[], embed_model=self.embed_model)
                print("MemoryDB FIRST init finished")

    def insert_sentence(
        self,
        query,
        subplans,
        status,
    ):
        """
        plan structure
        """
        if not self.insert_mode:
            return

        new_node = TextNode(
            text=query,
            metadata={
                "query": query,
                "subplans": subplans,
                "status": status,
            },
        )
        try:
            self.index.insert_nodes([new_node])
            print(f"insert {query} success!")

        except Exception as e:
            print(e)
            print("Warning: Fail to insert", query)

    def search_similar_sentences(self, query_sentence: str, status, top_k=3):
        """
        return the top_k similar sentences 
        """
        filters = MetadataFilters(
            filters=[
                MetadataFilter(
                    key="status",
                    value=status,
                    operator=FilterOperator.EQ,
                ),
            ]
        )

        retriever = self.index.as_retriever(similarity_top_k=top_k, filters=filters)

        try:
            res = retriever.retrieve(query_sentence)
            ans = []
            for node in res:
                if node.get_score(node) > CONFIG["plan_score_threshold"]:
                    node = node.to_dict()
                    ans.append(
                        {
                            "relevant task": node["node"]["metadata"]["query"],
                            "relevant knowledge": node["node"]["metadata"]["subplans"],
                        }
                    )
            str = ""
            for index, p in enumerate(ans):
                str += format_dict(p, index)

            return str
        except Exception as e:
            print(e)
            print("Warning: Fail to search similar sentences")

    def search_nodes(self, query_text):
        return self.retriever.retrieve(
            query_text,
        )

    def save_vector(self):
        self.index.storage_context.persist(persist_dir=self.save_dir)


# FOR TESTING
if __name__ == "__main__":
    DB = PlanMemoryDB(init_mode=False)
    print("d")
    query_text = "calculate 1+1"
    DB.insert_sentence(
        "calculate (232+17*2)/2",
        ["calculate 232+17*2", "calculate the before answer/2"],
        "SUCCESS",
    )
    result_node = DB.search_similar_sentences(query_text, "SUCCESS")
    print(result_node)
    DB.save_vector()
