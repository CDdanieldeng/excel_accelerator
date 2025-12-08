"""Chat with Data page."""

import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

import streamlit as st

from frontend.utils import call_chat_init_api, call_chat_message_api


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

        # Call API (pass table_id for session recovery if needed)
        with st.spinner("正在处理您的问题..."):
            result = call_chat_message_api(
                st.session_state.chat_session_id, 
                user_query,
                table_id=st.session_state.current_dataset_id
            )

        if result:
            final_answer = result.get("final_answer", {})
            thinking_summary = result.get("thinking_summary", [])

            # Add assistant message
            st.session_state.chat_messages.append({
                "role": "assistant",
                "question": user_query,  # Keep for reference
                "thinking_summary": thinking_summary,
                "final_text": final_answer.get("text", ""),
                "pandas_code": final_answer.get("pandas_code", ""),
            })

            st.rerun()
        else:
            # Remove the user message if API call failed
            if st.session_state.chat_messages and st.session_state.chat_messages[-1].get("role") == "user":
                st.session_state.chat_messages.pop()

    # Back button
    st.divider()
    if st.button("⬅️ 返回数据预览", use_container_width=True):
        st.session_state.page = "preview"
        st.rerun()

