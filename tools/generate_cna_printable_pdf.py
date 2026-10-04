#!/usr/bin/env python3

from pathlib import Path
import argparse
import json
import re
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    PageBreak,
    KeepTogether,
)

NAVY = colors.HexColor("#173F6D")
TEXT = colors.HexColor("#202B3A")
MUTED = colors.HexColor("#58697B")
LIGHT_BOX = colors.HexColor("#F1F4F7")
BORDER = colors.HexColor("#CDD6DF")
WHITE = colors.white

PAGE_W, PAGE_H = letter


def clean(text):
    return escape(str(text or ""))


def exam_number(path):
    m = re.search(r"cna_exam_(\d{2})", Path(path).stem)
    if not m:
        raise SystemExit("ERROR: expected filename like cna_exam_01.json")
    return m.group(1)


def draw_page(canvas, doc):
    canvas.saveState()

    canvas.setFont("Helvetica-Bold", 8.5)
    canvas.setFillColor(MUTED)
    canvas.drawString(
        0.60 * inch,
        PAGE_H - 0.42 * inch,
        "HEALTH BEACON | CNA EXAM PREP"
    )

    canvas.setStrokeColor(BORDER)
    canvas.setLineWidth(0.6)
    canvas.line(
        0.60 * inch,
        PAGE_H - 0.54 * inch,
        PAGE_W - 0.60 * inch,
        PAGE_H - 0.54 * inch
    )

    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(MUTED)
    canvas.drawRightString(
        PAGE_W - 0.60 * inch,
        0.28 * inch,
        f"Page {doc.page}"
    )

    canvas.restoreState()


def build_pdf(input_json, output_pdf):
    input_json = Path(input_json)
    output_pdf = Path(output_pdf)

    questions = json.loads(input_json.read_text(encoding="utf-8"))

    if not isinstance(questions, list) or len(questions) != 70:
        raise SystemExit(
            f"ERROR: expected exactly 70 questions; found "
            f"{len(questions) if isinstance(questions, list) else 'non-list JSON'}"
        )

    num = exam_number(input_json)

    output_pdf.parent.mkdir(parents=True, exist_ok=True)

    doc = SimpleDocTemplate(
        str(output_pdf),
        pagesize=letter,
        leftMargin=0.68 * inch,
        rightMargin=0.68 * inch,
        topMargin=0.82 * inch,
        bottomMargin=0.55 * inch,
        title=f"CNA Practice Exam {num}",
        author="Health Beacon",
        subject="CNA Exam Prep Printable Practice Exam",
    )

    title_brand = ParagraphStyle(
        "title_brand",
        fontName="Helvetica-Bold",
        fontSize=13,
        leading=16,
        alignment=TA_CENTER,
        textColor=TEXT,
        spaceAfter=8,
    )

    title_main = ParagraphStyle(
        "title_main",
        fontName="Helvetica-Bold",
        fontSize=21,
        leading=24,
        alignment=TA_CENTER,
        textColor=NAVY,
        spaceAfter=9,
    )

    title_exam = ParagraphStyle(
        "title_exam",
        fontName="Helvetica-Bold",
        fontSize=14,
        leading=17,
        alignment=TA_CENTER,
        textColor=TEXT,
        spaceAfter=8,
    )

    subtitle = ParagraphStyle(
        "subtitle",
        fontName="Helvetica",
        fontSize=10.5,
        leading=14,
        alignment=TA_CENTER,
        textColor=MUTED,
        spaceAfter=16,
    )

    part_heading = ParagraphStyle(
        "part_heading",
        fontName="Helvetica-Bold",
        fontSize=16,
        leading=19,
        textColor=NAVY,
        spaceBefore=8,
        spaceAfter=12,
    )

    qnum_style = ParagraphStyle(
        "qnum",
        fontName="Helvetica-Bold",
        fontSize=10.8,
        leading=13,
        textColor=NAVY,
        spaceAfter=5,
    )

    scenario_label = ParagraphStyle(
        "scenario_label",
        fontName="Helvetica-Bold",
        fontSize=9.4,
        leading=11,
        textColor=MUTED,
        spaceAfter=3,
    )

    scenario_text = ParagraphStyle(
        "scenario_text",
        fontName="Helvetica",
        fontSize=9.8,
        leading=12.5,
        textColor=TEXT,
    )

    prompt_style = ParagraphStyle(
        "prompt",
        fontName="Helvetica-Bold",
        fontSize=10,
        leading=13,
        textColor=TEXT,
        spaceAfter=5,
    )

    option_style = ParagraphStyle(
        "option",
        fontName="Helvetica",
        fontSize=9.8,
        leading=12.5,
        textColor=TEXT,
        leftIndent=0,
        spaceAfter=2,
    )

    instruction_label = ParagraphStyle(
        "instruction_label",
        fontName="Helvetica",
        fontSize=10,
        leading=13,
        textColor=TEXT,
    )

    instruction_text = ParagraphStyle(
        "instruction_text",
        fontName="Helvetica",
        fontSize=10,
        leading=13,
        textColor=TEXT,
    )

    part_b_intro = ParagraphStyle(
        "part_b_intro",
        fontName="Helvetica",
        fontSize=9.5,
        leading=12,
        textColor=MUTED,
        spaceAfter=12,
    )

    answer_head = ParagraphStyle(
        "answer_head",
        fontName="Helvetica-Bold",
        fontSize=9.8,
        leading=12.5,
        textColor=NAVY,
        spaceAfter=3,
    )

    answer_body = ParagraphStyle(
        "answer_body",
        fontName="Helvetica",
        fontSize=9.6,
        leading=12.5,
        textColor=TEXT,
        spaceAfter=10,
    )

    story = []

    story.append(Spacer(1, 0.22 * inch))
    story.append(Paragraph("HEALTH BEACON", title_brand))
    story.append(Paragraph("CNA EXAM PREP", title_main))
    story.append(Paragraph(f"Practice Exam {num}", title_exam))
    story.append(
        Paragraph(
            "70 practice questions | Printable Practice Exam",
            subtitle
        )
    )

    instruction_table = Table(
        [[
            Paragraph("Instructions", instruction_label),
            Paragraph(
                "Select the single best answer for each question. "
                "An answer key with explanations begins after the question section.",
                instruction_text
            )
        ]],
        colWidths=[1.02 * inch, 5.38 * inch],
        hAlign="CENTER",
    )

    instruction_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), LIGHT_BOX),
        ("BOX", (0, 0), (-1, -1), 0.6, BORDER),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))

    story.append(instruction_table)
    story.append(Spacer(1, 0.13 * inch))
    story.append(Paragraph("PART A - QUESTIONS", part_heading))

    for idx, q in enumerate(questions, start=1):
        block = []

        block.append(Paragraph(f"{idx}.", qnum_style))

        scenario = q.get("scenarioContext", "")
        if scenario:
            block.append(Paragraph("Scenario", scenario_label))

            scenario_box = Table(
                [[Paragraph(clean(scenario), scenario_text)]],
                colWidths=[6.38 * inch],
                hAlign="LEFT",
            )

            scenario_box.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), LIGHT_BOX),
                ("BOX", (0, 0), (-1, -1), 0.5, BORDER),
                ("LEFTPADDING", (0, 0), (-1, -1), 7),
                ("RIGHTPADDING", (0, 0), (-1, -1), 7),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]))

            block.append(scenario_box)
            block.append(Spacer(1, 4))

        block.append(
            Paragraph(clean(q.get("prompt", "")), prompt_style)
        )

        choices = q.get("choices", {})

        for choice_letter in ["A", "B", "C", "D"]:
            block.append(
                Paragraph(
                    f"{choice_letter}) {clean(choices.get(choice_letter, ''))}",
                    option_style
                )
            )

        block.append(Spacer(1, 8))

        story.append(KeepTogether(block))

    story.append(PageBreak())
    story.append(Paragraph(
        "PART B - ANSWER KEY AND EXPLANATIONS",
        part_heading
    ))
    story.append(
        Paragraph(
            "Question numbering below corresponds to the questions in Part A.",
            part_b_intro
        )
    )

    answer_pairs = []
    for idx, q in enumerate(questions, start=1):
        answer_pairs.append((str(idx), q["correct"]))

    table_rows = []
    for i in range(0, len(answer_pairs), 5):
        row = []
        for n, answer_letter in answer_pairs[i:i + 5]:
            row.extend([n, answer_letter])

        while len(row) < 10:
            row.extend(["", ""])

        table_rows.append(row)

    answer_table = Table(
        table_rows,
        colWidths=[
            0.38 * inch, 0.44 * inch,
            0.38 * inch, 0.44 * inch,
            0.38 * inch, 0.44 * inch,
            0.38 * inch, 0.44 * inch,
            0.38 * inch, 0.44 * inch,
        ],
        hAlign="CENTER",
    )

    answer_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F7F9FB")),
        ("GRID", (0, 0), (-1, -1), 0.45, BORDER),
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), 8.6),
        ("TEXTCOLOR", (0, 0), (-1, -1), MUTED),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))

    story.append(answer_table)
    story.append(Spacer(1, 0.20 * inch))

    for idx, q in enumerate(questions, start=1):
        correct = q["correct"]
        correct_text = q["choices"][correct]

        story.append(
            Paragraph(
                f"{idx}. Correct: {correct} - {clean(correct_text)}",
                answer_head
            )
        )

        story.append(
            Paragraph(
                clean(q.get("explanation", "")),
                answer_body
            )
        )

    doc.build(
        story,
        onFirstPage=draw_page,
        onLaterPages=draw_page,
    )

    print(f"CREATED: {output_pdf}")
    print(f"Questions: {len(questions)}")
    print(f"Exam: {num}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("input_json")
    parser.add_argument("output_pdf")
    args = parser.parse_args()

    build_pdf(args.input_json, args.output_pdf)


if __name__ == "__main__":
    main()
