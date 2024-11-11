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

    Provide a comprehensive, detailed analysis of the resume, addressing the candidate directly in the first person throughout your evaluation. Your analysis should include the following sections:

    <h2><b>1. Overall Match Assessment</b></h2>
    <p>Calculate and present an overall match percentage between the resume and the job description. Explain the key factors contributing to this percentage.</p>

    <h2><b>2. Skills Gap Analysis</b></h2>
    <p>Create a detailed list of key skills or qualifications mentioned in the job description that are missing from the resume. For each missing skill:</p>
    <ul>
    <li>Explain its importance to the role</li>
    <li>Suggest how the candidate might acquire or demonstrate this skill</li>
    </ul>

    <h2><b>3. Resume Improvement Suggestions</b></h2>
    <p>Offer specific, actionable suggestions for improving the resume to better align with the job requirements. For each suggestion:</p>
    <ul>
    <li><b>Provide a clear rationale</li>
    <li>Include an example of how to implement the suggestion</li>
    <li>Explain how this change will positively impact the resume's effectiveness</li>
    </ul>

    <h2><b>4. Standout Qualifications</b></h2>
    <p>Highlight and analyze any standout qualifications or experiences in the resume that are particularly relevant to the position. For each standout item:</p>
    <ul>
    <li>Explain its relevance to the job description</li>
    <li>Suggest how to further leverage or expand upon this qualification</li>
    <li>If applicable, recommend how to better present this information in the resume</li>
    </ul>

    <h2><b>5. Recommended Projects</b></h2>
    <p>Based on the candidate's current skills and the job requirements, recommend 2-3 impactful and real-world problem-solving portfolio projects that could help bridge any skill gaps. For each project:</p>
    <ul>
    <li>Provide a short, but detailed description</li>
    <li>Explain how it relates to the desired skills</li>
    <li>Outline the potential impact on the candidate's qualifications</li>
    </ul>

    <h2><b>6. Skill Acquisition Strategy</b></h2>
    <p>Develop a targeted strategy for the candidate to acquire or demonstrate the missing skills in a short period. This strategy should:</p>
    <ul>
    <li>Be specific and practical</li>
    <li>Include a mix of short-term and long-term actions</li>
    <li>Prioritize skills based on their importance to the job description</li>
    <li>Suggest relevant courses, certifications, or hands-on experiences</li>
    </ul>

    <h2><b>7. Summary</b></h2>
    <p>Provide a concise list of 3-5 key areas for improvement, summarizing the main points of your feedback.</p>

    Remember, as a professional resume expert, your goal is to provide constructive, supportive, and actionable feedback that will genuinely help the candidate improve their resume and significantly enhance their chances of securing the job. Maintain a balance between honesty and encouragement throughout your analysis.

    End the analysis on a new line, using a creative or witty closing phrase.

    """

    model = ChatGoogleGenerativeAI(model="gemini-1.5-flash", temperature=0.7)
    prompt = PromptTemplate(template=prompt_template, input_variables=["job_description", "context"])
    return load_qa_chain(model, chain_type="stuff", prompt=prompt)


async def generate_ats_analysis(resume_text, job_description):
    text_chunks = await get_text_chunks(resume_text)
    if not text_chunks:
        return "Error: The resume is empty or could not be processed. Did you accidentally submit a blank page? Even " \
               "our AI needs something to work with!"

    try:
        # Create and save the FAISS index
        vector_store = await create_faiss_index(text_chunks, "ats_index")
    except ValueError as e:
        return f"Oops! {str(e)} It seems your resume is playing hide and seek, and winning."

    docs = vector_store.similarity_search(resume_text)
    chain = await get_ats_chain(job_description)
    response = chain.invoke({"input_documents": docs, "job_description": job_description, "context": resume_text})
    ats_response = response["output_text"]
    ats_response = remove_duplicate_lines(ats_response)
    return ats_response
