"""华为云FunctionGraph Prompt模板生成器

提供华为云FunctionGraph Serverless函数的Prompt模板:
- AI推理函数模板(文本生成/摘要/翻译)
- 对话函数模板(多轮对话上下文管理)
- 向量嵌入函数模板(文本向量化)
- 内容审核函数模板(安全审查)
- 自定义函数模板

参考: 华为云FunctionGraph Python运行时 + ModelArts推理
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class FGTemplateType(Enum):
    AI_INFERENCE = "ai_inference"
    CONVERSATION = "conversation"
    EMBEDDING = "embedding"
    CONTENT_MODERATION = "content_moderation"
    CUSTOM = "custom"


@dataclass
class FGTemplate:
    name: str
    template_type: FGTemplateType
    description: str
    description_en: str
    runtime: str = "Python3.9"
    handler: str = "index.handler"
    code: str = ""
    env_vars: dict[str, str] = field(default_factory=dict)
    dependencies: list[str] = field(default_factory=list)
    prompt_variables: list[str] = field(default_factory=list)
    version: str = "1.0.0"


_AI_INFERENCE_TEMPLATE = '''# -*- coding: utf-8 -*-
"""
华为云FunctionGraph AI推理函数 — {name}
{description}
运行时: Python3.9 | 触发器: APIG | 模型: ModelArts
"""
import json
import urllib.request


def handler(event, context):
    """FunctionGraph入口函数"""
    try:
        body = json.loads(event.get("body", "{{}}"))
        prompt = body.get("prompt", "")
        if not prompt:
            return _response(400, {{"error": "缺少prompt参数"}})

        model_endpoint = context.getUserData("MODEL_ENDPOINT") or context.getEnvironmentVariable("MODEL_ENDPOINT")
        api_key = context.getAccessKey()
        region = context.getUserData("REGION") or "cn-north-4"

        result = _call_modelarts(model_endpoint, prompt, api_key, region)
        return _response(200, {{"result": result, "model": model_endpoint}})
    except Exception as e:
        context.getLogger().error(f"推理失败: {{e}}")
        return _response(500, {{"error": str(e)}})


def _call_modelarts(endpoint: str, prompt: str, api_key: str, region: str) -> str:
    """调用ModelArts推理端点"""
    url = f"https://{{endpoint}}.{{region}}.myhuaweicloud.com/v1/{{endpoint}}/infer"
    data = json.dumps({{"prompt": prompt, "max_tokens": 2048}}).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers={{
        "Content-Type": "application/json",
        "X-Auth-Token": api_key,
    }})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read()).get("result", "")


def _response(status: int, body: dict) -> dict:
    return {{
        "statusCode": status,
        "headers": {{"Content-Type": "application/json"}},
        "body": json.dumps(body, ensure_ascii=False),
    }}
'''

_CONVERSATION_TEMPLATE = '''# -*- coding: utf-8 -*-
"""
华为云FunctionGraph 对话函数 — {name}
{description}
支持多轮对话上下文管理, 使用OBS存储会话历史
"""
import json
import urllib.request


def handler(event, context):
    """FunctionGraph入口函数"""
    try:
        body = json.loads(event.get("body", "{{}}"))
        prompt = body.get("prompt", "")
        session_id = body.get("session_id", "default")
        if not prompt:
            return _response(400, {{"error": "缺少prompt参数"}})

        history = _load_history(session_id, context)
        history.append({{"role": "user", "content": prompt}})

        model_endpoint = context.getUserData("MODEL_ENDPOINT") or context.getEnvironmentVariable("MODEL_ENDPOINT")
        api_key = context.getAccessKey()

        result = _call_conversation(model_endpoint, history, api_key)
        history.append({{"role": "assistant", "content": result}})

        _save_history(session_id, history, context)
        return _response(200, {{"result": result, "session_id": session_id}})
    except Exception as e:
        context.getLogger().error(f"对话失败: {{e}}")
        return _response(500, {{"error": str(e)}})


def _call_conversation(endpoint: str, messages: list, api_key: str) -> str:
    url = f"https://{{endpoint}}.infer.myhuaweicloud.com/v1/chat/completions"
    data = json.dumps({{"messages": messages, "max_tokens": 2048}}).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers={{
        "Content-Type": "application/json",
        "X-Auth-Token": api_key,
    }})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read()).get("choices", [{{}}])[0].get("message", {{}}).get("content", "")


def _load_history(session_id: str, context) -> list:
    try:
        obs_client = context.getOBSClient()
        bucket = context.getUserData("HISTORY_BUCKET") or "fg-chat-history"
        data = obs_client.getObject(bucket, f"sessions/{{session_id}}.json")
        return json.loads(data) if data else []
    except Exception:
        return []


def _save_history(session_id: str, history: list, context) -> None:
    try:
        obs_client = context.getOBSClient()
        bucket = context.getUserData("HISTORY_BUCKET") or "fg-chat-history"
        obs_client.putObject(bucket, f"sessions/{{session_id}}.json", json.dumps(history, ensure_ascii=False))
    except Exception as e:
        context.getLogger().warning(f"保存历史失败: {{e}}")


def _response(status: int, body: dict) -> dict:
    return {{
        "statusCode": status,
        "headers": {{"Content-Type": "application/json"}},
        "body": json.dumps(body, ensure_ascii=False),
    }}
'''

_EMBEDDING_TEMPLATE = '''# -*- coding: utf-8 -*-
"""
华为云FunctionGraph 向量嵌入函数 — {name}
{description}
文本向量化 + 华为云CSS(Elasticsearch)存储
"""
import json
import urllib.request


def handler(event, context):
    """FunctionGraph入口函数"""
    try:
        body = json.loads(event.get("body", "{{}}"))
        text = body.get("text", "")
        if not text:
            return _response(400, {{"error": "缺少text参数"}})

        model_endpoint = context.getUserData("EMBEDDING_ENDPOINT") or context.getEnvironmentVariable("EMBEDDING_ENDPOINT")
        api_key = context.getAccessKey()

        embedding = _get_embedding(model_endpoint, text, api_key)
        return _response(200, {{"embedding": embedding, "dimensions": len(embedding)}})
    except Exception as e:
        context.getLogger().error(f"嵌入失败: {{e}}")
        return _response(500, {{"error": str(e)}})


def _get_embedding(endpoint: str, text: str, api_key: str) -> list:
    url = f"https://{{endpoint}}.infer.myhuaweicloud.com/v1/embeddings"
    data = json.dumps({{"input": text}}).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers={{
        "Content-Type": "application/json",
        "X-Auth-Token": api_key,
    }})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read()).get("data", [{{}}])[0].get("embedding", [])


def _response(status: int, body: dict) -> dict:
    return {{
        "statusCode": status,
        "headers": {{"Content-Type": "application/json"}},
        "body": json.dumps(body, ensure_ascii=False),
    }}
'''

_CONTENT_MODERATION_TEMPLATE = '''# -*- coding: utf-8 -*-
"""
华为云FunctionGraph 内容审核函数 — {name}
{description}
华为云内容审核 Moderation 服务集成
"""
import json
import urllib.request


def handler(event, context):
    """FunctionGraph入口函数"""
    try:
        body = json.loads(event.get("body", "{{}}"))
        text = body.get("text", "")
        if not text:
            return _response(400, {{"error": "缺少text参数"}})

        region = context.getUserData("REGION") or "cn-north-4"
        project_id = context.getUserData("PROJECT_ID") or context.getEnvironmentVariable("PROJECT_ID")
        api_key = context.getAccessKey()

        result = _moderate(text, region, project_id, api_key)
        is_safe = result.get("suggestion", "block") == "pass"
        return _response(200, {{
            "is_safe": is_safe,
            "suggestion": result.get("suggestion", "unknown"),
            "categories": result.get("categories", []),
        }})
    except Exception as e:
        context.getLogger().error(f"审核失败: {{e}}")
        return _response(500, {{"error": str(e)}})


def _moderate(text: str, region: str, project_id: str, api_key: str) -> dict:
    url = f"https://moderation.{{region}}.myhuaweicloud.com/v3/{{project_id}}/moderation/text"
    data = json.dumps({{"items": [{{"text": text, "type": "text"}}]}}).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers={{
        "Content-Type": "application/json",
        "X-Auth-Token": api_key,
    }})
    with urllib.request.urlopen(req, timeout=10) as resp:
        resp_data = json.loads(resp.read())
        return resp_data.get("result", {{}})


def _response(status: int, body: dict) -> dict:
    return {{
        "statusCode": status,
        "headers": {{"Content-Type": "application/json"}},
        "body": json.dumps(body, ensure_ascii=False),
    }}
'''

_TEMPLATES: dict[FGTemplateType, str] = {
    FGTemplateType.AI_INFERENCE: _AI_INFERENCE_TEMPLATE,
    FGTemplateType.CONVERSATION: _CONVERSATION_TEMPLATE,
    FGTemplateType.EMBEDDING: _EMBEDDING_TEMPLATE,
    FGTemplateType.CONTENT_MODERATION: _CONTENT_MODERATION_TEMPLATE,
}

_TEMPLATE_META: dict[FGTemplateType, FGTemplate] = {
    FGTemplateType.AI_INFERENCE: FGTemplate(
        name="ai_inference", template_type=FGTemplateType.AI_INFERENCE,
        description="AI推理函数(文本生成/摘要/翻译)", description_en="AI inference function (text generation/summary/translation)",
        env_vars={"MODEL_ENDPOINT": "ModelArts推理端点ID"}, prompt_variables=["prompt"],
    ),
    FGTemplateType.CONVERSATION: FGTemplate(
        name="conversation", template_type=FGTemplateType.CONVERSATION,
        description="对话函数(多轮对话+OBS历史存储)", description_en="Conversation function (multi-turn + OBS history)",
        env_vars={"MODEL_ENDPOINT": "对话模型端点ID", "HISTORY_BUCKET": "OBS历史桶名"}, prompt_variables=["prompt", "session_id"],
    ),
    FGTemplateType.EMBEDDING: FGTemplate(
        name="embedding", template_type=FGTemplateType.EMBEDDING,
        description="向量嵌入函数(文本向量化)", description_en="Embedding function (text vectorization)",
        env_vars={"EMBEDDING_ENDPOINT": "嵌入模型端点ID"}, prompt_variables=["text"],
    ),
    FGTemplateType.CONTENT_MODERATION: FGTemplate(
        name="content_moderation", template_type=FGTemplateType.CONTENT_MODERATION,
        description="内容审核函数(华为云Moderation)", description_en="Content moderation function (Huawei Cloud Moderation)",
        env_vars={"PROJECT_ID": "华为云项目ID"}, prompt_variables=["text"],
    ),
}


def get_fg_template(template_type: str, name: str = "", description: str = "") -> FGTemplate:
    tt = FGTemplateType(template_type)
    meta = _TEMPLATE_META[tt]
    code = _TEMPLATES[tt].format(name=name or meta.name, description=description or meta.description)
    return FGTemplate(
        name=name or meta.name, template_type=tt,
        description=description or meta.description,
        description_en=meta.description_en,
        code=code, env_vars=dict(meta.env_vars),
        dependencies=list(meta.dependencies),
        prompt_variables=list(meta.prompt_variables),
    )


def list_fg_templates() -> list[dict[str, Any]]:
    return [
        {"type": tt.value, "name": m.name, "description": m.description, "description_en": m.description_en,
         "env_vars": m.env_vars, "prompt_variables": m.prompt_variables, "runtime": m.runtime}
        for tt, m in _TEMPLATE_META.items()
    ]
