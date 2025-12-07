import gradio as gr
from patrick_githendu import orchestrate

def run_agents(topic):
    # Orchestrate should return a dict with keys: summary, findings, citations, critic_review
    results = orchestrate(topic)
    summary = results.get("summary", "")
    findings = results.get("findings", "")
    citations = results.get("citations", "")
    critic_review = results.get("critic_review", "")
    return summary, findings, citations, critic_review

def download_markdown(summary, findings, citations, critic_review):
    md = (
        f"# Overall Summary\n{summary}\n\n"
        f"## Per-Researcher Findings\n{findings}\n\n"
        f"## Sources / Citations\n{citations}\n\n"
        f"## Critic Agent Review\n{critic_review}\n"
    )
    with open("report.md", "w", encoding="utf-8") as f:
        f.write(md)
    return "report.md"

def download_json(summary, findings, citations, critic_review):
    import json
    data = {
        "summary": summary,
        "findings": findings,
        "citations": citations,
        "critic_review": critic_review
    }
    with open("report.json", "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    return "report.json"

with gr.Blocks() as demo:
    gr.Markdown("# Multi-Agent Research System")
    topic = gr.Textbox(label="Main Research Topic")
    run_btn = gr.Button("Run Agents")

    with gr.Tab("Overall Summary"):
        summary = gr.Textbox(label="Overall Summary")
    with gr.Tab("Per-Researcher Findings"):
        findings = gr.Textbox(label="Per-Researcher Findings")
    with gr.Tab("Sources / Citations"):
        citations = gr.Textbox(label="Sources / Citations")
    with gr.Tab("Critic Agent Review"):
        critic_review = gr.Textbox(label="Critic Agent Review")

    download_md = gr.Button("Download Markdown Report")
    download_json_btn = gr.Button("Download JSON Report")

    run_btn.click(
        run_agents,
        inputs=topic,
        outputs=[summary, findings, citations, critic_review]
    )
    download_md.click(
        download_markdown,
        inputs=[summary, findings, citations, critic_review],
        outputs=gr.File()
    )
    download_json_btn.click(
        download_json,
        inputs=[summary, findings, citations, critic_review],
        outputs=gr.File()
    )

demo.launch()