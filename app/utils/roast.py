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
FAISS_INDEX_DIR = "../faiss_indices"

# Ensure the directory exists
os.makedirs(FAISS_INDEX_DIR, exist_ok=True)

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


async def create_faiss_index(text_chunks, index_name):
    if not text_chunks:
        raise ValueError("The text chunks are empty. Cannot create a vector store.")

    embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001")
    vector_store = FAISS.from_texts(text_chunks, embedding=embeddings)

    # Save the FAISS index
    index_path = os.path.join(FAISS_INDEX_DIR, f"{index_name}.faiss")
    vector_store.save_local(index_path)

    return vector_store


async def get_conversational_chain(candidate_name):
    prompt_template = f"""Alright, prepare to unleash your inner Jeffery Ross. 
    I'm about to paste the text of a resume belonging to {candidate_name}. 
    I need you to unleash your inner critic and dissect this document with a blend of sharp wit and brutal honesty. 
    Your mission is to deliver a scathing yet entertaining critique that leaves {candidate_name} questioning their life 
    choices and scrambling to overhaul this resume from the ground up.
    
    Instructions: 
    
    Tone: Adopt a brutally sarcastic and humorous approach. Be merciless in your critique while keeping it 
    engaging and entertaining. 
    
    Focus Areas: 
    
    Projects: Highlight any glaring flaws, lack of impact, 
    or vague descriptions that make these projects sound more like hobbies than achievements. 
    
    Skills: 
    Call out any buzzwords or clichés that are overused, and point out skills that seem irrelevant or exaggerated. 
    
    Experience: 
    Critique the relevance and depth of the work experience. 
    Are they just listing duties instead of showcasing accomplishments? 
    
    Extracurricular: 
    Examine how these activities contribute to their professional image. Are they 
    impressive or just a collection of uninspired activities? Addressing the Candidate: Write directly to 
    {candidate_name} in the first person. Make it personal and impactful.
    
    Length: 
    Deliver your roast in a single, powerful paragraph that captures the essence of the critique.

    Context:\n {{context}}

    Resume:
    """
    model = ChatGoogleGenerativeAI(model="gemini-1.5-flash", temperature=1)
    prompt = PromptTemplate(template=prompt_template, input_variables=["context"])
    return load_qa_chain(model, chain_type="stuff", prompt=prompt)


async def load_faiss_index(index_name, embeddings):
    index_path = os.path.join(FAISS_INDEX_DIR, f"{index_name}.faiss")
    return FAISS.load_local(index_path, embeddings, allow_dangerous_deserialization=True)


async def generate_roast(resume_text, candidate_name):
    text_chunks = await get_text_chunks(resume_text)

    if not text_chunks:
        return "Error: The document is empty or could not be processed."

    try:
        # Create and save the FAISS index
        vector_store = await create_faiss_index(text_chunks, "roast_index")
    except ValueError as e:
        return str(e)

    docs = vector_store.similarity_search(resume_text)

    chain = await get_conversational_chain(candidate_name)
    response = chain.invoke({"input_documents": docs, "context": resume_text})

    roast_response = response["output_text"].replace("*", "\"")
    roast_response = remove_duplicate_lines(roast_response)

    return roast_response
