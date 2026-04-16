from langchain.agents import create_agent
from langchain_openai import ChatOpenAI
import os
from dotenv import load_dotenv

from core.tools import get_all_tools

# 加载 .env 文件中的环境变量
load_dotenv()


def get_llm(
        max_token=4096,
        temperature=0.5
):
    return  ChatOpenAI(
            base_url = os.getenv("OPENAI_BASE_URL"),
            model = os.getenv("OPENAI_MODEL"),
            api_key=os.getenv("OPENAI_API_KEY"),
            max_tokens=max_token,
            temperature=temperature,
            streaming=True
        )

async def agent_chat_stream(
    messages,
    system_prompt,
    max_token,
    temperature
):
    """
            流式运行 ReAct Agent，yield 事件:
              {"type": "token", "content": "..."}        - 逐 token 文本流
              {"type": "tool_call", "name": "...", "args": {...}}  - 工具调用
              {"type": "tool_result", "name": "...", "content": "..."}  - 工具返回

            使用 stream_mode="messages" 实现最终回复的逐 token 流式输出。
    """
    agent =  await  create_chat_agent(system_prompt, max_token, temperature)
    name = ""
    id = ""
    async for token,metadate in agent.astream(
            {"messages": messages},
            stream_mode="messages",
    ):
        # print(type(token),token)

        node = metadate.get("langgraph_node","")
        # print("token start-----------\n",type(token),"\n",token)
        # 查询一下长沙今天天气，获取一下腾讯skill怎么用
        if node =="model":  # AI回复内容  ，调用工具的内容
            complete_tool_calls = getattr(token, "tool_calls", None) or []
            if complete_tool_calls:
                for tc in complete_tool_calls:
                    if tc.get("id") and tc.get("name"):
                          id = tc["id"]
                          name = tc["name"]
                    elif tc.get("args")!={}:
                        args = tc.get("args")
                        # print(f"{id}-{name}-{args}")
                        yield {
                            "type": "tool_call",
                            "id" : id,
                            "name": name,
                            "args": args,
                        }

            # 文本内容 token
            elif token.content:
                yield {"type": "token", "content": token.content}

        elif node == "tools":  # 工具返回的结果 网络搜索引擎搜索一下现在的时间
            content = token.content
            id = token.tool_call_id
            # print(f"{id}:\n{content}")
            if content:
                yield{
                    "type":"tools_result",
                    "id":id,
                    "name": getattr(token, "name", "tool"),
                    "content":content[:1000]
                }


async  def create_chat_agent(
        system_prompt,
        max_token=4096,
        temperature=0.5
):
    llm = get_llm(max_token,temperature)
    tools = await  get_all_tools()
    agent =   create_agent(model = llm,tools = tools,system_prompt=system_prompt)
    return agent
