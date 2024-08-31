from langchain_google_genai import GoogleGenerativeAIEmbeddings
import google.generativeai as genai
from langchain_community.vectorstores import FAISS
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.chains.question_answering import load_qa_chain
from langchain.prompts import PromptTemplate
from langchain.text_splitter import RecursiveCharacterTextSplitter
from dotenv import load_dotenv
import os

load_dotenv()
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))


def remove_duplicate_lines(text):
    lines = text.split("\n")
    unique_lines = []
    seen_lines = set()
    for line in lines:
        if line.strip() not in seen_lines:
            unique_lines.append(line.strip())
            seen_lines.add(line.strip())
    return "\n".join(unique_lines)


async def get_text_chunks(text):
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100)
    return text_splitter.split_text(text)


async def create_in_memory_faiss_index(text_chunks):
    if not text_chunks:
        raise ValueError("The text chunks are empty. Cannot create a vector store.")
    embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001")
    vector_store = FAISS.from_texts(text_chunks, embedding=embeddings)
    return vector_store


async def get_ats_chain(job_description):
    prompt_template = f"""As serious and insightful Applicant Tracking System (ATS) with expertise across various 
    fields evaluate the given resume based on the following job description:

    Job Description: {{job_description}}

    Resume: {{context}}

    Provide a comprehensive analysis of the resume, addressing it directly to the candidate in the first person. 
    Include the following:
    1. An overall match percentage between the resume and the job description.
    2. A list of key skills or qualifications mentioned in the job description that are missing from the resume. 
    3. Specific, actionable suggestions for improving the resume to better match the job requirements. 
    Provide examples where possible to help the candidate understand how to implement your suggestions.
    4. Highlight any standout qualifications or experiences in the resume that are particularly relevant to the position. 
    Explain how these can be leveraged or expanded upon.
    5. Based on the candidate's current skills and the job requirements, recommend 2-3 impactful and real-world 
    problem-solving projects that could help bridge any skill gaps. Provide short descriptions of these projects and 
    explain how they relate to the desired skills.
    6. Suggest how the candidate can acquire or demonstrate the missing skills in a short period of time.
    Be specific and practical in your advice.
    Remember, you are a professional resume expert here. The goal is to provide constructive and supportive feedback 
    that will genuinely help the candidate improve their resume and chances of landing the job.
    
    Format the analysis using the following HTML tags:
    - <ul> for unordered lists
    - <li> for list items
    - <b> for emphasis on key terms or achievements
    - <i> for any technical terms or job titles

    Sign of your analysis with a motivational call-to-action, encouraging the candidate to revamp their resume based 
    on your feedback.

"""

    model = ChatGoogleGenerativeAI(model="gemini-1.5-pro", temperature=0.7)
    prompt = PromptTemplate(template=prompt_template, input_variables=["job_description", "context"])
    return load_qa_chain(model, chain_type="stuff", prompt=prompt)


async def generate_ats_analysis(resume_text, job_description):
    text_chunks = await get_text_chunks(resume_text)
    if not text_chunks:
        return "Error: The resume is empty or could not be processed. Did you accidentally submit a blank page? Even " \
               "our AI needs something to work with!"

    try:
        vector_store = await create_in_memory_faiss_index(text_chunks)
    except ValueError as e:
        return f"Oops! {str(e)} It seems your resume is playing hide and seek, and winning."

    docs = vector_store.similarity_search(resume_text)
    chain = await get_ats_chain(job_description)
    response = chain.invoke({"input_documents": docs, "job_description": job_description, "context": resume_text})
    ats_response = response["output_text"]
    ats_response = remove_duplicate_lines(ats_response)
    return ats_response
