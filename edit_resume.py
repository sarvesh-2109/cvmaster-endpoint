from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain
import google.generativeai as genai
from dotenv import load_dotenv
import os

load_dotenv()
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))


async def generate_improved_content(content):
    prompt_template = """You are an expert resume builder tasked with improving and reformatting the given content to 
    make it more impactful and suitable for a resume. Your goal is to enhance the content's effectiveness while 
    maintaining its core message.

    Guidelines:
    Summarize the input content.
    If the summarized content is in a paragraph, convert the summarized content into concise, impactful bullet points.
    If the summarized content is in points or short sentences, improve each point to make it more compelling.
    Rewrite the sentence using actionable and impactful points. Make use strong action verbs and quantifiable achievements.
    While rewriting, avoid clichés and generic statements; aim for unique and specific content.
    Rewrite in an industry-appropriate and professional language.
    Whilst rewriting maintain a balance between being concise and providing enough detail to showcase expertise.
    
    At the end add "Additional Points" where provide examples of sentence(s) that will quantify the achievements.
    

    Format the output using the following HTML tags:
    - <ul> for unordered lists
    - <li> for list items
    - <b> for emphasis on key terms or achievements
    - <i> for any technical terms or job titles

    Original content:
    {content}

    Please provide the improved version:
    """

    prompt = PromptTemplate(template=prompt_template, input_variables=["content"])

    model = ChatGoogleGenerativeAI(model="gemini-1.5-pro", temperature=1)
    chain = LLMChain(llm=model, prompt=prompt)

    response = await chain.arun(content=content)
    return response.strip()