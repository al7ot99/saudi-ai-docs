from flask import Flask, render_template, request, jsonify
import json
import os
import random

app = Flask(__name__)

# =========================================================
# المسارات الأساسية للمشروع
# =========================================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

CURRICULUM_FILE = os.path.join(
    BASE_DIR,
    "data",
    "curriculum.json"
)

QUESTIONS_FILE = os.path.join(
    BASE_DIR,
    "data",
    "questions_bank_allstages_v389_launch_candidate.json"
)


# =========================================================
# تحميل ملف المناهج
# =========================================================

def load_curriculum():
    try:
        with open(CURRICULUM_FILE, "r", encoding="utf-8") as f:
            return json.load(f)

    except FileNotFoundError:
        print("لم يتم العثور على ملف curriculum.json")
        return {}

    except json.JSONDecodeError as e:
        print("خطأ في ملف curriculum.json:", e)
        return {}


# =========================================================
# تحميل بنك الأسئلة
# =========================================================

def load_questions_bank():
    try:
        with open(QUESTIONS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)

        if isinstance(data, dict):
            return data.get("questions", [])

        if isinstance(data, list):
            return data

        return []

    except FileNotFoundError:
        print("لم يتم العثور على بنك الأسئلة:")
        print(QUESTIONS_FILE)
        return []

    except json.JSONDecodeError as e:
        print("خطأ في قراءة بنك الأسئلة:", e)
        return []


curriculum_data = load_curriculum()
questions_bank = load_questions_bank()


# =========================================================
# دالة تنظيف النصوص
# =========================================================

def clean_value(value):
    if value is None:
        return ""

    return str(value).strip()


# =========================================================
# دالة البحث والفلترة داخل بنك الأسئلة
# =========================================================

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

    results = []

    if lessons is None:
        lessons = []

    if isinstance(lessons, str):
        lessons = [lessons]

    for q in questions_bank:

        if stage and clean_value(q.get("stage")) != clean_value(stage):
            continue

        if grade and clean_value(q.get("grade")) != clean_value(grade):
            continue

        if term and clean_value(q.get("term")) != clean_value(term):
            continue

        if subject and clean_value(q.get("subject")) != clean_value(subject):
            continue

        if unit and clean_value(q.get("unit")) != clean_value(unit):
            continue

        if lessons:
            if clean_value(q.get("lesson")) not in [
                clean_value(x) for x in lessons
            ]:
                continue

        if question_type and clean_value(q.get("type")) != clean_value(question_type):
            continue

        if difficulty and clean_value(q.get("difficulty")) != clean_value(difficulty):
            continue

        results.append(q)

    return results


# =========================================================
# الصفحة الرئيسية
# =========================================================

@app.route("/")
def index():

    return render_template(
        "index.html",
        data=curriculum_data
    )


# =========================================================
# اختبار عمل الموقع
# =========================================================

@app.route("/health")
def health():

    return jsonify({
        "status": "ok",
        "message": "الموقع يعمل بنجاح",
        "questions_count": len(questions_bank)
    })


# =========================================================
# اختبار بنك الأسئلة
# =========================================================

@app.route("/test-questions")
def test_questions():

    sample = questions_bank[:10]

    return jsonify({
        "status": "success",
        "total_questions": len(questions_bank),
        "sample_count": len(sample),
        "questions": sample
    })


# =========================================================
# إحصائيات بنك الأسئلة
# =========================================================

@app.route("/api/stats")
def bank_stats():

    stages = {}

    for q in questions_bank:

        stage = clean_value(q.get("stage"))

        if not stage:
            stage = "غير محدد"

        stages[stage] = stages.get(stage, 0) + 1

    return jsonify({
        "total_questions": len(questions_bank),
        "stages": stages
    })


# =========================================================
# إرجاع المراحل
# =========================================================

@app.route("/api/stages")
def get_stages():

    stages = sorted(
        list(
            set(
                clean_value(q.get("stage"))
                for q in questions_bank
                if q.get("stage")
            )
        )
    )

    return jsonify(stages)


# =========================================================
# إرجاع الصفوف حسب المرحلة
# =========================================================

@app.route("/api/grades")
def get_grades():

    stage = request.args.get("stage", "")

    grades = sorted(
        list(
            set(
                clean_value(q.get("grade"))
                for q in questions_bank
                if clean_value(q.get("stage")) == clean_value(stage)
                and q.get("grade")
            )
        )
    )

    return jsonify(grades)


# =========================================================
# إرجاع الفصول الدراسية
# =========================================================

@app.route("/api/terms")
def get_terms():

    stage = request.args.get("stage", "")
    grade = request.args.get("grade", "")

    terms = sorted(
        list(
            set(
                clean_value(q.get("term"))
                for q in questions_bank
                if clean_value(q.get("stage")) == clean_value(stage)
                and clean_value(q.get("grade")) == clean_value(grade)
                and q.get("term")
            )
        )
    )

    return jsonify(terms)


# =========================================================
# إرجاع المواد
# =========================================================

@app.route("/api/subjects")
def get_subjects():

    stage = request.args.get("stage", "")
    grade = request.args.get("grade", "")
    term = request.args.get("term", "")

    subjects = sorted(
        list(
            set(
                clean_value(q.get("subject"))
                for q in questions_bank
                if clean_value(q.get("stage")) == clean_value(stage)
                and clean_value(q.get("grade")) == clean_value(grade)
                and clean_value(q.get("term")) == clean_value(term)
                and q.get("subject")
            )
        )
    )

    return jsonify(subjects)


# =========================================================
# إرجاع الوحدات
# =========================================================

@app.route("/api/units")
def get_units():

    stage = request.args.get("stage", "")
    grade = request.args.get("grade", "")
    term = request.args.get("term", "")
    subject = request.args.get("subject", "")

    units = []

    seen = set()

    for q in questions_bank:

        if clean_value(q.get("stage")) != clean_value(stage):
            continue

        if clean_value(q.get("grade")) != clean_value(grade):
            continue

        if clean_value(q.get("term")) != clean_value(term):
            continue

        if clean_value(q.get("subject")) != clean_value(subject):
            continue

        unit = clean_value(q.get("unit"))

        if unit and unit not in seen:
            seen.add(unit)
            units.append(unit)

    return jsonify(units)


# =========================================================
# إرجاع الدروس
# =========================================================

@app.route("/api/lessons")
def get_lessons():

    stage = request.args.get("stage", "")
    grade = request.args.get("grade", "")
    term = request.args.get("term", "")
    subject = request.args.get("subject", "")
    unit = request.args.get("unit", "")

    lessons = []

    seen = set()

    for q in questions_bank:

        if clean_value(q.get("stage")) != clean_value(stage):
            continue

        if clean_value(q.get("grade")) != clean_value(grade):
            continue

        if clean_value(q.get("term")) != clean_value(term):
            continue

        if clean_value(q.get("subject")) != clean_value(subject):
            continue

        if unit:
            if clean_value(q.get("unit")) != clean_value(unit):
                continue

        lesson = clean_value(q.get("lesson"))

        if lesson and lesson not in seen:
            seen.add(lesson)
            lessons.append(lesson)

    return jsonify(lessons)


# =========================================================
# معاينة الأسئلة
# =========================================================

@app.route("/api/questions", methods=["GET", "POST"])
def api_questions():

    if request.method == "POST":
        data = request.get_json(silent=True) or {}
    else:
        data = request.args

    stage = data.get("stage")
    grade = data.get("grade")
    term = data.get("term")
    subject = data.get("subject")
    unit = data.get("unit")
    difficulty = data.get("difficulty")
    question_type = data.get("type")

    lessons = data.get("lessons", [])

    if request.method == "GET":
        lessons = request.args.getlist("lesson")

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
        "count": len(results),
        "questions": results
    })


# =========================================================
# توليد اختبار عشوائي
# =========================================================

@app.route("/api/generate-test", methods=["POST"])
def generate_test():

    data = request.get_json(silent=True) or {}

    stage = data.get("stage")
    grade = data.get("grade")
    term = data.get("term")
    subject = data.get("subject")
    unit = data.get("unit")

    lessons = data.get("lessons", [])

    mcq_count = int(data.get("mcq_count", 0) or 0)
    tf_count = int(data.get("tf_count", 0) or 0)
    fill_count = int(data.get("fill_count", 0) or 0)

    selected = []

    # =====================================================
    # اختيار من متعدد
    # =====================================================

    if mcq_count > 0:

        mcq_questions = get_questions(
            stage=stage,
            grade=grade,
            term=term,
            subject=subject,
            unit=unit,
            lessons=lessons,
            question_type="mcq"
        )

        random.shuffle(mcq_questions)

        selected.extend(
            mcq_questions[:mcq_count]
        )

    # =====================================================
    # صح أو خطأ
    # =====================================================

    if tf_count > 0:

        tf_questions = get_questions(
            stage=stage,
            grade=grade,
            term=term,
            subject=subject,
            unit=unit,
            lessons=lessons,
            question_type="tf"
        )

        random.shuffle(tf_questions)

        selected.extend(
            tf_questions[:tf_count]
        )

    # =====================================================
    # أكمل
    # =====================================================

    if fill_count > 0:

        fill_questions = get_questions(
            stage=stage,
            grade=grade,
            term=term,
            subject=subject,
            unit=unit,
            lessons=lessons,
            question_type="fill"
        )

        random.shuffle(fill_questions)

        selected.extend(
            fill_questions[:fill_count]
        )

    random.shuffle(selected)

    return jsonify({
        "status": "success",
        "count": len(selected),
        "questions": selected
    })


# =========================================================
# البحث عن سؤال بواسطة ID
# =========================================================

@app.route("/api/question/<question_id>")
def question_by_id(question_id):

    for q in questions_bank:

        if str(q.get("id")) == str(question_id):
            return jsonify(q)

    return jsonify({
        "error": "السؤال غير موجود"
    }), 404


# =========================================================
# معالجة خطأ 404
# =========================================================

@app.errorhandler(404)
def page_not_found(error):

    return jsonify({
        "error": "الصفحة غير موجودة"
    }), 404


# =========================================================
# معالجة الأخطاء العامة
# =========================================================

@app.errorhandler(500)
def internal_error(error):

    return jsonify({
        "error": "حدث خطأ داخلي في الخادم"
    }), 500


# =========================================================
# تشغيل التطبيق
# =========================================================

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
