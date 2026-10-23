"""Readable, escaped evidence cards and offline controls for non-programmers."""
import json
from html import escape
from pathlib import Path

import ipywidgets as widgets
import pandas as pd
from IPython.display import HTML, display

from src.corpus import digest, make_chunks, read_jsonl
from src.sourcepack import load_pack


STYLE = """<style>
.evidence-card{width:100%;box-sizing:border-box;border:1px solid #aaa;border-radius:8px;padding:18px;margin:10px 0}
.evidence-card pre{white-space:pre-wrap!important;overflow-wrap:anywhere;word-break:normal;font:16px/1.6 system-ui,sans-serif;max-height:none!important}
.evidence-card .meta{font-size:13px;line-height:1.6;color:#555;overflow-wrap:anywhere}
.lab-table{width:100%;border-collapse:collapse;table-layout:auto}
.lab-table th,.lab-table td{white-space:normal!important;overflow-wrap:anywhere;text-align:left;vertical-align:top;padding:9px;border-bottom:1px solid #ddd;max-width:none!important}
.lab-table th{background:#edf3f7}
.lab-note{padding:12px;border-left:4px solid #27677d;background:#f0f7fa;margin:8px 0;line-height:1.5}
</style>"""


def table_html(rows):
    return pd.DataFrame(rows).to_html(index=False, escape=True, classes="lab-table", border=0)


def evidence_html(record, number=None, total=None):
    """No truncation of text; escape all source data before embedding in HTML."""
    label = record.get("chunk_id", record["passage_id"])
    position = f" · {number} von {total}" if number else ""
    page = record["pdf_page"]
    filename = record.get("filename", f"{record['ballot_id']}.pdf")
    return f"""<article class="evidence-card">
<h3>{escape(record['title'])}</h3>
<div class="meta"><b>{escape(label)}</b>{position}<br>
Vorlage {escape(record['ballot_id'])} · Abstimmung {escape(record['ballot_date'])} · Wissensstand {escape(record['information_cutoff'])}<br>
PDF-Seite {page} · gedruckte Seite {record['printed_page']} · {escape(record['source_role'])}<br>
<a href="corpus/pdfs/{escape(filename, quote=True)}#page={page}" target="_blank">Original-PDF öffnen</a>
 · <a href="{escape(record['source_url'], quote=True)}" target="_blank">Herkunft</a></div>
<pre>{escape(record['text'])}</pre></article>"""


def evidence_browser(records, title="Volltext lesen"):
    if not records:
        return widgets.HTML("Keine Passagen vorhanden.")
    titles = {r["ballot_id"]: r["title"] for r in records}
    ballot = widgets.Dropdown(options=[(f"{bid} · {name}", bid) for bid, name in titles.items()],
                              description="Vorlage:", layout=widgets.Layout(width="100%"),
                              style={"description_width": "initial"})
    item = widgets.Dropdown(description="Textstelle:", layout=widgets.Layout(width="100%"),
                            style={"description_width": "initial"})
    body = widgets.HTML(layout=widgets.Layout(width="100%"))
    filtered = []

    def render(change=None):
        if item.value is not None and filtered:
            body.value = evidence_html(filtered[item.value], item.value + 1, len(filtered))

    def choose_ballot(change=None):
        filtered[:] = [r for r in records if r["ballot_id"] == ballot.value]
        item.options = [(f"{i+1}: PDF-Seite {r['pdf_page']} · {r.get('chunk_id', r['passage_id'])}", i)
                        for i, r in enumerate(filtered)]
        item.value = 0
        render()

    ballot.observe(choose_ballot, names="value")
    item.observe(render, names="value")
    choose_ballot()
    return widgets.VBox([widgets.HTML(f"<h3>{escape(title)}</h3>"), ballot, item, body], layout=widgets.Layout(width="100%"))


BASELINE = {"chunk_size": 300, "chunk_overlap": 50, "top_k": 5, "filter_ballot": False}


def preview_configs(variable, value):
    if variable not in BASELINE:
        raise ValueError("Unbekannte Veränderung.")
    baseline = dict(BASELINE)
    intervention = {**baseline, variable: value}
    if not (0 <= intervention["chunk_overlap"] < intervention["chunk_size"]):
        raise ValueError("Überlappung muss kleiner als die Chunkgrösse sein.")
    if intervention["top_k"] < 1:
        raise ValueError("top-k muss mindestens 1 sein.")
    changed = [key for key in baseline if baseline[key] != intervention[key]]
    if len(changed) != 1:
        raise ValueError("B muss sich in genau einer Einstellung von A unterscheiden.")
    return baseline, intervention


class OfflineLab:
    def __init__(self, root):
        self.root = Path(root)
        self.sources = json.loads((self.root / "corpus/sources.json").read_text(encoding="utf-8"))
        self.passages = load_pack(self.root)
        self.questions = read_jsonl(self.root / "evaluation/questions_development.jsonl")
        self.chunks_a = make_chunks(self.passages, BASELINE["chunk_size"], BASELINE["chunk_overlap"])
        self.saved_path = self.root / "outputs/arbeitsblatt.json"
        self.saved = json.loads(self.saved_path.read_text(encoding="utf-8")) if self.saved_path.exists() else {}
        display(HTML(STYLE))
        display(HTML('<div class="lab-note"><b>Offline-Modus aktiv.</b> Quellen und Chunkgrenzen werden lokal untersucht. '
                     'Es entstehen keine Embeddings, Modellantworten oder API-Kosten. Die lokale .env wird hier nicht geladen.</div>'))

    def show_sources(self):
        rows = []
        for s in self.sources:
            pages = [p for part in s["sections"] for p in part["pdf_pages"]]
            rows.append({"ID": s["ballot_id"], "Initiative": s["title"], "Abstimmung": s["ballot_date"],
                         "Quellenseiten": len(pages), "Status": "lokal verfügbar" if s["status"] == "available" else s["status"]})
        display(HTML(table_html(rows)))
        display(evidence_browser(self.passages, "Quellenseite vollständig lesen"))

    def show_chunks(self):
        display(HTML(f"<p>Baseline A: <b>{len(self.chunks_a)} Chunks</b>, Zielgrösse 300 Tokens, Überlappung bis 50 Tokens. "
                     "Kurze Seiten erzeugen kürzere Chunks. Kein Chunk überschreitet eine Quellenseite.</p>"))
        display(evidence_browser(self.chunks_a, "Baseline A: Chunk vollständig lesen"))

    def show_questions(self):
        self.question = widgets.Dropdown(options=[(f"{q['question_id']} · {q['category']}", q["question_id"]) for q in self.questions],
            description="Testfrage:", layout=widgets.Layout(width="100%"), style={"description_width": "initial"})
        if self.saved.get("question_id") in {q["question_id"] for q in self.questions}:
            self.question.value = self.saved["question_id"]
        body = widgets.HTML()
        def render(change=None):
            q = next(q for q in self.questions if q["question_id"] == self.question.value)
            body.value = f'<div class="evidence-card"><b>{escape(q["question_id"])}</b><pre>{escape(q["question"])}</pre>' \
                         '<div class="meta">Fragenentwurf · Referenzantworten werden von der Lehrperson geprüft.</div></div>'
        self.question.observe(render, names="value")
        render()
        display(widgets.VBox([self.question, body], layout=widgets.Layout(width="100%")))

    def show_experiment_controls(self):
        options = [("Chunkgrösse (Tokens)", "chunk_size"), ("Überlappung (Tokens)", "chunk_overlap"),
                   ("Anzahl abgerufener Chunks (top-k)", "top_k"), ("Nur die Zielvorlage abrufen", "filter_ballot")]
        self.variable = widgets.Dropdown(options=options, description="Ich verändere:", layout=widgets.Layout(width="100%"),
            style={"description_width": "initial"}, value=self.saved.get("variable", "chunk_size"))
        value_box = widgets.VBox()
        preview = widgets.Output(layout=widgets.Layout(width="100%"))
        self.prediction = widgets.Textarea(value=self.saved.get("prediction", ""), description="Vorhersage:",
            placeholder="Wenn wir … verändern, erwarten wir …, weil …",
            layout=widgets.Layout(width="100%", height="110px"), style={"description_width": "initial"})
        self.observations = widgets.Textarea(value=self.saved.get("observations", ""), description="Beobachtung:",
            placeholder="Welche Aussage wird getrennt? Welche Quellenstelle würdet ihr zusätzlich benötigen?",
            layout=widgets.Layout(width="100%", height="130px"), style={"description_width": "initial"})
        update = widgets.Button(description="B-Vorschau aktualisieren", layout=widgets.Layout(width="240px"))
        save = widgets.Button(description="Arbeitsblatt speichern", button_style="info", layout=widgets.Layout(width="240px"))
        self.save_button = save
        status = widgets.HTML()

        def choose_variable(change=None):
            key = self.variable.value
            if key == "filter_ballot":
                self.value = widgets.Dropdown(options=[("Nur Zielvorlage", True)], value=True, description="B:")
            else:
                limits = {"chunk_size": (180, 60, 1200), "chunk_overlap": (100, 0, 299), "top_k": (8, 1, 30)}
                default, minimum, maximum = limits[key]
                if self.saved.get("variable") == key:
                    default = max(minimum, min(maximum, self.saved.get("value", default)))
                self.value = widgets.BoundedIntText(value=default, min=minimum, max=maximum, description="B:")
            value_box.children = [self.value]

        def show_preview(button=None):
            with preview:
                preview.clear_output(wait=True)
                try:
                    a, b = preview_configs(self.variable.value, self.value.value)
                except ValueError as exc:
                    display(HTML(f'<div class="lab-note">{escape(str(exc))}</div>'))
                    return
                rows = [{"Bedingung": label, "Chunkgrösse (Tokens)": c["chunk_size"], "Überlappung (Tokens)": c["chunk_overlap"],
                         "Anzahl Chunks (top-k)": c["top_k"], "Quellenauswahl beim Abruf": "nur Zielvorlage" if c["filter_ballot"] else "alle Vorlagen"}
                        for label, c in (("A – bleibt fest", a), ("B – eine Änderung", b))]
                display(HTML(table_html(rows)))
                chunks_b = make_chunks(self.passages, b["chunk_size"], b["chunk_overlap"])
                display(HTML(f"<p>A: {len(self.chunks_a)} Chunks · B: {len(chunks_b)} Chunks.</p>"))
                if self.variable.value in ("top_k", "filter_ballot"):
                    display(HTML('<div class="lab-note">Diese Änderung betrifft den späteren Abruf. '
                                 'Ohne Embeddings wird jetzt keine Rangliste berechnet. Die Chunks bleiben gleich.</div>'))
                display(evidence_browser(chunks_b, "B-Vorschau: Chunk vollständig lesen"))

        def save_notes(button=None):
            try:
                a, b = preview_configs(self.variable.value, self.value.value)
            except ValueError as exc:
                status.value = escape(str(exc))
                return
            payload = {"mode": "offline", "question_id": self.question.value, "variable": self.variable.value,
                "value": self.value.value, "baseline": a, "intervention": b,
                "prediction": self.prediction.value, "observations": self.observations.value,
                "corpus_sha256": digest(self.passages)}
            self.saved_path.parent.mkdir(exist_ok=True)
            self.saved_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            status.value = '<b>Gespeichert in outputs/arbeitsblatt.json.</b> Diese Datei enthält eure Notizen, keine Modellresultate.'

        self.variable.observe(choose_variable, names="value")
        choose_variable()
        update.on_click(show_preview)
        save.on_click(save_notes)
        display(widgets.VBox([self.variable, value_box, self.prediction, update, preview,
                              self.observations, save, status], layout=widgets.Layout(width="100%")))
        show_preview()
