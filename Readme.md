# CvMaster API Routing Guide

This guide explains the API routing structure and endpoints for the CvMaster Flask application.

## API Routes

The API routes are defined in the `api/routes.py` file and are registered with the Flask application in `app.py` using the `api_bp` blueprint.

### Get All Resumes
- **Endpoint**: `GET /api/resumes`
- **Description**: Retrieves a list of all uploaded resumes.
- **Response**: Returns a JSON array of resume objects, including `id`, `filename`, and `candidate_name`.

### Upload a Resume
- **Endpoint**: `POST /api/resumes`
- **Description**: Uploads a new resume file.
- **Request**: Expects a `file` field (PDF or DOCX) and a `candidate_name` field in the request body.
- **Response**: Returns a JSON object with a `message` indicating successful upload and the `id` of the newly created resume.

### Get a Specific Resume
- **Endpoint**: `GET /api/resumes/<int:resume_id>`
- **Description**: Retrieves a specific resume by its ID.
- **Response**: Returns a JSON object containing the `id`, `filename`, `candidate_name`, and `extracted_text` of the requested resume.

### Delete a Resume
- **Endpoint**: `DELETE /api/resumes/<int:resume_id>`
- **Description**: Deletes a specific resume by its ID.
- **Response**: Returns a JSON object with a `message` indicating successful deletion.

### Improve Resume Content
- **Endpoint**: `POST /api/improve_content`
- **Description**: Improves the content of a resume.
- **Request**: Expects a `content` field in the request body containing the text to be improved.
- **Response**: Returns a JSON object with an `improved_content` field containing the enhanced text.

### Generate Roast Response
- **Endpoint**: `POST /api/roast/<int:resume_id>`
- **Description**: Generates a roast response for a specific resume.
- **Response**: Returns a JSON object with a `roast_response` field containing the generated roast.

### Generate Feedback
- **Endpoint**: `POST /api/feedback/<int:resume_id>`
- **Description**: Generates feedback for a specific resume.
- **Response**: Returns a JSON object with a `feedback_response` field containing the generated feedback.

### Perform ATS Analysis
- **Endpoint**: `POST /api/ats_analysis/<int:resume_id>`
- **Description**: Performs ATS analysis on a specific resume.
- **Request**: Expects a `job_description` field in the request body containing the job description for analysis.
- **Response**: Returns a JSON object with an `analysis` field containing the ATS analysis results.

## Testing the API

You can test the API using tools like Postman or cURL. Here are some example requests:

1. **Get All Resumes**:
   - **Endpoint**: `GET /api/resumes`

2. **Upload a Resume**:
   - **Endpoint**: `POST /api/resumes`
   - **Body**: Form-data with `file` and `candidate_name`

3. **Get a Specific Resume**:
   - **Endpoint**: `GET /api/resumes/<resume_id>`

4. **Delete a Resume**:
   - **Endpoint**: `DELETE /api/resumes/<resume_id>`

5. **Improve Resume Content**:
   - **Endpoint**: `POST /api/improve_content`
   - **Body**: JSON with `content`

6. **Generate Roast Response**:
   - **Endpoint**: `POST /api/roast/<resume_id>`

7. **Generate Feedback**:
   - **Endpoint**: `POST /api/feedback/<resume_id>`

8. **Perform ATS Analysis**:
   - **Endpoint**: `POST /api/ats_analysis/<resume_id>`
   - **Body**: JSON with `job_description`

Feel free to explore and test the API using these endpoints!