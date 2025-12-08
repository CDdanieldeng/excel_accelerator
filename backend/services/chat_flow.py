"""LangGraph flow for Chat with Data functionality."""

import json
import logging
from typing import Any, Dict, List, Optional, TypedDict, Literal
import pandas as pd
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, END

from backend import config
from backend.models.schemas import DataFrameSummary
from backend.services.table_metadata_service import get_metadata_service

logger = logging.getLogger(__name__)

# Check LLM API key
if not config.LLM_API_KEY:
    logger.warning("QWEN_API_KEY not set, LLM features will not work")


class ChatState(TypedDict):
    """State for the chat flow."""

    session_id: str
    table_id: str
    df_summary: DataFrameSummary  # Limited DataFrame info for LLM
    user_query: str
    intent: Optional[Literal["data_analysis", "chitchat", "unclear"]]
    intent_confidence: Optional[float]
    unclear_reason: Optional[str]
    clarification_question: Optional[str]
    clarification_context: Optional[Dict[str, Any]]
    awaiting_clarification: bool
    plan: Optional[Dict[str, Any]]
    bound_plan: Optional[Dict[str, Any]]
    pandas_code: Optional[str]
    short_explanation: Optional[str]
    excel_thinking_steps: List[str]  # Excel-friendly chain of thought
    execution_result: Optional[Dict[str, Any]]
    thinking_steps: List[str]  # Keep for backward compatibility
    final_answer: Optional[str]
    error: Optional[str]
    retry_count: int


def create_llm(temperature: float = 0.0) -> ChatOpenAI:
    """Create LLM instance for Qwen (using OpenAI-compatible API)."""
    if not config.LLM_API_KEY:
        raise ValueError("QWEN_API_KEY not set. Please set it in environment variable or .env file.")
    
    # Qwen uses OpenAI-compatible API, so we can use ChatOpenAI with custom base_url
    # Default base URL for Qwen DashScope API
    base_url = config.LLM_BASE_URL or "https://dashscope.aliyuncs.com/compatible-mode/v1"
    model = config.LLM_MODEL if config.LLM_MODEL else "qwen-turbo"
    
    return ChatOpenAI(
        model=model,
        temperature=temperature,
        api_key=config.LLM_API_KEY,
        base_url=base_url,
    )


def intent_classifier_node(state: ChatState) -> ChatState:
    """Classify user intent: data analysis, chitchat, or unclear."""
    logger.info(f"Intent classification: query='{state['user_query']}'")

    # Check if this is a follow-up to clarification
    if state.get("awaiting_clarification", False):
        # This is a response to clarification, treat as data_analysis
        state["intent"] = "data_analysis"
        state["awaiting_clarification"] = False
        # Combine original query with clarification response
        clarification_context = state.get("clarification_context", {})
        original_query = clarification_context.get("original_query", "")
        current_query = state["user_query"]
        if original_query:
            state["user_query"] = f"{original_query} ({current_query})"
        logger.info("Handling clarification follow-up")
        return state

    try:
        df_summary = state.get("df_summary")
        column_names = df_summary.column_names if df_summary else []

        llm = create_llm()
        prompt = f"""你是一个意图分类器。判断用户的问题是数据分析问题、闲聊，还是不够明确需要澄清。

用户问题：{state['user_query']}

可用的列名：{', '.join(column_names) if column_names else '未知'}

分类规则：
1. 如果是明确的数据分析问题（有具体的列名、操作、条件），返回：{{"intent": "data_analysis"}}
2. 如果是闲聊（如问候、无关话题），返回：{{"intent": "chitchat"}}
3. 如果问题不够明确（缺少列名、操作不清晰、条件模糊），返回：{{"intent": "unclear", "reason": "不明确的原因"}}

只返回JSON，不要其他内容。"""

        response = llm.invoke(prompt)
        content = response.content.strip()

        # Try to parse JSON
        try:
            result = json.loads(content)
            intent = result.get("intent", "data_analysis")
            unclear_reason = result.get("reason", "")
        except json.JSONDecodeError:
            # Fallback: check if it's clearly chitchat
            query_lower = state["user_query"].lower()
            chitchat_keywords = ["你好", "hello", "hi", "谢谢", "再见", "拜拜"]
            if any(keyword in query_lower for keyword in chitchat_keywords):
                intent = "chitchat"
                unclear_reason = None
            else:
                intent = "data_analysis"
                unclear_reason = None

        state["intent"] = intent
        state["unclear_reason"] = unclear_reason if intent == "unclear" else None
        logger.info(f"Intent classified as: {intent}, reason: {unclear_reason}")

    except Exception as e:
        logger.exception(f"Error in intent classification: {e}")
        # Default to data_analysis on error
        state["intent"] = "data_analysis"
        state["unclear_reason"] = None

    return state


def chitchat_blocker_node(state: ChatState) -> ChatState:
    """Handle chitchat by returning fixed message."""
    logger.info("Blocking chitchat")
    state["final_answer"] = "本应用不支持闲聊，只能帮助你分析表格数据。请提出数据分析相关的问题。"
    state["pandas_code"] = "# 闲聊请求，无需执行代码"
    state["thinking_steps"] = ["检测到闲聊请求，已拒绝"]
    state["excel_thinking_steps"] = []
    return state


def clarification_node(state: ChatState) -> ChatState:
    """Generate a concise clarification question for unclear queries."""
    logger.info("Generating clarification question")

    try:
        df_summary = state["df_summary"]
        user_query = state["user_query"]
        unclear_reason = state.get("unclear_reason", "查询不够明确")

        llm = create_llm()

        # Build context for clarification
        column_names = df_summary.column_names
        example_row = df_summary.example_row

        prompt = f"""用户的问题不够明确，需要澄清。生成一个简洁的澄清问题（1-2句话）。

用户问题：{user_query}
不明确的原因：{unclear_reason}

可用的列名：{', '.join(column_names)}
示例数据行：{json.dumps(example_row, ensure_ascii=False)}

要求：
1. 只问一个最关键的问题
2. 如果涉及列名，列出可能的选项
3. 保持简洁（最多2句话）
4. 用友好的语气

返回JSON格式：
{{
    "clarification_question": "澄清问题文本",
    "clarification_type": "column|operation|value|filter"
}}

只返回JSON，不要其他内容。"""

        response = llm.invoke(prompt)
        content = response.content.strip()

        # Remove markdown code blocks if present
        if content.startswith("```"):
            lines = content.split("\n")
            content = "\n".join(lines[1:-1]) if len(lines) > 2 else content

        # Parse response
        result = json.loads(content)
        clarification_question = result.get("clarification_question", "请提供更多详细信息。")

        state["clarification_question"] = clarification_question
        state["final_answer"] = clarification_question
        state["pandas_code"] = "# 需要澄清，暂未生成代码"
        state["thinking_steps"] = ["检测到不明确的查询，请求澄清"]
        state["excel_thinking_steps"] = []
        state["awaiting_clarification"] = True

        # Store context for follow-up
        state["clarification_context"] = {
            "original_query": user_query,
            "unclear_reason": unclear_reason,
            "available_columns": column_names,
        }

        logger.info(f"Clarification question generated: {clarification_question}")

    except Exception as e:
        logger.exception(f"Error generating clarification: {e}")
        # Fallback clarification
        state["clarification_question"] = "请提供更具体的问题，例如：要查询哪些列？使用什么筛选条件？"
        state["final_answer"] = state["clarification_question"]
        state["pandas_code"] = "# 需要澄清，暂未生成代码"
        state["thinking_steps"] = ["请求澄清"]
        state["excel_thinking_steps"] = []
        state["awaiting_clarification"] = True
        state["clarification_context"] = {
            "original_query": user_query,
            "unclear_reason": unclear_reason,
            "available_columns": df_summary.column_names if "df_summary" in state else [],
        }

    return state


def planner_node(state: ChatState) -> ChatState:
    """Generate analysis plan from user query and DataFrame summary."""
    logger.info("Generating analysis plan")

    try:
        # Build schema description from DataFrameSummary (limited info)
        df_summary = state["df_summary"]
        columns_info = []
        for col_name in df_summary.column_names:
            col_type = df_summary.column_types.get(col_name, "unknown")
            example_value = df_summary.example_row.get(col_name, None)
            col_desc = f"- {col_name} ({col_type})"
            if example_value is not None:
                col_desc += f" (示例值: {example_value})"
            columns_info.append(col_desc)

        schema_text = "\n".join(columns_info)
        metadata = df_summary.metadata
        metadata_text = f"总行数: {metadata.get('n_rows', '未知')}, 总列数: {metadata.get('n_cols', '未知')}"

        llm = create_llm()
        prompt = f"""你是一个数据分析计划生成器。根据用户问题和表结构，生成一个结构化的分析计划。

表结构（仅包含列名、类型和示例值）：
{schema_text}

表基本信息：{metadata_text}

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

        df_summary = state["df_summary"]
        column_names = df_summary.column_names

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

        df_summary = state["df_summary"]
        column_names = df_summary.column_names

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


def excel_translator_node(state: ChatState) -> ChatState:
    """Translate analysis plan steps to Excel-friendly language."""
    logger.info("Translating steps to Excel-friendly language")

    try:
        bound_plan = state.get("bound_plan")
        if not bound_plan:
            # No plan to translate, skip
            state["excel_thinking_steps"] = []
            return state

        steps = bound_plan.get("steps", [])
        excel_steps = []

        llm = create_llm()

        # Translate each step
        for i, step in enumerate(steps, 1):
            operation = step.get("operation", "")
            description = step.get("description", "")
            params = step.get("params", {})

            # Build prompt for Excel translation
            prompt = f"""将以下数据分析步骤翻译成Excel用户能理解的语言。

操作类型：{operation}
操作描述：{description}
操作参数：{json.dumps(params, ensure_ascii=False)}

要求：
1. 使用Excel术语（筛选、数据透视表、SUM函数、排序等）
2. 避免使用技术术语（如pandas、DataFrame、groupby等）
3. 用一句话描述，清晰简洁
4. 如果涉及列名，直接使用列名

示例：
- filter → "筛选出[列名]满足[条件]的行（类似使用自动筛选功能）"
- groupby + aggregate sum → "按[列名]分组，对[列名]求和（类似创建数据透视表）"
- sort → "按[列名]排序（类似使用排序功能）"
- select → "选择[列名]列"

只返回翻译后的描述，不要其他内容。"""

            response = llm.invoke(prompt)
            excel_description = response.content.strip()

            # Format as step
            excel_steps.append(f"步骤{i}：{excel_description}")

        state["excel_thinking_steps"] = excel_steps
        logger.info(f"Translated {len(excel_steps)} steps to Excel language")

    except Exception as e:
        logger.exception(f"Error translating to Excel language: {e}")
        # Fallback: use original descriptions
        bound_plan = state.get("bound_plan", {})
        steps = bound_plan.get("steps", [])
        excel_steps = []
        for i, step in enumerate(steps, 1):
            desc = step.get("description", f"执行步骤{i}")
            excel_steps.append(f"步骤{i}：{desc}")
        state["excel_thinking_steps"] = excel_steps

    return state


def result_explainer_node(state: ChatState) -> ChatState:
    """Generate natural language explanation using Excel terminology."""
    logger.info("Generating Excel-friendly explanation")

    try:
        bound_plan = state.get("bound_plan")
        execution_result = state.get("execution_result")
        user_query = state["user_query"]
        excel_steps = state.get("excel_thinking_steps", [])

        if not bound_plan or not execution_result:
            state["error"] = "缺少必要信息用于生成解释"
            return state

        # Use Excel-friendly steps if available
        if excel_steps:
            state["thinking_steps"] = excel_steps
        else:
            # Fallback to original steps
            thinking_steps = []
            for i, step in enumerate(bound_plan.get("steps", []), 1):
                desc = step.get("description", f"执行步骤{i}")
                thinking_steps.append(f"步骤{i}：{desc}")
            state["thinking_steps"] = thinking_steps

        # Generate final answer using Excel terminology
        llm = create_llm()
        prompt = f"""你是一个数据分析结果解释器。根据用户问题、分析步骤和执行结果，生成面向Excel用户的自然语言解释。

用户问题：{user_query}

分析步骤（已转换为Excel术语）：
{chr(10).join(excel_steps) if excel_steps else '无'}

执行结果摘要：
{json.dumps(execution_result, ensure_ascii=False, indent=2)}

要求：
1. 使用Excel用户熟悉的语言（避免pandas、SQL等技术术语）
2. 可以类比Excel操作（如"类似数据透视表"、"类似SUM函数"等）
3. 简洁明了，直接回答用户问题
4. 如果结果是数字，直接给出数字和单位

只返回回答文本，不要其他内容。"""

        response = llm.invoke(prompt)
        final_answer = response.content.strip()

        state["final_answer"] = final_answer
        logger.info("Excel-friendly explanation generated")

    except Exception as e:
        logger.exception(f"Error generating explanation: {e}")
        # Fallback
        state["thinking_steps"] = ["执行数据分析", "生成结果"]
        state["excel_thinking_steps"] = state.get("excel_thinking_steps", [])
        state["final_answer"] = "根据您的问题，我已经完成了数据分析。"

    return state


def should_continue(state: ChatState) -> Literal["chitchat", "unclear", "data_analysis"]:
    """Determine next step based on intent."""
    intent = state.get("intent")
    if intent == "chitchat":
        return "chitchat"
    elif intent == "unclear":
        return "unclear"
    return "data_analysis"


def create_chat_flow():
    """Create the LangGraph flow for chat with clarification and Excel translation."""
    workflow = StateGraph(ChatState)

    # Add nodes
    workflow.add_node("intent_classifier", intent_classifier_node)
    workflow.add_node("chitchat_blocker", chitchat_blocker_node)
    workflow.add_node("clarification_handler", clarification_node)
    workflow.add_node("planner", planner_node)
    workflow.add_node("schema_resolver", schema_resolver_node)
    workflow.add_node("code_generator", code_generator_node)
    workflow.add_node("executor", executor_node)
    workflow.add_node("excel_translator", excel_translator_node)
    workflow.add_node("result_explainer", result_explainer_node)

    # Set entry point
    workflow.set_entry_point("intent_classifier")

    # Add conditional edges
    workflow.add_conditional_edges(
        "intent_classifier",
        should_continue,
        {
            "chitchat": "chitchat_blocker",
            "unclear": "clarification_handler",
            "data_analysis": "planner",
        },
    )

    # Add edges for data analysis flow
    workflow.add_edge("planner", "schema_resolver")
    workflow.add_edge("schema_resolver", "code_generator")
    workflow.add_edge("code_generator", "executor")
    workflow.add_edge("executor", "excel_translator")
    workflow.add_edge("excel_translator", "result_explainer")

    # Add edges to end
    workflow.add_edge("chitchat_blocker", END)
    workflow.add_edge("clarification_handler", END)
    workflow.add_edge("result_explainer", END)

    return workflow.compile()

