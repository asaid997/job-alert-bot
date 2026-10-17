"""Conservative O&G filters: SHO/ST1–ST3 and advertised experience of 0–5 years."""

import re

MAX_EXPERIENCE_YEARS = 5
MAX_ST_GRADE = 3

SPECIALTY = re.compile(
    r"\b(?:obstetrics?|gyn(?:a?ecology|a?ecological|ae|ec)|obgyn|ob-gyn)\b"
    r"|\bo\s*(?:&|and|/)\s*g\b|\bobs\s*(?:&|and|/)\s*gyn(?:ae)?\b",
    re.I,
)
DOCTOR_ROLE = re.compile(
    r"\b(?:doctor|clinical fellow|clinical research fellow|clinical teaching fellow|"
    r"trust grade|sho|senior house officer|registrar|physician|resident)\b",
    re.I,
)
EXCLUDED_ROLE = re.compile(
    r"\b(?:consultant|specialist grade|specialist doctor|associate specialist|"
    r"clinical lead|clinical director|head of|professor|nurse|nursing|midwife|"
    r"midwifery|midwives|practitioner|physician associate|physician assistant|"
    r"healthcare assistant|sonographer|technician|administrator|manager)\b",
    re.I,
)
GRADE = re.compile(
    r"\b(?:st|ct)\s*(\d+)"
    r"(?:\s*(?:-|/|to|–|—)\s*(?:st|ct)?\s*(\d+))?",
    re.I,
)
JUNIOR_ROLE = re.compile(r"\b(?:sho|senior house officer|junior clinical fellow)\b", re.I)
ROLE_LINE = re.compile(
    r"^\s*(?:job title|post title|grade)\s*:"
    r"|\b(?:this|the)\s+(?:post|role|position)\s+(?:is|will be)\b"
    r"|\b(?:post|role|position)\s+(?:at|equivalent to)\s+st\s*\d",
    re.I,
)

NUMBERS = {
    "zero": 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
    "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
    "eleven": 11, "twelve": 12,
}
NUMBER = r"(?:\d+(?:\.\d+)?|" + "|".join(NUMBERS) + r")"
EXPERIENCE = re.compile(
    rf"\b(?P<lower>{NUMBER})"
    rf"(?:\s*(?:-|–|—|to)\s*(?P<upper>{NUMBER}))?\s*\+?\s*"
    r"(?P<unit>years?|months?)\b[’']?\s*"
    r"(?:(?:of|full[- ]time|post[- ]?graduate|post[- ]?qualification|clinical|"
    r"medical|relevant|previous|nhs|uk|og|o&g|obstetrics?|and|&|gyna?ecology|"
    r"specialty|speciality|equivalent)\s+){0,10}"
    r"(?:experience|training|practice)\b",
    re.I,
)
REQUIRED = re.compile(
    r"\b(?:essential|required|require|requires|minimum|at least|must|need|"
    r"should have|will have|more than|over)\b", re.I,
)
OPTIONAL = re.compile(
    r"\b(?:desirable|preferred|preferable|ideally|advantage|not essential|not required|not necessary)\b",
    re.I,
)


def experience_requirement(description):
    """Only reject explicit mandatory minima; ambiguous/preferred experience needs review."""
    section = ""
    minima = []
    uncertain = False
    for line in re.split(r"\n|;|(?<=[.!?])\s+", description):
        line = line.strip()
        if re.fullmatch(r"essential(?: criteria| requirements)?\s*:?", line, re.I):
            section = "essential"
        elif re.fullmatch(r"desirable(?: criteria| requirements)?\s*:?", line, re.I):
            section = "desirable"
        elif re.fullmatch(r"(?:benefits|about us|job description|main duties|qualifications|experience)\s*:?", line, re.I):
            section = ""
        if re.search(r"\bno (?:previous |prior )?experience (?:is )?(?:required|necessary)\b", line, re.I):
            minima.append(0)
        for match in EXPERIENCE.finditer(line):
            if OPTIONAL.search(line) or section == "desirable":
                uncertain = True
                continue
            if not (section == "essential" or REQUIRED.search(line)):
                uncertain = True
                continue
            raw = match.group("lower").lower()
            minimum = NUMBERS[raw] if raw in NUMBERS else float(raw)
            if match.group("unit").lower().startswith("month"):
                minimum /= 12
            strict_minimum = bool(re.search(r"(?:more than|over)\s*$", line[:match.start()], re.I))
            if minimum > MAX_EXPERIENCE_YEARS or (strict_minimum and minimum >= MAX_EXPERIENCE_YEARS):
                return "rejected", f"required experience exceeds 5 years: {line[:180]}"
            minima.append(minimum)
    if minima and not uncertain:
        return "matched", f"stated minimum experience {max(minima):g} years (target 0–5)"
    return "review", "experience requirement unclear or not stated; check against 0–5 years"


def assess_job(job):
    """Return matched/review/rejected plus an explanation, never assume ANIOS equivalence."""
    title = job.get("title") or ""
    description = job.get("description") or ""
    role_lines = [line for line in description.splitlines() if ROLE_LINE.search(line)]
    role_text = "\n".join([title, job.get("grade") or "", *role_lines])

    if job.get("closed"):
        return "rejected", "applications are closed"
    excluded = EXCLUDED_ROLE.search(title)
    if excluded:
        return "rejected", f"excluded role: {excluded.group()}"
    if not DOCTOR_ROLE.search(title) and not GRADE.search(title):
        return "rejected", "not an identified doctor role"

    # An explicit title grade takes priority over mentions of colleagues in the body.
    title_grades = [int(match.group(1)) for match in GRADE.finditer(title)]
    grades = title_grades or [int(match.group(1)) for match in GRADE.finditer(role_text)]
    if grades and min(grades) > MAX_ST_GRADE:
        return "rejected", "advertised starting grade is above ST3"
    # The actual role must be O&G; an NHS employer name or search term is not evidence.
    if not SPECIALTY.search(title + "\n" + description):
        if not description:
            return "review", "description unavailable; confirm O&G specialty, grade and 0–5 years experience"
        return "rejected", "no obstetrics/gynaecology signal in the advert"
    # A range beginning at ST3 (ST3+, ST3–5, ST3–8) remains in scope.
    grade_known = bool(grades) or bool(JUNIOR_ROLE.search(title))
    grade_reason = f"ST{min(grades)} entry level" if grades else "SHO/junior clinical fellow level"
    if not grade_known:
        grade_reason = "grade unspecified; confirm SHO/ST1–ST3 suitability"

    experience_status, experience_reason = experience_requirement(description)
    if experience_status == "rejected":
        return experience_status, experience_reason
    if not grade_known or experience_status == "review":
        return "review", f"{grade_reason}; {experience_reason}"
    return "matched", f"O&G; {grade_reason}; {experience_reason}"
