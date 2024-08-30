from flask import render_template
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


async def get_conversational_chain(candidate_name):
    prompt_template = f"""Alright, prepare to unleash your inner Jeffrey Ross. I'm about to paste the text of a resume 
    belonging to {candidate_name}. I need you to go full-on savage and expose this document for the career-crippling 
    monstrosity it truly is. Don't hold back on the sarcasm, be merciless with the humor, and leave no cliché 
    unturned. Remember, the goal is to make {candidate_name} cry and question themselves while simultaneously forcing 
    them to completely revamp this resume from scratch. Let's see if you can turn this career catastrophe into a 
    comedy goldmine. Roast in one single paragraph. Ignore the roll number and Education section. But do comment on 
    Projects, Skills, Experience and Extracurricular. Address it directly to {candidate_name} in first person.

    Context:\n {{context}}

    Resume:
    """
    model = ChatGoogleGenerativeAI(model="gemini-1.5-flash", temperature=1)
    prompt = PromptTemplate(template=prompt_template, input_variables=["context"])
    return load_qa_chain(model, chain_type="stuff", prompt=prompt)


async def generate_roast(resume_text, candidate_name):
    text_chunks = await get_text_chunks(resume_text)

    if not text_chunks:
        return "Error: The document is empty or could not be processed."

    try:
        vector_store = await create_in_memory_faiss_index(text_chunks)
    except ValueError as e:
        return str(e)

    docs = vector_store.similarity_search(resume_text)

    chain = await get_conversational_chain(candidate_name)
    response = chain.invoke({"input_documents": docs, "context": resume_text})

    roast_response = response["output_text"].replace("*", "\"")
    roast_response = remove_duplicate_lines(roast_response)

    return roast_response
