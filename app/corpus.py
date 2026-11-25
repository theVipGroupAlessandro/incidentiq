"""Searchable documents built from incidents and ADRs.

Each document has:
  doc_id       unique id of the searchable piece (an ADR is split into sections)
  evidence_id  the id an answer cites and the benchmark scores (INC-001, ADR-001)
  kind         "incident" or "adr"
  services     services the document is about (for incidents: all affected services)
  root_service incidents only: the service where the failure started (None for ADRs)
  status       incident status or ADR status (accepted, superseded, ...)
  text         what gets embedded and searched
"""
import json
import re
from pathlib import Path

FIXTURES = Path(__file__).parent.parent / "data" / "fixtures"


def parse_frontmatter(markdown):
    """Split a Markdown file into (metadata dict, body). Handles `key: value` and `key: [a, b]`."""
    match = re.match(r"^---\n(.*?)\n---\n(.*)$", markdown, re.DOTALL)
    if not match:
        raise ValueError("Missing frontmatter")
    metadata = {}
    for line in match.group(1).splitlines():
        key, _, value = line.partition(":")
        value = value.strip()
        if value.startswith("[") or value.endswith("]"):
            if not (value.startswith("[") and value.endswith("]")):
                raise ValueError(f"Malformed list for '{key.strip()}': {value}")
            value = [item.strip() for item in value[1:-1].split(",") if item.strip()]
        elif value == "null":
            value = None
        metadata[key.strip()] = value
    return metadata, match.group(2)


def split_sections(body):
    """Return {section title: text} for every `## Title` in the body."""
    sections = {}
    for match in re.finditer(r"^## (.+?)\n(.*?)(?=^## |\Z)", body, re.MULTILINE | re.DOTALL):
        sections[match.group(1).strip()] = " ".join(match.group(2).split())
    return sections


def incident_documents(path=FIXTURES / "incidents.json"):
    incidents = json.loads(Path(path).read_text(encoding="utf-8"))
    return [
        {
            "doc_id": incident["id"],
            "evidence_id": incident["id"],
            "kind": "incident",
            "services": incident["affected_services"],
            "root_service": incident["service"],
            "status": incident["status"],
            "text": (f"{incident['title']}. Symptoms: {incident['symptoms']} "
                     f"Cause: {incident['cause']} Mitigation: {incident['mitigation']}"),
        }
        for incident in incidents
    ]


def read_adrs(folder=FIXTURES / "adrs"):
    """(metadata, body) for every ADR file, in ID order."""
    adrs = []
    for path in sorted(Path(folder).glob("ADR-*.md")):
        adrs.append(parse_frontmatter(path.read_text(encoding="utf-8").replace("\r\n", "\n")))
    return adrs


def adr_documents(folder=FIXTURES / "adrs"):
    documents = []
    for metadata, body in read_adrs(folder):
        for title, text in split_sections(body).items():
            documents.append({
                "doc_id": f"{metadata['id']}#{title.lower()}",
                "evidence_id": metadata["id"],
                "kind": "adr",
                "services": metadata["services"],
                "root_service": None,
                "status": metadata["status"],
                # The ADR title goes in every section, so each piece still says what it is about.
                "text": f"{metadata['title']} ({title}): {text}",
            })
    return documents


def load_corpus():
    return incident_documents() + adr_documents()