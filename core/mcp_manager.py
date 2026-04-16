import asyncio
import json
from pathlib import Path
from langchain_mcp_adapters.client import  MultiServerMCPClient


CONFIG_FILE = Path(__file__).parent.parent/"data"/"mcp_server.json"

def load_config() -> dict:
    """将mcp配置内容更加状态进行取出"""
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        servers = json.load(f)
        print(servers)

    # 待删除的列表
    del_list = []
    """根据mcp状态进行筛选，将状态为false的服务剔除掉"""
    for name in servers.keys():
        enable = servers[name].get("enable")
        if enable :
             del servers[name]["enable"]
        else:
            del_list.append(name)

    for name in del_list:
        del servers[name]

    return servers

servers = load_config()
mcp_clint = MultiServerMCPClient(servers)
async def get_all_mcp_tools():

    tools = await mcp_clint.get_tools()
    return tools
    print(tools)

if __name__ == "__main__":
    asyncio.run(get_all_mcp_tools())