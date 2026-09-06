"""测试 LLM API 的不同访问方式和流式输出

测试内容：
1. OpenAI SDK 方式（当前使用）
2. Claude (Anthropic) SDK 方式
3. 流式输出实现
"""

import json
from rich.console import Console

console = Console()

# ==================== 测试 1: OpenAI SDK 流式输出 ====================
def test_openai_streaming():
    """测试 OpenAI SDK 的流式输出"""
    console.rule("[bold cyan]测试 1: OpenAI SDK 流式输出[/bold cyan]")

    try:
        from openai import OpenAI

        client = OpenAI(
            api_key="not-needed",
            base_url="http://100.64.0.5:8000/v1"
        )

        console.print("[green]✓[/green] OpenAI 客户端初始化成功\n")

        # 流式请求
        console.print("[bold]开始流式请求...[/bold]\n")
        stream = client.chat.completions.create(
            model="qwen36-local",
            messages=[{"role": "user", "content": "用100字介绍艾宾浩斯记忆曲线"}],
            temperature=0.7,
            max_tokens=500,
            stream=True  # 启用流式输出
        )

        full_content = ""
        full_reasoning = ""

        for chunk in stream:
            if chunk.choices:
                delta = chunk.choices[0].delta

                # 检查 content 字段
                if hasattr(delta, 'content') and delta.content:
                    content_chunk = delta.content
                    full_content += content_chunk
                    console.print(content_chunk, end="", style="green")

                # 检查 reasoning 字段
                if hasattr(delta, 'reasoning') and delta.reasoning:
                    reasoning_chunk = delta.reasoning
                    full_reasoning += reasoning_chunk
                    console.print(reasoning_chunk, end="", style="dim cyan")

        console.print("\n\n[bold]流式输出完成[/bold]")
        console.print(f"Content 长度: {len(full_content)}")
        console.print(f"Reasoning 长度: {len(full_reasoning)}")

        if full_content:
            console.print("\n[bold green]✓ Content 字段有内容（标准模式）[/bold green]")
        elif full_reasoning:
            console.print("\n[bold yellow]⚠ 只有 Reasoning 字段有内容（推理模式）[/bold yellow]")

        return True

    except Exception as e:
        console.print(f"[red]✗[/red] OpenAI 流式测试失败: {e}")
        import traceback
        console.print(traceback.format_exc())
        return False


# ==================== 测试 2: Claude (Anthropic) SDK ====================
def test_anthropic_sdk():
    """测试 Anthropic SDK 访问方式"""
    console.rule("[bold cyan]测试 2: Claude (Anthropic) SDK[/bold cyan]")

    try:
        from anthropic import Anthropic

        client = Anthropic(
            api_key="not-needed",
            base_url="http://100.64.0.5:8000"  # 注意：Anthropic SDK 可能不需要 /v1
        )

        console.print("[green]✓[/green] Anthropic 客户端初始化成功\n")

        console.print("[bold]发送请求...[/bold]\n")
        message = client.messages.create(
            model="qwen36-local",
            max_tokens=500,
            messages=[
                {"role": "user", "content": "用一句话介绍你自己"}
            ]
        )

        console.print(f"Response type: {type(message)}")
        console.print(f"Content: {message.content}")

        console.print("\n[bold green]✓ Anthropic SDK 访问成功[/bold green]")
        return True

    except ImportError:
        console.print("[yellow]⚠[/yellow] anthropic 包未安装，尝试安装...")
        import subprocess
        result = subprocess.run(
            ["pip", "install", "anthropic"],
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            console.print("[green]✓[/green] anthropic 安装成功，请重新运行测试")
        else:
            console.print(f"[red]✗[/red] 安装失败: {result.stderr}")
        return False

    except Exception as e:
        console.print(f"[red]✗[/red] Anthropic SDK 测试失败: {e}")
        import traceback
        console.print(traceback.format_exc())

        # 尝试其他端点
        console.print("\n[yellow]尝试其他端点...[/yellow]")
        try:
            client = Anthropic(
                api_key="not-needed",
                base_url="http://100.64.0.5:8000/v1"
            )
            message = client.messages.create(
                model="qwen36-local",
                max_tokens=500,
                messages=[
                    {"role": "user", "content": "你好"}
                ]
            )
            console.print("[green]✓[/green] 使用 /v1 端点成功")
            return True
        except Exception as e2:
            console.print(f"[red]✗[/red] /v1 端点也失败: {e2}")
            return False


# ==================== 测试 3: Anthropic SDK 流式输出 ====================
def test_anthropic_streaming():
    """测试 Anthropic SDK 的流式输出"""
    console.rule("[bold cyan]测试 3: Anthropic SDK 流式输出[/bold cyan]")

    try:
        from anthropic import Anthropic

        # 尝试不同的 base_url
        for base_url in ["http://100.64.0.5:8000", "http://100.64.0.5:8000/v1"]:
            try:
                client = Anthropic(
                    api_key="not-needed",
                    base_url=base_url
                )

                console.print(f"[bold]尝试端点: {base_url}[/bold]\n")

                with client.messages.stream(
                    model="qwen36-local",
                    max_tokens=500,
                    messages=[
                        {"role": "user", "content": "用50字介绍间隔重复学习法"}
                    ]
                ) as stream:
                    for text in stream.text_stream:
                        console.print(text, end="", style="green")

                console.print("\n\n[bold green]✓ Anthropic 流式输出成功[/bold green]")
                console.print(f"成功的端点: {base_url}")
                return True

            except Exception as e:
                console.print(f"[yellow]端点 {base_url} 失败: {e}[/yellow]\n")
                continue

        console.print("[red]✗[/red] 所有端点都失败")
        return False

    except ImportError:
        console.print("[yellow]⚠[/yellow] anthropic 包未安装")
        return False
    except Exception as e:
        console.print(f"[red]✗[/red] Anthropic 流式测试失败: {e}")
        import traceback
        console.print(traceback.format_exc())
        return False


# ==================== 测试 4: 直接 HTTP 请求测试 ====================
def test_direct_http():
    """直接使用 HTTP 请求测试 API 兼容性"""
    console.rule("[bold cyan]测试 4: 直接 HTTP 请求[/bold cyan]")

    try:
        import requests

        # 测试 OpenAI 兼容端点
        console.print("[bold]测试 OpenAI 格式 (/v1/chat/completions)...[/bold]")
        response = requests.post(
            "http://100.64.0.5:8000/v1/chat/completions",
            json={
                "model": "qwen36-local",
                "messages": [{"role": "user", "content": "你好"}],
                "max_tokens": 100,
                "stream": False
            },
            headers={"Content-Type": "application/json"},
            timeout=30
        )

        console.print(f"状态码: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            console.print(f"Response keys: {data.keys()}")
            console.print("[green]✓ OpenAI 格式兼容[/green]\n")
        else:
            console.print(f"[red]✗ 请求失败: {response.text}[/red]\n")

        # 测试 Anthropic 兼容端点
        console.print("[bold]测试 Anthropic 格式 (/v1/messages)...[/bold]")
        response = requests.post(
            "http://100.64.0.5:8000/v1/messages",
            json={
                "model": "qwen36-local",
                "messages": [{"role": "user", "content": "你好"}],
                "max_tokens": 100
            },
            headers={
                "Content-Type": "application/json",
                "anthropic-version": "2023-06-01"
            },
            timeout=30
        )

        console.print(f"状态码: {response.status_code}")
        if response.status_code == 200:
            console.print("[green]✓ Anthropic 格式兼容[/green]")
        else:
            console.print(f"[yellow]⚠ Anthropic 格式不支持: {response.text}[/yellow]")

        return True

    except Exception as e:
        console.print(f"[red]✗[/red] HTTP 请求测试失败: {e}")
        return False


# ==================== 主测试函数 ====================
def main():
    """运行所有测试"""
    console.print("\n")
    console.print("=" * 70, style="bold blue")
    console.print("LLM API 兼容性和流式输出测试", style="bold blue", justify="center")
    console.print("=" * 70, style="bold blue")
    console.print("\n")

    results = {
        "OpenAI 流式输出": test_openai_streaming(),
        "Anthropic SDK": test_anthropic_sdk(),
        "Anthropic 流式输出": test_anthropic_streaming(),
        "HTTP 直接请求": test_direct_http(),
    }

    console.print("\n")
    console.rule("[bold]测试结果汇总[/bold]")
    console.print()

    for test_name, result in results.items():
        status = "[green]✓ 通过[/green]" if result else "[red]✗ 失败[/red]"
        console.print(f"  {test_name}: {status}")

    console.print("\n")
    passed = sum(results.values())
    total = len(results)
    console.print(f"[bold]总计: {passed}/{total} 通过[/bold]")
    console.print()


if __name__ == "__main__":
    main()
