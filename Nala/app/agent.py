# app/agent.py
import operator
import os
from typing import Annotated, TypedDict

from langgraph.graph import END, StateGraph

from app.tools.rag_tool import RAG_TOOL_SCHEMA, rag_search
from app.tools.sql_tool import SQL_TOOL_SCHEMA, query_data_operasional

MAX_TOOL_ROUNDS = int(os.environ.get("MAX_TOOL_ROUNDS", "3"))


def _count_tool_rounds(messages: list[dict]) -> int:
    return sum(1 for m in messages if m.get("role") == "tool")


class AgentState(TypedDict):
    messages: Annotated[list[dict], operator.add]


def build_agent(
    ollama_client,
    vector_store,
    ollama_base_url: str,
    reranker=None,
    trace=None,
    model_name: str = "llama3.2:3b",
):
    tools_schema = [RAG_TOOL_SCHEMA, SQL_TOOL_SCHEMA]

    def call_model(state: AgentState) -> dict:
        generation = trace.generation(
            name="agent_call_model", model=model_name, input=state["messages"]
        ) if trace else None

        response_message = ollama_client.chat(state["messages"], tools=tools_schema)

        if generation:
            generation.end(output=response_message)
        return {"messages": [response_message]}

    def call_tool(state: AgentState) -> dict:
        last_message = state["messages"][-1]
        tool_messages = []
        for call in last_message.get("tool_calls", []):
            name = call["function"]["name"]
            args = call["function"]["arguments"]

            span = trace.span(name=f"agent_tool:{name}", input=args) if trace else None

            try:
                if name == "cari_dokumen_sop":
                    result = rag_search(args["query"], vector_store, ollama_base_url, reranker=reranker)
                elif name == "query_data_operasional":
                    result = query_data_operasional(**args)
                else:
                    result = f"Tool '{name}' tidak dikenal."
            except (TypeError, KeyError) as e:
                result = f"Tool '{name}' dipanggil dengan argumen tidak lengkap/tidak valid ({e}). Coba tanyakan ulang dengan lebih spesifik."

            if span:
                span.end(output={"result": result[:300]})
            tool_messages.append({"role": "tool", "content": result, "tool_call_id": call.get("id"), "name": name})
        return {"messages": tool_messages}

    def force_answer(state: AgentState) -> dict:
        response_message = ollama_client.chat(state["messages"])  # tanpa parameter tools
        return {"messages": [response_message]}

    def should_continue(state: AgentState) -> str:
        last_message = state["messages"][-1]
        if last_message.get("tool_calls"):
            if _count_tool_rounds(state["messages"]) >= MAX_TOOL_ROUNDS:
                return "force_answer"
            return "call_tool"
        return END

    graph = StateGraph(AgentState)
    graph.add_node("call_model", call_model)
    graph.add_node("call_tool", call_tool)
    graph.add_node("force_answer", force_answer)
    graph.set_entry_point("call_model")
    graph.add_conditional_edges(
        "call_model",
        should_continue,
        {"call_tool": "call_tool", "force_answer": "force_answer", END: END},
    )
    graph.add_edge("call_tool", "call_model")
    graph.add_edge("force_answer", END)

    return graph.compile()
