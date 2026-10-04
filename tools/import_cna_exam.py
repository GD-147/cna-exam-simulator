#!/usr/bin/env python3

from pathlib import Path
import argparse
import json
import re
import sys
from collections import Counter

DOMAIN_CATEGORIES = {
    "Physical Care Skills": {
        "Activities of Daily Living",
        "Basic Nursing Skills",
        "Self Care/Independence",
    },
    "Psychosocial Care Skills": {
        "Emotional and Mental Health Needs",
        "Spiritual and Cultural Needs",
    },
    "Role of the Nurse Aide": {
        "Communication",
        "Client Rights",
        "Legal and Ethical Behavior",
        "Member of the Health Care Team",
    },
}

EXPECTED_SCORED = {
    "Activities of Daily Living": 13,
    "Basic Nursing Skills": 21,
    "Self Care/Independence": 4,
    "Emotional and Mental Health Needs": 5,
    "Spiritual and Cultural Needs": 1,
    "Communication": 4,
    "Client Rights": 5,
    "Legal and Ethical Behavior": 3,
    "Member of the Health Care Team": 4,
}

EXPECTED_UNSCORED = {
    "Activities of Daily Living": 2,
    "Basic Nursing Skills": 3,
    "Self Care/Independence": 1,
    "Emotional and Mental Health Needs": 1,
    "Spiritual and Cultural Needs": 0,
    "Communication": 1,
    "Client Rights": 1,
    "Legal and Ethical Behavior": 0,
    "Member of the Health Care Team": 1,
}

QID_RE = re.compile(r"^CNA(\d{2})-(\d{3})$")
KEY_RE = re.compile(
    r"^(CNA\d{2}-\d{3}), Correct: ([A-D]), Correct Answer: (.*?), Explanation: (.+)$"
)

def fail(errors, msg):
    errors.append(msg)

def parse_questions(lines, errors):
    try:
        start = lines.index("PART A, QUESTIONS") + 1
        end = lines.index("PART B, ANSWER KEY AND EXPLANATIONS")
    except ValueError:
        raise ValueError("Missing PART A or PART B marker")

    part = lines[start:end]
    questions = []
    i = 0

    while i < len(part):
        line = part[i].strip()

        if not line:
            i += 1
            continue

        if not QID_RE.match(line):
            fail(errors, f"Unexpected line in PART A: {line[:100]}")
            i += 1
            continue

        qid = line

        try:
            domain_line = part[i + 1].strip()
            category_line = part[i + 2].strip()
            type_line = part[i + 3].strip()
            unscored_line = part[i + 4].strip()
            scenario_line = part[i + 5].strip()
            context_label = part[i + 6].strip()
            context = part[i + 7].strip()
            prompt_label = part[i + 8].strip()
            prompt = part[i + 9].strip()
            option_lines = [part[i + 10 + x].strip() for x in range(4)]
        except IndexError:
            fail(errors, f"{qid}: incomplete question block")
            break

        required_prefixes = [
            ("Domain: ", domain_line),
            ("Category: ", category_line),
            ("Type: ", type_line),
            ("Unscored: ", unscored_line),
            ("Scenario-Based: ", scenario_line),
        ]

        for prefix, value in required_prefixes:
            if not value.startswith(prefix):
                fail(errors, f"{qid}: expected '{prefix.strip()}' field")

        if context_label != "Scenario Context:":
            fail(errors, f"{qid}: missing Scenario Context label")

        if prompt_label != "Prompt:":
            fail(errors, f"{qid}: missing Prompt label")

        domain = domain_line.removeprefix("Domain: ").strip()
        category = category_line.removeprefix("Category: ").strip()
        qtype = type_line.removeprefix("Type: ").strip()
        unscored_raw = unscored_line.removeprefix("Unscored: ").strip()
        scenario_raw = scenario_line.removeprefix("Scenario-Based: ").strip()

        if unscored_raw not in {"true", "false"}:
            fail(errors, f"{qid}: invalid Unscored value '{unscored_raw}'")

        if scenario_raw not in {"true", "false"}:
            fail(errors, f"{qid}: invalid Scenario-Based value '{scenario_raw}'")

        choices = {}
        for letter, opt in zip("ABCD", option_lines):
            prefix = f"{letter}) "
            if not opt.startswith(prefix):
                fail(errors, f"{qid}: malformed option {letter}")
                choices[letter] = ""
            else:
                choices[letter] = opt[len(prefix):].strip()

        questions.append({
            "id": qid,
            "domain": domain,
            "category": category,
            "type": qtype,
            "unscored": unscored_raw == "true",
            "scenarioBased": scenario_raw == "true",
            "scenarioContext": None if context == "None" else context,
            "prompt": prompt,
            "choices": choices,
        })

        i += 14

    return questions, end + 1

def parse_answer_key(lines, start, errors):
    answers = {}

    for raw in lines[start:]:
        line = raw.strip()

        if not line:
            continue

        m = KEY_RE.match(line)

        if not m:
            fail(errors, f"Malformed answer-key line: {line[:120]}")
            continue

        qid, letter, answer_text, explanation = m.groups()

        if qid in answers:
            fail(errors, f"Duplicate answer-key entry: {qid}")
            continue

        answers[qid] = {
            "correct": letter,
            "correctAnswer": answer_text.strip(),
            "explanation": explanation.strip(),
        }

    return answers

def validate(questions, answers, exam_num, errors):
    expected_ids = [
        f"CNA{exam_num}-{i:03d}"
        for i in range(1, 71)
    ]

    actual_ids = [q["id"] for q in questions]

    if len(questions) != 70:
        fail(errors, f"Expected 70 questions; found {len(questions)}")

    if actual_ids != expected_ids:
        fail(errors, "Question IDs are not exactly sequential CNAxx-001 through CNAxx-070")

    if len(set(actual_ids)) != len(actual_ids):
        fail(errors, "Duplicate question IDs found")

    if len(answers) != 70:
        fail(errors, f"Expected 70 answer-key entries; found {len(answers)}")

    scored = [q for q in questions if not q["unscored"]]
    unscored = [q for q in questions if q["unscored"]]

    if len(scored) != 60:
        fail(errors, f"Expected 60 scored questions; found {len(scored)}")

    if len(unscored) != 10:
        fail(errors, f"Expected 10 unscored questions; found {len(unscored)}")

    scenario_count = sum(q["scenarioBased"] for q in questions)

    if scenario_count < 39:
        fail(errors, f"Scenario-Based minimum is 39; found {scenario_count}")

    for q in questions:
        qid = q["id"]

        if q["type"] != "mcq":
            fail(errors, f"{qid}: Type must be mcq")

        if q["domain"] not in DOMAIN_CATEGORIES:
            fail(errors, f"{qid}: invalid Domain '{q['domain']}'")
        elif q["category"] not in DOMAIN_CATEGORIES[q["domain"]]:
            fail(
                errors,
                f"{qid}: Category '{q['category']}' does not belong to Domain '{q['domain']}'"
            )

        if set(q["choices"].keys()) != {"A", "B", "C", "D"}:
            fail(errors, f"{qid}: must have exactly A-D choices")

        if any(not text for text in q["choices"].values()):
            fail(errors, f"{qid}: blank answer choice")

        if len(set(q["choices"].values())) != 4:
            fail(errors, f"{qid}: duplicate answer-choice text")

        if q["scenarioBased"] and not q["scenarioContext"]:
            fail(errors, f"{qid}: Scenario-Based true but Scenario Context is missing")

        if not q["scenarioBased"] and q["scenarioContext"] is not None:
            fail(errors, f"{qid}: Scenario-Based false but Scenario Context is not None")

        if qid not in answers:
            fail(errors, f"{qid}: missing answer-key entry")
            continue

        key = answers[qid]
        letter = key["correct"]

        if letter not in q["choices"]:
            fail(errors, f"{qid}: invalid correct letter '{letter}'")
            continue

        if key["correctAnswer"] != q["choices"][letter]:
            fail(
                errors,
                f"{qid}: Correct Answer text does not exactly match option {letter}"
            )

        if not key["explanation"]:
            fail(errors, f"{qid}: explanation is empty")

    scored_counts = Counter(q["category"] for q in scored)
    unscored_counts = Counter(q["category"] for q in unscored)

    for category, expected in EXPECTED_SCORED.items():
        actual = scored_counts.get(category, 0)
        if actual != expected:
            fail(
                errors,
                f"{category}: scored count {actual}, expected {expected}"
            )

    for category, expected in EXPECTED_UNSCORED.items():
        actual = unscored_counts.get(category, 0)
        if actual != expected:
            fail(
                errors,
                f"{category}: unscored count {actual}, expected {expected}"
            )

    answer_letters = [
        answers[q["id"]]["correct"]
        for q in questions
        if q["id"] in answers
    ]

    dist = Counter(answer_letters)

    if sorted(dist.values()) != [17, 17, 18, 18]:
        fail(
            errors,
            "Correct-answer distribution must be 18/18/17/17; "
            f"found A={dist['A']} B={dist['B']} C={dist['C']} D={dist['D']}"
        )

    run = 1
    for i in range(1, len(answer_letters)):
        if answer_letters[i] == answer_letters[i - 1]:
            run += 1
            if run > 3:
                fail(
                    errors,
                    f"Correct answer {answer_letters[i]} appears more than 3 times consecutively"
                )
                break
        else:
            run = 1

    return scored_counts, unscored_counts, scenario_count, dist

def build_json(questions, answers):
    output = []

    for q in questions:
        key = answers[q["id"]]

        item = {
            "id": q["id"],
            "prompt": q["prompt"],
            "choices": q["choices"],
            "correct": key["correct"],
            "explanation": key["explanation"],
            "domain": q["domain"],
            "category": q["category"],
            "unscored": q["unscored"],
            "scenarioBased": q["scenarioBased"],
        }

        if q["scenarioContext"]:
            item["scenarioContext"] = q["scenarioContext"]

        output.append(item)

    return output

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("source")
    parser.add_argument("--validate-only", action="store_true")
    parser.add_argument(
        "--output-dir",
        default="packs/cna/data"
    )
    args = parser.parse_args()

    source = Path(args.source)

    m = re.fullmatch(r"cna_exam_(\d{2})\.txt", source.name)
    if not m:
        print("ERROR: filename must be cna_exam_XX.txt", file=sys.stderr)
        sys.exit(1)

    exam_num = m.group(1)

    text = source.read_text(encoding="utf-8")
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = text.split("\n")

    errors = []

    expected_title = f"CNA Practice Exam {exam_num}"
    first_nonblank = next((x.strip() for x in lines if x.strip()), "")

    if first_nonblank != expected_title:
        fail(
            errors,
            f"Title must be exactly '{expected_title}'; found '{first_nonblank}'"
        )

    try:
        questions, answer_start = parse_questions(lines, errors)
        answers = parse_answer_key(lines, answer_start, errors)
    except Exception as e:
        print(f"INVALID | {source.name}")
        print(f"- {e}")
        sys.exit(1)

    scored_counts, unscored_counts, scenario_count, dist = validate(
        questions,
        answers,
        exam_num,
        errors
    )

    if errors:
        print(f"INVALID | {source.name}")
        print()
        for err in errors:
            print(f"- {err}")
        sys.exit(1)

    print(f"VALID | {source.name}")
    print(f"Total: {len(questions)}")
    print(f"Scored: {sum(not q['unscored'] for q in questions)}")
    print(f"Unscored: {sum(q['unscored'] for q in questions)}")
    print(f"Scenario-Based: {scenario_count}")
    print(
        "Answers: "
        f"A={dist['A']} B={dist['B']} C={dist['C']} D={dist['D']}"
    )

    print()
    print("Category counts:")
    for category in EXPECTED_SCORED:
        print(
            f"- {category}: "
            f"{scored_counts.get(category, 0)} scored + "
            f"{unscored_counts.get(category, 0)} unscored"
        )

    if args.validate_only:
        print()
        print("VALIDATION ONLY — no JSON created")
        return

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    output_path = output_dir / f"cna_exam_{exam_num}.json"
    payload = build_json(questions, answers)

    output_path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8"
    )

    print()
    print(f"CREATED: {output_path}")
    print(f"Questions: {len(payload)}")
    print(f"IDs: {payload[0]['id']} -> {payload[-1]['id']}")

if __name__ == "__main__":
    main()
