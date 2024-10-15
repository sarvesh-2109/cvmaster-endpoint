# CvMaster API Routing Guide

This guide explains the API routing structure and endpoints for the CvMaster Flask application.

## Base URL
`http://localhost:5000`

---

## 1. Home

### GET /
Retrieves a list of all resumes.

#### Response
- **Status Code**: 200 OK
- **Content-Type**: application/json
- **Body**:
```json
{
  "status": "success",
  "data": [
    {
      "id": 1,
      "filename": "resume.pdf",
      "candidate_name": "John Doe"
    }
  ]
}
```

### POST /
Uploads a new resume.

#### Request
- **Content-Type**: multipart/form-data
- **Body**:
  - `file`: The resume file (PDF or DOCX)
  - `candidate_name`: Name of the candidate

#### Response
- **Status Code**: 201 Created
- **Content-Type**: application/json
- **Body**:
```json
{
  "status": "success",
  "message": "Resume uploaded successfully",
  "id": 1
}
```

---

## 2. View Resume

### GET /view_resume/{resume_id}
Retrieves a specific resume file.

#### Parameters
- `resume_id`: ID of the resume (integer)

#### Response
- **Status Code**: 200 OK
- **Content-Type**: application/pdf or application/vnd.openxmlformats-officedocument.wordprocessingml.document
- **Body**: Binary file content

---

## 3. Download Resume

### GET /download_resume/{resume_id}
Downloads a specific resume file.

#### Parameters
- `resume_id`: ID of the resume (integer)

#### Response
- **Status Code**: 200 OK
- **Content-Type**: application/pdf or application/vnd.openxmlformats-officedocument.wordprocessingml.document
- **Body**: Binary file content

---

## 4. Delete Resume

### DELETE /delete_resume/{resume_id}
Deletes a specific resume.

#### Parameters
- `resume_id`: ID of the resume (integer)

#### Response
- **Status Code**: 200 OK
- **Content-Type**: application/json
- **Body**:
```json
{
  "status": "success",
  "message": "Resume deleted successfully"
}
```

---

## 5. Roast Resume

### GET /roast/{resume_id}
Retrieves or generates a roast for a specific resume.

#### Parameters
- `resume_id`: ID of the resume (integer)

#### Response
- **Status Code**: 200 OK
- **Content-Type**: application/json
- **Body**:
```json
{
  "status": "success",
  "roast_response": "Roast content here",
  "candidate_name": "John Doe",
  "resume_filename": "resume.pdf"
}
```

### POST /roast/{resume_id}
Regenerates or saves a roast for a specific resume.

#### Parameters
- `resume_id`: ID of the resume (integer)

#### Request
- **Content-Type**: application/json
- **Body**:
```json
{
  "action": "regenerate",
  "roast_response": "New roast content here"
}
```

#### Response
- **Status Code**: 200 OK
- **Content-Type**: application/json
- **Body** (for "regenerate" action):
```json
{
  "status": "success",
  "roast_response": "Roast content here"
}
```
**Body** (for "save" action):
```json
{
  "status": "success",
  "message": "Roast saved successfully"
}
```

---

## 6. Feedback

### GET /feedback/{resume_id}
Retrieves or generates feedback for a specific resume.

#### Parameters
- `resume_id`: ID of the resume (integer)

#### Response
- **Status Code**: 200 OK
- **Content-Type**: application/json
- **Body**:
```json
{
  "status": "success",
  "feedback_response": "Feedback content here",
  "candidate_name": "John Doe",
  "resume_filename": "resume.pdf"
}
```

### POST /feedback/{resume_id}
Regenerates or saves feedback for a specific resume.

#### Parameters
- `resume_id`: ID of the resume (integer)

#### Request
- **Content-Type**: application/json
- **Body**:
```json
{
  "action": "regenerate",
  "feedback_response": "New feedback content here"
}
```

#### Response
- **Status Code**: 200 OK
- **Content-Type**: application/json
- **Body** (for "regenerate" action):
```json
{
  "status": "success",
  "feedback_response": "Feedback content here"
}
```
**Body** (for "save" action):
```json
{
  "status": "success",
  "message": "Feedback saved successfully"
}
```

---

## 7. Edit Resume

### POST /edit_resume/{resume_id}
Edits and improves the content of a specific resume.

#### Parameters
- `resume_id`: ID of the resume (integer)

#### Request
- **Content-Type**: application/json
- **Body**:
```json
{
  "content": "Updated resume content here"
}
```

#### Response
- **Status Code**: 200 OK
- **Content-Type**: application/json
- **Body**:
```json
{
  "status": "success",
  "resume_id": 1,
  "candidate_name": "John Doe",
  "improved_content": "Improved resume content here"
}
```

---

## 8. ATS Analysis

### GET /ats_analysis
Retrieves a list of resumes for ATS analysis.

#### Response
- **Status Code**: 200 OK
- **Content-Type**: application/json
- **Body**:
```json
{
  "status": "success",
  "resumes": [
    {
      "id": 1,
      "filename": "resume.pdf",
      "candidate_name": "John Doe"
    }
  ]
}
```

### POST /ats_analysis
Performs ATS analysis on a resume against a job description.

#### Request
- **Content-Type**: application/json
- **Body**:
```json
{
  "resume_id": 1,
  "job_description": "Job description text here"
}
```

#### Response
- **Status Code**: 200 OK
- **Content-Type**: application/json
- **Body**:
```json
{
  "status": "success",
  "analysis": "ATS analysis results here",
  "candidate_name": "John Doe"
}
```

---

## 9. Cover Letter

### GET /cover_letter
Retrieves a list of resumes for cover letter generation.

#### Response
- **Status Code**: 200 OK
- **Content-Type**: application/json
- **Body**:
```json
{
  "status": "success",
  "resumes": [
    {
      "id": 1,
      "filename": "resume.pdf",
      "candidate_name": "John Doe"
    }
  ]
}
```

### POST /cover_letter
Generates a cover letter based on provided information.

#### Request
- **Content-Type**: application/json
- **Body**:
```json
{
  "resume_id": 1,
  "job_description": "Job description text here",
  "company_name": "Example Company",
  "position_name": "Software Developer",
  "recipient_name": "Jane Smith"
}
```

#### Response
- **Status Code**: 200 OK
- **Content-Type**: application/json
- **Body**:
```json
{
  "status": "success",
  "cover_letter": "Generated cover letter text here"
}
```