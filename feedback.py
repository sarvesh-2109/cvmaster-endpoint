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


async def get_feedback_chain(candidate_name):
    prompt_template = f"""When provided with a resume belonging to {candidate_name}, generate constructive and serious feedback addressing the following points:

    Use HTML tags for formatting instead of markdown. Specifically:
    
    Use <h2> for main headings
    Use <h3> for subheadings
    Use <p> for paragraphs
    Use <br> for line breaks
    Use <b> for bold text
    Use <i> for italic text
    Use <ol> for numbered lists and <li> for list items
    Use <ul> for unordered lists and <li> for list items
    
    1. Begin the response with "{candidate_name}," and address them directly in the first person throughout the feedback.
    
    2. Focus on providing actionable and specific feedback for the following sections:
    <h2>Projects</h2>
    <h2>Skills</h2>
    <h2>Experience</h2>
    <h2>Extracurricular Activities</h2>
    
    3. For each section, offer detailed suggestions and include specific examples to illustrate your points, ensuring {candidate_name} can easily understand and implement the feedback.
    
    4. Projects section:
       a. Comment on all the projects individually.
       b. If a project is well-presented, offer genuine appreciation.
       c. Suggest improvements or expansions where applicable.
       d. Comment on each project individually. Use a <br> tag after each project title. 
       For example:
       <br><p><b>Project Title</b><br>
       Your feedback here...</p>
       Suggest improvements or expansions where applicable.
    
    5. Skills section:
       a. Evaluate the relevance and presentation of listed skills.
       b. Either group the technical skills by category / type or by proficiency level and provide an example.
       c. Recommend additional skills that could enhance the resume, if appropriate.
       d. Also evaluate and recommend soft skill if any.
    
    6. Experience section:
       a. If {candidate_name} has work experience, provide feedback on how to better highlight achievements and responsibilities.
       b. If {candidate_name} has no experience:
          i. Suggest an alternative section to replace "Experience" (e.g., "Relevant Coursework" or "Academic Achievements").
          ii. Provide specific suggestions on how {candidate_name} can gain relevant experience (e.g., internships, volunteer work, personal projects).
    
    7. Extracurricular activities:
       a. Comment on the relevance and presentation of listed activities.
       b. Suggest ways to better highlight leadership roles or transferable skills gained from these activities.
    
    8. Do not comment on the Header (Introduction section) or the Education section.
    
    9. Based on {candidate_name}'s projects and skills, recommend 2-3 impactful and real-world problem-solving projects that could enhance their resume.
    
    10. Provide a concise list of 3-5 key areas for improvement, summarizing the main points of your feedback.
        Do consider suggesting the removal any unnecessary details form the resume if needed.
    
    11. Maintain a constructive and supportive tone throughout the feedback, avoiding overly harsh criticism.
    
    12. <br>Conclude the feedback with a single, sarcastic line that encourages {candidate_name} to revamp their resume. 
        This line should be noticeably different in tone from the rest of the feedback.
    
    13. Do not comment on the formatting or the use of a formal resume template.

    Context:\n {{context}}

    Resume:
    """
    model = ChatGoogleGenerativeAI(model="gemini-1.5-flash", temperature=1)
    prompt = PromptTemplate(template=prompt_template, input_variables=["context"])
    return load_qa_chain(model, chain_type="stuff", prompt=prompt)


async def generate_feedback(resume_text, candidate_name):
    text_chunks = await get_text_chunks(resume_text)
    if not text_chunks:
        return "Error: The document is empty or could not be processed."

    try:
        # Create and save the FAISS index
        vector_store = await create_faiss_index(text_chunks, "feedback_index")
    except ValueError as e:
        return str(e)

    docs = vector_store.similarity_search(resume_text)

    chain = await get_feedback_chain(candidate_name)
    response = chain.invoke({"input_documents": docs, "context": resume_text})

    feedback_response = response["output_text"].replace("*", "\"")
    feedback_response = remove_duplicate_lines(feedback_response)

    return feedback_response
