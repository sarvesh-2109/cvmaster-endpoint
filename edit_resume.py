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

prompt_template = """You are an expert resume builder tasked with improving and reformatting the given content to make it more impactful and suitable for a resume. Your goal is to enhance the content's effectiveness while maintaining its core message.

    Guidelines:
    - Summarize the input content
    - Analyze and restructure the content to follow the STAR method (Situation, Task, Action, Result)
    - Present exactly 4 bullet points that implicitly follow the STAR sequence
    - Use strong action verbs and quantifiable achievements
    - Highlight key skills, technologies, metrics, and achievements using <b> tags
    - Avoid clichés and generic statements; aim for unique and specific content
    - Write in an industry-appropriate and professional language
    - Maintain a balance between being concise and providing enough detail
    
    The final response should contain:
    
    <h2><b>Improved Points:</b></h2>
    <ul>
    <li>[First point implicitly describing the situation/context with <b>key terms</b> highlighted]</li>
    <li>[Second point implicitly conveying the specific task/responsibility with <b>key terms</b> highlighted]</li>
    <li>[Third point detailing the actions taken with <b>key terms</b> highlighted]</li>
    <li>[Fourth point highlighting the quantifiable results with <b>key terms</b> highlighted]</li>
    </ul>
    
    <h2><b>Additional Points:</b></h2>
    [Provide examples of sentences that quantify achievements using variables instead of numbers, with <b>key terms</b> highlighted]
    
    Original content: {content}
    
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
