import requests


def Asr(File_Path):
    # 请求URL
    url = "https://open.bigmodel.cn/api/paas/v4/audio/transcriptions"

    # 请求头（Authorization 需替换为实际 API Key）
    headers = {
        "Authorization": "89537a50b18a4644a6c8829d8abc6493.w7oL0reCLw9qiVCL"
    }

    # 表单数据（multipart/form-data 格式）
    files = {
        "model": (None, "glm-asr-2512"),  # 普通表单字段，None 表示无文件名
        "stream": (None, "false"),       # 普通表单字段
        "file": open(File_Path, "rb")  # 文件字段，需指定文件路径
    }

    # 发送 POST 请求
    response = requests.post(url, headers=headers, files=files)

    # 打印响应内容（可根据需求处理）
    # print(response.json())
    return response.json().get("text")