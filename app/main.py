"""CA Legislature Resume RAG App - Streamlit UI."""
import sys
from pathlib import Path

# Add project root to path so "app" package is findable
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

import streamlit as st
import re
from datetime import date

from app.config import (
    SOURCES_DIR,
    CHROMA_DIR,
    OUTPUTS_DIR,
    GENERATED_DIR,
    RESUMES_DIR,
    EXPERIENCES_DIR,
    BOOKS_DIR,
    OLLAMA_BASE_URL,
    EMBEDDING_MODEL,
    LLM_MODEL,
    CHUNK_SIZE,
    CHUNK_OVERLAP,
    DEFAULT_TOP_K,
)
from app.ingestion import load_documents_from_dir, load_uploaded_file, chunk_documents, VectorStore
from app.retrieval import retrieve_context, extract_keywords
from app.generation import (
    build_resume_prompt,
    build_cover_letter_prompt,
    save_output,
    get_output_filename_with_ext,
    load_history,
)
from app.utils.contact import load_contact_config, save_contact_config, parse_vcard
from app.utils.html_export import md_to_html


def extract_contact_info(job_description: str) -> dict:
    """
    Best-effort extraction of contact info from a job description.
    Returns keys: job_title, hiring_manager_name, contact_email, contact_phone, contact_org.
    """
    text = job_description or ""
    result = {
        "job_title": "",
        "hiring_manager_name": "",
        "contact_email": "",
        "contact_phone": "",
        "contact_org": "",
    }

    # Job title (common patterns)
    for pattern in [
        r"(?:Position|Job\s*Title|Title)\s*[:\-]\s*([^\n\r]{5,80})",
        r"(?:Seeking|Hiring)\s+(?:a|an)?\s*([A-Za-z\s\-]+(?:Assistant|Analyst|Director|Coordinator|Specialist|Manager))",
        r"^([A-Za-z\s\-]+(?:Legislative\s+Assistant|Legislative\s+Analyst|Staff\s+Assistant|District\s+Director))(?:\s|$|,)",
    ]:
        m = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
        if m:
            title = m.group(1).strip()
            title = re.split(r"[\n\r,;]", title)[0].strip()
            if 5 <= len(title) <= 80:
                result["job_title"] = title
                break

    # Email
    email_match = re.search(r"([A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,})", text, re.IGNORECASE)
    if email_match:
        result["contact_email"] = email_match.group(1).strip()

    # Phone (very permissive)
    phone_match = re.search(
        r"(\+?1[\s\-\.]?)?(\(?\d{3}\)?[\s\-\.]?\d{3}[\s\-\.]?\d{4})",
        text,
        re.IGNORECASE,
    )
    if phone_match:
        result["contact_phone"] = phone_match.group(0).strip()

    # Hiring manager / contact name lines
    for pattern in [
        r"(Hiring\s+Manager|Hiring\s+Contact|Contact\s+Person|Contact)\s*[:\-]\s*(.+)",
        r"(ATTN|Attn|Attention)\s*[:\-]\s*(.+)",
    ]:
        m = re.search(pattern, text)
        if m:
            name = m.group(m.lastindex).strip()
            # Trim trailing punctuation and overly-long captures
            name = re.split(r"[\n\r,;]", name)[0].strip()
            if 2 <= len(name) <= 80:
                result["hiring_manager_name"] = name
                break

    # Organization guess (common government phrasing)
    org_match = re.search(r"(California\s+State\s+Senate|California\s+State\s+Assembly|Office\s+of\s+[A-Z][^\n\r]{3,80}|Department\s+of\s+[A-Z][^\n\r]{3,80}|Committee\s+on\s+[A-Z][^\n\r]{3,80})", text)
    if org_match:
        result["contact_org"] = org_match.group(1).strip()

    return result


def check_ollama_health(host: str, embed_model: str, llm_model: str) -> tuple[bool, str]:
    """Verify Ollama is running and models exist. Returns (ok, error_message)."""
    try:
        import ollama
        client = ollama.Client(host=host)
        client.embed(model=embed_model, input="test")
        return True, ""
    except Exception as e:
        err = str(e).lower()
        if "connection" in err or "refused" in err or "fetch" in err:
            return False, f"Ollama not reachable at {host}. Start with 'ollama serve'."
        if "not found" in err or "404" in err:
            return False, f"Model not found. Run: ollama pull {embed_model} and ollama pull {llm_model}"
        return False, f"Ollama error: {e}"


def run_generation(
    prompt_type: str,
    job_desc: str,
    context: str,
    job_title: str,
    hiring_manager_name: str,
    contact_email: str,
    contact_phone: str,
    contact_org: str,
    my_name: str,
    my_email: str,
    my_phone: str,
    my_address: str,
    llm_model: str,
    ollama_host: str,
) -> str:
    """Generate resume or cover letter using Ollama."""
    import ollama
    client = ollama.Client(host=ollama_host)
    if prompt_type == "resume":
        system, user = build_resume_prompt(
            job_description=job_desc,
            context=context,
            job_title=job_title,
            my_name=my_name,
            my_email=my_email,
            my_phone=my_phone,
            my_address=my_address,
        )
    else:
        system, user = build_cover_letter_prompt(
            job_description=job_desc,
            context=context,
            job_title=job_title,
            hiring_manager_name=hiring_manager_name,
            contact_email=contact_email,
            contact_phone=contact_phone,
            contact_org=contact_org,
            my_name=my_name,
            my_email=my_email,
            my_phone=my_phone,
            my_address=my_address,
        )
    response = client.chat(
        model=llm_model,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    )
    return response["message"]["content"]


def main():
    st.set_page_config(page_title="CA Legislature Resume App", page_icon="📄", layout="wide")
    st.title("CA Legislature Resume RAG App")
    st.caption("Tailor resumes and cover letters for CA Legislature jobs using your documents")

    # Session state for generated outputs (persist across reruns)
    if "generated_resume" not in st.session_state:
        st.session_state.generated_resume = None
    if "generated_letter" not in st.session_state:
        st.session_state.generated_letter = None
    # Session state for contact fields
    for k, default in [
        ("hiring_manager_name", ""),
        ("contact_email", ""),
        ("contact_phone", ""),
        ("contact_org", ""),
    ]:
        if k not in st.session_state:
            st.session_state[k] = default

    # Session state for YOUR contact info — load from config if first run
    if "contact_loaded" not in st.session_state:
        saved = load_contact_config()
        for k in ("my_name", "my_email", "my_phone", "my_address"):
            st.session_state[k] = saved.get(k, "")
        st.session_state.contact_loaded = True

    # Sidebar config
    with st.sidebar:
        st.header("⚙️ Configuration")
        ollama_host = st.text_input("Ollama URL", value=OLLAMA_BASE_URL, key="ollama_host")
        embed_model = st.text_input("Embedding model", value=EMBEDDING_MODEL, key="embed_model")
        llm_model = st.text_input("LLM model", value=LLM_MODEL, key="llm_model")
        top_k = st.slider("Retrieval chunks (k)", min_value=5, max_value=20, value=DEFAULT_TOP_K)
        st.divider()
        st.caption("Paths")
        st.code(f"sources: {SOURCES_DIR}", language=None)
        outputs_dir_input = st.text_input("Generated folder", value=str(GENERATED_DIR), key="outputs_dir")
        outputs_dir = Path(outputs_dir_input).expanduser()
        outputs_dir.mkdir(parents=True, exist_ok=True)
        st.code(f"generated: {outputs_dir}", language=None)

        st.divider()
        st.subheader("My contact info (saved)")
        st.text_input("Full name", key="my_name", placeholder="e.g., Dylan Carpowich")
        st.text_input("Email", key="my_email", placeholder="e.g., you@example.com")
        st.text_input("Phone", key="my_phone", placeholder="e.g., (916) 555-1234")
        st.text_input("Address", key="my_address", placeholder="Street, City, State ZIP")
        if st.button("Save contact info", key="save_contact_btn"):
            save_contact_config({
                "my_name": st.session_state.get("my_name", ""),
                "my_email": st.session_state.get("my_email", ""),
                "my_phone": st.session_state.get("my_phone", ""),
                "my_address": st.session_state.get("my_address", ""),
            })
            st.success("Contact info saved.")
        vcf_file = st.file_uploader("Or import from vCard (.vcf)", type=["vcf"], key="vcf_upload")
        if vcf_file and st.session_state.get("_last_vcf") != vcf_file.name:
            try:
                content = vcf_file.getvalue().decode("utf-8", errors="replace")
                parsed = parse_vcard(content)
                for k, v in parsed.items():
                    if v:
                        st.session_state[k] = v
                st.session_state["_last_vcf"] = vcf_file.name
                st.success("Contact info imported from vCard.")
                st.rerun()
            except Exception as e:
                st.error(f"Could not parse vCard: {e}")

    # Health check (show warning but don't block the UI)
    ok, err = check_ollama_health(ollama_host, embed_model, llm_model)
    if not ok:
        st.warning(f"**Setup required:** {err}")
        st.info("Pull the models in a terminal: `ollama pull nomic-embed-text` and `ollama pull llama3.2` — then refresh this page. You can still add documents below.")
        st.divider()

    # Ensure dirs exist
    SOURCES_DIR.mkdir(parents=True, exist_ok=True)
    for sub, path in [("resumes", RESUMES_DIR), ("experiences", EXPERIENCES_DIR), ("books", BOOKS_DIR)]:
        path.mkdir(exist_ok=True)
    CHROMA_DIR.mkdir(parents=True, exist_ok=True)
    # (outputs dir is created from sidebar input above)

    vector_store = VectorStore(
        persist_dir=CHROMA_DIR,
        embedding_model=embed_model,
        ollama_host=ollama_host,
    )
    chunk_count = vector_store.count()

    # Tabs
    tab_ingest, tab_resume, tab_letter, tab_css_editor = st.tabs(
        ["📥 Ingest Documents", "📄 Resume", "✉️ Cover Letter", "🎨 CSS Editor"]
    )

    # ============ INGEST TAB ============
    with tab_ingest:
        st.subheader("1. Index Your Documents")
        st.markdown("""
        Add your documents to the RAG database. Use either:
        - **Upload files** below, or
        - **Place files** in the `sources/` folder structure
        """)

        st.write(f"**Current index:** {chunk_count} chunks")

        # File uploader
        st.subheader("Upload files")
        doc_type = st.selectbox(
            "Save to folder",
            ["resumes", "experiences", "books"],
            key="upload_doc_type",
        )
        target_dir = SOURCES_DIR / doc_type
        uploaded = st.file_uploader(
            "Choose PDF, DOCX, or TXT files",
            type=["pdf", "docx", "doc", "txt", "md"],
            accept_multiple_files=True,
            key="file_uploader",
        )
        if uploaded:
            for f in uploaded:
                dest = target_dir / f.name
                dest.write_bytes(f.getvalue())
            st.success(f"Saved {len(uploaded)} file(s) to `sources/{doc_type}/`")

        st.divider()
        st.subheader("Folder structure")
        st.markdown("""
        - **sources/resumes/** — Your resumes
        - **sources/experiences/** — Work history, projects
        - **sources/books/** — Relevant reading

        Supported: PDF, DOCX, TXT, Markdown
        """)
        st.code(str(SOURCES_DIR.resolve()), language=None)

        st.divider()
        if st.button("Process & Index", type="primary", key="process_index"):
            if not ok:
                st.error("Ollama models required. Run: `ollama pull nomic-embed-text` and `ollama pull llama3.2`")
            else:
                docs = list(load_documents_from_dir(SOURCES_DIR))
                if not docs:
                    st.warning("No documents found in sources/. Add or upload PDF, DOCX, or TXT files.")
                else:
                    try:
                        with st.spinner("Chunking and embedding..."):
                            progress = st.progress(0)
                            chunks = list(chunk_documents(
                                iter(docs),
                                chunk_size=CHUNK_SIZE,
                                overlap=CHUNK_OVERLAP,
                            ))
                            progress.progress(0.3)
                            vector_store.clear()
                            chunk_texts = [c[0] for c in chunks]
                            chunk_metas = [c[1] for c in chunks]
                            added = vector_store.add_chunks(chunk_texts, chunk_metas)
                            progress.progress(1.0)
                        st.success(f"Indexed {len(docs)} documents, {added} chunks.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Indexing failed: {e}. Make sure Ollama is running and models are pulled.")

        if chunk_count > 0:
            if st.button("Reset database", key="reset_db"):
                vector_store.clear()
                st.session_state.generated_resume = None
                st.session_state.generated_letter = None
                st.success("Database cleared.")
                st.rerun()

    # ============ RESUME TAB ============
    with tab_resume:
        st.subheader("Generate Resume")
        st.caption("Index your documents first, then generate a tailored resume from the job description.")

        if chunk_count == 0:
            st.warning("**Index documents first.** Go to **Ingest Documents**, add your documents, then **Process & Index**.")
        elif not ok:
            st.warning("**Ollama setup required.** Pull models: `ollama pull nomic-embed-text` and `ollama pull llama3.2`")

        if chunk_count == 0 or not ok:
            st.stop()

        def _autofill_job_title() -> None:
            info = extract_contact_info(st.session_state.get("job_desc_resume", ""))
            if info.get("job_title") and not (st.session_state.get("job_title_resume") or "").strip():
                st.session_state.job_title_resume = info["job_title"]

        job_title_resume = st.text_input("Job title (for filename)", key="job_title_resume", placeholder="e.g., Legislative Analyst")
        job_desc_resume = st.text_area(
            "Paste job description",
            height=200,
            placeholder="Paste the full job posting...",
            key="job_desc_resume",
        )
        st.button("Auto-fill job title from description", key="autofill_job_resume", on_click=_autofill_job_title)

        st.write("**Include in retrieval:**")
        col1, col2, col3 = st.columns(3)
        with col1:
            use_resumes = st.checkbox("Resumes", value=True, key="use_resumes")
        with col2:
            use_experiences = st.checkbox("Experiences", value=True, key="use_experiences")
        with col3:
            use_books = st.checkbox("Books", value=False, key="use_books")

        include_doc_types = []
        if use_resumes:
            include_doc_types.append("resume")
        if use_experiences:
            include_doc_types.append("experience")
        if use_books:
            include_doc_types.append("book")
        if not include_doc_types:
            include_doc_types = None

        context_resume = ""
        chunks_preview = []
        if job_desc_resume.strip():
            context_resume, chunks_preview = retrieve_context(
                vector_store, job_desc_resume.strip(), top_k=top_k, include_doc_types=include_doc_types
            )
            kw = extract_keywords(job_desc_resume.strip())
            if kw:
                st.caption(f"Keywords: {', '.join(kw[:12])}{'…' if len(kw) > 12 else ''}")
            with st.expander("Preview retrieved chunks"):
                for i, c in enumerate(chunks_preview):
                    st.markdown(f"**{i+1}. {c['source']}** ({c['doc_type']})")
                    st.text(c["content"][:300] + ("..." if len(c["content"]) > 300 else ""))
                    st.divider()

        if st.button("Generate Resume", type="primary", key="gen_resume"):
            if job_desc_resume.strip() and context_resume:
                with st.spinner("Generating resume..."):
                    resume = run_generation(
                        "resume",
                        job_desc_resume.strip(),
                        context_resume,
                        job_title_resume,
                        "",
                        "",
                        "",
                        "",
                        st.session_state.my_name,
                        st.session_state.my_email,
                        st.session_state.my_phone,
                        st.session_state.my_address,
                        llm_model,
                        ollama_host,
                    )
                    st.session_state.generated_resume = resume
                    save_output(resume, "resume", job_title_resume, outputs_dir, ext="md")
                    st.success("Resume generated and saved.")
            else:
                st.error("Paste a job description first.")

        st.divider()
        if st.session_state.generated_resume:
            st.subheader("Output")
            st.text_area("Resume", value=st.session_state.generated_resume, height=350, key="resume_display")
            dl_content = st.session_state.get("resume_display") or st.session_state.generated_resume
            st.download_button("Download Resume (.md)", dl_content, file_name=get_output_filename_with_ext("resume", job_title_resume, "md"), key="dl_resume_md")
            if st.button("Save to generated folder", key="save_resume_btn"):
                content = st.session_state.get("resume_display") or st.session_state.generated_resume
                save_output(content, "resume", job_title_resume, outputs_dir, ext="md")
                st.success("Saved.")
        else:
            st.info("Generate a resume above, then edit it to your liking before creating a cover letter.")

    # ============ COVER LETTER TAB ============
    with tab_letter:
        st.subheader("Generate Cover Letter")
        st.caption("Upload your finalized resume (or use the one you generated), add hiring manager info, and generate a tailored cover letter.")

        if not ok:
            st.warning("**Ollama setup required.** Pull models: `ollama pull nomic-embed-text` and `ollama pull llama3.2`")
            st.stop()

        # Resume source: upload or use generated
        resume_content = ""
        st.write("**Resume (source for cover letter)**")
        use_generated = st.radio(
            "Resume source",
            ["Use generated resume (from Resume tab)", "Upload resume file"],
            key="letter_resume_source",
        )
        if use_generated == "Use generated resume (from Resume tab)":
            resume_for_letter = st.session_state.get("resume_display") or st.session_state.get("generated_resume")
            if resume_for_letter:
                resume_content = resume_for_letter
                st.success("Using resume from Resume tab (includes your edits).")
            else:
                st.warning("No generated resume. Go to the **Resume** tab and generate one first, or upload a file below.")
        else:
            uploaded_resume = st.file_uploader("Upload resume (PDF, DOCX, TXT, MD)", type=["pdf", "docx", "doc", "txt", "md"], key="letter_resume_upload")
            if uploaded_resume:
                try:
                    resume_content = load_uploaded_file(uploaded_resume)
                    st.success(f"Loaded {uploaded_resume.name}")
                except Exception as e:
                    st.error(f"Could not load file: {e}")

        st.divider()
        st.write("**Recipient info (used in the letter)**")
        job_title_letter = st.text_input("Job title", key="job_title_letter", placeholder="e.g., Legislative Assistant")
        hiring_manager = st.text_input("Hiring manager name", key="hiring_manager_name", placeholder="e.g., Ms. Garcia")
        contact_org = st.text_input("Organization/Office", key="contact_org", placeholder="e.g., Office of Senator X")

        job_desc_letter = st.text_area(
            "Paste job description",
            height=150,
            placeholder="Paste the job posting...",
            key="job_desc_letter",
        )

        def _autofill_letter() -> None:
            info = extract_contact_info(st.session_state.get("job_desc_letter", ""))
            if not (st.session_state.get("job_title_letter") or "").strip() and info.get("job_title"):
                st.session_state.job_title_letter = info["job_title"]
            if not (st.session_state.get("hiring_manager_name") or "").strip() and info.get("hiring_manager_name"):
                st.session_state.hiring_manager_name = info["hiring_manager_name"]
            if not (st.session_state.get("contact_org") or "").strip() and info.get("contact_org"):
                st.session_state.contact_org = info["contact_org"]

        st.button("Auto-fill from job description", key="autofill_letter", on_click=_autofill_letter)

        can_gen_letter = bool(resume_content.strip() and job_desc_letter.strip())

        if st.button("Generate Cover Letter", type="primary", key="gen_letter"):
            if can_gen_letter:
                with st.spinner("Generating cover letter..."):
                    letter = run_generation(
                        "cover_letter",
                        job_desc_letter.strip(),
                        resume_content,
                        job_title_letter,
                        hiring_manager,
                        st.session_state.contact_email,
                        st.session_state.contact_phone,
                        contact_org,
                        st.session_state.my_name,
                        st.session_state.my_email,
                        st.session_state.my_phone,
                        st.session_state.my_address,
                        llm_model,
                        ollama_host,
                    )
                    st.session_state.generated_letter = letter
                    save_output(letter, "cover_letter", job_title_letter, outputs_dir, ext="md")
                    st.success("Cover letter generated and saved.")
            else:
                st.error("Add a resume and paste the job description.")

        st.divider()
        if st.session_state.generated_letter:
            st.subheader("Output")
            st.text_area("Cover Letter", value=st.session_state.generated_letter, height=350, key="letter_display")
            dl_letter = st.session_state.get("letter_display") or st.session_state.generated_letter
            st.download_button("Download Cover Letter (.md)", dl_letter, file_name=get_output_filename_with_ext("cover_letter", job_title_letter, "md"), key="dl_letter_md")
            if st.button("Save to generated folder", key="save_letter_btn"):
                content = st.session_state.get("letter_display") or st.session_state.generated_letter
                save_output(content, "cover_letter", job_title_letter, outputs_dir, ext="md")
                st.success("Saved.")

        # Generation history (both resume and letter)
        history = load_history(outputs_dir)
        if history:
            with st.expander("📜 Recent generations"):
                for i, entry in enumerate(history[:15]):
                    ts = entry.get("timestamp", "")[:19].replace("T", " ")
                    typ = entry.get("type", "?")
                    jt = entry.get("job_title", "output") or "output"
                    fp = entry.get("filepath", "")
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        st.caption(f"{ts} — {typ} for {jt}")
                    with col2:
                        if Path(fp).exists():
                            content = Path(fp).read_text(encoding="utf-8")
                            if st.button("Load", key=f"hist_load_{i}"):
                                if typ == "resume":
                                    st.session_state.generated_resume = content
                                    st.session_state.resume_display = content
                                else:
                                    st.session_state.generated_letter = content
                                    st.session_state.letter_display = content
                                st.rerun()
                        else:
                            st.caption("(deleted)")

    # ============ CSS EDITOR TAB ============
    with tab_css_editor:
        st.subheader("MD → HTML → PDF")
        st.caption(
            "Turn Markdown into styled HTML with hardcoded CA Legislature theme. "
            "Edit the Markdown below, preview, then save as HTML (print to PDF from your browser)."
        )

        # MD source: generated folder (reliable), session resume/letter, upload, or paste
        st.write("**Markdown source**")
        md_source = st.radio(
            "Source",
            [
                "Load from generated folder",
                "Use generated resume (from Resume tab)",
                "Use generated cover letter (from Cover Letter tab)",
                "Upload .md or .txt file",
                "Paste / edit below",
            ],
            key="css_editor_source",
        )

        md_content = ""
        selected_from_folder = ""

        if md_source == "Load from generated folder":
            # List .md and .txt files, newest first
            gen_files = sorted(
                [f for f in outputs_dir.glob("*") if f.suffix.lower() in (".md", ".txt") and f.name != "history.json"],
                key=lambda p: p.stat().st_mtime,
                reverse=True,
            )
            if gen_files:
                file_options = [""] + [f.name for f in gen_files]
                selected_from_folder = st.selectbox(
                    "Choose file",
                    options=file_options,
                    format_func=lambda x: "(Select a file)" if x == "" else x,
                    key="css_editor_file_select",
                )
                if selected_from_folder:
                    try:
                        md_content = (outputs_dir / selected_from_folder).read_text(encoding="utf-8")
                        st.success(f"Loaded **{selected_from_folder}**")
                    except Exception as e:
                        st.error(f"Could not read file: {e}")
            else:
                st.warning("No .md or .txt files in generated folder. Generate a resume or cover letter first.")

        elif md_source == "Use generated resume (from Resume tab)":
            md_content = st.session_state.get("resume_display") or st.session_state.get("generated_resume") or ""
            if not md_content:
                st.warning("No generated resume. Go to **Resume** tab and generate one first, or **Load from generated folder**.")
        elif md_source == "Use generated cover letter (from Cover Letter tab)":
            md_content = st.session_state.get("letter_display") or st.session_state.get("generated_letter") or ""
            if not md_content:
                st.warning("No generated cover letter. Go to **Cover Letter** tab and generate one first, or **Load from generated folder**.")
        elif md_source == "Upload .md or .txt file":
            uploaded_md = st.file_uploader(
                "Upload Markdown or text file",
                type=["md", "txt", "markdown"],
                key="css_editor_upload",
            )
            if uploaded_md:
                md_content = uploaded_md.getvalue().decode("utf-8", errors="replace")
                st.success(f"Loaded {uploaded_md.name}")

        # Persist editor content when source changes
        source_key = f"{md_source}:{selected_from_folder}" if md_source == "Load from generated folder" else md_source
        if "css_editor_last_source" not in st.session_state:
            st.session_state.css_editor_last_source = None
        if st.session_state.css_editor_last_source != source_key:
            st.session_state.css_editor_last_source = source_key
            st.session_state.css_editor_md = md_content
            # Reset doc title when loading new file
            if md_source == "Load from generated folder" and selected_from_folder:
                stem = Path(selected_from_folder).stem.lower()
                st.session_state.css_editor_title = "Resume" if "resume" in stem else "Cover Letter" if "cover" in stem or "letter" in stem else stem.split("-")[0].title()
            elif "resume" in md_source.lower():
                st.session_state.css_editor_title = "Resume"
            elif "letter" in md_source.lower():
                st.session_state.css_editor_title = "Cover Letter"
            else:
                st.session_state.css_editor_title = "Document"

        # Editable text area (always show when we have content or when paste/edit selected)
        if md_source == "Paste / edit below" or md_content:
            doc_title = st.text_input(
                "Document title (for HTML <title>)",
                value=st.session_state.get("css_editor_title", "Document"),
                key="css_editor_title",
            )
            edited_md = st.text_area(
                "Markdown (edit here)",
                value=st.session_state.get("css_editor_md", md_content),
                height=300,
                key="css_editor_md",
            )

            if edited_md.strip():
                html_output = md_to_html(edited_md.strip(), title=doc_title or "Document")

                st.divider()
                st.write("**Preview**")
                st.components.v1.html(html_output, height=500, scrolling=True)

                st.divider()
                col1, col2, col3 = st.columns([1, 1, 2])
                with col1:
                    st.download_button(
                        "Download HTML",
                        html_output,
                        file_name=f"{doc_title or 'document'}.html",
                        mime="text/html",
                        key="dl_css_editor_html",
                    )
                with col2:
                    if st.button("Save HTML to generated folder", key="save_css_editor_html"):
                        out_name = f"HTML-{doc_title or 'output'}-{date.today().strftime('%Y-%m-%d')}.html"
                        out_path = outputs_dir / out_name
                        out_path.write_text(html_output, encoding="utf-8")
                        st.success(f"Saved to {out_path}")
                with col3:
                    st.caption("Open the HTML file in a browser and use File → Print → Save as PDF.")
        else:
            st.info("Select a source above or choose **Paste / edit below** to enter Markdown.")


if __name__ == "__main__":
    main()
