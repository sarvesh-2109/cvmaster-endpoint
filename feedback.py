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


async def get_feedback_chain(candidate_name):
    prompt_template = f"""Alright, I need you to provide constructive and serious feedback on the following 
    resume belonging to {candidate_name}. Address it directly to {candidate_name} in the first person. Start with 
    {candidate_name}, . Focus on providing actionable and specific feedback on the Projects, Skills, 
    Experience, and Extracurricular sections. While providing feedback also, provide examples so that {candidate_name}
    can easily understand. Ignore the Header (Introduction section) and the Education section. 
    Your feedback should help {candidate_name} improve their resume by highlighting areas for improvement and 
    suggesting ways to enhance the content. Avoid being overly harsh or sarcastic; the goal is to be constructive 
    and supportive. Do not comment on the formatting or the use of a formal resume template. Make sure the 
    response is not in markdown format (i.e., no use of ## for headings or ** for bold). Instead, use HTML tags 
    such as <h2> for headings, <h3> for subheadings, <p> for paragraphs, <br> for line breaks, <b> for bold, 
    and <i> for italic. Use numbered lists or <li> tags for pointers if necessary. Before ending the feedback, based 
    on the {candidate_name}'s project and skills recommend some impactful and real-world problem-solving projects. 
    Also provide the user with Areas for improvement End the feedback with a harsh sarcastic line, 
    forcing {candidate_name} to revamp their resume.
    Sign off the feedback creatively with the name CV Toaster on a new line.

    Context:\n {{context}}

    Resume:
    """
    model = ChatGoogleGenerativeAI(model="gemini-1.5-pro", temperature=0.7)
    prompt = PromptTemplate(template=prompt_template, input_variables=["context"])
    return load_qa_chain(model, chain_type="stuff", prompt=prompt)


async def generate_feedback(resume_text, candidate_name):
    text_chunks = await get_text_chunks(resume_text)
    if not text_chunks:
        return "Error: The document is empty or could not be processed."
    try:
        vector_store = await create_in_memory_faiss_index(text_chunks)
    except ValueError as e:
        return str(e)
    docs = vector_store.similarity_search(resume_text)
    chain = await get_feedback_chain(candidate_name)
    response = chain.invoke({"input_documents": docs, "context": resume_text})
    feedback_response = response["output_text"].replace("*", "\"")
    feedback_response = remove_duplicate_lines(feedback_response)
    return feedback_response
