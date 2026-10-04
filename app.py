from flask import Flask, render_template, request, jsonify
import json
import os
import random


# ============================================================
# FLASK APP
# ============================================================

app = Flask(__name__)


# ============================================================
# FILE PATHS
# ============================================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

QUESTIONS_FILE = os.path.join(
    BASE_DIR,
    "data",
    "questions.json"
)

QUESTIONS_FILE = os.path.join(
    BASE_DIR,
    "data",
    "questions_bank_allstages_v389_launch_candidate.json"
)


# ============================================================
# LOAD CURRICULUM
# ============================================================

def load_curriculum():
    try:
        with open(CURRICULUM_FILE, "r", encoding="utf-8") as file:
            data = json.load(file)

        print("Curriculum loaded successfully")

        return data

    except FileNotFoundError:
        print("WARNING: curriculum.json not found")
        return {}

    except json.JSONDecodeError as error:
        print("ERROR: curriculum.json is not valid JSON")
        print(error)
        return {}

    except Exception as error:
        print("ERROR while loading curriculum")
        print(error)
        return {}


# ============================================================
# LOAD QUESTIONS BANK
# ============================================================

def load_questions_bank():
    try:
        with open(QUESTIONS_FILE, "r", encoding="utf-8") as file:
            data = json.load(file)

        if isinstance(data, dict):
            questions = data.get("questions", [])

        elif isinstance(data, list):
            questions = data

        else:
            questions = []

        print("Questions bank loaded successfully")
        print("Questions count:", len(questions))

        return questions

    except FileNotFoundError:
        print("ERROR: Questions bank file not found")
        print(QUESTIONS_FILE)
        return []

    except json.JSONDecodeError as error:
        print("ERROR: Questions bank JSON is invalid")
        print(error)
        return []

    except Exception as error:
        print("ERROR while loading questions bank")
        print(error)
        return []


# ============================================================
# LOAD DATA
# ============================================================

curriculum_data = load_curriculum()
questions_bank = load_questions_bank()


# ============================================================
# HELPERS
# ============================================================

def clean_value(value):
    if value is None:
        return ""

    return str(value).strip()


def safe_int(value, default=0):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def get_request_data():
    if request.is_json:
        return request.get_json(silent=True) or {}

    return request.form


def get_first_value(data, names, default=None):
    for name in names:
        try:
            value = data.get(name)

            if value is not None and value != "":
                return value

        except Exception:
            pass

    return default


# ============================================================
# FILTER QUESTIONS
# ============================================================

def get_questions(
    stage=None,
    grade=None,
    term=None,
    subject=None,
    unit=None,
    lessons=None,
    question_type=None,
    difficulty=None
):

    if lessons is None:
        lessons = []

    if isinstance(lessons, str):
        lessons = [lessons]

    cleaned_lessons = [
        clean_value(item)
        for item in lessons
        if clean_value(item)
    ]

    results = []

    for question in questions_bank:

        if stage:
            if clean_value(question.get("stage")) != clean_value(stage):
                continue

        if grade:
            if clean_value(question.get("grade")) != clean_value(grade):
                continue

        if term:
            if clean_value(question.get("term")) != clean_value(term):
                continue

        if subject:
            if clean_value(question.get("subject")) != clean_value(subject):
                continue

        if unit:
            if clean_value(question.get("unit")) != clean_value(unit):
                continue

        if cleaned_lessons:
            if clean_value(question.get("lesson")) not in cleaned_lessons:
                continue

        if question_type:
            if clean_value(question.get("type")) != clean_value(question_type):
                continue

        if difficulty:
            if clean_value(question.get("difficulty")) != clean_value(difficulty):
                continue

        results.append(question)

    return results


# ============================================================
# HOME PAGE
# ============================================================

@app.route("/")
def index():
    return render_template(
        "index.html",
        data=curriculum_data
    )


# ============================================================
# HEALTH CHECK
# ============================================================

@app.route("/health")
def health():
    return jsonify({
        "status": "ok",
        "questions_count": len(questions_bank)
    })


# ============================================================
# QUESTIONS BANK TEST
# ============================================================

@app.route("/test-questions")
def test_questions():

    return jsonify({
        "status": "ok",
        "total_questions": len(questions_bank),
        "sample": questions_bank[:5]
    })


# ============================================================
# BANK STATISTICS
# ============================================================

@app.route("/api/stats")
def api_stats():

    stages = {}

    for question in questions_bank:

        stage = clean_value(
            question.get("stage")
        )

        if not stage:
            stage = "unknown"

        stages[stage] = stages.get(stage, 0) + 1

    return jsonify({
        "total_questions": len(questions_bank),
        "stages": stages
    })


# ============================================================
# STAGES
# ============================================================

@app.route("/api/stages")
def api_stages():

    values = []
    seen = set()

    for question in questions_bank:

        value = clean_value(
            question.get("stage")
        )

        if value and value not in seen:
            seen.add(value)
            values.append(value)

    return jsonify(values)


# ============================================================
# GRADES
# ============================================================

@app.route("/api/grades")
def api_grades():

    stage = request.args.get(
        "stage",
        ""
    )

    values = []
    seen = set()

    for question in questions_bank:

        if clean_value(
            question.get("stage")
        ) != clean_value(stage):
            continue

        value = clean_value(
            question.get("grade")
        )

        if value and value not in seen:
            seen.add(value)
            values.append(value)

    return jsonify(values)


# ============================================================
# TERMS
# ============================================================

@app.route("/api/terms")
def api_terms():

    stage = request.args.get(
        "stage",
        ""
    )

    grade = request.args.get(
        "grade",
        ""
    )

    values = []
    seen = set()

    for question in questions_bank:

        if clean_value(
            question.get("stage")
        ) != clean_value(stage):
            continue

        if clean_value(
            question.get("grade")
        ) != clean_value(grade):
            continue

        value = clean_value(
            question.get("term")
        )

        if value and value not in seen:
            seen.add(value)
            values.append(value)

    return jsonify(values)


# ============================================================
# SUBJECTS
# ============================================================

@app.route("/api/subjects")
def api_subjects():

    stage = request.args.get(
        "stage",
        ""
    )

    grade = request.args.get(
        "grade",
        ""
    )

    term = request.args.get(
        "term",
        ""
    )

    values = []
    seen = set()

    for question in questions_bank:

        if clean_value(
            question.get("stage")
        ) != clean_value(stage):
            continue

        if clean_value(
            question.get("grade")
        ) != clean_value(grade):
            continue

        if clean_value(
            question.get("term")
        ) != clean_value(term):
            continue

        value = clean_value(
            question.get("subject")
        )

        if value and value not in seen:
            seen.add(value)
            values.append(value)

    return jsonify(values)


# ============================================================
# UNITS
# ============================================================

@app.route("/api/units")
def api_units():

    stage = request.args.get(
        "stage",
        ""
    )

    grade = request.args.get(
        "grade",
        ""
    )

    term = request.args.get(
        "term",
        ""
    )

    subject = request.args.get(
        "subject",
        ""
    )

    values = []
    seen = set()

    for question in questions_bank:

        if clean_value(
            question.get("stage")
        ) != clean_value(stage):
            continue

        if clean_value(
            question.get("grade")
        ) != clean_value(grade):
            continue

        if clean_value(
            question.get("term")
        ) != clean_value(term):
            continue

        if clean_value(
            question.get("subject")
        ) != clean_value(subject):
            continue

        value = clean_value(
            question.get("unit")
        )

        if value and value not in seen:
            seen.add(value)
            values.append(value)

    return jsonify(values)


# ============================================================
# LESSONS
# ============================================================

@app.route("/api/lessons")
def api_lessons():

    stage = request.args.get(
        "stage",
        ""
    )

    grade = request.args.get(
        "grade",
        ""
    )

    term = request.args.get(
        "term",
        ""
    )

    subject = request.args.get(
        "subject",
        ""
    )

    unit = request.args.get(
        "unit",
        ""
    )

    values = []
    seen = set()

    for question in questions_bank:

        if clean_value(
            question.get("stage")
        ) != clean_value(stage):
            continue

        if clean_value(
            question.get("grade")
        ) != clean_value(grade):
            continue

        if clean_value(
            question.get("term")
        ) != clean_value(term):
            continue

        if clean_value(
            question.get("subject")
        ) != clean_value(subject):
            continue

        if unit:
            if clean_value(
                question.get("unit")
            ) != clean_value(unit):
                continue

        value = clean_value(
            question.get("lesson")
        )

        if value and value not in seen:
            seen.add(value)
            values.append(value)

    return jsonify(values)


# ============================================================
# QUESTIONS PREVIEW
# ============================================================

@app.route(
    "/api/questions",
    methods=["GET", "POST"]
)
def api_questions():

    if request.method == "POST":
        data = get_request_data()
    else:
        data = request.args

    stage = get_first_value(
        data,
        ["stage"]
    )

    grade = get_first_value(
        data,
        ["grade"]
    )

    term = get_first_value(
        data,
        ["term", "semester"]
    )

    subject = get_first_value(
        data,
        ["subject"]
    )

    unit = get_first_value(
        data,
        ["unit"]
    )

    difficulty = get_first_value(
        data,
        ["difficulty"]
    )

    question_type = get_first_value(
        data,
        ["type", "question_type"]
    )

    lessons = []

    if request.method == "GET":

        lessons = request.args.getlist(
            "lesson"
        )

        if not lessons:
            lessons = request.args.getlist(
                "lessons"
            )

    elif request.is_json:

        lessons = data.get(
            "lessons",
            []
        )

        if isinstance(lessons, str):
            lessons = [lessons]

        if not lessons:

            lesson = data.get(
                "lesson"
            )

            if lesson:
                lessons = [lesson]

    else:

        lessons = request.form.getlist(
            "lessons"
        )

        if not lessons:
            lessons = request.form.getlist(
                "lesson"
            )

    results = get_questions(
        stage=stage,
        grade=grade,
        term=term,
        subject=subject,
        unit=unit,
        lessons=lessons,
        question_type=question_type,
        difficulty=difficulty
    )

    return jsonify({
        "status": "ok",
        "count": len(results),
        "questions": results
    })


# ============================================================
# GENERATE TEST
#
# Multiple routes are supported so the old interface can
# continue working.
# ============================================================

@app.route(
    "/api/generate-test",
    methods=["POST"]
)
@app.route(
    "/generate-test",
    methods=["POST"]
)
@app.route(
    "/create-test",
    methods=["POST"]
)
@app.route(
    "/generate",
    methods=["POST"]
)
@app.route(
    "/generate_exam",
    methods=["POST"]
)
@app.route(
    "/create_exam",
    methods=["POST"]
)
def generate_test():

    data = get_request_data()

    stage = get_first_value(
        data,
        [
            "stage",
            "education_stage"
        ]
    )

    grade = get_first_value(
        data,
        [
            "grade",
            "class",
            "school_grade"
        ]
    )

    term = get_first_value(
        data,
        [
            "term",
            "semester"
        ]
    )

    subject = get_first_value(
        data,
        [
            "subject"
        ]
    )

    unit = get_first_value(
        data,
        [
            "unit"
        ]
    )

    lessons = []

    if request.is_json:

        lessons = data.get(
            "lessons",
            []
        )

        if isinstance(lessons, str):
            lessons = [lessons]

        if not lessons:

            lesson = data.get(
                "lesson"
            )

            if lesson:
                lessons = [lesson]

    else:

        lessons = request.form.getlist(
            "lessons"
        )

        if not lessons:

            lessons = request.form.getlist(
                "lesson"
            )

        if not lessons:

            lesson = request.form.get(
                "lesson"
            )

            if lesson:
                lessons = [lesson]

    mcq_count = safe_int(
        get_first_value(
            data,
            [
                "mcq_count",
                "multiple_choice_count",
                "choice_count"
            ],
            0
        )
    )

    tf_count = safe_int(
        get_first_value(
            data,
            [
                "tf_count",
                "true_false_count"
            ],
            0
        )
    )

    fill_count = safe_int(
        get_first_value(
            data,
            [
                "fill_count",
                "fill_blank_count"
            ],
            0
        )
    )

    # Default question numbers if the old interface
    # does not send counts.
    if (
        mcq_count == 0
        and tf_count == 0
        and fill_count == 0
    ):
        mcq_count = 5
        tf_count = 5
        fill_count = 5

    if not stage:
        return jsonify({
            "status": "error",
            "message": "يرجى اختيار المرحلة التعليمية"
        }), 400

    if not grade:
        return jsonify({
            "status": "error",
            "message": "يرجى اختيار الصف"
        }), 400

    if not term:
        return jsonify({
            "status": "error",
            "message": "يرجى اختيار الفصل الدراسي"
        }), 400

    if not subject:
        return jsonify({
            "status": "error",
            "message": "يرجى اختيار المادة"
        }), 400

    selected_questions = []

    # --------------------------------------------------------
    # MULTIPLE CHOICE
    # --------------------------------------------------------

    if mcq_count > 0:

        available = get_questions(
            stage=stage,
            grade=grade,
            term=term,
            subject=subject,
            unit=unit,
            lessons=lessons,
            question_type="mcq"
        )

        random.shuffle(available)

        selected_questions.extend(
            available[:mcq_count]
        )

    # --------------------------------------------------------
    # TRUE / FALSE
    # --------------------------------------------------------

    if tf_count > 0:

        available = get_questions(
            stage=stage,
            grade=grade,
            term=term,
            subject=subject,
            unit=unit,
            lessons=lessons,
            question_type="tf"
        )

        random.shuffle(available)

        selected_questions.extend(
            available[:tf_count]
        )

    # --------------------------------------------------------
    # FILL
    # --------------------------------------------------------

    if fill_count > 0:

        available = get_questions(
            stage=stage,
            grade=grade,
            term=term,
            subject=subject,
            unit=unit,
            lessons=lessons,
            question_type="fill"
        )

        random.shuffle(available)

        selected_questions.extend(
            available[:fill_count]
        )

    if not selected_questions:

        return jsonify({
            "status": "error",
            "message": "لم يتم العثور على أسئلة مطابقة للاختيارات المحددة",
            "filters": {
                "stage": stage,
                "grade": grade,
                "term": term,
                "subject": subject,
                "unit": unit,
                "lessons": lessons
            }
        }), 404

    random.shuffle(
        selected_questions
    )

    return jsonify({
        "status": "success",
        "message": "تم إنشاء الاختبار بنجاح",
        "count": len(selected_questions),
        "questions": selected_questions
    })


# ============================================================
# QUESTION BY ID
# ============================================================

@app.route(
    "/api/question/<question_id>"
)
def question_by_id(question_id):

    for question in questions_bank:

        if str(
            question.get("id")
        ) == str(question_id):

            return jsonify(question)

    return jsonify({
        "status": "error",
        "message": "السؤال غير موجود"
    }), 404


# ============================================================
# ROUTES TEST
# ============================================================

@app.route("/routes")
def routes():

    result = []

    for rule in app.url_map.iter_rules():

        result.append({
            "route": str(rule),
            "methods": sorted(
                list(rule.methods)
            )
        })

    return jsonify(result)


# ============================================================
# 404
# ============================================================

@app.errorhandler(404)
def not_found(error):

    return jsonify({
        "status": "error",
        "message": "الصفحة غير موجودة"
    }), 404


# ============================================================
# 500
# ============================================================

@app.errorhandler(500)
def server_error(error):

    print(
        "Internal server error:",
        error
    )

    return jsonify({
        "status": "error",
        "message": "حدث خطأ داخلي في الخادم"
    }), 500


# ============================================================
# START APP
# ============================================================

if __name__ == "__main__":

    port = int(
        os.environ.get(
            "PORT",
            5000
        )
    )

    app.run(
        host="0.0.0.0",
        port=port,
        debug=False
    )
