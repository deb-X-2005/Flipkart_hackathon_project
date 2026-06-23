"""Imports every module to catch path/syntax breakage early."""
import importlib


def test_imports_all_modules():
    mods = [
        "src.config",
        "src.data.loader",
        "src.data.preprocess",
        "src.data.cache",
        "src.data.sources.weather",
        "src.data.sources.news",
        "src.data.sources.reddit",
        "src.data.sources.gdelt",
        "src.data.sources.datagov",
        "src.rag.embeddings",
        "src.rag.vector_store",
        "src.rag.retriever",
        "src.models.forecast",
        "src.agents.orchestrator",
        "src.agents.planner_agent",
        "src.llm.client",
        "src.llm.ollama",
        "src.llm.openai_client",
        "src.llm.anthropic_client",
        "src.viz.heatmap",
        "src.security.pii",
        "src.security.audit",
        "src.security.auth",
        "src.security.crypto",
        "src.security.classify",
        "src.security.retention",
        "src.security.erasure",
        "src.api.main",
        "src.api.schemas",
        "src.mcp_server.server",
    ]
    for m in mods:
        importlib.import_module(m)
