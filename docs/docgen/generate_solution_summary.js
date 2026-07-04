const fs = require("fs");
const {
  Document, Packer, Paragraph, TextRun, HeadingLevel, Table, TableRow, TableCell,
  ImageRun, WidthType, BorderStyle, ShadingType, AlignmentType, PageBreak,
  LevelFormat, convertInchesToTwip,
} = require("docx");

const PAGE_W = 12240, PAGE_H = 15840; // US Letter DXA

const heading = (text, level = HeadingLevel.HEADING_1) =>
  new Paragraph({ text, heading: level, spacing: { before: 280, after: 140 } });

const body = (text, opts = {}) =>
  new Paragraph({
    children: [new TextRun({ text, ...opts })],
    spacing: { after: 160 },
    alignment: AlignmentType.JUSTIFIED,
  });

const bullet = (text) =>
  new Paragraph({ text, numbering: { reference: "bullets", level: 0 }, spacing: { after: 80 } });

function cell(text, opts = {}) {
  const { width, header = false, shade = null } = opts;
  return new TableCell({
    width: { size: width, type: WidthType.DXA },
    shading: shade ? { type: ShadingType.CLEAR, fill: shade } : undefined,
    margins: { top: 80, bottom: 80, left: 100, right: 100 },
    children: [new Paragraph({
      children: [new TextRun({ text, bold: header, size: 19 })],
    })],
  });
}

function table(colWidths, rows) {
  const tableWidth = colWidths.reduce((a, b) => a + b, 0);
  return new Table({
    width: { size: tableWidth, type: WidthType.DXA },
    columnWidths: colWidths,
    rows: rows.map((r, i) => new TableRow({
      children: r.map((text, ci) => cell(text, { width: colWidths[ci], header: i === 0, shade: i === 0 ? "D3D1C7" : null })),
    })),
  });
}

function image(path, width, height) {
  return new Paragraph({
    children: [new ImageRun({ type: "png", data: fs.readFileSync(path), transformation: { width, height } })],
    alignment: AlignmentType.CENTER,
    spacing: { before: 120, after: 200 },
  });
}

const doc = new Document({
  numbering: {
    config: [{
      reference: "bullets",
      levels: [{ level: 0, format: LevelFormat.BULLET, text: "\u2022", alignment: AlignmentType.LEFT,
        style: { paragraph: { indent: { left: 480, hanging: 260 } } } }],
    }],
  },
  sections: [{
    properties: { page: { size: { width: PAGE_W, height: PAGE_H }, margin: { top: 1080, bottom: 1080, left: 1080, right: 1080 } } },
    children: [
      new Paragraph({
        children: [new TextRun({ text: "Social Support AI Workflow", bold: true, size: 44 })],
        alignment: AlignmentType.CENTER, spacing: { after: 120 },
      }),
      new Paragraph({
        children: [new TextRun({ text: "Solution Summary — Agentic GenAI Prototype for Social Support & Economic Enablement", size: 26, color: "444441" })],
        alignment: AlignmentType.CENTER, spacing: { after: 400 },
      }),

      heading("1. Executive Summary"),
      body("This solution automates the end-to-end social support application journey — from document intake through eligibility decisioning to economic enablement recommendations — reducing a manual, 5-to-20-working-day process to a same-session, chat-driven experience. A Master Orchestrator built on LangGraph coordinates five specialist agents (Data Extraction, Data Validation, Eligibility Assessment, Decision Recommendation, and Economic Enablement), each following a ReAct (Thought \u2192 Action \u2192 Observation) reasoning loop, backed by a locally hosted LLM (via Ollama) and a locally trained scikit-learn eligibility classifier. The system targets the brief's core goal: automated decisions within minutes of a live chatbot interaction, while preserving a human-in-the-loop safety net for borderline or inconsistent cases."),
      body("The prototype is designed to run fully offline / locally: every external dependency (PostgreSQL, MongoDB, Qdrant, Neo4j, Ollama, Langfuse) has an in-process fallback, so functional correctness can be demonstrated without standing up the full docker-compose stack, while the docker-compose stack itself reflects the intended production shape."),

      heading("2. High-Level Architecture"),
      body("The architecture separates concerns into six layers: interaction (Streamlit chat UI), API (FastAPI), orchestration (LangGraph master orchestrator), specialist agents, local AI services (ML model, local LLM, vector search, graph relationships), and the data pipeline (PostgreSQL, MongoDB, Qdrant, Neo4j). Multimodal documents enter through the ingestion layer at the bottom and flow upward through extraction, validation, and assessment."),
      image("../architecture_diagram.png", 620, 460),

      heading("3. Agent Workflow & Reasoning Framework"),
      body("Each application moves through a fixed pipeline with one conditional branch point. The reasoning framework used within every agent is ReAct: each step is recorded as a Thought (why the agent is about to act), an Action (the function it calls \u2014 an extraction routine, a comparison rule, a model inference, or an LLM call), and an Observation (the result), which keeps every automated decision traceable end-to-end."),
      image("../workflow_diagram.png", 620, 335),
      body("A deliberate design choice: high-severity data-validation flags (for example, an expired Emirates ID, or an applicant name that does not match the ID on file) always force routing to a human case officer, regardless of how confident the ML model's eligibility score is. This directly targets the brief's \u201csubjective decision-making\u201d pain point \u2014 the goal is consistent, explainable automation, not the removal of human accountability for ambiguous cases."),

      heading("4. Modular Component Breakdown"),
      new Paragraph({ children: [new TextRun({ text: "Master Orchestrator", bold: true })], spacing: { after: 60 } }),
      body("Defines the pipeline as an explicit LangGraph StateGraph (intake \u2192 extraction \u2192 validation \u2192 eligibility \u2192 decision \u2192 enablement \u2192 finalize) with a conditional edge after validation. A functionally equivalent sequential executor is used automatically when LangGraph is not installed, so the same agent contracts run in restricted environments."),
      new Paragraph({ children: [new TextRun({ text: "Data Extraction Agent", bold: true })], spacing: { after: 60 } }),
      body("Ingests the application form and five attachment types (bank statement, Emirates ID, resume, assets/liabilities spreadsheet, credit report), routing each to the tool best suited to its structure: pdfplumber/pytesseract for scanned or PDF text, openpyxl/pandas for the structured Excel workbook, and the local LLM (prompted for strict JSON) for free-text narrative documents such as resumes."),
      new Paragraph({ children: [new TextRun({ text: "Data Validation Agent", bold: true })], spacing: { after: 60 } }),
      body("Cross-checks extracted fields against each other and against the application form \u2014 name similarity, address match between the form and the credit bureau record, income variance between self-reported figures and bank statement flows, and Emirates ID expiry \u2014 directly automating the brief's \u201cinconsistent information\u201d pain point. Findings are summarized by the local LLM in plain language for the applicant and case officer."),
      new Paragraph({ children: [new TextRun({ text: "Eligibility Assessment Agent", bold: true })], spacing: { after: 60 } }),
      body("Builds the engineered feature vector (per-capita income, debt-to-asset ratio, employment tenure, family size, credit score, etc.) and scores it with the trained scikit-learn classifier, returning a calibrated probability plus a short list of the top contributing factors for explainability."),
      new Paragraph({ children: [new TextRun({ text: "Decision Recommendation Agent", bold: true })], spacing: { after: 60 } }),
      body("Applies the department's threshold policy (configurable via AUTO_APPROVE_THRESHOLD / AUTO_DECLINE_THRESHOLD) to the ML score, factoring in the validation report's severity, and asks the local LLM to draft a clear, respectful explanation of the outcome for the applicant."),
      new Paragraph({ children: [new TextRun({ text: "Economic Enablement Agent", bold: true })], spacing: { after: 60 } }),
      body("Runs for every applicant \u2014 not only declines \u2014 matching resume-extracted skills and employment status against a curated programme catalog (upskilling, vocational training, career counseling, job matching), then asks the local LLM to turn the matches into an encouraging, personalized narrative."),

      new Paragraph({ children: [new PageBreak()] }),

      heading("5. Technology Choices & Justification"),
      table(
        [2000, 3600, 3800],
        [
          ["Component", "Tool", "Why (suitability / scalability / maintainability / performance / security)"],
          ["Programming language", "Python", "Native ecosystem for both classical ML (scikit-learn) and GenAI orchestration (LangGraph, LLM SDKs); one language across data, ML, and API layers reduces integration surface area and hiring/maintenance overhead."],
          ["Relational DB", "PostgreSQL", "Strong relational integrity for applicants/applications/decisions (foreign keys, transactions); mature horizontal read-scaling and row-level security options suit a government audit-sensitive workload. SQLite fallback keeps local development frictionless."],
          ["Document store", "MongoDB", "Raw multimodal document payloads vary in shape per document type; a schema-flexible store avoids constant migrations as new document types are added, while PostgreSQL retains the normalized, query-heavy records."],
          ["Vector DB", "Qdrant", "Lightweight, self-hostable, strong filtering support alongside vector search \u2014 used for RAG over policy text and for precedent-case retrieval to make similar-case comparison explicit rather than tribal knowledge."],
          ["Graph DB", "Neo4j", "Household/applicant/document relationships (e.g., multiple applications sharing an address) are natural graph queries; catches duplicate-claim patterns a relational join would need increasingly complex recursive queries for."],
          ["Classifier", "scikit-learn HistGradientBoostingClassifier", "Handles the mixed skewed-continuous / categorical feature set and non-linear interactions without heavy feature engineering, natively tolerates missing values from partial extractions, trains in seconds on modest hardware (fits the \u201clocally hosted\u201d requirement), and outputs usable probabilities for threshold banding. A LogisticRegression baseline is retained for coefficient-level explainability."],
          ["Agent reasoning", "ReAct", "Thought/Action/Observation steps give a human-auditable trace for every automated judgment \u2014 important for a government process that must justify individual decisions."],
          ["Orchestration", "LangGraph", "Explicit, inspectable state graph with conditional routing (e.g., forcing human review) is easier to reason about and unit-test than an implicit agent loop; graceful degrade to a sequential executor keeps the prototype portable."],
          ["Model hosting", "Ollama", "Runs open-weight LLMs (and a vision model for scanned documents) entirely on local infrastructure, avoiding sending sensitive applicant data to third-party APIs \u2014 a hard requirement for this data class."],
          ["Observability", "Langfuse", "Captures per-agent latency, cost, and prompt/response pairs across the whole pipeline; the same trace data is also persisted locally so auditability does not depend on an external service being reachable."],
          ["Serving", "FastAPI", "Async-capable, automatic OpenAPI docs, native Pydantic validation for the multimodal multipart upload endpoint; a natural fit for both the interactive chatbot and future system-to-system integration."],
          ["Front-end", "Streamlit", "Fast to build a chat-driven, form-plus-file-upload interface with a live agent-reasoning panel \u2014 appropriate for a prototype where the priority is demonstrating the workflow, not a bespoke production UI."],
        ],
      ),

      heading("6. Data & Decision Audit Trail"),
      body("Every application produces: (a) the raw multimodal documents (MongoDB), (b) normalized structured fields (PostgreSQL, JSON columns), (c) the full per-agent Thought/Action/Observation trace (PostgreSQL agent_traces table and Langfuse), and (d) the final decision with a plain-language explanation. This means any decision \u2014 automated or human-reviewed \u2014 can be reconstructed and justified after the fact, which is essential for a government benefits process."),

      heading("7. API Design Considerations (for production integration)"),
      bullet("POST /applications accepts multipart form data (structured fields + up to five document attachments) and returns a decision synchronously for the prototype; a production version would return 202 Accepted with a webhook/polling pattern once processing moves to an async queue (see below)."),
      bullet("GET /applications/{id} exposes current status and decision for case-management system integration."),
      bullet("POST /chat is a RAG-grounded endpoint (Qdrant policy retrieval + application status context) suited for embedding in an existing citizen-services portal or WhatsApp/SMS gateway."),
      bullet("Versioned endpoints (/v1/...) and an API gateway (rate limiting, authentication via the existing government identity provider, request/response schema validation) would sit in front of FastAPI in production, as sketched in the architecture diagram."),

      heading("8. Future Improvements & Integration Roadmap"),
      bullet("Move long-running extraction/decisioning to an async task queue (e.g., Celery/Redis or a durable workflow engine) so document-heavy applications don't block the request thread, with webhook or polling-based status updates to the front-end."),
      bullet("Replace the illustrative hashing-based embedding fallback with a locally hosted embedding model (e.g., nomic-embed-text via Ollama) for production-grade RAG quality."),
      bullet("Add a case-officer review console (approve/override/annotate) that writes back into the same PostgreSQL audit trail, closing the human-in-the-loop feedback cycle."),
      bullet("Integrate directly with the national identity/credit-bureau systems via secure government APIs to replace the synthetic-document ingestion path with authoritative, pre-validated data \u2014 reducing the Data Validation Agent's workload to genuine anomalies."),
      bullet("Introduce model monitoring (drift detection on the eligibility classifier's input distribution and periodic retraining) and a bias/fairness audit process, given the sensitivity of automated eligibility decisions."),
      bullet("Harden security: encryption at rest for PostgreSQL/MongoDB, field-level encryption for Emirates ID numbers, role-based access control on the case-officer console, and full request/response audit logging at the API gateway layer."),
      bullet("Extend the Neo4j graph to actively score duplicate-claim risk (shared address/bank account across applications) as an additional Eligibility Agent input."),

      heading("9. Submission Notes"),
      body("Source code, this document, and a README.md with setup/run instructions are provided via the accompanying GitHub repository. The prototype runs end-to-end without external infrastructure via in-process fallbacks (see README \u201cQuickstart \u2014 zero infrastructure\u201d); docker-compose.yml stands up the full target stack (PostgreSQL, MongoDB, Qdrant, Neo4j, Ollama, Langfuse) for a production-shaped demo."),
    ],
  }],
});

Packer.toBuffer(doc).then((buffer) => {
  fs.writeFileSync("/home/claude/ssai-phased/docs/Solution_Summary.docx", buffer);
  console.log("Solution_Summary.docx written");
});
