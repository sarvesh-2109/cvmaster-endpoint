import docx
import fitz
import re


async def get_pdf_text(file_stream):
    """Extract text from a PDF file."""
    doc = fitz.open("pdf", file_stream.read())
    text = ""
    for page in doc:
        text += page.get_text()

    return text


async def get_docx_text(file_stream):
    """Extract text from a DOCX file."""
    doc = docx.Document(file_stream)
    text = ""
    for para in doc.paragraphs:
        text += para.text + "\n"

    return text


def remove_special_characters(text):
    """Remove special characters and emojis from text."""
    emoji_pattern = re.compile("["
                               u"\U0001F600-\U0001F64F"  # emoticons
                               u"\U0001F300-\U0001F5FF"  # symbols & pictographs
                               u"\U0001F680-\U0001F6FF"  # transport & map symbols
                               u"\U0001F1E0-\U0001F1FF"  # flags (iOS)
                               u"\U00002702-\U000027B0"  # Dingbats
                               u"\U000024C2-\U0001F251"
                               "]+", flags=re.UNICODE)
    text = emoji_pattern.sub(r'', text)
    text = re.sub(r'[^\x00-\x7F]+', ' ', text)
    return text


def preprocess_text(text):
    """Preprocess text by removing special characters and organizing it into sections."""
    text = remove_special_characters(text)

    return text.strip()
