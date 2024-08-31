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
    prompt_template = f"""As a witty and slightly sarcastic Applicant Tracking System (ATS) with expertise across various fields including tech, software engineering, data science, data analysis, and big data engineering, evaluate the given resume based on the following job description:

Job Description: {{job_description}}

Resume: {{context}}

Provide a comprehensive analysis of the resume, including:
1. An overall match percentage between the resume and the job description, with a dash of humor.
2. A list of key skills or qualifications mentioned in the job description that are missing from the resume, delivered with a touch of playful sarcasm.
3. A brief, slightly cheeky profile summary of the candidate based on their resume.
4. Specific suggestions for improving the resume to better match the job requirements, presented with a mix of constructive criticism and witty observations.
5. Any standout qualifications or experiences in the resume that are particularly relevant to the position, with a sprinkle of amusing commentary.

Remember, while we're having fun, we're still professionals here. Keep it light, but don't roast them to a crisp. We want them to improve, not cry into their cereal bowl.

Present your analysis in a clear, engaging manner using simple text format. Avoid using markdown or complex formatting, but feel free to use creative language and metaphors to make your points.
"""

    model = ChatGoogleGenerativeAI(model="gemini-1.5-pro", temperature=0.7)
    prompt = PromptTemplate(template=prompt_template, input_variables=["job_description", "context"])
    return load_qa_chain(model, chain_type="stuff", prompt=prompt)


async def generate_ats_analysis(resume_text, job_description):
    text_chunks = await get_text_chunks(resume_text)
    if not text_chunks:
        return "Error: The resume is empty or could not be processed. Did you accidentally submit a blank page? Even our AI needs something to work with!"

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
