from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.prompts import PromptTemplate
from langchain.schema.runnable import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser
import google.generativeai as genai
from langchain_community.vectorstores import FAISS
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from dotenv import load_dotenv
import os

load_dotenv()

genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

FAISS_INDEX_DIR = "faiss_indices"

# Ensure the directory exists
os.makedirs(FAISS_INDEX_DIR, exist_ok=True)

prompt_template = """You are an expert resume builder tasked with improving and reformatting the given content to 
    make it more impactful and suitable for a resume. Your goal is to enhance the content's effectiveness while 
    maintaining its core message.

    Guidelines:
    Summarize the input content.
    If the summarized content is in a paragraph, convert the summarized content into concise, impactful bullet points.
    If the summarized content is in points or short sentences, improve each point to make it more compelling.
    Don't give the summarized points in the final response.
    Rewrite the sentence using actionable and impactful points. Make use strong action verbs and quantifiable achievements.
    While rewriting, avoid clichés and generic statements; aim for unique and specific content.
    Rewrite in an industry-appropriate and professional language.
    Whilst rewriting maintain a balance between being concise and providing enough detail to showcase expertise.
    
    The final response should only contain:
    Append the rewritten points under "<h2><b>Improved Point(s):</b></h2>". 
    At the end add "<h2><b>Additional Points:</b></h2>" where provide examples of sentence(s) that will quantify the achievements and use variables instead of numbers.
    Make the keywords or phrases bold by using the <b> tag.
    

    Format the output using the following HTML tags:
    - <ul> for unordered lists
    - <li> for list items
    - <b> for emphasis on key terms or achievements
    - <i> for any technical terms or job titles

    Original content:
    {content}

    Please provide the improved version:
    """

prompt = PromptTemplate.from_template(prompt_template)

model = ChatGoogleGenerativeAI(model="gemini-1.5-flash", temperature=0.7)

chain = (
        {"content": RunnablePassthrough()}
        | prompt
        | model
        | StrOutputParser()
)


async def create_faiss_index(text_chunks, index_name):
    if not text_chunks:
        raise ValueError("The text chunks are empty. Cannot create a vector store.")

    embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001")
    vector_store = FAISS.from_texts(text_chunks, embedding=embeddings)

    # Save the FAISS index
    index_path = os.path.join(FAISS_INDEX_DIR, f"{index_name}.faiss")
    vector_store.save_local(index_path)

    return vector_store


async def load_faiss_index(index_name, embeddings):
    index_path = os.path.join(FAISS_INDEX_DIR, f"{index_name}.faiss")
    return FAISS.load_local(index_path, embeddings, allow_dangerous_deserialization=True)


def generate_improved_content(content: str) -> str:
    response = chain.invoke(content)
    return response.strip()


async def generate_improved_content_with_faiss(content: str) -> str:
    text_chunks = [content]  # Assuming content is a single string; modify as needed for multiple chunks.

    try:
        # Create and save the FAISS index
        vector_store = await create_faiss_index(text_chunks, "edit_resume_index")
    except ValueError as e:
        return f"Error: {str(e)}"

    docs = vector_store.similarity_search(content)

    # Invoke the chain with the content
    improved_content = generate_improved_content(content)

    return improved_content
