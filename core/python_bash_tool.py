import subprocess
import asyncio
from typing import Optional, Type
from langchain.tools import BaseTool
from pydantic import BaseModel, Field


class WindowsCmdInput(BaseModel):
    """CMD 命令执行工具的输入参数校验"""
    command: str = Field(description="需要在 Windows CMD 中执行的命令（例如：dir, ipconfig, echo 你好）")
    timeout: Optional[int] = Field(default=30, description="命令执行超时时间（秒），默认30秒")


class WindowsCmdTool(BaseTool):
    name: str = "windows_cmd"
    description: str = (
        "在 Windows 系统的 CMD 终端中执行命令，支持所有原生 CMD 指令，"
        "返回 UTF-8 编码的执行结果，可用于查看文件、执行脚本、查询系统信息等操作。"
        "注意：请勿执行危险、删除、格式化等破坏性命令！"
    )
    args_schema: Type[BaseModel] = WindowsCmdInput

    def _run(
        self,
        command: str,
        timeout: Optional[int] = 30
    ) -> str:
        """同步执行 CMD 命令（LangChain 同步调用）"""
        try:
            # 核心：Windows CMD 强制 UTF-8 编码 + 隐藏命令行窗口
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

            # 执行命令，指定编码为 utf-8，捕获标准输出+标准错误
            result = subprocess.run(
                command,
                shell=True,        # 必须开启，才能执行 CMD 命令
                startupinfo=startupinfo,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,         # 文本模式输出
                encoding="utf-8",  # 强制 UTF-8 编码（解决中文乱码）
                timeout=timeout
            )

            # 拼接输出结果
            output = result.stdout.strip()
            error = result.stderr.strip()

            if result.returncode != 0:
                return f"命令执行失败（错误码：{result.returncode}）\n错误信息：{error}"
            return f"命令执行成功！\n输出结果：\n{output if output else '无输出内容'}"

        except subprocess.TimeoutExpired:
            return f"命令执行超时！超时时间：{timeout} 秒"
        except Exception as e:
            return f"命令执行异常：{str(e)}"

    async def _arun(
        self,
        command: str,
        timeout: Optional[int] = 30
    ) -> str:
        """异步执行 CMD 命令（LangChain 异步调用）"""
        try:
            # Windows CMD 异步执行 + UTF-8 编码
            proc = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                creationflags=subprocess.CREATE_NO_WINDOW  # 隐藏窗口
            )

            # 等待执行完成并读取输出
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(),
                timeout=timeout
            )

            # UTF-8 解码
            output = stdout.decode("utf-8").strip()
            error = stderr.decode("utf-8").strip()

            if proc.returncode != 0:
                return f"命令执行失败（错误码：{proc.returncode}）\n错误信息：{error}"
            return f"命令执行成功！\n输出结果：\n{output if output else '无输出内容'}"

        except asyncio.TimeoutError:
            return f"命令执行超时！超时时间：{timeout} 秒"
        except Exception as e:
            return f"命令执行异常：{str(e)}"


# ------------------- 测试工具 -------------------
if __name__ == "__main__":
    # 初始化工具
    cmd_tool = WindowsCmdTool()

    # 测试 1：执行中文命令（验证 UTF-8 编码）
    print("===== 测试中文命令 =====")
    print(cmd_tool.run("echo 你好，这是 LangChain CMD 工具！"))

    # 测试 2：执行系统命令
    print("\n===== 测试系统命令 =====")
    print(cmd_tool.run("dir"))