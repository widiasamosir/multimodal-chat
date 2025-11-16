# Multimodal Document Chat System 


## Table of Contents

- Project overview  
- Tech stack  
- Quickstart (Docker)  
- Environment variables (`.env.example`)  
- API endpoints & testing examples  
- Features implemented  
- Known limitations  
- Future improvements  
- Test scenarios & checklist  
- Screenshots (placeholders)  

***

## Evaluation Criteria

- RAG (Retrieval Augmented Generation) implementation quality (relevance, accuracy)  
- Multi-turn conversation support (context maintenance)  
- Inclusion of images and tables in responses  
- Quality of LLM prompt engineering  
- Response speed and user experience  

***

## System Architecture

```
┌────────────┐
│  Frontend  │ (Next.js)
│  Chat UI   │
└──────┬─────┘
       │ HTTP
       ▼
┌────────────┐
│  Backend   │ (FastAPI)
│ API Server │
└──────┬─────┘
       │
  ┌────┴─────┐
  │          │
  ▼          ▼
┌────────────┐   ┌────────────┐
│ Document   │   │    Chat    │
│ Processor  │   │   Engine   │
│ (Docling)  │   │   (RAG)    │
└──────┬─────┘   └──────┬─────┘
       │               │
       ▼               ▼
┌──────────────────────────┐
│      Vector Store        │
│ (PostgreSQL + pgvector)  │
└──────────────────────────┘
       │
       ▼
┌──────────────────────────┐
│     File Storage         │
│ (Images, Tables, PDFs)   │
└──────────────────────────┘
```

***

## Tech Stack

- Backend: FastAPI (Python)  
- Document processing: Docling  
- Image handling: Pillow  
- Embeddings: OpenAI / local embedding model (fallback)  
- Vector DB: PostgreSQL + pgvector  
- Chat/QA: LangChain-style retrieval + LLM (configurable)  
- Storage: local `./uploads` directory  
- Orchestration: Docker & docker-compose  

***

## Quickstart (Docker)

> **Prerequisites:** Docker and Docker Compose installed locally.

1. Copy `.env.example` to `.env` and update values as needed:
   ```bash
   cp .env.example .env
   # edit .env 
   ```
   
2. Build and start the services:
   ```bash
   docker-compose build --no-cache
   docker-compose up -d
   # follow logs for the backend
   docker-compose logs -f web
   ```
3. Access the frontend UI (if included) at [http://localhost:3000](http://localhost:3000) and the FastAPI interactive docs at [http://localhost:8000/docs](http://localhost:8000/docs).  
4. Upload a sample PDF (`1706.03762v7.pdf`) using the web UI or via API (see API endpoints below).

***

### For test, please use Groq (Free Tier) or OpenAI. In This submission result, I use Groq for LLM and HF for embedding. 

1. **Get free API key**
   - Go to https://console.groq.com
   - Sign up and get API key

2. **Update .env**
```bash
GROQ_API_KEY=your-groq-api-key
LLM_PROVIDER=groq
```
***

## Environment Variables (`.env.example`)

```ini
# OpenAI API Key (if using OpenAI for embeddings and LLM)
OPENAI_API_KEY=enter_your_openai_api_key_here

# OpenAI API Key (if using Groq for LLM)
GROQ_API_KEY=enter_your_groq_api_key_here
LLM_PROVIDER=groq

# OpenAI Models (Optional - defaults provided)
OPENAI_MODEL=gpt-4o-mini
OPENAI_EMBEDDING_MODEL=text-embedding-3-small
GROQ_MODEL=llama-3.3-70b-versatile

# Groq Models (Optional - defaults provided)
GROQ_MODEL=llama-3.3-70b-versatile

# Database (Configured in docker-compose.yml)
DATABASE_URL=postgresql://docuser:docpass@localhost:5432/docdb

# Redis (Configured in docker-compose.yml)
REDIS_URL=redis://localhost:6379/0

# Upload Settings
UPLOAD_DIR=./uploads
MAX_FILE_SIZE=50  # MB

```

***

## API Endpoints & Testing Examples

> All endpoints are documented and available interactively at `/docs`.

### 1. Upload a document

```bash
curl -X POST "http://localhost:8000/api/documents/upload" \
  -H "accept: application/json" \
  -H "Authorization: Bearer $API_KEY" \
  -F "file=@doc/1706.03762v7.pdf;type=application/pdf"
````

**Response:** JSON with `document_id` and processing job ID.

---

### 2. Check document processing status

```bash
curl "http://localhost:8000/api/documents/{document_id}" -H "accept: application/json"
```

**Note:** The response JSON contains a `status` field (`pending`, `processing`, `completed`) that you can check before performing a chat query.

---

### 3. Retrieve document details (text chunks, images, tables)

```bash
curl "http://localhost:8000/api/documents/{document_id}" -H "accept: application/json"
```

**Response:** Includes `text_chunks`, `images`, and `tables` metadata.

---

### 4. Perform a chat/QA query

```bash
curl -X POST "http://localhost:8000/api/chat" \
  -H "Content-Type: application/json" \
  -d '{"document_id":"<document_id>","query":"What is the main conclusion of this paper?"}'
```

**Response:** Includes an `answer` along with an `evidence` array, plus related images and tables metadata for inline display.

---

## Running the Automated Test Script

We provide a Bash script `test_api.sh` to test all endpoints automatically 

```bash
./test_api.sh
```

**Features of `test_api.sh`:**

* Uploads a document (`doc/1706.03762v7.pdf`)
* Waits until the document processing status is `completed`
* Retrieves document details
* Performs a chat/QA query automatically
* Displays all JSON responses directly in the terminal

## Features Implemented

- PDF upload API and basic web UI for file uploads  
- Background processing extracting text, images, and tables  
- OCR fallback using Tesseract for scanned page support  
- Chunking and embedding generation with configurable providers  
- Embeddings stored in PostgreSQL + pgvector  
- Retrieval pipeline returning top-k chunks with linked images/tables  
- Chat API providing retrieval-augmented answers with evidence metadata  
- Frontend chat UI displaying images and tables inline  

***

## Known Limitations

- Large PDF files may require increased memory limits beyond Docker defaults  
- Embeddings and LLM calls depend on external provider rate limits and API keys  
- Only local filesystem storage is supported by default  

***

## Future Improvements

- Support for blob storage via self-hosted or third-party services  
- Ability to select different LLM/embedding models dynamically (i.e., GPT models, Perplexity, and other AI agents)  

***

## Test Scenarios & Checklist

### Scenario 1: Basic Document Processing

- [ ] Upload `1706.03762v7.pdf` via UI or API  
- [ ] Confirm processing reaches status `processed`  
- [ ] Verify extracted text snippets, images (thumbnails and downloads), and tables (CSV/HTML)

### Scenario 2: Text-based Question

- [ ] Query: "What is the main conclusion of this paper?"  
- [ ] Response contains conclusion or paraphrase with supporting evidence text chunks

### Scenario 3: Image-related Question

- [ ] Query: "Show me the architecture diagram"  
- [ ] Answer includes relevant image(s) with captions and clickable full-size view

### Scenario 4: Table-related Question

- [ ] Query: "What are the experimental results?"  
- [ ] Response shows related table(s) and a brief textual summary

### Scenario 5: Multi-turn Conversation

- [ ] Q1: "What is the dataset used?"  
- [ ] Q2: "How many samples does it contain?"  
- [ ] Q2 answer uses Q1 context correctly  

***
## Screenshots

### 1. Document Upload Screen
![Document Upload](screenshots/01-upload.png)

### 2. Document Processing Complete
![Processing Complete](screenshots/02-processing-complete.png)

### 3. Chat Interface
![Chat Interface](screenshots/03-chat-interface.png)

### 4. Scenarios

#### Scenario 1
![Scenario 1](screenshots/Scenario-1.png)

#### Scenario 2
![Scenario 2](screenshots/Scenario-2.png)

#### Scenario 3.1
![Scenario 3.1](screenshots/Scenario-3.1.png)

#### Scenario 3.2
![Scenario 3.2](screenshots/Scenario-3.2.png)

#### Scenario 4.1
![Scenario 4.1](screenshots/Scenario-4.1.png)

#### Scenario 4.2
![Scenario 4.2](screenshots/Scenario-4.2.png)

#### Scenario 5.1
![Scenario 5.1](screenshots/Scenario-5.1.png)

#### Scenario 5.2
![Scenario 5.2](screenshots/Scenario-5.2.png)
***
