## Resume Renaissance – CA Legislature Resume RAG App

Generate tailored resumes and cover letters for California Legislature job applications using your documents, free local LLMs, and some old‑school writing wisdom.

This project is a kind of **“resume renaissance”**: it combines
- **Old wisdom**: distilled writing tips from 1990s California Legislature materials (originally given to me in the 4th‑grade)
- **New tools**: a Retrieval‑Augmented Generation (RAG) pipeline and free local LLMs via Ollama

The goal is to help you communicate clearly and professionally to legislative offices while staying private and fully local.

## Features

- **RAG pipeline**: Index your resumes, experiences, and books; retrieve relevant chunks for each job
- **Keyword‑aware retrieval**: Extracts keywords and phrases from each job description, then uses them to semantically match your own experience/chunks for highly tailored results
- **Tailored output**: Resume and cover letter generation that closely aligns with each specific posting
- **CA Legislature writing rules**: Built‑in guidance distilled from 1990s CA Legislature writing advice (see `docs/CA_Legislature_Writing_Rules_1990s.md`)
- **ATS‑friendly**: Plain text, standard headers, no tables or graphics
- **Local & private**: Runs entirely with Ollama—no API keys, data stays on your machine
- **Resume‑first flow**: Generate and edit a resume, then build a cover letter directly from that finalized resume
- **Versioning & history**: Auto‑save with `v2`, `v3`, etc. for the same job and day, plus a simple history browser
- **Saved contact info**: Persist your own contact details and optionally import from a vCard (`.vcf`)

## Setup

### 1. Install dependencies

```bash
cd "CA Legislature Resume App"
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Install Ollama and pull models

```bash
# Install Ollama from https://ollama.com
ollama pull nomic-embed-text   # For embeddings
ollama pull llama3.2          # For generation (or mistral, etc.)
```

### 3. Add your documents

Create folders and add your files:

```
sources/
  resumes/      # Your resumes (PDF, DOCX, TXT)
  experiences/  # Work history, projects
  books/        # Relevant reading
```

### 4. Run the app

```bash
streamlit run app/main.py
```

## Usage

### 1. Ingest your documents

- Go to the **Ingest Documents** tab.
- Drop files into `sources/resumes/`, `sources/experiences/`, `sources/books/` or upload via the UI.
- Click **Process & Index** to chunk and embed your documents with FAISS + Ollama.

### 2. Generate a resume (Resume tab)

- Go to the **Resume** tab.
- Paste the **job description**.
- Optionally adjust which doc types to include (resumes / experiences / books).
- Preview the retrieved chunks to see exactly what context the model will use.
- Click **Generate Resume**.
- Edit the result in the text area.
- Click **Save to generated folder** to create a versioned Markdown file in `generated/`.

### 3. Generate a cover letter (Cover Letter tab)

- Go to the **Cover Letter** tab.
- Choose a **Resume source**:
  - Use the resume you just generated (including your edits), or
  - Upload a resume file (PDF, DOCX, TXT, MD).
- Fill in **Hiring Manager**, **Organization/Office**, and **Job Title**.
- Paste the **job description** (used for targeting, not for addressee names).
- Click **Generate Cover Letter**.
- Edit as needed, then download or save (also versioned in `generated/`).

The cover letter is generated **from your resume content plus the job description**, and it uses only the recipient info you provide (not names pulled from old chunks).

## Troubleshooting

**Dependency conflicts**: This app uses FAISS (not ChromaDB) to avoid onnxruntime issues on ARM Macs. If `pip install` fails, try upgrading pip first: `pip install --upgrade pip`

## Configuration

- **Ollama URL**: Default `http://localhost:11434`
- **Embedding model**: `nomic-embed-text`
- **LLM model**: `llama3.2` (or `mistral`, etc.)
- **Retrieval chunks**: 5–20 (default 12)

## Privacy & what goes to GitHub

By default, the following are **git‑ignored** and stay on your machine:

- `sources/` – your resumes, experience docs, books
- `generated/` – all generated resumes and cover letters
- `chroma_db/` / FAISS index files
- `config/contact.json` – your saved contact info

That means you can safely publish the app code on GitHub without exposing your personal documents or generated outputs. Just commit the code, not your data.
