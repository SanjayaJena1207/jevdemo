"""Random multiple-choice race questions (A-D) with a known answer, plus grading.

Every model sees the same question and the same four options. Chat models reply
with "ANSWER: <letter>"; decision models like Jev pick an option natively.
"""

from __future__ import annotations

import random
import re
from dataclasses import dataclass

LETTERS = "ABCD"

INSTRUCTIONS = (
    "Choose the correct option. Keep any explanation brief. "
    "End your reply with a final line in exactly this format:\n"
    "ANSWER: <letter>"
)


@dataclass
class Question:
    text: str
    category: str  # "math" | "trivia"
    options: dict[str, str]  # letter -> option text
    correct: str  # letter

    @property
    def answer(self) -> str:
        return f"{self.correct}) {self.options[self.correct]}"

    @property
    def prompt(self) -> str:
        opts = "\n".join(f"{k}) {v}" for k, v in self.options.items())
        return f"{self.text}\n\n{opts}\n\n{INSTRUCTIONS}"

    def public(self) -> dict:
        return {"text": self.text, "category": self.category, "options": self.options,
                "correct": self.correct, "answer": self.answer}


def _build(text: str, category: str, right: str, wrong: list[str]) -> Question:
    choices = [right, *random.sample(sorted(wrong), 3)]
    random.shuffle(choices)
    options = dict(zip(LETTERS, choices))
    return Question(text, category, options, LETTERS[choices.index(right)])


# (question, correct answer, plausible wrong answers)
TRIVIA: list[tuple[str, str, list[str]]] = [
    ("What is the chemical symbol for gold?", "Au", ["Ag", "Gd", "Go", "Ge"]),
    ("Which planet is known as the Red Planet?", "Mars", ["Venus", "Jupiter", "Mercury", "Saturn"]),
    ("What is the capital city of Australia?", "Canberra", ["Sydney", "Melbourne", "Perth", "Brisbane"]),
    ("Who wrote the play 'Romeo and Juliet'?", "William Shakespeare", ["Christopher Marlowe", "Charles Dickens", "Ben Jonson", "John Milton"]),
    ("What is the largest ocean on Earth?", "Pacific Ocean", ["Atlantic Ocean", "Indian Ocean", "Arctic Ocean", "Southern Ocean"]),
    ("In what year did the Apollo 11 mission land on the Moon?", "1969", ["1967", "1971", "1965", "1972"]),
    ("What is the hardest natural substance?", "Diamond", ["Quartz", "Titanium", "Corundum", "Graphite"]),
    ("How many sides does a hexagon have?", "6", ["5", "7", "8", "9"]),
    ("What gas do plants absorb from the atmosphere for photosynthesis?", "Carbon dioxide", ["Oxygen", "Nitrogen", "Hydrogen", "Methane"]),
    ("Which element has atomic number 1?", "Hydrogen", ["Helium", "Lithium", "Oxygen", "Carbon"]),
    ("What is the longest river in South America?", "Amazon", ["Paraná", "Orinoco", "Magdalena", "São Francisco"]),
    ("Who painted the Mona Lisa?", "Leonardo da Vinci", ["Michelangelo", "Raphael", "Sandro Botticelli", "Titian"]),
    ("What is the smallest prime number?", "2", ["1", "3", "0", "5"]),
    ("What is the capital of Canada?", "Ottawa", ["Toronto", "Montreal", "Vancouver", "Calgary"]),
    ("Which programming language was created by Guido van Rossum?", "Python", ["Ruby", "Perl", "Java", "JavaScript"]),
    ("What is the boiling point of water at sea level in degrees Celsius?", "100", ["90", "110", "212", "80"]),
    ("What is the currency of Japan?", "Yen", ["Won", "Yuan", "Ringgit", "Baht"]),
    ("Which organ in the human body produces insulin?", "Pancreas", ["Liver", "Kidney", "Spleen", "Gallbladder"]),
    ("How many continents are there on Earth?", "7", ["5", "6", "8", "9"]),
    ("What is the tallest mountain above sea level?", "Mount Everest", ["K2", "Kangchenjunga", "Mont Blanc", "Denali"]),
    ("Who developed the theory of general relativity?", "Albert Einstein", ["Isaac Newton", "Niels Bohr", "Max Planck", "Stephen Hawking"]),
    ("What is the capital of Kenya?", "Nairobi", ["Mombasa", "Kampala", "Addis Ababa", "Dar es Salaam"]),
    ("Which planet has the most prominent ring system?", "Saturn", ["Jupiter", "Uranus", "Neptune", "Mars"]),
    ("What is the main language spoken in Brazil?", "Portuguese", ["Spanish", "French", "English", "Italian"]),
    ("How many bits are in a byte?", "8", ["4", "16", "10", "32"]),
    ("What is the freezing point of water in degrees Fahrenheit?", "32", ["0", "20", "40", "212"]),
    ("Which country gifted the Statue of Liberty to the United States?", "France", ["United Kingdom", "Spain", "Italy", "Germany"]),
    ("Which blood cells carry oxygen around the body?", "Red blood cells", ["White blood cells", "Platelets", "Plasma cells", "Stem cells"]),
]


def _math_question() -> Question:
    kind = random.choice(["mul_add", "sub_mul", "square_sub", "percent"])
    if kind == "mul_add":
        a, b, c = random.randint(12, 99), random.randint(12, 99), random.randint(100, 999)
        text, ans = f"What is {a} * {b} + {c}?", a * b + c
        near = [a * b - c, a * (b + 1) + c, a * (b - 1) + c, ans + 10, ans - 10, ans + 100]
    elif kind == "sub_mul":
        a, b, c = random.randint(200, 999), random.randint(10, 99), random.randint(3, 19)
        text, ans = f"What is ({a} - {b}) * {c}?", (a - b) * c
        near = [a - b * c, (a + b) * c, (a - b) * (c + 1), ans + 10, ans - 10, ans + c]
    elif kind == "square_sub":
        a, b = random.randint(15, 60), random.randint(10, 500)
        text, ans = f"What is {a} squared minus {b}?", a * a - b
        near = [a * a + b, (a - 1) ** 2 - b, (a + 1) ** 2 - b, ans + 10, ans - 10, 2 * a - b]
    else:
        pct, base = random.choice([10, 15, 20, 25, 30, 40, 75]), random.randint(4, 60) * 20
        text, ans = f"What is {pct}% of {base}?", pct * base // 100
        near = [base * (pct + 5) // 100, base * (pct - 5) // 100, ans * 2, ans + 10, ans - 10, base - ans]
    wrong = {str(n) for n in near if n != ans}
    step = 1
    while len(wrong) < 3:  # tiny answers can collapse the distractors; pad with neighbours
        wrong.add(str(ans + step))
        step += 1
    return _build(text, "math", str(ans), wrong)


def random_question() -> Question:
    if random.random() < 0.5:
        return _math_question()
    text, right, wrong = random.choice(TRIVIA)
    return _build(text, "trivia", right, wrong)


# ---------- grading ----------

_ANSWER_RE = re.compile(r"answer\s*[:：]\s*(.+)", re.IGNORECASE)
_LETTER_RE = re.compile(r"^[\s(\[*_`\"']*([A-D])\b")


def extract_answer(content: str) -> str:
    """Take the last 'ANSWER: ...' line, else the last non-empty line."""
    text = re.sub(r"<think>.*?</think>", "", content, flags=re.DOTALL)
    matches = _ANSWER_RE.findall(text)
    if matches:
        ans = matches[-1]
    else:
        lines = [ln for ln in text.strip().splitlines() if ln.strip()]
        ans = lines[-1] if lines else ""
    return ans.strip().strip("*_`\"' .").strip()


def _norm(s: str) -> str:
    return " ".join(re.sub(r"[^a-z0-9.]+", " ", s.lower()).split())


def to_letter(q: Question, extracted: str) -> str | None:
    """Map a model's answer ("B", "(B)", "B) 144", or just "144") to an option letter."""
    if not extracted:
        return None
    m = _LETTER_RE.match(extracted)
    if m:
        return m.group(1)
    got = _norm(extracted)
    for letter, text in q.options.items():
        if _norm(text) == got:
            return letter
    return None


def is_correct(q: Question, letter: str | None) -> bool:
    return letter == q.correct
