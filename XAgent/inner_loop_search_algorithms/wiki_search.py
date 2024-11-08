import ast
import json
import time
from XAgent.config import CONFIG
from openai import AzureOpenAI
import re

import requests
from bs4 import BeautifulSoup

# import wikipedia


def clean_str(p):
    return p.encode().decode("unicode-escape").encode("latin1").decode("utf-8")


class WikiEnv:

    def __init__(self):
        """
        Initialize the environment.
        """
        super().__init__()
        self.page = None  # current Wikipedia page
        self.obs = None  # current observation
        self.lookup_keyword = None  # current lookup keyword
        self.lookup_list = None  # list of paragraphs containing current lookup keyword
        self.lookup_cnt = None  # current lookup index
        self.steps = 0  # current number of steps
        self.answer = None  # current answer from the agent

        self.search_time = 0
        self.num_searches = 0

    def _get_obs(self):
        return self.obs

    def _get_info(self):
        return {"steps": self.steps, "answer": self.answer}

    def reset(self, seed=None, return_info=False, options=None):
        # We need the following line to seed self.np_random
        # super().reset(seed=seed)
        self.obs = (
            "Interact with Wikipedia using search[], lookup[], and " "finish[].\n"
        )
        self.page = None
        self.lookup_keyword = None
        self.lookup_list = None
        self.lookup_cnt = None
        self.steps = 0
        self.answer = None
        observation = self._get_obs()
        info = self._get_info()
        return (observation, info) if return_info else observation

    def construct_lookup_list(self, keyword):
        # find all paragraphs
        if self.page is None:
            return []
        paragraphs = self.page.split("\n")
        paragraphs = [p.strip() for p in paragraphs if p.strip()]

        # find all sentence
        sentences = []
        for p in paragraphs:
            sentences += p.split(". ")
        sentences = [s.strip() + "." for s in sentences if s.strip()]

        parts = sentences
        parts = [p for p in parts if keyword.lower() in p.lower()]
        return parts

    @staticmethod
    def get_page_obs(page):
        # find all paragraphs
        paragraphs = page.split("\n")
        paragraphs = [p.strip() for p in paragraphs if p.strip()]

        # find all sentence
        sentences = []
        for p in paragraphs:
            sentences += p.split(". ")
        sentences = [s.strip() + "." for s in sentences if s.strip()]
        return " ".join(sentences[:5])

        # ps = page.split("\n")
        # ret = ps[0]
        # for i in range(1, len(ps)):
        #   if len((ret + ps[i]).split(" ")) <= 50:
        #     ret += ps[i]
        #   else:
        #     break
        # return ret

    def search_step(self, entity):
        entity_ = entity.replace(" ", "+")
        search_url = f"https://en.wikipedia.org/w/index.php?search={entity_}"
        proxies = {
            "http": "http://127.0.0.1:7890",
            "https": "http://127.0.0.1:7890",  # https -> http
        }
        old_time = time.time()
        response_text = requests.get(search_url, proxies=proxies).text
        self.search_time += time.time() - old_time
        self.num_searches += 1
        soup = BeautifulSoup(response_text, features="html.parser")
        result_divs = soup.find_all("div", {"class": "mw-search-result-heading"})
        if result_divs:  # mismatch
            self.result_titles = [
                clean_str(div.get_text().strip()) for div in result_divs
            ]
            self.obs = f"Could not find {entity}. Similar: {self.result_titles[:5]}."
        else:
            page = [
                p.get_text().strip() for p in soup.find_all("p") + soup.find_all("ul")
            ]
            if any("may refer to:" in p for p in page):
                self.search_step("[" + entity + "]")
            else:
                self.page = ""
                for p in page:
                    if len(p.split(" ")) > 2:
                        self.page += clean_str(p)
                        if not p.endswith("\n"):
                            self.page += "\n"
                self.obs = self.get_page_obs(self.page)
                self.lookup_keyword = self.lookup_list = self.lookup_cnt = None
        print(self.obs)
        return self.obs

    def get_time_info(self):
        speed = self.search_time / self.num_searches if self.num_searches else 0
        return {
            "call_speed": speed,
            "call_time": self.search_time,
            "num_calls": self.num_searches,
        }


def call_engine(query):
    """
    ask chatgpt
    """
    model = CONFIG.eva_model
    model_name = CONFIG.api_keys[model][0]["engine"]
    message = [{"content": query, "role": "user"}]
    response = None
    temp = int(CONFIG.default_completion_kwargs["temperature"])

    try:
        client = AzureOpenAI(
            api_key=CONFIG.api_keys[model][0]["api_key"],
            api_version=CONFIG.api_keys[model][0]["api_version"],
            azure_endpoint=CONFIG.api_keys[model][0]["api_base"],
        )
        response = client.chat.completions.create(
            model=model_name,
            messages=message,
            temperature=temp,
        )

        response = response.choices[0].message.content
        return response

    except Exception as e:
        print(e)
        print(f"chatcompletion: {model_name} Score Fail")
        return None


def search_from_concept(goal):
    wiki = WikiEnv()
    concept = call_engine(
        "I'm solving a difficult chemistry problem, please distill an incomprehensible chemistry concept from a problem, I'll look it up on the wiki. Don't answer superfluous, just return a concept. The questions are as follows: "
        + goal
    )
    res = wiki.search_step(concept)
    if "Could not find" in res:
        return ""
    else:
        return "\nHere are some relevant materials to help you: " + str(res) + "\n"


search_from_concept("sun")
