# -*- coding: utf-8 -*-
import json
from typing import List

from kag.interface import PromptABC


@PromptABC.register("company_only_ner")
class CompanyOnlyNERPrompt(PromptABC):
    template_en = """
{
  "instruction": "You are an information extraction expert. Extract company entities only. Output a JSON array. Each item must include: name, type, category, description. category must be exactly 'Company'. If no company is found, return [].",
  "schema": ["Company"],
  "input": "$input"
}
"""

    template_zh = """
{
  "instruction": "你是信息抽取专家。只抽取企业实体，并以JSON数组输出。每个元素包含name、type、category、description。category必须严格为'Company'。如果没有企业实体，返回[]。",
  "schema": ["Company"],
  "input": "$input"
}
"""

    def __init__(self, language: str = "", **kwargs):
        super().__init__(language, **kwargs)
        self.template = self.template

    @property
    def template_variables(self) -> List[str]:
        return ["input"]

    def parse_response(self, response: str, **kwargs):
        rsp = response
        if isinstance(rsp, str):
            rsp = json.loads(rsp)
        if isinstance(rsp, dict) and "output" in rsp:
            rsp = rsp["output"]
        if isinstance(rsp, dict) and "named_entities" in rsp:
            return rsp["named_entities"]
        return rsp
