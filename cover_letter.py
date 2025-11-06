# cover_letter.py
from langchain_google_genai import GoogleGenerativeAIEmbeddings
import google.generativeai as genai
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.chains.question_answering import load_qa_chain
from langchain.prompts import PromptTemplate
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.schema import Document  # <-- FIXED: Required for stuff chain
from dotenv import load_dotenv
import os

load_dotenv()
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

FAISS_INDEX_DIR = "faiss_indices"
os.makedirs(FAISS_INDEX_DIR, exist_ok=True)


async def get_text_chunks(text: str):
    """Split resume into chunks for processing."""
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100)
    return text_splitter.split_text(text)


# --- FAISS CODE COMMENTED OUT (safe to keep) ---
"""
async def create_faiss_index(...): ...
async def load_faiss_index(...): ...
"""
# --- END COMMENTED ---


async def get_cover_letter_chain():
    prompt_template = """
    As an expert career coach, your task is to create a compelling cover letter for a job application.
    Use the provided resume content and job description to tailor the letter specifically to the position and company.
    
    Resume Content:
    {context}
    
    Job Description:
    {job_description}
    
    Company Name: {company_name}
    Position: {position_name}
    Recipient: {recipient_name}
    Platform: {platform_name}
    Candidate Name: {candidate_name}
   
    Use HTML tags for formatting instead of markdown:
    - <p> for paragraphs
    - <br> for line breaks
    - <b> bold</b>, <i>italic</i>
    - <ol><li>ordered lists</li></ol>
    - <ul><li>bullet points</li></ul>
    
    Write a professional, enthusiastic cover letter that:
    1. Addresses {recipient_name} by name
    2. Shows genuine excitement for {company_name} and the role
    3. Uses bullet points to highlight 3–4 key achievements from the resume that match the job
    4. Shows you’ve researched {company_name}
    5. Ends with a confident call-to-action
    6. Signs off with {candidate_name}
    
    Keep it 3–4 paragraphs. Add <br> after each paragraph for spacing.
    
    Cover Letter:
    """
    model = ChatGoogleGenerativeAI(model="gemini-2.0-flash-001", temperature=0.7)
    prompt = PromptTemplate(
        template=prompt_template,
        input_variables=[
            "context", "job_description", "company_name",
            "position_name", "recipient_name", "platform_name", "candidate_name"
        ]
    )
    return load_qa_chain(model, chain_type="stuff", prompt=prompt)


async def generate_cover_letter(
    resume_text: str,
    job_description: str,
    company_name: str,
    position_name: str,
    recipient_name: str,
    platform_name: str,
    candidate_name: str
) -> str:
    """
    Generate a tailored HTML-formatted cover letter.
    """
    if not resume_text.strip():
        return "<p>Error: Resume is empty.</p>"

    # Step 1: Chunk the resume
    chunks = await get_text_chunks(resume_text)
    if not chunks:
        return "<p>Error: Could not process resume.</p>"

    # Step 2: Convert strings → Document objects (REQUIRED by stuff chain)
    docs = [Document(page_content=chunk) for chunk in chunks]

    # Step 3: Build and run the chain
    chain = await get_cover_letter_chain()
    response = chain.invoke({
        "input_documents": docs,
        "context": resume_text,                  # full resume as context
        "job_description": job_description,
        "company_name": company_name,
        "position_name": position_name,
        "recipient_name": recipient_name,
        "platform_name": platform_name,
        "candidate_name": candidate_name
    })

    cover_letter = response["output_text"]

    # Step 4: Light cleanup
    cover_letter = cover_letter.replace("**", "").replace("* ", "• ").strip()
    return cover_letter
