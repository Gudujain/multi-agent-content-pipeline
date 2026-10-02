import streamlit as st
from graph import build_graph

st.set_page_config(page_title="Content Pipeline", page_icon="✍️")
st.title("Multi-Agent Content Pipeline")
st.caption("Researcher → Writer → Editor (with a bounded revise loop)")

topic = st.text_input("Topic", placeholder="e.g. How do vector databases work")
fmt = st.radio("Format", ["blog", "thread"], horizontal=True)

if st.button("Generate", type="primary"):
    if not topic.strip():
        st.warning("Please type a topic first.")
        st.stop()

    state = {
        "topic": topic.strip(),
        "format": fmt,
        "research": "",
        "draft": "",
        "final": "",
        "feedback": "",
        "approved": False,
        "revision_count": 0,
        "errors": [],
    }

    final_state = dict(state)
    status = st.status("Agents are working...", expanded=True)

    try:
        app = build_graph()
        # stream_mode="updates" gives us one message each time a worker finishes
        for update in app.stream(state, {"recursion_limit": 15}, stream_mode="updates"):
            for node_name, changes in update.items():
                final_state.update(changes or {})
                if node_name == "writer":
                    status.write(f"✅ writer finished draft #{final_state['revision_count']}")
                elif node_name == "editor":
                    verdict = "approved" if final_state["approved"] else "asked for changes"
                    status.write(f"✅ editor {verdict}")
                else:
                    status.write(f"✅ {node_name} finished")
        status.update(label="Done!", state="complete")
    except Exception as e:
        status.update(label="Pipeline failed", state="error")
        st.error(str(e))
        st.stop()

    content = final_state["final"] or final_state["draft"]
    st.divider()
    st.markdown(content)
    st.download_button(
        "Download as .md",
        data=content,
        file_name="content.md",
        mime="text/markdown",
    )

    if final_state["errors"]:
        with st.expander("Warnings"):
            for err in final_state["errors"]:
                st.write(f"- {err}")