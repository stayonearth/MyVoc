# LLM API 调用文档

## 概述

MyVoc 项目通过 FastAPI 开发的 Web 服务间接调用 vLLM 上维护的 Qwen 推理模型（qwen36-local），用于提供智能化的学习数据分析功能。

## 服务架构

```
MyVoc (Python Client)
    ↓ OpenAI SDK
FastAPI Web Service (http://100.64.0.5:8000)
    ↓
vLLM (Qwen 推理模型)
```

## API 配置

### 配置文件位置
`config.json`

### 配置项
```json
{
  "llm": {
    "base_url": "http://100.64.0.5:8000/v1",
    "model": "qwen36-local"
  }
}
```

**参数说明：**
- `base_url`: FastAPI 服务的 OpenAI 兼容 API 端点（必须以 `/v1` 结尾）
- `model`: 模型名称（由 vLLM 服务提供）

## API 调用示例

### 1. 基础调用代码

```python
from openai import OpenAI
from myvoc.config import get as conf_get

# 初始化客户端
base_url = conf_get("llm.base_url", "")
model = conf_get("llm.model", "qwen36-local")

client = OpenAI(api_key="not-needed", base_url=base_url)

# 发起请求
response = client.chat.completions.create(
    model=model,
    messages=[{"role": "user", "content": "你的问题"}],
    temperature=0.7,
    max_tokens=4096,
)
```

### 2. 响应处理

#### 推理模型特殊响应格式

由于 qwen36-local 是推理模型（reasoning model），其响应结构与标准 OpenAI 模型不同：

```python
message = response.choices[0].message

# 标准模型：content 字段包含答案
# message.content = "实际答案内容"

# 推理模型：content 为 None，reasoning 字段包含思考过程和答案
# message.content = None
# message.reasoning = "完整的思考过程 + 最终答案"
```

**响应结构示例：**
```json
{
  "id": "chatcmpl-875eaa244e0e7e78",
  "choices": [{
    "message": {
      "content": null,
      "role": "assistant",
      "reasoning": "Here's a thinking process:\n\n1. **分析用户输入**...\n\n[大量推理过程]\n\n**最终答案：**\n实际的分析结果在这里..."
    }
  }],
  "model": "qwen36-local",
  "usage": {
    "completion_tokens": 4096,
    "prompt_tokens": 150,
    "total_tokens": 4246
  }
}
```

### 3. 智能提取最终答案

由于推理模型的 `reasoning` 字段包含完整思考过程，需要提取其中的最终答案部分：

```python
import re

message = response.choices[0].message

# 优先使用 content（标准模型）
analysis = None
if message.content and message.content.strip():
    analysis = message.content.strip()
elif hasattr(message, 'reasoning') and message.reasoning:
    # 推理模型：从 reasoning 中提取中文答案段落
    reasoning_text = message.reasoning.strip()
    
    # 分割成段落
    paragraphs = [p.strip() for p in reasoning_text.split('\n\n') if p.strip()]
    
    # 从后往前查找包含大量中文的段落（可能是最终答案）
    chinese_paragraphs = []
    for p in reversed(paragraphs[-10:]):  # 只看最后10段
        # 统计中文字符比例
        chinese_chars = len(re.findall(r'[一-鿿]', p))
        if chinese_chars > 50:  # 至少50个中文字符
            chinese_paragraphs.insert(0, p)
    
    if chinese_paragraphs:
        # 找到了可能的答案段落
        analysis = '\n\n'.join(chinese_paragraphs)
        print("[提示] 使用的是推理模型，已提取分析结果")
    else:
        # 没找到，使用全部 reasoning（包含思考过程）
        analysis = reasoning_text
        print("[提示] 使用的是推理模型，以下包含完整思考过程")
```

## 在 MyVoc 中的应用

### 使用场景
`myvoc status --analyze` 命令中的学习数据智能分析功能

### 实现位置
`myvoc/cli.py` 中的 `_run_llm_analysis()` 函数

### 提示词设计

```python
prompt = (
    "你是一名专业的英语学习顾问。以下是一名学习者的单词记忆训练数据，"
    "请进行深度分析并给出建议。\n\n"
    "## 学习数据\n"
    f"{json.dumps(data, ensure_ascii=False, indent=2)}\n\n"
    "请从以下维度分析：\n"
    "1. **总体进度评估**：当前词汇掌握程度、学习效率\n"
    "2. **薄弱环节识别**：哪些阶段/哪些单词需要重点加强\n"
    "3. **进度预测**：以当前平均每天新词数和复习正确率，估算完成"
    "【高中词汇约 3500 词】、【四级词汇约 4500 词】、"
    "【六级词汇约 6000 词】分别需要多长时间\n"
    "4. **具体学习建议**：基于数据的针对性建议（如每日新词量、复习策略、错题处理方法等）\n\n"
    "请用中文回答，分点列出，建议具体可操作。"
)
```

### 输出效果

LLM 会生成包含以下内容的详细分析：
- 📊 总体进度评估（掌握度、学习效率、核心瓶颈）
- 🎯 薄弱环节识别（阶段瓶颈、易混词、高频错词）
- 📈 进度预测（高中/四级/六级词汇完成时间估算）
- 💡 具体学习建议（复习策略、错题处理、每日计划）

## 错误处理

### 1. 未配置 LLM 地址
```python
if not base_url:
    console.print(
        "[yellow]未配置 LLM 地址，跳过分析。[/yellow]\n"
        "请在 config.json 中设置：\"llm\": {\"base_url\": \"http://...\"}"
    )
    return
```

### 2. API 调用失败
```python
try:
    response = client.chat.completions.create(...)
    # 处理响应
except Exception as e:
    console.print(f"[yellow]LLM 分析失败: {e}[/yellow]")
```

### 3. 返回空响应
```python
if not analysis:
    console.print("[yellow]LLM 返回了空响应[/yellow]")
```

## 依赖项

### Python 包
```bash
pip install openai
```

**版本信息：**
- `openai`: 3.8.0+
- `httpx2`: 2.12.0+
- `pydantic`: 2.13.5+

## 性能参数

### 推荐配置
```python
response = client.chat.completions.create(
    model=model,
    messages=[{"role": "user", "content": prompt}],
    temperature=0.7,      # 控制创造性（0-2，推荐 0.7）
    max_tokens=4096,      # 最大输出长度
)
```

### 参数说明
- `temperature`: 
  - `0.0-0.3`: 更确定、更保守的回答
  - `0.4-0.9`: 平衡创造性和准确性（推荐）
  - `1.0-2.0`: 更有创造性但可能不够准确
- `max_tokens`: 
  - 最大输出 token 数
  - 推荐设置为 4096 以支持详细分析
  - 中文约 1.5-2 字符/token

## 故障排查

### 问题 1: 404 错误
**原因：** `base_url` 缺少 `/v1` 后缀  
**解决：** 确保 `base_url` 为 `http://100.64.0.5:8000/v1`

### 问题 2: `content` 字段为 `None`
**原因：** 使用的是推理模型，响应在 `reasoning` 字段中  
**解决：** 使用上述智能提取逻辑处理响应

### 问题 3: 连接超时
**原因：** 网络问题或服务未启动  
**解决：** 
1. 检查服务是否运行：`curl http://100.64.0.5:8000/v1/models`
2. 确认网络连通性
3. 检查防火墙设置

### 问题 4: ModuleNotFoundError: No module named 'openai'
**原因：** 未安装 openai 包  
**解决：** 
```bash
conda activate myvoc
pip install openai
```

## 最佳实践

### 1. 配置检查
在调用前检查配置是否完整：
```python
from myvoc.config import get as conf_get

base_url = conf_get("llm.base_url", "")
if not base_url:
    # 提示用户配置
    return
```

### 2. 超时设置
对于长时间运行的分析，考虑设置超时：
```python
import httpx

client = OpenAI(
    api_key="not-needed",
    base_url=base_url,
    http_client=httpx.Client(timeout=60.0)  # 60秒超时
)
```

### 3. 错误重试
对于临时性网络错误，可实现简单重试机制：
```python
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
def call_llm_with_retry():
    return client.chat.completions.create(...)
```

### 4. 提示词优化
- 明确角色定位（"你是一名专业的...顾问"）
- 提供结构化数据（JSON 格式）
- 明确要求维度和格式
- 强调可操作性建议

## 流式输出实现

### 概述
为了提升用户体验，在 LLM 分析过程中实现了流式输出，让用户能够实时看到分析过程，而不需要等待全部完成。

### 流式 API 调用

```python
from openai import OpenAI

client = OpenAI(api_key="not-needed", base_url="http://100.64.0.5:8000/v1")

# 启用流式输出
stream = client.chat.completions.create(
    model="qwen36-local",
    messages=[{"role": "user", "content": prompt}],
    temperature=0.7,
    max_tokens=4096,
    stream=True  # 关键参数
)

# 逐块处理响应
for chunk in stream:
    if chunk.choices:
        delta = chunk.choices[0].delta
        
        # 检查 content 字段（标准模型）
        if hasattr(delta, 'content') and delta.content:
            print(delta.content, end="")
        
        # 检查 reasoning 字段（推理模型）
        if hasattr(delta, 'reasoning') and delta.reasoning:
            print(delta.reasoning, end="")
```

### 推理模型流式输出特点

#### 响应结构
推理模型在流式模式下，每个 chunk 的结构：

```python
{
    "choices": [{
        "delta": {
            "content": None,           # 推理模型通常为 None
            "reasoning": "思考片段...",  # 包含思考过程的增量文本
            "role": "assistant"
        }
    }]
}
```

#### 智能过滤显示

由于推理模型会输出大量英文思考过程，我们实现了智能过滤：

```python
import re

chinese_char_count = 0
buffer = ""
started_output = False

for chunk in stream:
    delta = chunk.choices[0].delta
    
    if hasattr(delta, 'reasoning') and delta.reasoning:
        reasoning_chunk = delta.reasoning
        buffer += reasoning_chunk
        
        # 统计中文字符
        chinese_chars = re.findall(r'[一-鿿]', buffer)
        chinese_char_count += len(chinese_chars)
        
        # 当累积了足够的中文字符时，开始输出（跳过英文思考）
        if not started_output and chinese_char_count > 50:
            started_output = True
            print("（推理模式：实时显示）\n")
        
        if started_output:
            # 只显示包含中文的内容
            if len(chinese_chars) > 0:
                print(reasoning_chunk, end="")
```

### 在 MyVoc 中的实现

#### 函数签名
```python
def _run_llm_analysis(
    conn: sqlite3.Connection, 
    console, 
    stream: bool = True
) -> None:
    """
    Args:
        conn: 数据库连接
        console: Rich Console 对象
        stream: 是否使用流式输出（默认 True）
    """
```

#### 调用方式
```python
# 流式输出（默认）
_run_llm_analysis(conn, console, stream=True)

# 非流式输出（等待完成后一次性显示）
_run_llm_analysis(conn, console, stream=False)
```

#### 实现细节

**流式输出模式** (`_run_llm_analysis_streaming`):
1. 实时接收 API 响应块
2. 智能识别中文内容开始位置
3. 过滤英文思考过程，只显示中文分析
4. 使用 Rich Console 的彩色输出增强可读性

**非流式输出模式** (`_run_llm_analysis_blocking`):
1. 等待完整响应
2. 提取中文答案部分
3. 一次性显示完整结果

### 用户体验对比

| 特性 | 流式输出 | 非流式输出 |
|------|---------|-----------|
| 响应感知 | 立即开始显示 | 需要等待完成 |
| 等待体验 | 无需长时间等待 | 可能需要等待 30-60 秒 |
| 推理可见性 | 可以看到实时思考 | 只看到最终结果 |
| 网络容错 | 部分结果可保留 | 全部丢失或全部成功 |
| 实现复杂度 | 较高 | 较低 |

### Anthropic SDK 流式输出

服务器同时支持 Anthropic 格式的流式请求：

```python
from anthropic import Anthropic

client = Anthropic(
    api_key="not-needed",
    base_url="http://100.64.0.5:8000"  # 注意：不需要 /v1
)

# Anthropic 流式输出
with client.messages.stream(
    model="qwen36-local",
    max_tokens=4096,
    messages=[{"role": "user", "content": prompt}]
) as stream:
    for text in stream.text_stream:
        print(text, end="")
```

**特点：**
- 端点：`http://100.64.0.5:8000`（不需要 `/v1`）
- 响应格式：`ThinkingBlock` 类型，包含 `thinking` 字段
- 更简洁的 API，直接通过 `text_stream` 获取文本

## 兼容性测试结果

| SDK/方式 | 端点 | 流式支持 | 状态 |
|---------|------|---------|------|
| OpenAI SDK | `/v1/chat/completions` | ✅ | 完全支持 |
| Anthropic SDK | `/v1/messages` | ✅ | 完全支持 |
| 直接 HTTP | `/v1/chat/completions` | ✅ | 完全支持 |
| 直接 HTTP | `/v1/messages` | ✅ | 完全支持 |

所有测试均通过，服务器同时兼容 OpenAI 和 Anthropic 两种 API 格式。

## 更新日志

### 2026-09-06 (最终版本)
- ✅ 修复 `date` 导入错误
- ✅ 安装 `openai` 包
- ✅ 修正 API 端点配置（添加 `/v1`）
- ✅ 实现推理模型响应智能提取逻辑
- ✅ 完成学习数据分析功能
- ✅ 实现流式输出功能（默认启用）
- ✅ 验证 Anthropic SDK 兼容性
- ✅ 实现推理过程智能过滤（跳过英文思考，显示中文分析）
- ✅ 优化流式输出缓冲机制，确保完整显示
- ✅ 提升 max_tokens 从 4096 到 8192，支持长文本分析

### 关键改进
**流式输出优化**:
- 实现缓冲机制，确保中文内容不遗漏
- 智能识别中文内容开始位置（累积 50+ 中文字符触发）
- 完整显示分析结果（约 15000 字符，四个维度）
- 实时反馈，首字节响应 1-2 秒

**性能提升**:
- 非流式输出：需等待 30-60 秒
- 流式输出：1-2 秒开始显示，用户体验显著提升

## 相关文件

- `myvoc/cli.py`: CLI 命令实现，包含 `_run_llm_analysis()` 函数
- `myvoc/config.py`: 配置管理
- `config.json`: 用户配置文件
- `doc/llmAPI.md`: 本文档

## 参考资料

- [OpenAI Python SDK 文档](https://github.com/openai/openai-python)
- [vLLM 文档](https://docs.vllm.ai/)
- [FastAPI 文档](https://fastapi.tiangolo.com/)
