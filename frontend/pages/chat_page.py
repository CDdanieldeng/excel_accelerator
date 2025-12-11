"""Chat with Data page."""

import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

import streamlit as st

from frontend.utils import call_chat_init_api, call_chat_message_api, stream_chat_message_api


def render():
    """Render Chat with Data page."""
    st.title("💬 Chat with Data")

    # Check if we have a table_id (dataset_id)
    table_id = st.session_state.current_dataset_id
    if not table_id:
        st.warning("⚠️ 请先在 Excel 页面选择主表并构建 DataFrame。")
        if st.button("⬅️ 返回数据预览"):
            st.session_state.page = "preview"
            st.rerun()
        return

    # Initialize chat session if needed
    if not st.session_state.chat_session_id:
        with st.spinner("正在初始化聊天会话..."):
            result = call_chat_init_api(table_id)
            if result:
                st.session_state.chat_session_id = result["session_id"]
                # Display table schema info
                table_schema = result.get("table_schema", {})
                columns = table_schema.get("columns", [])
                st.success(f"✅ 聊天会话已初始化，当前表有 {len(columns)} 个列")
                st.rerun()
            else:
                return

    # Display dataset info
    if st.session_state.current_dataset_info:
        info = st.session_state.current_dataset_info
        st.subheader("📋 当前数据集")
        st.info(
            f"**文件**: `{info['file_name']}` | "
            f"**Sheet**: `{info['sheet_name']}` | "
            f"**数据大小**: {info['n_rows']:,} 行 × {info['n_cols']} 列"
        )

    st.divider()

    # Display chat history
    st.subheader("💬 对话历史")
    if st.session_state.chat_messages:
        for msg in st.session_state.chat_messages:
            role = msg.get("role", "user")
            if role == "user":
                with st.chat_message("user"):
                    st.write(msg.get("question", ""))
            else:
                with st.chat_message("assistant"):
                    # Thinking summary
                    thinking_summary = msg.get("thinking_summary", [])
                    if thinking_summary:
                        st.markdown("**🤔 简化思考过程**")
                        for i, step in enumerate(thinking_summary, 1):
                            st.markdown(f"{step}")
                        st.divider()

                    # Final answer
                    st.markdown("**✅ 最终答案**")
                    final_text = msg.get("final_text", "")
                    st.write(final_text)

                    # Pandas code
                    pandas_code = msg.get("pandas_code", "")
                    if pandas_code and pandas_code != "# 闲聊请求，无需执行代码":
                        st.markdown("**📝 生成的代码**")
                        st.code(pandas_code, language="python")
    else:
        st.info("💡 开始提问吧！例如：\"筛选出销售额大于1000的记录\" 或 \"按地区统计销售额总和\"")

    st.divider()

    # Chat input
    user_query = st.chat_input("输入您的问题...")
    if user_query:
        # Add user message
        st.session_state.chat_messages.append({
            "role": "user",
            "question": user_query,
        })

        # Create placeholder for streaming response
        with st.chat_message("assistant"):
            thinking_container = st.empty()
            final_answer_container = st.empty()
            code_container = st.empty()
            
            # Initialize variables
            thinking_steps = []
            seen_steps = set()  # Track steps we've already displayed
            final_answer_text = ""
            pandas_code = ""
            thinking_summary = []
            error_occurred = False
            
            # Stream the response
            try:
                for event in stream_chat_message_api(
                    st.session_state.chat_session_id, 
                    user_query,
                    table_id=st.session_state.current_dataset_id
                ):
                    event_type = event.get("type")
                    
                    if event_type == "thinking":
                        # Get step and message
                        step = event.get("step", "")
                        message = event.get("message", step)
                        
                        # Create a unique key for this step (use step name + message to avoid duplicates)
                        step_key = f"{step}:{message}"
                        
                        # Only add if we haven't seen this exact step+message combination
                        if step_key not in seen_steps and step:
                            seen_steps.add(step_key)
                            thinking_steps.append({
                                "step": step,
                                "message": message,
                            })
                            
                            # Update thinking display - show all accumulated steps (only new ones are added)
                            thinking_html = "**🤔 思考过程**\n\n"
                            for i, ts in enumerate(thinking_steps, 1):
                                # Show last step as processing, others as completed
                                status_icon = "⏳" if i == len(thinking_steps) else "✅"
                                thinking_html += f"{status_icon} {ts['message']}\n\n"
                            
                            # Update the container (this replaces the content, not appends)
                            thinking_container.markdown(thinking_html)
                    
                    elif event_type == "complete":
                        # Final response received
                        final_answer = event.get("final_answer", {})
                        final_answer_text = final_answer.get("text", "")
                        pandas_code = final_answer.get("pandas_code", "")
                        thinking_summary = event.get("thinking_summary", [])
                        
                        # Update final answer display
                        final_answer_container.markdown("**✅ 最终答案**")
                        final_answer_container.write(final_answer_text)
                        
                        # Update code display
                        if pandas_code and pandas_code != "# 闲聊请求，无需执行代码":
                            code_container.markdown("**📝 生成的代码**")
                            code_container.code(pandas_code, language="python")
                    
                    elif event_type == "error":
                        # Error occurred
                        error_info = event.get("error", {})
                        error_code = error_info.get("code", "UNKNOWN_ERROR")
                        error_message = error_info.get("message", "未知错误")
                        st.error(f"**错误代码**: {error_code}\n\n**错误信息**: {error_message}")
                        error_occurred = True
                        break
                
                # If streaming completed successfully, save to chat history
                if not error_occurred:
                    # Use thinking_summary from final event if available, otherwise use collected steps
                    final_thinking_summary = thinking_summary if thinking_summary else [ts["message"] for ts in thinking_steps]
                    
                    st.session_state.chat_messages.append({
                        "role": "assistant",
                        "question": user_query,
                        "thinking_summary": final_thinking_summary,
                        "final_text": final_answer_text,
                        "pandas_code": pandas_code,
                    })
                    
                    st.rerun()
                else:
                    # Remove the user message if error occurred
                    if st.session_state.chat_messages and st.session_state.chat_messages[-1].get("role") == "user":
                        st.session_state.chat_messages.pop()
                    st.rerun()
                    
            except Exception as e:
                st.error(f"**处理错误**: {str(e)}")
                # Remove the user message if exception occurred
                if st.session_state.chat_messages and st.session_state.chat_messages[-1].get("role") == "user":
                    st.session_state.chat_messages.pop()
                st.rerun()

    # Back button
    st.divider()
    if st.button("⬅️ 返回数据预览", use_container_width=True):
        st.session_state.page = "preview"
        st.rerun()

