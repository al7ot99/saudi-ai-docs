from flask import Flask, render_template, request, jsonify
import json
import os
import random


# =========================================================
# إنشاء تطبيق Flask
# يجب أن يكون هذا السطر قبل أي @app.route
# =========================================================

app = Flask(__name__)


# =========================================================
# مسارات الملفات
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
# تحميل المناهج
# =========================================================

def load_curriculum():
    try:
        with open(CURRICULUM_FILE, "r", encoding="utf-8") as f:
            return json.load(f)

    except FileNotFoundError:
        print("تحذير: لم يتم العثور على curriculum.json")
        return {}

    except json.JSONDecodeError as e:
        print("خطأ في قراءة curriculum.json:", e)
        return {}

    except Exception as e:
        print("خطأ غير متوقع في curriculum.json:", e)
        return {}


# =========================================================
# تحميل بنك الأسئلة
# =========================================================

def load_questions_bank():
    try:
        with open(QUESTIONS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)

        if isinstance(data, dict):
            questions = data.get("questions", [])

        elif isinstance(data, list):
            questions = data

        else:
            questions = []

        print("تم تحميل بنك الأسئلة بنجاح")
        print("عدد الأسئلة:", len(questions))

        return questions

    except FileNotFoundError:
        print("خطأ: لم يتم العثور على بنك الأسئلة")
        print(QUESTIONS_FILE)
        return []

    except json.JSONDecodeError as e:
        print("خطأ في JSON بنك الأسئلة:", e)
        return []

    except Exception as e:
        print("خطأ أثناء تحميل بنك الأسئلة:", e)
        return []


# =========================================================
# تحميل البيانات عند تشغيل الموقع
# =========================================================

curriculum_data = load_curriculum()
questions_bank = load_questions_bank()


# =========================================================
# تنظيف القيم النصية
# =========================================================

def clean_value(value):
    if value is None:
        return ""

    return str(value).strip()


# =========================================================
# الحصول على قيمة من أكثر من اسم محتمل
# =========================================================

def get_value(data, *names, default=None):

    for name in names:
        try:
            value = data.get(name)

            if value is not None and value != "":
                return value

        except Exception:
            pass

    return default


# =========================================================
# تحويل الأرقام بأمان
# =========================================================

def safe_int(value, default=0):

    try:
        return int(value)

    except (TypeError, ValueError):
        return default


# =========================================================
# استخراج البيانات من POST
# يدعم JSON و Form
# =========================================================

def get_request_data():

    if request.is_json:
        return request.get_json(silent=True) or {}

    return request.form


# =========================================================
# فلترة بنك الأسئلة
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

    clean_lessons = [
        clean_value(x)
        for x in lessons
        if clean_value(x)
    ]

    for q in questions_bank:

        if stage:
            if clean_value(q.get("stage")) != clean_value(stage):
                continue

        if grade:
            if clean_value(q.get("grade")) != clean_value(grade):
                continue

        if term:
            if clean_value(q.get("term")) != clean_value(term):
                continue

        if subject:
            if clean_value(q.get("subject")) != clean_value(subject):
                continue

        if unit:
            if clean_value(q.get("unit")) != clean_value(unit):
                continue

        if clean_lessons:
            if clean_value(q.get("lesson")) not in clean_lessons:
                continue

        if question_type:
            if clean_value(q.get("type")) != clean_value(question_type):
                continue

        if difficulty:
            if clean_value(q.get("difficulty")) != clean_value(difficulty):
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
# فحص الموقع
# =========================================================

@app.route("/health")
def health():

    return jsonify({
        "status": "ok",
        "message": "الموقع يعمل بنجاح",
        "questions_count": len(questions_bank)
    })


# =========================================================
# فحص بنك الأسئلة
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
# إحصائيات البنك
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
        "status": "success",
        "total_questions": len(questions_bank),
        "stages": stages
    })


# =========================================================
# المراحل
# =========================================================

@app.route("/api/stages")
def api_stages():

    stages = []

    seen = set()

    for q in questions_bank:

        value = clean_value(q.get("stage"))

        if value and value not in seen:
            seen.add(value)
            stages.append(value)

    return jsonify(stages)


# =========================================================
# الصفوف
# =========================================================

@app.route("/api/grades")
def api_grades():

    stage = request.args.get("stage", "")

    grades = []
    seen = set()

    for q in questions_bank:

        if clean_value(q.get("stage")) != clean_value(stage):
            continue

        value = clean_value(q.get("grade"))

        if value and value not in seen:
            seen.add(value)
            grades.append(value)

    return jsonify(grades)


# =========================================================
# الفصول الدراسية
# =========================================================

@app.route("/api/terms")
def api_terms():

    stage = request.args.get("stage", "")
    grade = request.args.get("grade", "")

    terms = []
    seen = set()

    for q in questions_bank:

        if clean_value(q.get("stage")) != clean_value(stage):
            continue

        if clean_value(q.get("grade")) != clean_value(grade):
            continue

        value = clean_value(q.get("term"))

        if value and value not in seen:
            seen.add(value)
            terms.append(value)

    return jsonify(terms)


# =========================================================
# المواد
# =========================================================

@app.route("/api/subjects")
def api_subjects():

    stage = request.args.get("stage", "")
    grade = request.args.get("grade", "")
    term = request.args.get("term", "")

    subjects = []
    seen = set()

    for q in questions_bank:

        if clean_value(q.get("stage")) != clean_value(stage):
            continue

        if clean_value(q.get("grade")) != clean_value(grade):
            continue

        if clean_value(q.get("term")) != clean_value(term):
            continue

        value = clean_value(q.get("subject"))

        if value and value not in seen:
            seen.add(value)
            subjects.append(value)

    return jsonify(subjects)


# =========================================================
# الوحدات
# =========================================================

@app.route("/api/units")
def api_units():

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

        value = clean_value(q.get("unit"))

        if value and value not in seen:
            seen.add(value)
            units.append(value)

    return jsonify(units)


# =========================================================
# الدروس
# =========================================================

@app.route("/api/lessons")
def api_lessons():

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

        value = clean_value(q.get("lesson"))

        if value and value not in seen:
            seen.add(value)
            lessons.append(value)

    return jsonify(lessons)


# =========================================================
# معاينة الأسئلة
# =========================================================

@app.route("/api/questions", methods=["GET", "POST"])
def api_questions():

    if request.method == "POST":

        data = get_request_data()

    else:

        data = request.args

    stage = get_value(data, "stage")
    grade = get_value(data, "grade")
    term = get_value(data, "term")
    subject = get_value(data, "subject")
    unit = get_value(data, "unit")
    difficulty = get_value(data, "difficulty")
    question_type = get_value(
        data,
        "type",
        "question_type"
    )

    lessons = []

    if request.method == "GET":

        lessons = request.args.getlist("lesson")

        if not lessons:
            lessons = request.args.getlist("lessons")

    else:

        if request.is_json:

            lessons = data.get("lessons", [])

            if not lessons:
                lesson = data.get("lesson")

                if lesson:
                    lessons = [lesson]

        else:

            lessons = request.form.getlist("lessons")

            if not lessons:
                lessons = request.form.getlist("lesson")

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
        "status": "success",
        "count": len(results),
        "questions": results
    })


# =========================================================
# إنشاء الاختبار
#
# وضعت عدة مسارات حتى يعمل مع الواجهة القديمة والجديدة
# =========================================================

@app.route("/api/generate-test", methods=["POST"])
@app.route("/generate-test", methods=["POST"])
@app.route("/create-test", methods=["POST"])
@app.route("/generate", methods=["POST"])
@app.route("/generate_exam", methods=["POST"])
@app.route("/create_exam", methods=["POST"])
def generate_test():

    data = get_request_data()

    # -----------------------------------------------------
    # البيانات التعليمية
    # -----------------------------------------------------

    stage = get_value(
        data,
        "stage",
        "education_stage"
    )

    grade = get_value(
        data,
        "grade",
        "class",
        "school_grade"
    )

    term = get_value(
        data,
        "term",
        "semester"
    )

    subject = get_value(
        data,
        "subject"
    )

    unit = get_value(
        data,
        "unit"
    )

    # -----------------------------------------------------
    # الدروس
    # -----------------------------------------------------

    lessons = []

    if request.is_json:

        lessons = data.get("lessons", [])

        if isinstance(lessons, str):
            lessons = [lessons]

        if not lessons:

            lesson = data.get("lesson")

            if lesson:
                lessons = [lesson]

    else:

        lessons = request.form.getlist("lessons")

        if not lessons:
            lessons = request.form.getlist("lesson")

        if not lessons:

            single_lesson = request.form.get("lesson")

            if single_lesson:
                lessons = [single_lesson]

    # -----------------------------------------------------
    # أعداد الأسئلة
    # -----------------------------------------------------

    mcq_count = safe_int(
        get_value(
            data,
            "mcq_count",
            "multiple_choice_count",
            "choice_count",
            default=0
        )
    )

    tf_count = safe_int(
        get_value(
            data,
            "tf_count",
            "true_false_count",
            default=0
        )
    )

    fill_count = safe_int(
        get_value(
            data,
            "fill_count",
            "fill_blank_count",
            default=0
        )
    )

    # -----------------------------------------------------
    # في حال لم ترسل الواجهة أعدادًا
    # نعطي عددًا افتراضيًا للتجربة
    # -----------------------------------------------------

    if mcq_count == 0 and tf_count == 0 and fill_count == 0:

        mcq_count = 5
        tf_count = 5
        fill_count = 5

    # -----------------------------------------------------
    # التأكد من البيانات الأساسية
    # -----------------------------------------------------

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

    selected = []

    # -----------------------------------------------------
    # اختيار من متعدد
    # -----------------------------------------------------

    if mcq_count > 0:

        questions = get_questions(
            stage=stage,
            grade=grade,
            term=term,
            subject=subject,
            unit=unit,
            lessons=lessons,
            question_type="mcq"
        )

        random.shuffle(questions)

        selected.extend(
            questions[:mcq_count]
        )

    # -----------------------------------------------------
    # صح وخطأ
    # -----------------------------------------------------

    if tf_count > 0:

        questions = get_questions(
            stage=stage,
            grade=grade,
            term=term,
            subject=subject,
            unit=unit,
            lessons=lessons,
            question_type="tf"
        )

        random.shuffle(questions)

        selected.extend(
            questions[:tf_count]
        )

    # -----------------------------------------------------
    # أكمل
    # -----------------------------------------------------

    if fill_count > 0:

        questions = get_questions(
            stage=stage,
            grade=grade,
            term=term,
            subject=subject,
            unit=unit,
            lessons=lessons,
            question_type="fill"
        )

        random.shuffle(questions)

        selected.extend(
            questions[:fill_count]
        )

    # -----------------------------------------------------
    # إذا لم نجد أسئلة
    # -----------------------------------------------------

    if not selected:

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

    random.shuffle(selected)

    # -----------------------------------------------------
    # النتيجة
    # -----------------------------------------------------

    return jsonify({
        "status": "success",
        "message": "تم إنشاء الاختبار بنجاح",
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
        "status": "error",
        "message": "السؤال غير موجود"
    }), 404


# =========================================================
# اختبار المسارات الموجودة
# =========================================================

@app.route("/routes")
def show_routes():

    routes = []

    for rule in app.url_map.iter_rules():

        routes.append({
            "route": str(rule),
            "methods": sorted(
                list(rule.methods)
            )
        })

    return jsonify(routes)


# =========================================================
# خطأ 404
# =========================================================

@app.errorhandler(404)
def page_not_found(error):

    return jsonify({
        "status": "error",
        "message": "الصفحة غير موجودة"
    }), 404


# =========================================================
# خطأ 500
# =========================================================

@app.errorhandler(500)
def internal_error(error):

    print("Internal Server Error:", error)

    return jsonify({
        "status": "error",
        "message": "حدث خطأ داخلي في الخادم"
    }), 500


# =========================================================
# تشغيل الموقع
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
