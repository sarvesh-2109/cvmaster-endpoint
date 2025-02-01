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

FAISS_INDEX_DIR = "faiss_indices"
os.makedirs(FAISS_INDEX_DIR, exist_ok=True)


async def get_text_chunks(text):
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100)
    return text_splitter.split_text(text)


async def create_faiss_index(text_chunks, index_name):
    if not text_chunks:
        raise ValueError("The text chunks are empty. Cannot create a vector store.")

    embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001")
    vector_store = FAISS.from_texts(text_chunks, embedding=embeddings)

    index_path = os.path.join(FAISS_INDEX_DIR, f"{index_name}.faiss")
    vector_store.save_local(index_path)

    return vector_store


async def load_faiss_index(index_name):
    embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001")
    index_path = os.path.join(FAISS_INDEX_DIR, f"{index_name}.faiss")
    return FAISS.load_local(index_path, embeddings, allow_dangerous_deserialization=True)


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
    
    Use HTML tags for formatting instead of markdown. Specifically:
    
    Use <p> for paragraphs
    Use <br> for line breaks
    Use <b> for bold text
    Use <i> for italic text
    Use <ol> for numbered lists and <li> for list items
    Use <ul> for unordered lists and <li> for list items

    Please write a professional and engaging cover letter that:
    1. Addresses the recipient by name
    2. Expresses enthusiasm for the position and company
    3. Highlights key qualifications and experiences from the resume that align with the job requirements in bullet points.
    4. Demonstrates knowledge of the company and industry
    5. Explains why the applicant would be a great fit for the role
    6. Includes a call to action for next steps
    7. Closes with a professional sign-off
    8. Add a <br> tag after each paragraph
    
    The cover letter should be concise, engaging, and tailored to the specific job and company. 
    Aim for about 3-4 paragraphs. Keep space between paragraphs
    
    Make sure to sign off the letter with the candidate's name: {candidate_name}

    Cover Letter:
    """

    model = ChatGoogleGenerativeAI(model="gemini-1.5-flash", temperature=0.7)
    prompt = PromptTemplate(template=prompt_template,
                            input_variables=["context", "job_description", "company_name", "position_name",
                                             "recipient_name","platform_name", "candidate_name"])
    return load_qa_chain(model, chain_type="stuff", prompt=prompt)


async def generate_cover_letter(resume_text, job_description, company_name, position_name, recipient_name, platform_name, candidate_name):
    # Create or load the FAISS index for the resume
    resume_chunks = await get_text_chunks(resume_text)
    try:
        vector_store = await create_faiss_index(resume_chunks, "cover_letter_index")
    except ValueError as e:
        return f"Error: {str(e)}"

    # Perform similarity search to get relevant resume content
    docs = vector_store.similarity_search(job_description)

    # Generate the cover letter
    chain = await get_cover_letter_chain()
    response = chain.invoke({
        "input_documents": docs,
        "job_description": job_description,
        "company_name": company_name,
        "position_name": position_name,
        "recipient_name": recipient_name,
        "platform_name": platform_name,
        "candidate_name": candidate_name,
        "context": resume_text
    })

    return response["output_text"]
