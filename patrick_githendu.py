import openai
import os
from dotenv import load_dotenv
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed

load_dotenv()  # Loads variables from .env into environment

class TopicSplitterAgent:
    def __init__(self, api_key: str, model: str = "gpt-3.5-turbo"):
        openai.api_key = api_key
        self.model = model

    def run(self, topic: str) -> list:
        prompt = (
            f"Given the research topic: '{topic}', "
            "list 2–3 focused sub-topics that are narrower and suitable for deeper research. "
            "Return only the sub-topics as a Python list of strings."
        )
        response = openai.ChatCompletion.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=150,
            temperature=0.7,
        )
        reply = response.choices[0].message.content
        try:
            sub_topics = eval(reply)
            if isinstance(sub_topics, list):
                return sub_topics
        except Exception:
            pass
        return [line.strip('- ').strip() for line in reply.splitlines() if line.strip()]

class SerpAPIResearcherAgent:
    def __init__(self, api_key: str):
        self.api_key = api_key

    def search_and_summarize(self, subtopic: str) -> dict:
        params = {
            "q": subtopic,
            "api_key": self.api_key,
            "engine": "google_scholar"
        }
        response = requests.get("https://serpapi.com/search", params=params)
        results = response.json()
        papers = results.get("organic_results", [])[:3]
        findings = []
        for paper in papers:
            title = paper.get("title")
            link = paper.get("link")
            snippet = paper.get("snippet", "")
            findings.append(f"{title} ({link}): {snippet}")

        summary_prompt = (
            f"Summarize the following findings for the subtopic '{subtopic}'. "
            "Provide a TL;DR, key insights, and citations:\n\n" +
            "\n".join(findings)
        )
        summary_response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": summary_prompt}],
            max_tokens=300,
            temperature=0.7,
        )
        summary = summary_response.choices[0].message.content
        return {
            "subtopic": subtopic,
            "summary": summary,
            "citations": [paper.get("link") for paper in papers]
        }

class SynthesizerAgent:
    def __init__(self, api_key: str, model: str = "gpt-3.5-turbo"):
        openai.api_key = api_key
        self.model = model

    def synthesize(self, topic: str, researcher_results: list, style: str = "academic") -> str:
        findings = "\n\n".join(
            [f"Subtopic: {r['subtopic']}\nSummary: {r['summary']}\nCitations: {', '.join(r['citations'])}" for r in researcher_results]
        )
        prompt = (
            f"You are a research synthesis agent. Write in a {style} style. "
            f"Given the main topic '{topic}' and the following findings from multiple researchers, "
            "merge the findings, highlight consensus and conflicting results, and produce a final structured report with:\n"
            "- Executive Summary (≤150 words)\n"
            "- Key Insights by Subtopic\n"
            "- Conflicts or Gaps in Literature\n"
            "- Citations & Resource List\n\n"
            "Findings:\n" + findings
        )
        response = openai.ChatCompletion.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=700,
            temperature=0.7,
        )
        return response.choices[0].message.content

    def refine(self, report: str, critic_feedback: str, style: str = "academic") -> str:
        prompt = (
            f"Revise the following report based on this critique: '{critic_feedback}'. "
            f"Write in a {style} style. Improve factual accuracy, clarity, and coherence. Here is the report:\n\n{report}"
        )
        response = openai.ChatCompletion.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=700,
            temperature=0.7,
        )
        return response.choices[0].message.content

class CriticAgent:
    def __init__(self, api_key: str, model: str = "gpt-3.5-turbo"):
        openai.api_key = api_key
        self.model = model

    def review(self, report: str) -> str:
        prompt = (
            "You are a research critic agent. Review the following report for factual consistency and accuracy. "
            "Highlight any potential errors, unsupported claims, or areas needing clarification.\n\n"
            "Report:\n" + report
        )
        response = openai.ChatCompletion.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=300,
            temperature=0.7,
        )
        return response.choices[0].message.content

def orchestrate(topic: str, style: str = "academic", max_retries: int = 2):
    try:
        api_key = os.getenv("OPENAI_API_KEY")
        serpapi_key = os.getenv("SERPAPI_API_KEY")

        # Split topic
        splitter = TopicSplitterAgent(api_key=api_key)
        sub_topics = splitter.run(topic)

        # Research in parallel
        researcher = SerpAPIResearcherAgent(api_key=serpapi_key)
        researcher_results = []
        with ThreadPoolExecutor() as executor:
            futures = {executor.submit(researcher.search_and_summarize, sub): sub for sub in sub_topics}
            for future in as_completed(futures):
                result = future.result()
                researcher_results.append(result)

        # Synthesize findings with style
        synthesizer = SynthesizerAgent(api_key=api_key)
        final_report = synthesizer.synthesize(topic, researcher_results, style=style)

        # Critic Agent review
        critic = CriticAgent(api_key=api_key)
        critic_review = critic.review(final_report)

        improved_report = final_report
        retries = 0
        # Self-critique loop: refine the report using the critic's feedback, up to max_retries
        while retries < max_retries:
            # Check for keywords indicating issues
            if any(word in critic_review.lower() for word in ["error", "unsupported", "clarification", "inaccurate", "incorrect", "issue", "problem"]):
                improved_report = synthesizer.refine(improved_report, critic_review, style=style)
                critic_review = critic.review(improved_report)
                retries += 1
            else:
                break

        summary = improved_report
        findings = "\n\n".join([f"{r['subtopic']}:\n{r['summary']}" for r in researcher_results])
        citations = "\n".join([c for r in researcher_results for c in r['citations']])

        return {
            "summary": summary,
            "findings": findings,
            "citations": citations,
            "critic_review": critic_review
        }
    except Exception as e:
        print("Error in orchestrate:", e)
        return None