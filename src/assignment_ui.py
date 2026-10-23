"""Six-step learner interface; paid calls require an explicit live container startup."""
import json
import os
from html import escape
from pathlib import Path
from urllib.parse import quote

import ipywidgets as w
from IPython.display import HTML, display

from src.assignment import Assignment, DOSSIERS, TYPES, SUPPORT, AVAILABILITY, fulltext, prompt, now, validate_questions
from src.assignment import run_rag, evaluate_rag_only, DecisionsEvaluator
from src import live
from src.corpus import make_chunks
from src.notebook_ui import STYLE, evidence_browser, table_html


def textarea(value="", description="", height="110px", disabled=False):
    return w.Textarea(value=value, description=description, layout=w.Layout(width="100%", height=height),
                      style={"description_width": "initial"}, disabled=disabled)


def download_link(root, path, label):
    relative = Path(path).resolve().relative_to(Path(root).resolve())
    prefix = os.environ.get("JUPYTERHUB_SERVICE_PREFIX", "/").rstrip("/")
    href = prefix + "/files/" + quote(relative.as_posix()) + "?download=1"
    return '<a href="' + escape(href, quote=True) + '" download="' + escape(Path(path).name, quote=True) + '">' + escape(label) + '</a>'


class ChallengeNotebook:
    def __init__(self, root, output_root=None):
        self.root = Path(root)
        self.output_root = output_root
        self.project = Assignment(root, output_root=output_root)
        self.configure_project()
        self.refreshers = []
        display(HTML(STYLE))
        mode = ('<b>Live-Modus · API-Aufrufe sind kostenpflichtig.</b> Nur ein ausdrücklicher Klick startet Modellaufrufe. '
                'Zuerst die separate Probe in Schritt 3 ausführen.' if live.enabled() else
                '<b>Offline-Modus.</b> Keine Modellaufrufe. Die lokale .env wird nicht geladen.')
        display(HTML('<div class="lab-note">' + mode + ' Sie bearbeiten nur Eingabefelder.</div>'))

    def configure_project(self):
        # Never rewrite frozen protocols. Existing unfrozen drafts pick up the teacher's live model IDs.
        if live.enabled() and not self.project.frozen:
            config = live.configured_models(self.root)
            for key in ("embedding_model", "generation_model", "evaluation_model"):
                if config.get(key):
                    self.project.state["config"][key] = config[key]
            self.project.state["config"]["evaluation_endpoint"] = "/v1/decisions"

    def refresh(self):
        for callback in self.refreshers:
            callback()

    def section(self, render):
        box = w.VBox(layout=w.Layout(width="100%"))
        def update():
            box.children = render()
        self.refreshers.append(update)
        update()
        display(box)

    def action(self, status, callback, refresh=False):
        def run(button=None):
            try:
                result = callback()
                status.value = '<div class="lab-note">' + escape(str(result or "Gespeichert.")) + '</div>'
                if refresh:
                    self.refresh()
            except (ValueError, OSError) as exc:
                status.value = '<div class="lab-note">' + escape(str(exc)).replace("\n", "<br>") + '</div>'
        return run

    def show_dossier(self):
        choice = w.Dropdown(options=[(name, key) for key, name in DOSSIERS.items()], value=self.project.dossier_id,
                            description="Mein Dossier:", style={"description_width": "initial"}, layout=w.Layout(width="100%"))
        def choose(change):
            self.project = Assignment(self.root, change["new"], self.output_root)
            self.configure_project()
            self.refresh()
        choice.observe(choose, names="value")
        display(choice)
        def render():
            p = self.project
            pages = p.state["passages"]
            select = w.Dropdown(options=[(f"{r['passage_id']} · {r['source_role']}", i) for i, r in enumerate(pages)],
                                layout=w.Layout(width="100%"))
            body = textarea(pages[0]["text"], "Textfassung:", "220px", p.frozen)
            reviewed = w.Checkbox(value=p.state["text_reviewed"], description="Ich habe die gesamte Textfassung am Original geprüft.", disabled=p.frozen,
                                 layout=w.Layout(width="100%"))
            status = w.HTML()
            def show(change):
                body.value = pages[select.value]["text"]
            select.observe(show, names="value")
            save = w.Button(description="Textseite speichern", disabled=p.frozen, layout=w.Layout(width="220px"))
            confirm = w.Button(description="Textprüfung speichern", disabled=p.frozen, layout=w.Layout(width="220px"))
            def save_page():
                if not body.value.strip():
                    raise ValueError("Leere Seite nicht speichern.")
                p.state["passages"][select.value]["text"] = body.value
                p.state["text_reviewed"] = False
                p.save()
                return "Textseite gespeichert. Nach Änderungen gesamte Textprüfung erneut bestätigen."
            save.on_click(self.action(status, save_page, refresh=True))
            def confirm_review():
                p.state["text_reviewed"] = reviewed.value
                p.save()
            confirm.on_click(self.action(status, confirm_review))
            return [w.HTML(f"<p><b>{escape(DOSSIERS[p.dossier_id])}</b> · {len(pages)} ausgewählte Seiten. "
                           "Dossierwechsel erst nach dem Speichern. Jeder Dossierstand liegt in einem eigenen Ordner.</p>"),
                    evidence_browser(pages, "Originalnahe Quellenseiten lesen"), select, body, save, reviewed, confirm, status]
        self.section(render)

    def show_references(self):
        def render():
            p = self.project
            choice = w.Dropdown(options=[(f"{q['question_id']} · {q['type']}", i) for i, q in enumerate(p.state["questions"])],
                                layout=w.Layout(width="100%"))
            question = textarea(description="Meine Frage:", disabled=p.frozen)
            answer = textarea(description="Referenzantwort:", disabled=p.frozen)
            components = textarea(description="Erforderliche Bestandteile:", disabled=p.frozen)
            refs = w.SelectMultiple(options=[(r["passage_id"], r["passage_id"]) for r in p.state["passages"]],
                description="Fundstellen:", disabled=p.frozen, rows=6, style={"description_width": "initial"}, layout=w.Layout(width="100%"))
            missing = textarea(description="Fehlende Information:", height="75px", disabled=p.frozen)
            checked = w.Checkbox(description="Ich habe Frage und Referenz am gesamten Dossier geprüft.", disabled=p.frozen,
                                 layout=w.Layout(width="100%"))
            status = w.HTML()
            def populate(change=None):
                q = p.state["questions"][choice.value]
                question.value, answer.value = q["question"], q["reference_answer"]
                components.value = "\n".join(q["required_components"])
                refs.value = tuple(q["reference_passage_ids"])
                missing.value, checked.value = q["missing_information"], q["reviewed"]
            choice.observe(populate, names="value")
            populate()
            save = w.Button(description="Diese Frage speichern", disabled=p.frozen, layout=w.Layout(width="220px"))
            def save_question():
                q = p.state["questions"][choice.value]
                q.update(question=question.value, reference_answer=answer.value,
                    required_components=[s.strip() for s in components.value.splitlines() if s.strip()],
                    reference_passage_ids=list(refs.value), missing_information=missing.value, reviewed=checked.value)
                p.save()
                return f"{q['question_id']} gespeichert. Vor dem Wechsel zur nächsten Frage immer speichern."
            save.on_click(self.action(status, save_question))
            self.reference_widgets = {"choice": choice, "question": question, "answer": answer, "components": components,
                                      "refs": refs, "missing": missing, "checked": checked, "save": save}
            return [w.HTML('<p><b>20 leere Arbeitsfelder für Ihre eigenen Fragen.</b> '
                'F01–F05 direkt; F06–F10 andere Formulierung; F11–F15 mehrere Fundstellen; F16–F20 nicht beantwortbar. '
                'Erforderliche Antwortbestandteile: ein Bestandteil pro Zeile. Mehrere Fundstellen mit Strg/Cmd auswählen.</p>'),
                choice, question, answer, components, refs, missing, checked, save, status]
        self.section(render)

    def show_protocol(self):
        def render():
            p = self.project
            config = p.state["config"]
            chunks = make_chunks(p.state["passages"], config["chunk_size"], config["chunk_overlap"])
            prediction = textarea(p.state["prediction"], "Vorhersage:", disabled=p.frozen)
            assistance = textarea(p.state["ai_assistance"], "KI-Unterstützung bei Referenzen:", disabled=p.frozen)
            status = w.HTML()
            probe_question = textarea(description="Separate Probefrage:", height="70px")
            probe_task = textarea(description="RAG-Probeauftrag (Vorschau):", height="180px")
            probe_reference = textarea(description="Eigene geprüfte Probe-Referenz:", height="80px")
            probe_result = textarea(description="Ergebnis der API-Probe:", height="220px", disabled=True)
            probe_live = w.Button(description="Eine API-Probe starten", disabled=not live.enabled(), layout=w.Layout(width="240px"))
            def test_api(button):
                probe_live.disabled = True
                status.value = "API-Probe läuft: Embeddings → RAG-Antwort → Decisions. Bitte warten."
                try:
                    with live.client() as api:
                        result = live.run_probe(self.root, p.state["passages"], probe_question.value,
                                                probe_reference.value, live.configured_models(self.root), api)
                    probe_result.value = json.dumps(result, ensure_ascii=False, indent=2)
                    status.value = "Probe abgeschlossen. Ergebnis und Vorprüfung selbst am Original prüfen."
                except Exception as exc:
                    status.value = escape("API-Probe abgebrochen: " + type(exc).__name__ +
                        (": " + str(exc) if isinstance(exc, (ValueError, RuntimeError)) else "; Zugang, Modellfreigabe oder Kontingent prüfen. Details bleiben lokal."))
                finally:
                    probe_live.disabled = not live.enabled()
            probe_live.on_click(test_api)
            probe_button = w.Button(description="RAG-Probeauftrag anzeigen", disabled=p.frozen, layout=w.Layout(width="240px"))
            def build_probe():
                if not probe_question.value.strip():
                    raise ValueError("Eine separate Probefrage eingeben; sie gehört nicht zu F01–F20.")
                probe_task.value = prompt({"question_id": "PROBE", "question": probe_question.value}, fulltext(p.state["passages"]))
                return "Nur Funktionsprüfung vor dem Hauptvergleich; nicht als F01–F20 bewerten."
            probe_button.on_click(self.action(status, build_probe))
            save = w.Button(description="Vorbereitung speichern", disabled=p.frozen, layout=w.Layout(width="220px"))
            freeze = w.Button(description="Referenzen einfrieren", disabled=p.frozen, button_style="warning", layout=w.Layout(width="220px"))
            def store():
                p.state.update(prediction=prediction.value, ai_assistance=assistance.value)
                p.save()
            def freeze_all():
                if live.enabled() and not all(config.get(key) for key in ("embedding_model", "generation_model", "evaluation_model")):
                    raise ValueError("Vor dem Einfrieren alle drei Modell-IDs in der Live-Konfiguration festlegen und neu starten.")
                store()
                return p.freeze()
            save.on_click(self.action(status, store))
            freeze.on_click(self.action(status, freeze_all, refresh=True))
            errors = validate_questions(p.state["questions"], p.state["passages"])
            overview = [{"Einstellung": label, "R0": value} for label, value in (
                ("Chunkgrösse", config["chunk_size"]), ("Überlappung", config["chunk_overlap"]),
                ("top-k", config["top_k"]), ("Embedding-Modell", config["embedding_model"]),
                ("Antwortmodell", config["generation_model"] or "vor Freigabe durch Lehrperson festzulegen"),
                ("Bewertungsmodell (nur R0)", config["evaluation_model"] or "vor Freigabe festzulegen"))]
            text = "<b>Eingefroren.</b> Fragen, Text, Antwortauftrag und R0-Einstellungen bleiben unverändert." if p.frozen else f"Vorbereitung: {len(errors)} offene Prüfhinweise. Beim Einfrieren werden sie vollständig angezeigt."
            return [w.HTML(table_html(overview)), evidence_browser(chunks, "R0-Chunkvorschau – noch kein Retrieval"),
                    w.HTML("<p>Separate Probefrage verwenden, die nicht zu F01–F20 gehört. Die API-Probe nutzt nur das gewählte Dossier, erzeugt eine RAG-Antwort und prüft diese mit Decisions. Ergebnisse bleiben separat unter outputs/live_probes/. Im Offline-Modus ist die API-Probe gesperrt.</p>"),
                    probe_question, probe_reference, probe_live, probe_result, probe_button, probe_task,
                    w.HTML(f'<div class="lab-note">{text}</div>'), prediction, assistance, save, freeze, status]
        self.section(render)

    def show_runs(self):
        def render():
            p = self.project
            if not p.frozen:
                return [w.HTML('<div class="lab-note">Zuerst alle Fragen, Referenzen und die Vorhersage speichern und einfrieren. '
                               'Danach erscheinen das Upload-PDF, die 20 Fragenaufträge und Antwortfelder.</div>')]
            protocol = p.protocol()
            upload_mode = protocol.get("v_input_mode") == "document_upload"
            upload_note = "Altes eingefrorenes Volltext-Protokoll: gespeicherte Textaufträge unverändert verwenden."
            if upload_mode:
                path = p.frozen_folder / protocol["upload_pdf"]["filename"]
                upload_note = (download_link(self.root, path, "Gewähltes Dossier-PDF für ChatGPT/Claude herunterladen")
                               if path.resolve().is_relative_to(self.root.resolve()) else escape(str(path)))
            choice = w.Dropdown(options=[q["question_id"] for q in p.protocol()["questions"]], layout=w.Layout(width="100%"))
            task = textarea(p.v_prompt(choice.value), "Fragenauftrag für ChatGPT/Claude:", "220px")
            task.disabled = False  # select/copy must work; edits are never used or saved.
            response = textarea(description="Erste Antwort aus ChatGPT/Claude:", height="200px")
            service = w.Dropdown(options=["ChatGPT", "Claude"], description="Mein Dienst:")
            conversation = w.Dropdown(options=[("Eine Unterhaltung, F01–F20 nacheinander", "one_chat_all_questions"),
                                               ("Neue Unterhaltung je Frage", "fresh_chat_per_question")],
                                      description="Mein Vorgehen:", layout=w.Layout(width="100%"), style={"description_width": "initial"})
            model = w.Text(description="Angezeigtes Modell:", layout=w.Layout(width="100%"), style={"description_width": "initial"})
            settings = w.Text(value="nicht verfügbar", description="Einstellungen:", layout=w.Layout(width="100%"), style={"description_width": "initial"})
            run_date = w.Text(value=now().split("T")[0], description="Datum des Aufrufs:", layout=w.Layout(width="100%"), style={"description_width": "initial"})
            pasted = w.Checkbox(description=("Bereitgestelltes Dossier-PDF hochgeladen und denselben Fragenauftrag verwendet."
                                            if upload_mode else "Vollständigen Textauftrag unverändert eingefügt."), layout=w.Layout(width="100%"))
            note = w.HTML()
            save = w.Button(description="V-Antwort unverändert sichern", layout=w.Layout(width="260px"))
            def choose(change=None):
                task.value = p.v_prompt(choice.value)
                existing = p.answers("V").get(choice.value)
                response.value = existing.get("answer", "") if existing else ""
                response.disabled = bool(existing)
                save.disabled = bool(existing)
                if existing:
                    meta = existing.get("metadata", {})
                    service.value = meta.get("service", "ChatGPT")
                    conversation.value = meta.get("conversation_mode", "fresh_chat_per_question")
                    model.value = meta.get("model", "")
                    settings.value = meta.get("settings", "nicht verfügbar")
                    run_date.value = meta.get("run_date", "")
                    pasted.value = bool(meta.get("document_uploaded") or meta.get("fulltext_pasted"))
                else:
                    pasted.value = False
                note.value = "Bereits gespeichert; die erste Antwort wird nicht überschrieben." if existing else "Noch keine V-Antwort gespeichert."
            choice.observe(choose, names="value")
            choose()
            def save_response():
                # Prompt is regenerated from frozen input, never from an edited preview field.
                if task.value != p.v_prompt(choice.value):
                    raise ValueError("Vorschau wurde verändert. Frage neu wählen und nur den unveränderten Auftrag kopieren.")
                metadata = {"model": model.value, "service": service.value, "settings": settings.value,
                            "run_date": run_date.value, "conversation_mode": conversation.value}
                metadata["document_uploaded" if upload_mode else "fulltext_pasted"] = pasted.value
                p.store_answer("V", choice.value, response.value, metadata)
                choose()
            save.on_click(self.action(note, save_response))
            generate = w.Button(description="20 R0-Antworten erzeugen" if live.enabled() else "R0 erzeugen – offline gesperrt",
                                disabled=not live.enabled(), layout=w.Layout(width="300px"))
            def generate_r0(button):
                generate.disabled = True
                note.value = "R0-Lauf läuft. Bitte warten; bereits gespeicherte Antworten werden übersprungen."
                try:
                    with live.client() as api:
                        run_rag(p, live.embedder(self.root, api, p.protocol()["config"]), api)
                    self.refresh()
                except Exception as exc:
                    note.value = escape("R0-Lauf angehalten: " + type(exc).__name__ +
                        (": " + str(exc) if isinstance(exc, (ValueError, RuntimeError)) else "; Zugang, Modell oder Kontingent prüfen. Versuche bleiben gespeichert."))
                finally:
                    generate.disabled = not live.enabled()
            generate.on_click(generate_r0)
            return [w.HTML('<p>R0 benötigt Live-Modus und ein eingefrorenes Protokoll mit Modell-IDs. '
                'Ein Klick startet die noch fehlenden R0-Antworten. Antworten und Fehlversuche bleiben erhalten.</p>'), generate,
                w.HTML('<p><b>V: Ihr üblicher PDF-Upload in ChatGPT oder Claude.</b> Das bereitgestellte Dossier-PDF '
                    'herunterladen und hochladen. Es enthält dieselben ausgewählten Originalseiten wie R0. '
                    'Die 20 Fragen mit demselben Auftrag stellen, die erste Antwort jeweils hier sichern. '
                    'Wie gewohnt eine Unterhaltung für alle Fragen oder neue Chats nutzen; Dienst, Modell und Vorgehen festhalten. '
                    'Keine Referenzantworten, RAG-Antworten oder Bewertungshinweise hochladen. Keine Websuche, zusätzlichen Quellen '
                    'oder korrigierenden Folgefragen verwenden. Die interne Dokumentverarbeitung des Dienstes bleibt unbekannt; '
                    'V bedeutet keine Zusicherung vollständigen Modellkontexts. Aufträge liegen unter v_prompts/.</p>'
                    if upload_mode else '<p>Altes eingefrorenes Volltext-Protokoll: vollständigen Textauftrag in eine neue ChatGPT-Unterhaltung '
                    'einfügen, erste Antwort und Textübergabe dokumentieren. Dieser alte Vergleich wird nicht in einen Upload-Vergleich umgewandelt.</p>'),
                w.HTML(upload_note), service, conversation, choice, task, response, model, run_date, settings, pasted, save, note]
        self.section(render)

    def show_evaluation(self):
        def render():
            p = self.project
            if not p.frozen:
                return [w.HTML("Bewertungsfelder erscheinen nach dem Einfrieren.")]
            condition = w.Dropdown(options=[("R0 – Vorschlag prüfen", "R0"), ("V – selbst bewerten", "V")], description="Bedingung:")
            choice = w.Dropdown(options=[q["question_id"] for q in p.protocol()["questions"]], description="Frage:")
            content = w.HTML()
            correct = w.Dropdown(options=[("Bitte wählen", None), ("0 – nicht korrekt", 0), ("1 – korrekt", 1)], description="Korrektheit:")
            support = w.Dropdown(options=[("Bitte wählen", None)] + [(s, s) for s in SUPPORT], description="Belege:")
            evidence = w.Dropdown(options=[("Bitte wählen", None)] + [(s, s) for s in AVAILABILITY], description="R0-Belege:")
            claims = w.Checkbox(description="Die Antwort enthält Sachbehauptungen.")
            reason = textarea(description="Eigene Begründung / Korrektur:")
            confirmed = w.Checkbox(description="Ich habe Antwort, Referenz und Quellen selbst geprüft.", layout=w.Layout(width="100%"))
            save = w.Button(description="Menschliches Urteil speichern", layout=w.Layout(width="260px"))
            failure_note = textarea(description="Technischen Ausfall begründen:", height="70px")
            failure_confirm = w.Checkbox(description="Tatsächlich versucht; technischer Ausfall blieb ungelöst.", layout=w.Layout(width="100%"))
            failure_save = w.Button(description="Ungelösten Ausfall dokumentieren", layout=w.Layout(width="280px"))
            status = w.HTML()
            def populate(change=None):
                q = p.question(choice.value)
                record = p.answers(condition.value).get(choice.value)
                text = record.get("answer", record.get("reason", "")) if record else "Noch keine Antwort gespeichert."
                proposal = "Keine automatische Bewertung für V; hier beurteilen Sie selbst."
                path = p.frozen_folder / "automatic_r0" / f"{choice.value}.json"
                if condition.value == "R0":
                    if path.exists():
                        saved = json.loads(path.read_text(encoding="utf-8"))
                        proposal = json.dumps({"Vorschlag": saved["proposal"], "Einzelentscheidungen": saved.get("decisions", [])}, ensure_ascii=False, indent=2)
                    else:
                        proposal = "Noch kein automatischer R0-Vorschlag vorhanden (Entwicklungsmodus offline)."
                content.value = '<div class="evidence-card"><h3>Antwort</h3><pre>' + escape(text) + '</pre><h3>Ihre Referenz</h3><pre>' + escape(q["reference_answer"]) + '</pre><h3>Vorprüfung</h3><pre>' + escape(proposal) + '</pre></div>'
                old = p.human_reviews().get((condition.value, choice.value), {})
                correct.value, support.value = old.get("correct"), old.get("support")
                evidence.value = old.get("evidence_available", "nicht anwendbar" if condition.value == "V" or q["type"] == TYPES[3] else None)
                evidence.disabled = condition.value == "V" or q["type"] == TYPES[3]
                claims.value, reason.value, confirmed.value = old.get("has_claims", False), old.get("reason", ""), False
                save.disabled = record is None
            condition.observe(populate, names="value")
            choice.observe(populate, names="value")
            populate()
            def store():
                p.save_human_review(condition.value, choice.value, {"correct": correct.value, "support": support.value,
                    "evidence_available": evidence.value, "has_claims": claims.value, "reason": reason.value, "confirmed": confirmed.value})
                return "Urteil gespeichert. Frühere Bewertungen bleiben im Bewertungsprotokoll erhalten."
            save.on_click(self.action(status, store))
            def failure():
                if not failure_confirm.value:
                    raise ValueError("Ausfall nur nach tatsächlichem Versuch bestätigen. Offline-Sperre ist kein Experimentergebnis.")
                p.store_failure(condition.value, choice.value, failure_note.value)
                populate()
                return "Ungelöster technischer Ausfall dokumentiert; zählt im festen Nenner als 0."
            failure_save.on_click(self.action(status, failure))
            automatic = w.Button(description="20 R0-Antworten mit Decisions prüfen" if live.enabled() else "Nur R0 automatisch prüfen – offline gesperrt",
                                 disabled=not live.enabled(), layout=w.Layout(width="360px"))
            def evaluate_r0(button):
                automatic.disabled = True
                status.value = "Decisions-Vorprüfung läuft. Bitte warten."
                try:
                    with live.client() as api:
                        evaluate_rag_only(p, DecisionsEvaluator(api, p.frozen_folder / "raw_evaluation"))
                    self.refresh()
                except Exception as exc:
                    status.value = escape("Vorprüfung angehalten: " + type(exc).__name__ +
                        (": " + str(exc) if isinstance(exc, (ValueError, RuntimeError)) else "; Zugang, Modell oder Kontingent prüfen. Rohdaten bleiben gespeichert."))
                finally:
                    automatic.disabled = not live.enabled()
            automatic.on_click(evaluate_r0)
            return [automatic,
                    condition, choice, content, correct, support, evidence, claims, reason, confirmed, save,
                    failure_note, failure_confirm, failure_save, status]
        self.section(render)

    def show_results(self):
        def render():
            p = self.project
            if not p.frozen:
                return [w.HTML("Vergleich und Export erscheinen nach dem Einfrieren.")]
            out = w.HTML()
            status = w.HTML()
            refresh = w.Button(description="Vergleich aktualisieren", layout=w.Layout(width="240px"))
            export = w.Button(description="Arbeitsdateien als ZIP exportieren", layout=w.Layout(width="300px"))
            excel = w.Button(description="Prüftabelle als Excel erstellen", layout=w.Layout(width="300px"))
            downloads = w.HTML()
            def update(button=None):
                rows, metrics = p.result_tables()
                shown_metrics = [{"Bedingung": m["condition"], "Kennzahl": m["metric"], "Anzahl": m["numerator"] if m["numerator"] is not None else "offen",
                    "Nenner": m["denominator"], "Anteil": f"{m['proportion']:.1%}" if m["proportion"] is not None else ("nicht anwendbar" if m["status"] == "final" else "offen"),
                    "Stand": "Inventar" if m["status"] == "inventory" else ("vollständig" if m["status"] == "final" else "menschliche Prüfung / Antworten offen")}
                    for m in metrics]
                shown_rows = [{"Bedingung": r["condition"], "Frage": r["question_id"], "Typ": r["type"],
                    "Korrektheit": r["correct"] if r["correct"] is not None else "offen", "Belege": r["support"], "R0-Belege vorhanden": r["evidence_available"],
                    "Bearbeitung": {"missing": "Antwort fehlt", "technical_failure": "technischer Ausfall", "completed": "Antwort gespeichert"}[r["status"]],
                    "Begründung": r["reason"], "Menschlich geprüft": "ja" if r["human_confirmed"] else "nein"} for r in rows]
                out.value = table_html(shown_metrics) + table_html(shown_rows)
            refresh.on_click(update)
            update()
            def export_excel():
                path = p.export_workbook()
                downloads.value = download_link(self.root, path, "Excel-Prüftabelle herunterladen")
                return "Excel erstellt. Download-Link unten anklicken. Nur gespeicherte Eingaben sind enthalten."
            def export_all():
                path = p.export()
                downloads.value = download_link(self.root, p.frozen_folder / "Challenge_4_Prueftabelle.xlsx", "Excel-Prüftabelle herunterladen") + "<br>" + download_link(self.root, path, "Vollständige ZIP-Abgabe herunterladen")
                return "ZIP und Excel erstellt. Download-Links unten anklicken. Eigenen Kurzbericht ergänzen."
            excel.on_click(self.action(status, export_excel))
            export.on_click(self.action(status, export_all))
            return [w.HTML('<p>Nur bestätigte menschliche Urteile bestimmen die Kennzahlen. '
                           'Solange Antworten oder Urteile fehlen, sind Erfolgsquoten offen. '
                           'In Schritt 5 prüfen und speichern; hier die Excel-Prüftabelle neu erstellen und herunterladen. '
                           'Sie enthält Fragen, Referenzen, Antworten, Belege, Vorprüfungen und menschliche Urteile. '
                           'Excel-Änderungen werden nicht zurückgelesen. Die ZIP-Abgabe enthält die Prüftabelle; eigenen Kurzbericht ergänzen.</p>'),
                    refresh, out, excel, export, status, downloads]
        self.section(render)
