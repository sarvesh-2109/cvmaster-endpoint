from langchain_google_genai import GoogleGenerativeAIEmbeddings
import google.generativeai as genai
# from langchain_community.vectorstores import FAISS  # 🔒 Commented out FAISS
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.chains.question_answering import load_qa_chain
from langchain.prompts import PromptTemplate
from langchain.text_splitter import RecursiveCharacterTextSplitter
from dotenv import load_dotenv
import os

load_dotenv()

genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

FAISS_INDEX_DIR = "faiss_indices"

# Ensure the directory exists
os.makedirs(FAISS_INDEX_DIR, exist_ok=True)


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


# 🔒 Commented out all FAISS indexing logic
# async def create_faiss_index(text_chunks, index_name):
#     if not text_chunks:
#         raise ValueError("The text chunks are empty. Cannot create a vector store.")
#
#     embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001")
#     vector_store = FAISS.from_texts(text_chunks, embedding=embeddings)
#
#     # Save the FAISS index
#     index_path = os.path.join(FAISS_INDEX_DIR, f"{index_name}.faiss")
#     vector_store.save_local(index_path)
#
#     return vector_store
#
#
# async def load_faiss_index(index_name, embeddings):
#     index_path = os.path.join(FAISS_INDEX_DIR, f"{index_name}.faiss")
#     return FAISS.load_local(index_path, embeddings, allow_dangerous_deserialization=True)


async def get_ats_chain(job_description):
    prompt_template = f"""
    As a highly sophisticated and insightful Applicant Tracking System (ATS) with extensive expertise across various professional fields, your task is to thoroughly evaluate the given resume based on the following job description:

    Job Description:
    {job_description}

    Resume:
    {{context}}

    Please ensure to use HTML tags for formatting the response strictly as follows:
    <h2> for main headings
    <h3> for subheadings
    <p> for paragraphs
    <br> for line breaks
    <b> for bold text
    <i> for italic text
    <ol> for numbered lists and <li> for list items
    <ul> for unordered lists and <li> for list items

    Provide a comprehensive, detailed analysis of the resume, addressing the candidate directly in the first person throughout your evaluation...
    """

    model = ChatGoogleGenerativeAI(model="gemini-2.0-flash-001", temperature=0.7)
    prompt = PromptTemplate(template=prompt_template, input_variables=["job_description", "context"])
    return load_qa_chain(model, chain_type="stuff", prompt=prompt)


async def generate_ats_analysis(resume_text, job_description):
    text_chunks = await get_text_chunks(resume_text)
    if not text_chunks:
        return "Error: The resume is empty or could not be processed. Did you accidentally submit a blank page?"

    try:
        # 🔒 FAISS temporarily disabled
        # vector_store = await create_faiss_index(text_chunks, "ats_index")
        # docs = vector_store.similarity_search(resume_text)

        # Directly pass full resume as context instead of vector search
        docs = [{"page_content": resume_text}]
    except ValueError as e:
        return f"Oops! {str(e)} It seems your resume is playing hide and seek, and winning."

    chain = await get_ats_chain(job_description)
    response = chain.invoke({"input_documents": docs, "job_description": job_description, "context": resume_text})
    ats_response = response["output_text"]
    ats_response = remove_duplicate_lines(ats_response)
    return ats_response
