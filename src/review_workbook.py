"""Readable review workbook assembled solely from saved evidence; no model calls."""
import json
from pathlib import Path

import xlsxwriter


def build_workbook(project, destination):
    protocol = project.protocol()
    reviews = project.human_reviews()
    answers = {condition: project.answers(condition) for condition in ("R0", "V")}
    _, metrics = project.result_tables()
    automatic = {}
    for path in (project.frozen_folder / "automatic_r0").glob("F*.json"):
        automatic[path.stem] = json.loads(path.read_text(encoding="utf-8"))
    book = xlsxwriter.Workbook(str(destination), {"strings_to_formulas": False, "strings_to_urls": False})
    book.set_properties({"title": "Challenge 4 – Antworten prüfen", "comments": "Export gespeicherter Evidenz; keine neuen API-Aufrufe."})
    header = book.add_format({"bold": True, "font_color": "white", "bg_color": "#17365D", "text_wrap": True, "valign": "top"})
    body = book.add_format({"text_wrap": True, "valign": "top", "font_size": 11})
    link_format = book.add_format({"text_wrap": True, "valign": "top", "font_color": "#0563C1", "underline": True})
    percent = book.add_format({"num_format": "0.0%", "valign": "top"})
    sheets = {}
    longtexts = []

    def table(name, headers, rows, widths):
        sheet = book.add_worksheet(name)
        sheets[name] = sheet
        sheet.hide_gridlines(2)
        sheet.freeze_panes(1, 3 if name == "Prüftabelle" else 1)
        sheet.set_zoom(85)
        sheet.set_row(0, 42)
        sheet.write_row(0, 0, headers, header)
        for col, width in enumerate(widths):
            sheet.set_column(col, col, width, body)
        for row, values in enumerate(rows, 1):
            lines = max((sum(max(1, (len(line) + int(widths[col]) - 1) // int(widths[col]))
                             for line in str(value or "").split("\n"))
                         for col, value in enumerate(values)), default=1)
            sheet.set_row(row, min(409, max(45, lines * 15)))
            for col, value in enumerate(values):
                if isinstance(value, str) and len(value) > 32000:
                    first = len(longtexts) + 2
                    identifier = f"{name}!{xlsxwriter.utility.xl_rowcol_to_cell(row, col)}"
                    longtexts.extend([[identifier, i // 30000 + 1, value[i:i+30000]] for i in range(0, len(value), 30000)])
                    sheet.write_url(row, col, f"internal:'Langtexte'!A{first}", link_format,
                                    "Vollständiger Langtext → Langtexte (mehrere Teile)")
                elif value is not None:
                    sheet.write(row, col, value)
        sheet.autofilter(0, 0, max(1, len(rows)), len(headers)-1)
        sheet.set_landscape()
        sheet.fit_to_pages(1, 0)
        sheet.repeat_rows(0)
        return sheet

    def status(record):
        return {"completed": "Antwort gespeichert", "technical_failure": "technischer Ausfall"}.get(
            (record or {}).get("status"), "Antwort fehlt")

    def human(condition, qid):
        record = answers[condition].get(qid)
        review = reviews.get((condition, qid), {})
        failed = record is not None and record.get("status") == "technical_failure"
        return 0 if failed else (review.get("correct") if record and review else None)

    notes = [
        ["Dossier", project.dossier_id], ["Eingefrorener Vergleich", project.frozen_folder.name],
        ["Vergleich R0 / V", "R0 = unser RAG; V = persönlicher PDF-Upload in ChatGPT/Claude. Verglichen werden vollständige Arbeitsweisen. Interne Dokumentverarbeitung von V ist unbekannt; Modell, Oberfläche, Gesprächsverlauf und PDF-/Textaufbereitung können Unterschiede erklären."
         if protocol.get("v_input_mode") == "document_upload" else "Altes Volltext-Protokoll: V verwendet den vollständig eingefügten Dossiertext. Dieser gespeicherte Vergleich wurde nicht in einen PDF-Upload umgewandelt."],
        ["1. Überblick", "Übersicht: 20 Fragen, R0/V-Urteile, offene Bearbeitungen und Abweichungen vom automatischen Vorschlag."],
        ["2. Antworten prüfen", "Prüftabelle: 40 Zeilen (eine je Frage und Bedingung). Nach Frage-ID oder Bedingung filtern. Frage, Referenz und Antwort stehen zusammen."],
        ["3. Belege prüfen", "Fundstellen in Quellenseiten nachschlagen. R0-Chunks enthält den tatsächlich übergebenen Text in Retrieval-Reihenfolge. Interne Links öffnen jeweils die erste zugehörige Stelle; weitere IDs sind aufgeführt."],
        ["4. R0-Vorprüfung", "Vorprüfung R0 enthält die automatischen Klassifikationen und Einzelwahrscheinlichkeiten. Das sind Vorschläge, keine bestätigten Urteile und keine generierten Erklärungen."],
        ["5. Menschliches Urteil", "Studierende bewerten und begründen in Schritt 5 des Notebooks. Nur dort gespeicherte Urteile bestimmen die Kennzahlen. Anschliessend in Schritt 6 neu exportieren."],
        ["6. Rückmeldung der Lehrperson", "In der letzten Spalte der Prüftabelle können Lehrpersonen Kommentare ergänzen. Excel-Änderungen werden nicht in das Notebook zurückgelesen und ändern keine gespeicherten Kennzahlen."],
        ["7. Vollständigkeit", "Leere Urteile und fehlende Antworten bleiben offen. Ausdrücklich erklärte technische Ausfälle zählen gemäss Auftrag als 0. Nicht anwendbar ist kein Fehler."],
        ["8. Lange Texte", "Text ist umbrochen. Bei Bedarf Zeilenhöhe vergrössern oder Zelle/Formelzeile öffnen. Texte über der Excel-Zellgrenze liegen vollständig in Teilen unter Langtexte."],
        ["9. Abgabe", "Workbook Challenge_4_Prueftabelle.xlsx im ZIP zusammen mit Arbeitsdateien und tatsächlichem Kurzbericht abgeben. Der Export enthält keine Zugangsdaten."],
        ["Bewertungsregeln", "1 = vollständig korrekt ohne falsche Zusätze; sonst 0. Unbeantwortbare Fragen: zutreffende Begrenzung ohne erfundene Antwort. Belege und Evidenzverfügbarkeit getrennt prüfen."],
        ["Stand", "Gespeicherter Stand beim Export; nicht gespeicherte Formulareingaben sind nicht enthalten. Keine neuen API-Aufrufe."]]
    table("Hinweise", ["Thema", "Anleitung"], notes, [28, 115])
    overview, detailed, suggestions, chunkrows = [], [], [], []
    chunk_first = {}
    for q in protocol["questions"]:
        qid = q["question_id"]
        proposal = automatic.get(qid, {}).get("proposal", {})
        auto = proposal.get("correctness_proposal")
        r0_review = reviews.get(("R0", qid), {})
        disagreement = ("ja" if r0_review["correct"] != auto else "nein") if auto is not None and r0_review else "offen"
        overview.append([qid, q["type"], q["question"], human("R0", qid), human("V", qid), auto,
            disagreement, status(answers["R0"].get(qid)), status(answers["V"].get(qid)),
            "ja" if ("R0", qid) in reviews else "nein", "ja" if ("V", qid) in reviews else "nein"])
        for condition in ("R0", "V"):
            record = answers[condition].get(qid, {})
            review = reviews.get((condition, qid), {})
            detailed.append([qid, q["type"], condition, q["question"], q["reference_answer"],
                "\n".join(q["required_components"]), "\n".join(q["reference_passage_ids"]),
                record.get("answer", record.get("reason", "")), status(record),
                auto if condition == "R0" else "keine automatische V-Bewertung",
                human(condition, qid), review.get("support", "offen"), review.get("evidence_available", "offen") if condition == "R0" else "V: PDF-Upload; Kontext intern unbekannt",
                review.get("reason", ""), "ja" if review else "nein",
                record.get("metadata", {}).get("actual_model", record.get("metadata", {}).get("model", "")),
                record.get("metadata", {}).get("service", "OpenAI API" if condition == "R0" else "nicht dokumentiert"),
                ({"one_chat_all_questions": "Eine Unterhaltung für alle Fragen", "fresh_chat_per_question": "Neue Unterhaltung je Frage"}.get(
                    record.get("metadata", {}).get("conversation_mode"), "nicht dokumentiert") if condition == "V" else "Unabhängige API-Aufrufe"),
                "R0-Chunks →" if condition == "R0" and record.get("retrieved") else "", ""])
            if condition == "R0":
                for rank, chunk in enumerate(record.get("retrieved", []), 1):
                    chunk_first.setdefault(qid, len(chunkrows) + 2)
                    chunkrows.append([qid, rank, chunk["chunk_id"], chunk["passage_id"], chunk.get("source_role", ""),
                                      chunk["text"], chunk.get("score")])
        suggestions.append([qid, "vorhanden" if proposal else "noch nicht vorhanden", auto,
            proposal.get("support"), proposal.get("evidence_available"), "\n".join(proposal.get("missing_components", [])),
            "\n".join(proposal.get("evidence_ids", [])), proposal.get("reason", ""),
            json.dumps(automatic[qid].get("decisions", []), ensure_ascii=False, indent=2) if qid in automatic else "",
            disagreement])
    overview_sheet = table("Übersicht", ["Frage-ID", "Fragetyp", "Frage", "R0 Mensch 0/1", "V Mensch 0/1", "R0 automatisch",
          "R0-Vorschlag korrigiert?", "R0 Status", "V Status", "R0 selbst geprüft?", "V selbst geprüft?"],
          overview, [13, 25, 65, 15, 15, 18, 22, 25, 25, 18, 18])
    green = book.add_format({"bg_color": "#E2F0D9"})
    red = book.add_format({"bg_color": "#FCE4D6"})
    yellow = book.add_format({"bg_color": "#FFF2CC"})
    for column in (3, 4):
        cell = xlsxwriter.utility.xl_rowcol_to_cell(1, column)
        overview_sheet.conditional_format(1, column, 20, column, {"type": "formula", "criteria": f"=AND(ISNUMBER({cell}),{cell}=1)", "format": green})
        overview_sheet.conditional_format(1, column, 20, column, {"type": "formula", "criteria": f"=AND(ISNUMBER({cell}),{cell}=0)", "format": red})
    overview_sheet.conditional_format(1, 6, 20, 6, {"type": "text", "criteria": "containing", "value": "ja", "format": yellow})
    review_sheet = table("Prüftabelle", ["Frage-ID", "Fragetyp", "Bedingung", "Frage", "Geprüfte Referenzantwort",
        "Erforderliche Bestandteile", "Referenz-Fundstellen", "Unveränderte Modellantwort / Ausfallgrund", "Antwortstatus",
        "Automatischer R0-Vorschlag", "Menschliche Korrektheit 0/1", "Menschliche Belegprüfung", "Notwendige R0-Belege vorhanden?",
        "Menschliche Begründung / Korrektur", "Menschlich geprüft?", "Modell", "Dienst", "Vorgehen / Gesprächskontext", "Tatsächliche R0-Chunks", "Kommentar Lehrperson"],
        detailed, [13, 25, 12, 55, 60, 40, 25, 75, 25, 23, 20, 24, 25, 65, 20, 25, 22, 45, 25, 55])
    table("Vorprüfung R0", ["Frage-ID", "Status", "Korrektheitsvorschlag", "Beleglage", "Evidenzverfügbarkeit",
        "Fehlende/falsche Pflichtbestandteile", "Automatische Beleg-IDs", "Hinweis zur Vorprüfung", "Einzelentscheidungen und Wahrscheinlichkeiten", "Mensch korrigiert?"],
        suggestions, [13, 25, 22, 24, 25, 55, 25, 65, 85, 20])
    source_rows = [[p["passage_id"], p["title"], p["pdf_page"], p["source_role"], p["text"], p.get("source_url", "")]
                   for p in protocol["passages"]]
    table("Quellenseiten", ["Seiten-ID", "Dokument", "PDF-Seite", "Quellenrolle", "Vollständige geprüfte Textfassung", "Herkunft"],
          source_rows, [25, 45, 13, 40, 110, 55])
    table("R0-Chunks", ["Frage-ID", "Rang", "Chunk-ID", "Seiten-ID", "Quellenrolle", "Tatsächlich übergebener Text", "Ähnlichkeit"],
          chunkrows, [13, 10, 40, 25, 40, 110, 15])
    metric_rows = [[m["condition"], m["metric"], m["numerator"], m["denominator"], m["proportion"],
        "Inventar" if m["status"] == "inventory" else ("vollständig" if m["status"] == "final" else "offen; Antworten oder menschliche Urteile fehlen")]
        for m in metrics]
    metric_sheet = table("Kennzahlen", ["Bedingung", "Kennzahl", "Zähler", "Nenner", "Anteil", "Stand"], metric_rows, [14, 75, 14, 14, 16, 55])
    for row, m in enumerate(metrics, 1):
        if m["proportion"] is not None:
            metric_sheet.write_number(row, 4, m["proportion"], percent)
    source_locations = {p["passage_id"]: i + 2 for i, p in enumerate(protocol["passages"])}
    for row, q in enumerate(protocol["questions"]):
        for offset in (1, 2):
            if q["reference_passage_ids"]:
                review_sheet.write_url(row*2+offset, 6, f"internal:'Quellenseiten'!A{source_locations[q['reference_passage_ids'][0]]}",
                                       link_format, "\n".join(q["reference_passage_ids"]))
        if q["question_id"] in chunk_first:
            review_sheet.write_url(row*2+1, 18, f"internal:'R0-Chunks'!A{chunk_first[q['question_id']]}", link_format, "Tatsächliche R0-Chunks →")
    table("Langtexte", ["Ursprüngliche Zelle", "Teil", "Vollständiger Textabschnitt"], longtexts, [35, 10, 115])
    book.close()
    return Path(destination)
