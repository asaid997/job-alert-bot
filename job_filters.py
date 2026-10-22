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
    r"healthcare assistant|sonographer|technician|administrator|manager|"
    r"general\s+safety\s+officer|safety\s+evaluation\s+physician)\b",
    re.I,
)
OTHER_SPECIALTY = re.compile(
    r"\b(?:icu|itu|icm|intensive\s+care|critical\s+care|"
    r"orthodont(?:ics|ic|ist)|dent(?:al|ist|istry)|psychiatr(?:y|ic|ist))\b", re.I,
)
SENIOR_ROLE = re.compile(
    r"\bsenior\s+(?:clinical\s+(?:(?:research|teaching)\s+)?fellow|registrar)\b", re.I,
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
SPECIALTY_FIELD = re.compile(
    r"^[ \t]*(?:special(?:i)?ty|department|main area|job title|post title)"
    r"[ \t]*(?::[ \t]*|\n[ \t]*)([^\n]+)", re.I | re.M,
)
ROLE_SPECIALTY_CONTEXT = re.compile(
    r"\b(?:you|post[- ]?holder|successful candidate)\b"
    r"|\bjoin\b.{0,100}\b(?:team|department|service|unit)\b", re.I,
)


def has_og_role_evidence(title, description):
    """Require O&G in the role itself, not just the employer's list of services."""
    if SPECIALTY.search(title):
        return True
    for field in SPECIALTY_FIELD.finditer(description):
        if SPECIALTY.search(field.group(1)):
            return True
    for line in re.split(r"\n|;|(?<=[.!?])\s+", description):
        if SPECIALTY.search(line) and (
            DOCTOR_ROLE.search(line) or ROLE_LINE.search(line) or ROLE_SPECIALTY_CONTEXT.search(line)
        ):
            return True
    return False

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
GRADE_REQUIREMENT = re.compile(
    r"\b(?:completed?|completion|achieved?|satisfactory|arcp|competenc(?:e|ies)|equivalent)\b"
    r"|\b(?:st|ct)\s*\d+\s*(?:\+|and above\b|or above\b|level\b|experience\b|training\b)",
    re.I,
)
APPLICANT_REQUIREMENT = re.compile(
    r"\b(?:applicants?|candidates?|you)\b.{0,80}\b(?:must|should|need|require)\b"
    r"|^\s*(?:must|should|required to)\b", re.I,
)


def required_grade_minima(description):
    """Read applicant grade requirements without treating supervisors as applicants."""
    section = ""
    minima = []
    for raw_line in re.split(r"\n|;|(?<=[.!?])\s+", description):
        line = raw_line.strip(" \t•*-")
        if re.fullmatch(r"essential(?: criteria| requirements)?\s*:?", line, re.I):
            section = "essential"
        elif re.fullmatch(r"desirable(?: criteria| requirements)?\s*:?", line, re.I):
            section = "desirable"
        elif re.fullmatch(
            r"(?:qualifications|experience|aptitudes|interests|benefits|about us|"
            r"job description|main duties)\s*:?", line, re.I,
        ):
            section = ""
        grades = [int(match.group(1)) for match in GRADE.finditer(line)]
        if not grades or section == "desirable" or OPTIONAL.search(line):
            continue
        applicant_requirement = APPLICANT_REQUIREMENT.search(line)
        if not applicant_requirement and re.search(
            r"\b(?:work(?:ing)? with|supported by|supervised by|supervision|"
            r"colleagues|team includes)\b", line, re.I,
        ):
            continue
        required = (
            section == "essential" or REQUIRED.search(line)
            or re.search(r"\bby (?:the )?(?:commencement|start)\b", line, re.I)
        )
        if required and (applicant_requirement or GRADE_REQUIREMENT.search(line) or GRADE.fullmatch(line)):
            minima.append(min(grades))
    return minima


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


def assess_job(job, *, details_pending=False):
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
    other_specialty = OTHER_SPECIALTY.search(title)
    if other_specialty and not SPECIALTY.search(title):
        return "rejected", f"different specialty from O&G: {other_specialty.group()}"
    if not DOCTOR_ROLE.search(title) and not GRADE.search(title):
        return "rejected", "not an identified doctor role"

    # An explicit title grade takes priority over mentions of colleagues in the body.
    title_grades = [int(match.group(1)) for match in GRADE.finditer(title)]
    grades = title_grades or [int(match.group(1)) for match in GRADE.finditer(role_text)]
    if grades and min(grades) > MAX_ST_GRADE:
        return "rejected", "advertised starting grade is above ST3"
    required_grades = required_grade_minima(description)
    if required_grades and max(required_grades) > MAX_ST_GRADE:
        return "rejected", "mandatory applicant grade is above ST3"
    grades = grades or required_grades
    grade_known = bool(grades) or bool(JUNIOR_ROLE.search(title))
    if SENIOR_ROLE.search(title) and not grade_known and not details_pending:
        return "rejected", "senior role without confirmed SHO/ST1–ST3 eligibility"
    # Generic doctor titles can be fetched, but must establish O&G before alerting.
    if not has_og_role_evidence(title, description):
        if details_pending:
            return "review", "fetch description to confirm the role is in obstetrics/gynaecology"
        return "rejected", "obstetrics/gynaecology specialty not confirmed for this role"
    # A range beginning at ST3 (ST3+, ST3–5, ST3–8) remains in scope.
    grade_reason = f"ST{min(grades)} entry level" if grades else "SHO/junior clinical fellow level"
    if not grade_known:
        grade_reason = "grade unspecified; confirm SHO/ST1–ST3 suitability"

    experience_status, experience_reason = experience_requirement(description)
    if experience_status == "rejected":
        return experience_status, experience_reason
    if not grade_known or experience_status == "review":
        return "review", f"{grade_reason}; {experience_reason}"
    return "matched", f"O&G; {grade_reason}; {experience_reason}"
