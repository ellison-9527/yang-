import locale
import os
import shutil
import subprocess
from pathlib import Path

import httpx
from bs4 import BeautifulSoup
from langchain_core.tools import tool, StructuredTool
from langchain_tavily import TavilySearch
from dotenv import load_dotenv
from pydantic import BaseModel, Field

from core.mcp_manager import get_all_mcp_tools
from core.python_bash_tool import  WindowsCmdTool

# 加载 .env 文件中的环境变量
load_dotenv()


@tool
def fetch_url(url: str) -> str:
    """抓取指定 URL 网页内容并返回纯文本。用于获取在线文档、文章、博客等网页内容。

    Args:
        url: 要抓取的网页 URL 地址
    """
    try:
        resp = httpx.get(

            url,
            timeout=30,
            follow_redirects=True,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            },
        )
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        # 移除无关标签
        for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
            tag.decompose()
        text = soup.get_text(separator="\n", strip=True)
        # 清理多余空行
        lines = [line for line in text.splitlines() if line.strip()]
        text = "\n".join(lines)
        return text[:8000]
    except Exception as e:
        return f"抓取失败: {str(e)}"

    # 初始化工具


cmd_tool = WindowsCmdTool()

tavily_search =   TavilySearch(max_results=5,api_key=os.getenv("TAVILY_API_KEY"))


all_tools = [fetch_url,tavily_search,cmd_tool]


"""SKILL相关工具----------------------------------------------------------------------------------"""

from core.skill_manager import scan,skills,get_skill_content_for_tool,get_skill_reference_content
class LoadSKILLInput(BaseModel):
    name:str = Field(description="要加载 skill 的名称")

class LoadSkillReferenceInput(BaseModel):
    name: str = Field(description="Skill 名称")
    path: str = Field(description="要读取的引用文件相对路径")

def _load_skill_impl(name: str):  # impl implementation 表具体实现
    """加载指定的skill 的主体内容与文件索引"""
    content = get_skill_content_for_tool(name)

    if content is None:
        return f"Skill '{name}' 未找到,请确认名称或重新检索相关skill"

    return content


def create_load_skill_tool():
    """创建load_skill工具，让大模型通过该工具可以加载相应skills技能包"""
    scan() # 扫描skills目录下所有的技能
    # print( skills)
    """将skill的名字和描述信息拼接成一个字符串  - name : desc"""
    skill_lines = []
    for name,skll in skills.items():
       desc = skll.get("description")
       if len(desc) > 1000:  # 截取前1000个字符
           desc = desc[:1000] + "..."
       skill_lines.append(f" - {name} : {desc}")

    skill_list = "\n".join(skill_lines) if skill_lines else "(暂无可用skill)" # 将多个skill技能信息拼接成一个大的字符串
    # print("skill_list\n",skill_list)
    # 填写工具的描述信息
    description = f"""当用户任务匹配某个 skill 时，优先调用本工具加载该skill获得专业的指导。只有在没有合适的skill时，才调用自带的工具。
        本工具返回skill的主体指令和引用文件目录，不会直接展开引用文件内容，当需要具体的引用文件内容时，再调用load_skill_reference。
        当前可用的skills:\n
        {skill_list}
    """
    # print( "description:\n",description)
    return StructuredTool.from_function(
        func=_load_skill_impl,
        name = "load_skill",        # 工具的名称
        args_schema=LoadSKILLInput, # 对输入参数进行约束
        description=description,  # 工具的描述信息
    )
def _load_skill_reference_impl(name: str, path: str) -> str: # impl  implementation 表示某个功能的具体实现代码。
    """按需加载指定 Skill 的单个引用文件"""
    content = get_skill_reference_content(name, path)
    # print(f"load_skill_reference: {name} -> {path}")
    if content is None:
        return f"Skill '{name}' 的引用文件 '{path}' 未找到，请先通过 load_skill 确认文件路径"
    return content
def create_load_skill_reference_tool() -> StructuredTool:
    """创建 load_skill_reference 工具，按需读取单个引用文件"""
    description = (
        "读取某个 Skill 的单个引用文件正文。"
        "请先调用 load_skill 获取可用文件路径，再按需读取具体文件。"
    )

    return StructuredTool.from_function(
        func=_load_skill_reference_impl,
        name="load_skill_reference",
        description=description,
        args_schema=LoadSkillReferenceInput,
    )




async def get_all_tools() -> list:
    tools = list(all_tools)
    mcp_tools =  await get_all_mcp_tools()
    tools.extend(mcp_tools)
    tools.append(create_load_skill_tool())
    tools.append(create_load_skill_reference_tool())
    return tools

if __name__ == "__main__":
    create_load_skill_tool()
    # print(fetch_url.run("https://docs.langchain.com/oss/python/langchain/streaming"))
    # print(tavily_search.run("gradio的官网网址是什么"))
