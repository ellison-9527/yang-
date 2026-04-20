import base64

import gradio as gr


from langchain.agents import create_agent
from langchain_openai import ChatOpenAI

from core.agent import create_chat_agent, agent_chat_stream
from core.my_asr import Asr
from core.my_tts import tts
# 存储多轮对话
lc_message = []

async def agent_ui_flush(lc_message,history,system_prompt,max_token,temperature):
    """
            生成输出并刷新ui
            正常一轮流程  先 工具调用  ->   工具结果  ->   AI消息
    """
    # history.append({'role': 'user', 'content': user})  # 用户消息

    # history.append({"role": "assistant", "content": "正在思考中...", "metadata": {"title": "🤔 思考中"}})
    # yield history, {}
    async  for event in agent_chat_stream(lc_message,system_prompt,max_token,temperature):
        if event["type"] == "tool_call":
            # 百叶窗: 工具调用，状态 pending
            history.append({
                "role": "assistant",
                "content": "",
                "metadata": {
                    "title": f"tools:并行: {event['is_parallel']} - {event['name']}",
                    "status": "pending",
                    "id": event["id"],
                    "args": event["args"],
                },
            })
            yield history
            print(f'tools:{event["name"]}{event["args"]}')
        elif event["type"] == "tools_result":
            for message in history[::-1]:
                # print(f"tools:{event['content']}")
                if message.get("metadata") :
                    id = message["metadata"].get("id")
                    if id == event["id"]:
                        message["content"] += f"{event['name']} {message['metadata'].get('args')}\n\n--- 返回结果 ---\n{event['content']}"
                        message["metadata"]["status"] = "done"
                        print(f'tools result:{event["name"]}{event["content"]}')
                        yield history
                        break

                # print(f'tools result:{event["name"]}{event["content"]}')
        elif event["type"] == "token":
            # 逐 token 流式输出最终回答
            if (
                    history[-1].get("metadata") is not None or history[-1]["role"] != "assistant"
            ):
                history.append({
                    "role": "assistant",
                    "content": "",
                })
            history[-1]["content"] += event["content"]
            # print(f'AI: {event["content"]}')
            yield history

    """根据用户问题流式输出答案并刷新ui"""


async def chat(message,history,system_prompt,max_token,temperature):

    """数据解析-------------------------------------------------"""
    # print( message)
    user =message.get("text")
    files = message.get("files")

    if files: # 多模态消息
        mutil_content = []
        for file in files:
            # 判断是否为图片格式
            if file.endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp')):
                history.append({"role": "user", "content": {"path": file}})  # 用户消息
                with open(file, "rb") as img_file:
                    img_base = base64.b64encode(img_file.read()).decode("utf-8")
                    mutil_content.append({"type":"image_url","image_url":{"url": img_base}})
            elif file.endswith('.wav'):
                user = Asr(file)
        mutil_content.append({"type":"text","text":user})
        lc_message.append({"role":"user","content":mutil_content})
    else: # 文本消息
        lc_message.append({"role": "user", "content": user})

    history.append({'role': 'user', 'content': user})  # 更新历史记录
    yield history, {}
    """agent处理-------------------------------------------------"""
    # agent = await  create_chat_agent(system_prompt, max_token, temperature)
    # await agent_chat_stream(lc_message,system_prompt,max_token,temperature)
    async for history in agent_ui_flush(lc_message,history,system_prompt,max_token,temperature):
        yield history, {}

    # print(result['messages'][-1].content)
    """消息后处理-------------------------------------------------"""
    # lc_message.append({'role': 'assistant', 'content': result['messages'][-1].content})
    # history.append({'role': 'assistant', 'content': result['messages'][-1].content})  # 用户消息
    # # await  tts(result['messages'][-1].content)
    # yield history, {}

SYS_PROMOT="""
    # Role: 私人助手
    ## Profile:
        - Description: 你是一名专业的私人助手，能够从复杂文本中提炼关键信息并拆解任务并一步一步完成
    ## Skills:
        1. 能够全面理解用户问题，识别核心概念、事实与逻辑结构。
        2. 擅长任务的规划
        3. 善于理解任务中的报错信息并尝试修复
    ## Workflow:
        1. **任务拆解**：通读全文，分段识别关键实体、事件、数值与结论。对任务进行拆解成单步或多步
        2. **工具调用**：当任务可操作时，首先使用真正的工具调用或具体行动；不要止步于计划或承诺采取行动。
        3. **质量检查**：逐条校验自己的步骤，确保：
           - 拆分的任务都非常精简并和合理
           - 传递给工具的参数无语法错误
           - 确保任务都是以用户的问题展开

    ## Constraints:
        1. 所有答案必须严格依据上下文内容，不得添加外部信息或假设情境。
        2. 只有当任务已经完成才结束思考。\n\n
    用户的问题如下：
"""

def create_chat_tab():
    with gr.Row():
        with gr.Column(scale=1):
            session_btn = gr.Button("新建对话")
        with gr.Column(scale=5):
            # 创建聊天显示区域
            chatbot = gr.Chatbot(
                label='agent',
                avatar_images=(
                    "./assert/user.png",
                    "./assert/bot.png"
                ),
                min_height=700
            )

            #  创建多模态输入框
            chat_input = gr.MultimodalTextbox(
                file_types=["image", "video", "audio", ".pdf", ".docx"],
                file_count="multiple",  # # 允许多文件上传
                placeholder="请输入消息或上传文件...",
                show_label=False,
                sources=["microphone", "upload"]
            )


        with gr.Column(scale=2):
            system_prompt = gr.Text(label="系统提示词",lines=2,value="""
              你是一个有用的助手，可以调用相应工具帮用户解决问题。自己做决定，用户只需要最后的结果。一定要减少用户参与的频率。
                # 工作过程:
                    1、理解用户的问题
                    2、自主判断是否需要调用工具，不需要则直接回答
                    3、再调用工具的过程中，好好研读任务对应的skill，根据skill严格执行
                    4、获取工具的返回结果与用户的问题进行对比，如果结果与问题一致，则直接返回结果，否则回到步骤2
            """)
            max_token =  gr.Number(label="Maxtoken",value=20000,interactive=True)
            temperature = gr.Number(label="temperature", value=0.5, interactive=True)
    # 绑定事件回调函数
    chat_input.submit(
        fn=chat,
        inputs=[chat_input, chatbot,system_prompt,max_token,temperature],
        outputs=[chatbot, chat_input]
    )