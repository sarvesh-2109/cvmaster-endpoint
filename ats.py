from langchain_google_genai import GoogleGenerativeAIEmbeddings
import google.generativeai as genai
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.chains.question_answering import load_qa_chain
from langchain.prompts import PromptTemplate
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.schema import Document  # <-- Fixed: Required for stuff chain
from dotenv import load_dotenv
import os

load_dotenv()
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

FAISS_INDEX_DIR = "faiss_indices"
os.makedirs(FAISS_INDEX_DIR, exist_ok=True)


def remove_duplicate_lines(text: str) -> str:
    """Remove duplicate lines while preserving order and stripping empty lines."""
    lines = text.split("\n")
    seen = set()
    unique = []
    for line in lines:
        stripped = line.strip()
        if stripped and stripped not in seen:
            unique.append(stripped)
            seen.add(stripped)
    return "\n".join(unique)


async def get_text_chunks(text: str):
    """Split text into manageable chunks with overlap."""
    splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100)
    return splitter.split_text(text)


# FAISS logic fully disabled (kept commented for future use)
# async def create_faiss_index(...) ...
# async def load_faiss_index(...) ...


async def get_ats_chain(job_description: str):
    """Build the ATS analysis chain with job description baked into prompt."""
    prompt_template = f"""
    As a highly sophisticated and insightful Applicant Tracking System (ATS) with extensive expertise across various professional fields, your task is to thoroughly evaluate the given resume based on the following job description:
    
    <b>Job Description:</b><br>
    {job_description}
    
    <b>Resume:</b><br>
    {{context}}
    
    Please ensure to use HTML tags for formatting the response strictly as follows:
    - <h2> for main headings
    - <h3> for subheadings
    - <p> for paragraphs
    - <br> for line breaks
    - <b> for bold text
    - <i> for italic text
    - <ol> for numbered lists and <li> for list items
    - <ul> for unordered lists and <li> for list items
    
    Provide a comprehensive, detailed analysis of the resume, addressing the candidate directly in the first person throughout your evaluation.
    Focus on keyword alignment, skill relevance, experience gaps, formatting, and overall ATS compatibility.
    Be constructive, precise, and professional — but don’t hold back on tough truths.
    """
    model = ChatGoogleGenerativeAI(model="gemini-2.0-flash-001", temperature=0.7)
    prompt = PromptTemplate(
        template=prompt_template,
        input_variables=["context"]  # job_description is f-string injected
    )
    return load_qa_chain(model, chain_type="stuff", prompt=prompt)


async def generate_ats_analysis(resume_text: str, job_description: str) -> str:
    """
    Generate ATS compatibility analysis using full resume context.
    """
    if not resume_text.strip():
        return "<p>Error: The resume is empty or could not be processed. Did you accidentally submit a blank page?</p>"

    # Chunk resume for consistency with other modules
    chunks = await get_text_chunks(resume_text)
    if not chunks:
        return "<p>Error: Failed to parse resume content.</p>"

    # Convert to Document objects — REQUIRED by StuffDocumentsChain
    docs = [Document(page_content=chunk) for chunk in chunks]

    # Build and invoke chain
    chain = await get_ats_chain(job_description)
    response = chain.invoke({
        "input_documents": docs,
        "context": resume_text  # Full resume passed as context
    })

    ats_response = response["output_text"]
    ats_response = remove_duplicate_lines(ats_response)

    return ats_response
