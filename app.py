
import gradio as gr

from ui.chat_tab import create_chat_tab


def create_app():
    with gr.Blocks(title = "AI 私人助手",fill_height= True) as demo:
        with gr.Tab('私人助手'):
            create_chat_tab()
        with gr.Tab('RAG管理'):
            pass
        with gr.Tab('MCP配置'):
            pass
        with gr.Tab('Skill配置'):
            pass

    return demo


if __name__ == "__main__":
    demo = create_app()
    demo.launch(server_name="0.0.0.0",server_port=8888)



