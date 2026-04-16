import base64

import gradio as gr


from langchain.agents import create_agent
from langchain_openai import ChatOpenAI

from core.agent import create_chat_agent, agent_chat_stream
from core.my_asr import Asr
from core.my_tts import tts

lc_message = []
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

    # history.append({'role': 'user', 'content': user})  # 用户消息
    history.append({'role': 'user', 'content': user})
    history.append({"role": "assistant", "content": "正在思考中...", "metadata": {"title": "🤔 思考中"}})
    yield history, {"text": "", "files": []}  # 清空输入框并先显示用户消息
    yield history, {}
    """agent处理-------------------------------------------------"""
    # agent = await  create_chat_agent(system_prompt, max_token, temperature)
    # await agent_chat_stream(lc_message,system_prompt,max_token,temperature)


    async  for event in agent_chat_stream(lc_message,system_prompt,max_token,temperature):
        if event["type"] == "tool_call":
            # 百叶窗: 工具调用，状态 pending
            history.append({
                "role": "assistant",
                "content": "",
                "metadata": {
                    "title": f"调用工具: {event['name']}\n{event['args']}\n",
                    "status": "pending",
                    "id": event["id"],
                },
            })
            yield history, {}
            print(f'tools:{event["name"]}{event["args"]}')
        elif event["type"] == "tools_result":
            for message in history[::-1]:
                # print(f"tools:{event['content']}")
                if message.get("metadata") :
                    id = message["metadata"].get("id")
                    if id == event["id"]:
                        message["content"] += f"\n\n--- 返回结果 ---\n{event['content']}"
                        message["metadata"]["status"] = "done"
                        print(f'tools result:{event["name"]}{event["content"]}')
                        yield history, {}
                        break

                # print(f'tools result:{event["name"]}{event["content"]}')
        elif event["type"] == "token":
            # 逐 token 流式输出最终回答
            if (
                    history[-1].get("metadata") is not None
            ):
                history.append({
                    "role": "assistant",
                    "content": "",
                })
            history[-1]["content"] += event["content"]
            # print(f'AI: {event["content"]}')
            yield history, {}


    # print(result['messages'][-1].content)
    """消息后处理-------------------------------------------------"""
    # lc_message.append({'role': 'assistant', 'content': result['messages'][-1].content})
    # history.append({'role': 'assistant', 'content': result['messages'][-1].content})  # 用户消息
    # # await  tts(result['messages'][-1].content)
    # yield history, {}


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
                )
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
            max_token =  gr.Number(label="Maxtoken",value=4096,interactive=True)
            temperature = gr.Number(label="temperature", value=0.5, interactive=True)
    # 绑定事件回调函数
    chat_input.submit(
        fn=chat,
        inputs=[chat_input, chatbot,system_prompt,max_token,temperature],
        outputs=[chatbot, chat_input]
    )