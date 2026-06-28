"""多模型 Provider 层。

支持本地 Ollama（默认）与多家在线大模型（DeepSeek / OpenAI / 通义千问 / Claude），
可在运行时切换。analyzer 通过 get_llms() 拿到当前激活的 (json_llm, text_llm)。

- DeepSeek / OpenAI / 通义千问 均为 OpenAI 兼容接口，统一用 ChatOpenAI + base_url。
- Claude 用 ChatAnthropic。
- 向量化(embeddings)始终走本地 bge，不受此处影响。
"""
from typing import Tuple

from langchain_ollama import ChatOllama
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic

# Provider 默认配置（label 给前端展示；needs_key 是否需要 API Key）
PROVIDERS = {
    "ollama":    {"label": "本地 Ollama (隐私)", "model": "qwen2.5",      "base_url": "http://127.0.0.1:11434",                          "needs_key": False, "kind": "ollama"},
    "deepseek":  {"label": "DeepSeek",          "model": "deepseek-chat", "base_url": "https://api.deepseek.com",                        "needs_key": True,  "kind": "openai"},
    "openai":    {"label": "OpenAI (GPT)",       "model": "gpt-4o-mini",   "base_url": None,                                              "needs_key": True,  "kind": "openai"},
    "qwen":      {"label": "通义千问 Qwen 在线",  "model": "qwen-plus",     "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1", "needs_key": True, "kind": "openai"},
    "anthropic": {"label": "Claude",            "model": "claude-sonnet-4-6", "base_url": None,                                          "needs_key": True,  "kind": "anthropic"},
}

# 运行时状态：当前 provider + 每个 provider 的 {model, api_key}
_state = {
    "provider": "ollama",
    "providers": {k: {"model": v["model"], "api_key": ""} for k, v in PROVIDERS.items()},
}


def load_state(provider: str | None, providers_config: dict | None):
    """从持久化配置载入（启动时 / 更新后调用）。"""
    if provider in PROVIDERS:
        _state["provider"] = provider
    if providers_config:
        for k, cfg in providers_config.items():
            if k in _state["providers"] and isinstance(cfg, dict):
                _state["providers"][k].update({
                    kk: vv for kk, vv in cfg.items() if kk in ("model", "api_key")
                })


def export_state() -> dict:
    """导出用于持久化（含 api_key）。"""
    return {"provider": _state["provider"], "providers": _state["providers"]}


def set_provider(provider: str):
    if provider not in PROVIDERS:
        raise ValueError(f"Unknown provider: {provider}")
    _state["provider"] = provider


def update_provider_config(provider: str, model: str | None = None, api_key: str | None = None):
    if provider not in _state["providers"]:
        raise ValueError(f"Unknown provider: {provider}")
    if model is not None:
        _state["providers"][provider]["model"] = model
    if api_key is not None and api_key != "":  # 空字符串不覆盖已存的 key
        _state["providers"][provider]["api_key"] = api_key


def public_info() -> dict:
    """给前端的安全视图：不返回明文 key，只返回是否已配置。"""
    return {
        "active": _state["provider"],
        "providers": [
            {
                "key": k,
                "label": meta["label"],
                "needs_key": meta["needs_key"],
                "model": _state["providers"][k].get("model") or meta["model"],
                "default_model": meta["model"],
                "configured": (not meta["needs_key"]) or bool(_state["providers"][k].get("api_key")),
            }
            for k, meta in PROVIDERS.items()
        ],
    }


def _build(provider: str, cfg: dict, json_mode: bool, temperature: float = 0):
    meta = PROVIDERS[provider]
    model = cfg.get("model") or meta["model"]
    key = cfg.get("api_key") or ""
    kind = meta["kind"]

    if kind == "ollama":
        kw = dict(base_url=meta["base_url"], model=model, temperature=temperature,
                  num_ctx=16384 if json_mode else 8192)
        if json_mode:
            kw["format"] = "json"
        return ChatOllama(**kw)

    if kind == "anthropic":
        return ChatAnthropic(model=model, temperature=temperature, api_key=key, max_tokens=8192)

    # openai 兼容：openai / deepseek / qwen
    kw = dict(model=model, temperature=temperature, api_key=key, timeout=120)
    if meta["base_url"]:
        kw["base_url"] = meta["base_url"]
    if json_mode:
        kw["model_kwargs"] = {"response_format": {"type": "json_object"}}
    return ChatOpenAI(**kw)


def build_text_llm(provider: str | None = None, temperature: float = 0.3):
    """为 Agent 构建一个文本对话 LLM。provider 为空/无效则用当前激活 provider。"""
    p = provider if provider in PROVIDERS else _state["provider"]
    return _build(p, _state["providers"].get(p, {}), json_mode=False, temperature=temperature)


def get_llms() -> Tuple[object, object]:
    """返回当前激活 provider 的 (json_llm, text_llm)。"""
    p = _state["provider"]
    cfg = _state["providers"].get(p, {})
    return _build(p, cfg, True), _build(p, cfg, False)


def is_online() -> bool:
    return PROVIDERS[_state["provider"]]["kind"] != "ollama"
