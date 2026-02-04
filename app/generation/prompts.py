"""Prompt templates with CA Legislature writing rules and ATS-friendly guidance."""

# Distilled from 1990s CA Legislature writing advice (Writing advice CA Legislature 1990's 16 conv.txt)
CA_LEG_WRITING_RULES = """
CA LEGISLATURE WRITING GUIDELINES (adapted for job applications):
- Be brief: Get to the point quickly. Cover letters: one page max. Effectiveness is often inversely proportional to length.
- Introduce yourself simply: Tell who you are without making a biography. A simple statement of role/affiliation suffices.
- Be specific: Match concrete job requirements. Use concrete examples and outcomes, not vague claims.
- Make it personal: Use your own words. Avoid generic templates. Tailor each application.
- Give your reasons: State your case clearly. Explain why you're a fit and what value you bring.
- Be constructive: Focus on what you can contribute. Emphasize solutions and contributions.
- Be courteous and reasonable: Professional tone throughout. Never threaten or be rude.
- Don't be vague: Use concrete outcomes, metrics, and examples.
- Don't apologize: Don't apologize for taking their time or use weak openings.
- Don't overstate: Give reasons but don't overstate. Credibility matters.
"""

SYSTEM_BASE = f"""You MUST follow these official CA Legislature writing guidelines:
{CA_LEG_WRITING_RULES}

You are an expert resume and cover letter writer for California Legislature positions.
Match language and requirements from the job description.
Use ONLY information from the provided context—do not invent experience or qualifications.
"""

RESUME_SYSTEM = SYSTEM_BASE + """
For resumes: Use ATS-friendly formatting. No tables, no graphics, no columns.
Use standard section headers: Experience, Education, Skills.
Simple bullet points. Plain text suitable for CalCareers and ATS systems.

CRITICAL: Do not mention a target office/person/committee in the resume unless it appears in the JOB DESCRIPTION.
If the retrieved context contains office-specific phrases from past tailored resumes, ignore them unless they are clearly past experience.
"""

COVER_LETTER_SYSTEM = SYSTEM_BASE + """
For cover letters: Professional, concise, CA government-appropriate tone.
Structure: greeting, 2-3 paragraphs, sign-off.

CRITICAL—RECIPIENT / CONTACT INFO is the ONLY source for addressee details:
- Hiring Manager, Organization, and Job Title come ONLY from the RECIPIENT / CONTACT INFO block.
- IGNORE any hiring manager, office, or contact names mentioned in the JOB DESCRIPTION or RELEVANT INFORMATION (context). Those may be from other postings or past applications.
- If Hiring Manager is provided in RECIPIENT: use that exact name for the salutation (e.g., "Dear Ms. Garcia,").
- If Organization/Office is provided in RECIPIENT: use that exact value in the letter.
- Use MY CONTACT INFO for the signature. Never use [Your Name]—use the actual name provided.
"""


def build_resume_prompt(
    job_description: str,
    context: str,
    job_title: str = "",
    my_name: str = "",
    my_email: str = "",
    my_phone: str = "",
    my_address: str = "",
) -> tuple[str, str]:
    """Build system and user prompts for resume generation."""
    contact_lines = []
    if my_name.strip():
        contact_lines.append(f"Name: {my_name.strip()}")
    if my_address.strip():
        contact_lines.append(f"Address: {my_address.strip()}")
    if my_phone.strip():
        contact_lines.append(f"Phone: {my_phone.strip()}")
    if my_email.strip():
        contact_lines.append(f"Email: {my_email.strip()}")

    contact_block = ""
    if contact_lines:
        contact_block = "MY CONTACT INFO (use to populate the resume header):\n" + "\n".join(contact_lines) + "\n\n"

    user = f"""{contact_block}JOB DESCRIPTION:
{job_description}

RELEVANT INFORMATION FROM MY BACKGROUND (use only this—do not invent):
{context}

Generate a tailored resume that matches the job requirements. Use only the information above.
If MY CONTACT INFO is provided, include it at the top in a clean ATS-friendly header."""
    if job_title:
        user = f"Job title: {job_title}\n\n" + user
    return RESUME_SYSTEM, user


def build_cover_letter_prompt(
    job_description: str,
    context: str,
    job_title: str = "",
    hiring_manager_name: str = "",
    contact_email: str = "",
    contact_phone: str = "",
    contact_org: str = "",
    my_name: str = "",
    my_email: str = "",
    my_phone: str = "",
    my_address: str = "",
) -> tuple[str, str]:
    """Build system and user prompts for cover letter generation."""
    recipient_lines = []
    if job_title.strip():
        recipient_lines.append(f"Job title / Position: {job_title.strip()}")
    if hiring_manager_name.strip():
        recipient_lines.append(f"Hiring manager (use for salutation): {hiring_manager_name.strip()}")
    if contact_org.strip():
        recipient_lines.append(f"Organization/Office: {contact_org.strip()}")
    if contact_email.strip():
        recipient_lines.append(f"Contact email: {contact_email.strip()}")
    if contact_phone.strip():
        recipient_lines.append(f"Contact phone: {contact_phone.strip()}")

    recipient_block = ""
    if recipient_lines:
        recipient_block = (
            "RECIPIENT / CONTACT INFO — USE ONLY THESE VALUES for addressee, office, and position. "
            "Do NOT use names or offices from the job description or context below:\n"
            + "\n".join(recipient_lines)
            + "\n\n"
        )

    my_lines = []
    if my_name.strip():
        my_lines.append(f"My name: {my_name.strip()}")
    if my_address.strip():
        my_lines.append(f"My address: {my_address.strip()}")
    if my_phone.strip():
        my_lines.append(f"My phone: {my_phone.strip()}")
    if my_email.strip():
        my_lines.append(f"My email: {my_email.strip()}")

    my_block = ""
    if my_lines:
        my_block = "MY CONTACT INFO (use for signature / header as appropriate):\n" + "\n".join(my_lines) + "\n\n"

    user = f"""{recipient_block}{my_block}JOB DESCRIPTION:
{job_description}

RESUME (use this to tailor the cover letter—highlight relevant experience and skills from it):
{context}

Generate a professional cover letter/email (one page max). Use ONLY the Hiring Manager, Organization, and Job Title from the RECIPIENT block—ignore any such info in the job description or resume."""
    return COVER_LETTER_SYSTEM, user
