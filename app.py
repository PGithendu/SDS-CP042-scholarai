import streamlit as st
from patrick_githendu import orchestrate

st.title("Multi-Agent Research System")
topic = st.text_input("Main Research Topic")
style = st.selectbox("Style", ["academic", "business", "layperson"], index=0)

if st.button("Run Agents"):
    results = orchestrate(topic, style=style)
    st.subheader("Overall Summary")
    st.write(results.get("summary", ""))
    st.subheader("Per-Researcher Findings")
    st.write(results.get("findings", ""))
    st.subheader("Sources / Citations")
    st.write(results.get("citations", ""))
    st.subheader("Critic Agent Review")
    st.write(results.get("critic_review", ""))

    # Download buttons
    import json
    md = (
        f"# Overall Summary\n{results.get('summary','')}\n\n"
        f"## Per-Researcher Findings\n{results.get('findings','')}\n\n"
        f"## Sources / Citations\n{results.get('citations','')}\n\n"
        f"## Critic Agent Review\n{results.get('critic_review','')}\n"
    )
    st.download_button("Download Markdown", md, file_name="report.md")
    st.download_button("Download JSON", json.dumps(results, indent=2), file_name="report.json")