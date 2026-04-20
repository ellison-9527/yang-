from langchain.agents import create_agent
from langchain_core.messages import AIMessageChunk
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
    max_token=10000,
    temperature=0.5
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
    tool_chunk = None  # 存储模型调用工具的消息
    async for token,metadate in agent.astream(
            {"messages": messages},
            stream_mode="messages",
    ):
        # print(type(token),token)

        node = metadate.get("langgraph_node","")
        # print("token start-----------\n",type(token),"\n",token)
        # print("token start-----------\n",type(token),"\n",token)
        # 查询一下长沙今天天气，获取一下腾讯skill怎么用

        if node =="model":  # AI回复内容  ，调用工具的内容
            # https://reference.langchain.com/python/langchain-core/messages/tool/ToolCallChunk
            # 参考这个链接，将工具的分块拼在一起形成一个完整的工具调用消息
            if getattr(token,"tool_call_chunks" , None):
                if tool_chunk is None:
                    tool_chunk = AIMessageChunk(content="", tool_call_chunks=token.tool_call_chunks)
                elif isinstance(tool_chunk, AIMessageChunk):
                    tool_chunk += AIMessageChunk(content="", tool_call_chunks=token.tool_call_chunks)
            elif token.response_metadata.get("finish_reason")=="tool_calls":
                # print("工具调用生成完成\n",tool_chunk)
                is_parallel = True if len(tool_chunk.tool_calls) >1 else  False
                for tool_call in tool_chunk.tool_calls:
                    name = tool_call['name']
                    id = tool_call['id']
                    args = tool_call['args']
                    print(f"是否可并行：{is_parallel}====工具调用: {name}====工具参数: {args}")
                    yield {
                        "type": "tool_call",
                        "id": id,
                        "name": name,
                        "args": args,
                        "is_parallel": is_parallel
                    }
                tool_chunk = None
            # 文本内容 token  如果AImessage 有内容，则表示AI生成的回复消息
            elif token.content:
                print(token.content,end='')
                yield {"type": "token", "content": token.content}

        elif node == "tools":  # 工具返回的结果 网络搜索引擎搜索一下现在的时间
            content = token.content
            id = token.tool_call_id
            if content:
                print(f"工具{token.name}-{id}的返回结果为\n{content}")
                yield{
                    "type":"tools_result",
                    "id":id,
                    "name": getattr(token, "name", "tool"),
                    "content":content
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
