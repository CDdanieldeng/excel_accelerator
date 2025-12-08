"""LangGraph flow for Chat with Data functionality."""

import json
import logging
from typing import Any, Dict, List, Optional, TypedDict, Literal
import pandas as pd
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, END

from backend import config
from backend.models.schemas import TableSchema
from backend.services.table_metadata_service import get_metadata_service

logger = logging.getLogger(__name__)

# Check LLM API key
if not config.LLM_API_KEY:
    logger.warning("QWEN_API_KEY not set, LLM features will not work")


class ChatState(TypedDict):
    """State for the chat flow."""

    session_id: str
    table_id: str
    table_schema: TableSchema
    user_query: str
    intent: Optional[Literal["data_analysis", "chitchat"]]
    plan: Optional[Dict[str, Any]]
    bound_plan: Optional[Dict[str, Any]]
    pandas_code: Optional[str]
    short_explanation: Optional[str]
    execution_result: Optional[Dict[str, Any]]
    thinking_steps: List[str]
    final_answer: Optional[str]
    error: Optional[str]


def create_llm(temperature: float = 0.0) -> ChatOpenAI:
    """Create LLM instance."""
    if not config.LLM_API_KEY:
        raise ValueError("QWEN_API_KEY not set. Please set it in environment variable or .env file.")
    return ChatOpenAI(
        model=config.LLM_MODEL if config.LLM_MODEL else "qwen-turbo",
        temperature=temperature,
        api_key=config.LLM_API_KEY,
        base_url=config.LLM_BASE_URL,
    )


def intent_classifier_node(state: ChatState) -> ChatState:
    """Classify user intent: data analysis or chitchat."""
    logger.info(f"Intent classification: query='{state['user_query']}'")

    try:
        llm = create_llm()
        prompt = f"""你是一个意图分类器。判断用户的问题是数据分析问题还是闲聊。

用户问题：{state['user_query']}

如果是数据分析问题（如查询、筛选、统计、排序等），返回：{{"intent": "data_analysis"}}
如果是闲聊（如问候、无关话题等），返回：{{"intent": "chitchat"}}

只返回JSON，不要其他内容。"""

        response = llm.invoke(prompt)
        content = response.content.strip()

        # Try to parse JSON
        try:
            result = json.loads(content)
            intent = result.get("intent", "data_analysis")
        except json.JSONDecodeError:
            # Fallback: check if it's clearly chitchat
            query_lower = state["user_query"].lower()
            chitchat_keywords = ["你好", "hello", "hi", "谢谢", "再见", "拜拜"]
            if any(keyword in query_lower for keyword in chitchat_keywords):
                intent = "chitchat"
            else:
                intent = "data_analysis"

        state["intent"] = intent
        logger.info(f"Intent classified as: {intent}")

    except Exception as e:
        logger.exception(f"Error in intent classification: {e}")
        # Default to data_analysis on error
        state["intent"] = "data_analysis"

    return state


def chitchat_blocker_node(state: ChatState) -> ChatState:
    """Handle chitchat by returning fixed message."""
    logger.info("Blocking chitchat")
    state["final_answer"] = "本应用不支持闲聊，只能帮助你分析表格数据。请提出数据分析相关的问题。"
    state["pandas_code"] = "# 闲聊请求，无需执行代码"
    state["thinking_steps"] = ["检测到闲聊请求，已拒绝"]
    return state


def planner_node(state: ChatState) -> ChatState:
    """Generate analysis plan from user query and table schema."""
    logger.info("Generating analysis plan")

    try:
        # Build schema description
        schema = state["table_schema"]
        columns_info = []
        for col in schema.columns:
            col_desc = f"- {col.name} ({col.dtype})"
            if col.chinese_description:
                col_desc += f": {col.chinese_description}"
            if col.stats:
                stats_str = ", ".join([f"{k}={v}" for k, v in col.stats.items() if v is not None])
                if stats_str:
                    col_desc += f" [{stats_str}]"
            columns_info.append(col_desc)

        schema_text = "\n".join(columns_info)

        llm = create_llm()
        prompt = f"""你是一个数据分析计划生成器。根据用户问题和表结构，生成一个结构化的分析计划。

表结构：
{schema_text}

用户问题：{state['user_query']}

生成一个JSON格式的分析计划，包含以下字段：
- goal: 分析目标（一句话描述）
- steps: 步骤列表，每个步骤包含：
  - operation: 操作类型（filter/groupby/sort_limit/aggregate/select等）
  - description: 操作描述
  - params: 操作参数（如筛选条件、分组字段等）

只返回JSON，不要其他内容。示例格式：
{{
  "goal": "筛选2024年上半年的销售记录，按大区汇总销售额",
  "steps": [
    {{"operation": "filter", "description": "筛选日期在2024年1-6月", "params": {{"column": "日期", "condition": "between 2024-01-01 and 2024-06-30"}}}},
    {{"operation": "groupby", "description": "按大区分组", "params": {{"by": "大区"}}}},
    {{"operation": "aggregate", "description": "计算销售额总和", "params": {{"column": "销售额", "agg": "sum"}}}}
  ]
}}"""

        response = llm.invoke(prompt)
        content = response.content.strip()

        # Remove markdown code blocks if present
        if content.startswith("```"):
            lines = content.split("\n")
            content = "\n".join(lines[1:-1]) if len(lines) > 2 else content

        plan = json.loads(content)
        state["plan"] = plan
        logger.info(f"Plan generated: {plan.get('goal', 'N/A')}")

    except Exception as e:
        logger.exception(f"Error in planning: {e}")
        state["error"] = f"生成分析计划时出错: {str(e)}"

    return state


def schema_resolver_node(state: ChatState) -> ChatState:
    """Resolve abstract field names in plan to actual column names."""
    logger.info("Resolving schema")

    try:
        plan = state.get("plan")
        if not plan:
            state["error"] = "分析计划不存在"
            return state

        schema = state["table_schema"]
        column_names = [col.name for col in schema.columns]

        # Simple matching: try to find column names that match the abstract names in plan
        bound_steps = []
        for step in plan.get("steps", []):
            params = step.get("params", {})
            bound_params = params.copy()

            # Try to match column names
            for key, value in params.items():
                if key in ["column", "by", "group_by"] and isinstance(value, str):
                    # Try exact match first
                    if value in column_names:
                        bound_params[key] = value
                    else:
                        # Try fuzzy match (contains)
                        matches = [col for col in column_names if value.lower() in col.lower() or col.lower() in value.lower()]
                        if matches:
                            bound_params[key] = matches[0]
                            logger.info(f"Matched '{value}' to '{matches[0]}'")

            bound_step = step.copy()
            bound_step["params"] = bound_params
            bound_steps.append(bound_step)

        bound_plan = plan.copy()
        bound_plan["steps"] = bound_steps
        state["bound_plan"] = bound_plan
        logger.info("Schema resolved")

    except Exception as e:
        logger.exception(f"Error in schema resolution: {e}")
        state["error"] = f"解析字段名时出错: {str(e)}"

    return state


def code_generator_node(state: ChatState) -> ChatState:
    """Generate pandas code from bound plan."""
    logger.info("Generating pandas code")

    try:
        bound_plan = state.get("bound_plan")
        if not bound_plan:
            state["error"] = "已绑定的分析计划不存在"
            return state

        schema = state["table_schema"]
        column_names = [col.name for col in schema.columns]

        llm = create_llm()
        prompt = f"""你是一个pandas代码生成器。根据分析计划生成完整的pandas代码。

表列名：{', '.join(column_names)}

分析计划：
{json.dumps(bound_plan, ensure_ascii=False, indent=2)}

生成完整的pandas代码，要求：
1. 假设主表已经加载为变量 `df`
2. 代码应该是完整的、可执行的
3. 最后将结果保存到变量 `result` 中
4. 如果结果很大，只返回汇总统计或前N行预览

返回JSON格式：
{{
  "pandas_code": "<完整的python代码字符串>",
  "short_explanation": "一句话解释这段代码在做什么"
}}

只返回JSON，不要其他内容。"""

        response = llm.invoke(prompt)
        content = response.content.strip()

        # Remove markdown code blocks if present
        if content.startswith("```"):
            lines = content.split("\n")
            content = "\n".join(lines[1:-1]) if len(lines) > 2 else content

        result = json.loads(content)
        state["pandas_code"] = result.get("pandas_code", "")
        state["short_explanation"] = result.get("short_explanation", "")
        logger.info(f"Code generated: {state['short_explanation']}")

    except Exception as e:
        logger.exception(f"Error in code generation: {e}")
        state["error"] = f"生成代码时出错: {str(e)}"

    return state


def executor_node(state: ChatState) -> ChatState:
    """Execute pandas code in controlled environment."""
    logger.info("Executing pandas code")

    try:
        pandas_code = state.get("pandas_code")
        if not pandas_code:
            state["error"] = "pandas代码不存在"
            return state

        # Get DataFrame
        table_id = state["table_id"]
        metadata_service = get_metadata_service()
        df = metadata_service.get_dataframe(table_id)

        if df is None:
            state["error"] = f"表 {table_id} 不存在"
            return state

        # Create execution environment
        exec_globals = {
            "pd": pd,
            "df": df.copy(),
        }
        exec_locals = {}

        # Execute code
        try:
            exec(pandas_code, exec_globals, exec_locals)
        except Exception as e:
            # Try to fix common errors
            logger.warning(f"Code execution failed, attempting fix: {e}")
            # For now, just raise the error
            raise

        # Get result
        result = exec_locals.get("result")
        if result is None:
            # Try to get from globals
            result = exec_globals.get("result")

        if result is None:
            state["error"] = "代码执行后未找到result变量"
            return state

        # Convert result to preview format
        if isinstance(result, pd.DataFrame):
            if len(result) > 100:
                preview = result.head(100)
                summary = {
                    "total_rows": len(result),
                    "preview_rows": 100,
                    "columns": result.columns.tolist(),
                }
            else:
                preview = result
                summary = {
                    "total_rows": len(result),
                    "columns": result.columns.tolist(),
                }
            # Convert to dict for JSON serialization
            preview_data = preview.to_dict(orient="records")
            state["execution_result"] = {
                "type": "dataframe",
                "summary": summary,
                "preview": preview_data[:20],  # Limit preview to 20 rows
            }
        elif isinstance(result, (int, float, str, bool)):
            state["execution_result"] = {
                "type": "scalar",
                "value": result,
            }
        else:
            # Try to convert to string
            state["execution_result"] = {
                "type": "other",
                "value": str(result),
            }

        logger.info("Code executed successfully")

    except Exception as e:
        logger.exception(f"Error in code execution: {e}")
        state["error"] = f"执行代码时出错: {str(e)}"

    return state


def result_explainer_node(state: ChatState) -> ChatState:
    """Generate natural language explanation of results."""
    logger.info("Generating explanation")

    try:
        bound_plan = state.get("bound_plan")
        execution_result = state.get("execution_result")
        user_query = state["user_query"]

        if not bound_plan or not execution_result:
            state["error"] = "缺少必要信息用于生成解释"
            return state

        # Generate thinking steps
        thinking_steps = []
        for i, step in enumerate(bound_plan.get("steps", []), 1):
            op = step.get("operation", "")
            desc = step.get("description", "")
            if desc:
                thinking_steps.append(f"① {desc}")
            elif op:
                thinking_steps.append(f"① 执行{op}操作")

        # Generate final answer
        llm = create_llm()
        prompt = f"""你是一个数据分析结果解释器。根据用户问题、分析计划和执行结果，生成面向Excel用户的自然语言解释。

用户问题：{user_query}

分析计划：
{json.dumps(bound_plan, ensure_ascii=False, indent=2)}

执行结果摘要：
{json.dumps(execution_result, ensure_ascii=False, indent=2)}

生成一个简洁的自然语言回答，用Excel用户听得懂的话描述结果。不要输出JSON，直接输出回答文本。"""

        response = llm.invoke(prompt)
        final_answer = response.content.strip()

        state["thinking_steps"] = thinking_steps
        state["final_answer"] = final_answer
        logger.info("Explanation generated")

    except Exception as e:
        logger.exception(f"Error in explanation generation: {e}")
        # Fallback explanation
        state["thinking_steps"] = ["执行数据分析", "生成结果"]
        state["final_answer"] = f"根据您的问题，我已经完成了数据分析。结果摘要：{json.dumps(execution_result, ensure_ascii=False)}"

    return state


def should_continue(state: ChatState) -> Literal["chitchat", "data_analysis"]:
    """Determine next step based on intent."""
    intent = state.get("intent")
    if intent == "chitchat":
        return "chitchat"
    return "data_analysis"


def create_chat_flow():
    """Create the LangGraph flow for chat."""
    workflow = StateGraph(ChatState)

    # Add nodes
    workflow.add_node("intent_classifier", intent_classifier_node)
    workflow.add_node("chitchat_blocker", chitchat_blocker_node)
    workflow.add_node("planner", planner_node)
    workflow.add_node("schema_resolver", schema_resolver_node)
    workflow.add_node("code_generator", code_generator_node)
    workflow.add_node("executor", executor_node)
    workflow.add_node("result_explainer", result_explainer_node)

    # Set entry point
    workflow.set_entry_point("intent_classifier")

    # Add conditional edges
    workflow.add_conditional_edges(
        "intent_classifier",
        should_continue,
        {
            "chitchat": "chitchat_blocker",
            "data_analysis": "planner",
        },
    )

    # Add edges for data analysis flow
    workflow.add_edge("planner", "schema_resolver")
    workflow.add_edge("schema_resolver", "code_generator")
    workflow.add_edge("code_generator", "executor")
    workflow.add_edge("executor", "result_explainer")

    # Add edges to end
    workflow.add_edge("chitchat_blocker", END)
    workflow.add_edge("result_explainer", END)

    return workflow.compile()

