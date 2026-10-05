from flask import (
    Flask,
    render_template,
    request,
    jsonify,
    send_file
)

import json
import os
import random
import io
import zipfile

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.section import WD_SECTION

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_RIGHT, TA_CENTER
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    PageBreak
)


# ============================================================
# APP
# ============================================================

app = Flask(__name__)


# ============================================================
# PATHS
# ============================================================

BASE_DIR = os.path.dirname(
    os.path.abspath(__file__)
)

DATA_DIR = os.path.join(
    BASE_DIR,
    "data"
)

CURRICULUM_FILE = os.path.join(
    DATA_DIR,
    "curriculum.json"
)

QUESTIONS_FILES = [
    os.path.join(
        DATA_DIR,
        f"questions_part_{i:02d}.json"
    )
    for i in range(1, 11)
]


# ============================================================
# LOAD CURRICULUM
# ============================================================

def load_curriculum():

    try:

        with open(
            CURRICULUM_FILE,
            "r",
            encoding="utf-8"
        ) as file:

            return json.load(file)

    except Exception as error:

        print(
            "Curriculum load error:",
            error
        )

        return {}


# ============================================================
# LOAD QUESTIONS
# ============================================================

def load_questions_bank():

    all_questions = []

    for file_path in QUESTIONS_FILES:

        try:

            with open(
                file_path,
                "r",
                encoding="utf-8"
            ) as file:

                data = json.load(file)

            if isinstance(data, dict):

                questions = data.get(
                    "questions",
                    []
                )

            elif isinstance(data, list):

                questions = data

            else:

                questions = []

            all_questions.extend(
                questions
            )

            print(
                "Loaded:",
                os.path.basename(file_path),
                len(questions)
            )

        except FileNotFoundError:

            print(
                "Missing:",
                file_path
            )

        except Exception as error:

            print(
                "Load error:",
                file_path,
                error
            )

    print(
        "TOTAL QUESTIONS:",
        len(all_questions)
    )

    return all_questions


curriculum_data = load_curriculum()

questions_bank = load_questions_bank()


# ============================================================
# HELPERS
# ============================================================

def clean(value):

    if value is None:

        return ""

    return str(value).strip()


def clean_subject_name(subject):

    value = clean(subject)

    suffixes = [
        " - مسار علوم الحاسب والهندسة",
        " - مسار الصحة والحياة",
        " - مسار إدارة الأعمال",
        " - المسار الشرعي",
        " - المسار العام"
    ]

    for suffix in suffixes:

        value = value.replace(
            suffix,
            ""
        )

    return value.strip()


def normalize_track(track):

    value = clean(track)

    if value == "المسار العام":

        return ""

    return value


def question_matches(
    question,
    stage,
    grade,
    term,
    subject,
    lessons,
    track=""
):

    if clean(
        question.get("stage")
    ) != clean(stage):

        return False

    if clean(
        question.get("grade")
    ) != clean(grade):

        return False

    if clean(
        question.get("term")
    ) != clean(term):

        return False

    q_subject = clean_subject_name(
        question.get("subject")
    )

    wanted_subject = clean_subject_name(
        subject
    )

    if q_subject != wanted_subject:

        return False

    if lessons:

        if clean(
            question.get("lesson")
        ) not in lessons:

            return False

    wanted_track = normalize_track(
        track
    )

    q_track = normalize_track(
        question.get("track")
    )

    # إذا كان السؤال محدد المسار
    # نتأكد من التطابق.
    # أما الحقول القديمة الفارغة فنسمح بها.
    if wanted_track and q_track:

        if wanted_track != q_track:

            return False

    return True


# ============================================================
# RANDOM SELECTION WITHOUT DUPLICATES
# ============================================================

def select_questions(
    stage,
    grade,
    term,
    subject,
    lessons,
    types,
    difficulties,
    track=""
):

    lesson_values = [
        clean(x)
        for x in lessons
        if clean(x)
    ]

    selected_types = [
        clean(x)
        for x in types
        if clean(x)
    ]

    base_pool = []

    for question in questions_bank:

        if not question_matches(
            question,
            stage,
            grade,
            term,
            subject,
            lesson_values,
            track
        ):

            continue

        if clean(
            question.get("type")
        ) not in selected_types:

            continue

        base_pool.append(
            question
        )

    selected = []

    used_ids = set()


    # ========================================================
    # PICK BY DIFFICULTY
    # ========================================================

    for difficulty in [
        "easy",
        "medium",
        "hard"
    ]:

        wanted = int(
            difficulties.get(
                difficulty,
                0
            ) or 0
        )

        if wanted <= 0:

            continue

        pool = [
            q
            for q in base_pool
            if clean(
                q.get("difficulty")
            ) == difficulty
            and q.get("id") not in used_ids
        ]

        random.shuffle(pool)

        chosen = pool[:wanted]

        for question in chosen:

            used_ids.add(
                question.get("id")
            )

            selected.append(
                question
            )


    # ========================================================
    # FILL SHORTAGE
    # ========================================================

    requested_total = sum(
        int(
            difficulties.get(
                x,
                0
            ) or 0
        )
        for x in [
            "easy",
            "medium",
            "hard"
        ]
    )

    if len(selected) < requested_total:

        shortage = (
            requested_total
            - len(selected)
        )

        extra_pool = [
            q
            for q in base_pool
            if q.get("id")
            not in used_ids
        ]

        random.shuffle(
            extra_pool
        )

        for question in extra_pool[
            :shortage
        ]:

            used_ids.add(
                question.get("id")
            )

            selected.append(
                question
            )

    random.shuffle(
        selected
    )

    return selected


# ============================================================
# HOME
# ============================================================

@app.route("/")
def index():

    return render_template(
        "index.html",
        data=curriculum_data
    )


# ============================================================
# HEALTH
# ============================================================

@app.route("/health")
def health():

    return jsonify({
        "status": "ok",
        "questions_count":
            len(questions_bank)
    })


# ============================================================
# STATS
# ============================================================

@app.route("/api/stats")
def stats():

    stages = {}

    for question in questions_bank:

        stage = clean(
            question.get("stage")
        )

        stages[stage] = (
            stages.get(
                stage,
                0
            )
            + 1
        )

    return jsonify({
        "ok": True,
        "total_questions":
            len(questions_bank),
        "stages": stages
    })


# ============================================================
# GENERATE
#
# هذا هو المسار الذي يستخدمه index.html الحالي
# ============================================================

@app.route(
    "/api/generate",
    methods=["POST"]
)
@app.route(
    "/api/generate-test",
    methods=["POST"]
)
@app.route(
    "/generate",
    methods=["POST"]
)
@app.route(
    "/generate-test",
    methods=["POST"]
)
def generate():

    try:

        data = request.get_json(
            silent=True
        ) or {}

        stage = clean(
            data.get("stage")
        )

        grade = clean(
            data.get("grade")
        )

        track = clean(
            data.get("track")
        )

        term = clean(
            data.get("term")
        )

        subject = clean(
            data.get("subject")
        )

        lessons = data.get(
            "lessons",
            []
        )

        types = data.get(
            "types",
            []
        )

        difficulties = data.get(
            "difficulties",
            {}
        )


        # ====================================================
        # VALIDATION
        # ====================================================

        if not stage:

            return jsonify({
                "ok": False,
                "error":
                    "اختر المرحلة التعليمية."
            }), 400


        if not grade:

            return jsonify({
                "ok": False,
                "error":
                    "اختر الصف."
            }), 400


        if not term:

            return jsonify({
                "ok": False,
                "error":
                    "اختر الفصل الدراسي."
            }), 400


        if not subject:

            return jsonify({
                "ok": False,
                "error":
                    "اختر المادة."
            }), 400


        if not lessons:

            return jsonify({
                "ok": False,
                "error":
                    "اختر درساً واحداً على الأقل."
            }), 400


        if not types:

            return jsonify({
                "ok": False,
                "error":
                    "اختر نوعاً واحداً على الأقل من الأسئلة."
            }), 400


        total_requested = sum(
            int(
                difficulties.get(
                    difficulty,
                    0
                ) or 0
            )
            for difficulty in [
                "easy",
                "medium",
                "hard"
            ]
        )


        if total_requested <= 0:

            return jsonify({
                "ok": False,
                "error":
                    "حدد عدد الأسئلة."
            }), 400


        # ====================================================
        # GENERATE
        # ====================================================

        selected = select_questions(
            stage=stage,
            grade=grade,
            term=term,
            subject=subject,
            lessons=lessons,
            types=types,
            difficulties=difficulties,
            track=track
        )


        if not selected:

            return jsonify({
                "ok": False,
                "error":
                    "لم يتم العثور على أسئلة مطابقة للاختيارات."
            }), 404


        # ====================================================
        # FORMAT FOR INDEX.HTML
        # ====================================================

        output = []

        for question in selected:

            item = dict(
                question
            )

            item["typeKey"] = (
                question.get("type")
            )

            output.append(
                item
            )


        return jsonify({
            "ok": True,
            "status": "success",
            "count": len(output),
            "requested":
                total_requested,
            "questions":
                output
        })


    except Exception as error:

        print(
            "Generate error:",
            error
        )

        return jsonify({
            "ok": False,
            "error":
                "حدث خطأ أثناء إنشاء الاختبار."
        }), 500


# ============================================================
# PDF HELPERS
# ============================================================

def find_pdf_font():

    candidates = [

        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",

        "/usr/share/fonts/truetype/dejavu/DejaVuSansCondensed.ttf",

        "/usr/share/fonts/truetype/freefont/FreeSans.ttf"
    ]

    for path in candidates:

        if os.path.exists(path):

            return path

    return None


PDF_FONT_NAME = "Helvetica"

font_path = find_pdf_font()

if font_path:

    try:

        pdfmetrics.registerFont(
            TTFont(
                "ArabicFont",
                font_path
            )
        )

        PDF_FONT_NAME = (
            "ArabicFont"
        )

    except Exception as error:

        print(
            "Font registration error:",
            error
        )


# ============================================================
# ARABIC PDF TEXT
# ============================================================

def pdf_text(value):

    text = clean(value)

    try:

        import arabic_reshaper

        from bidi.algorithm import (
            get_display
        )

        return get_display(
            arabic_reshaper.reshape(
                text
            )
        )

    except Exception:

        return text


# ============================================================
# CREATE DOCX
# ============================================================

def create_docx(
    questions,
    meta
):

    document = Document()

    section = document.sections[0]

    section.top_margin = (
        section.top_margin
    )


    title = document.add_paragraph()

    title.alignment = (
        WD_ALIGN_PARAGRAPH.CENTER
    )

    title_run = title.add_run(
        clean(
            meta.get("title")
        )
        or "اختبار"
    )

    title_run.bold = True


    info = document.add_paragraph()

    info.alignment = (
        WD_ALIGN_PARAGRAPH.RIGHT
    )

    info.add_run(
        "المادة: "
        + clean(
            meta.get("subject")
        )
        + " | الصف: "
        + clean(
            meta.get("grade")
        )
        + " | الفصل: "
        + clean(
            meta.get("term")
        )
    )


    teacher = document.add_paragraph()

    teacher.alignment = (
        WD_ALIGN_PARAGRAPH.RIGHT
    )

    teacher.add_run(
        "المعلم/ـة: "
        + (
            clean(
                meta.get("teacher")
            )
            or "________________"
        )
    )


    school = document.add_paragraph()

    school.alignment = (
        WD_ALIGN_PARAGRAPH.RIGHT
    )

    school.add_run(
        "المدرسة: "
        + (
            clean(
                meta.get("school")
            )
            or "________________"
        )
    )


    document.add_paragraph(
        "اسم الطالب/ـة: ______________________________"
    )


    type_titles = {

        "mcq":
            "اختر الإجابة الصحيحة:",

        "tf":
            "ضع علامة صح أو خطأ:",

        "fill":
            "أكمل الفراغ باختيار الإجابة المناسبة:"
    }


    question_number = 0

    for type_key in [
        "mcq",
        "tf",
        "fill"
    ]:

        items = [
            q
            for q in questions
            if clean(
                q.get("typeKey")
                or q.get("type")
            ) == type_key
        ]

        if not items:

            continue


        heading = document.add_paragraph()

        heading.alignment = (
            WD_ALIGN_PARAGRAPH.RIGHT
        )

        run = heading.add_run(
            type_titles[
                type_key
            ]
        )

        run.bold = True


        for question in items:

            question_number += 1

            paragraph = (
                document.add_paragraph()
            )

            paragraph.alignment = (
                WD_ALIGN_PARAGRAPH.RIGHT
            )

            paragraph.add_run(
                f"{question_number}. "
                + clean(
                    question.get("text")
                )
            )


            options = (
                question.get(
                    "options"
                )
                or []
            )

            if type_key in [
                "mcq",
                "fill"
            ]:

                for index, option in enumerate(
                    options,
                    1
                ):

                    option_paragraph = (
                        document.add_paragraph()
                    )

                    option_paragraph.alignment = (
                        WD_ALIGN_PARAGRAPH.RIGHT
                    )

                    option_paragraph.add_run(
                        f"{index}) "
                        + clean(option)
                    )


            elif type_key == "tf":

                answer_line = (
                    document.add_paragraph()
                )

                answer_line.alignment = (
                    WD_ALIGN_PARAGRAPH.RIGHT
                )

                answer_line.add_run(
                    "(        )"
                )


    output = io.BytesIO()

    document.save(
        output
    )

    output.seek(0)

    return output


# ============================================================
# CREATE PDF
# ============================================================

def create_pdf(
    questions,
    meta
):

    output = io.BytesIO()

    pdf = SimpleDocTemplate(
        output,
        pagesize=A4,
        rightMargin=35,
        leftMargin=35,
        topMargin=35,
        bottomMargin=35
    )


    styles = (
        getSampleStyleSheet()
    )


    title_style = (
        ParagraphStyle(
            "ArabicTitle",
            parent=styles[
                "Heading1"
            ],
            fontName=
                PDF_FONT_NAME,
            alignment=
                TA_CENTER,
            fontSize=18,
            leading=25
        )
    )


    normal_style = (
        ParagraphStyle(
            "ArabicNormal",
            parent=styles[
                "Normal"
            ],
            fontName=
                PDF_FONT_NAME,
            alignment=
                TA_RIGHT,
            fontSize=11,
            leading=18
        )
    )


    heading_style = (
        ParagraphStyle(
            "ArabicHeading",
            parent=styles[
                "Heading2"
            ],
            fontName=
                PDF_FONT_NAME,
            alignment=
                TA_RIGHT,
            fontSize=13,
            leading=20
        )
    )


    story = []


    story.append(
        Paragraph(
            pdf_text(
                meta.get("title")
                or "اختبار"
            ),
            title_style
        )
    )


    story.append(
        Spacer(
            1,
            12
        )
    )


    info = (
        "المادة: "
        + clean(
            meta.get("subject")
        )
        + " | الصف: "
        + clean(
            meta.get("grade")
        )
        + " | الفصل: "
        + clean(
            meta.get("term")
        )
    )


    story.append(
        Paragraph(
            pdf_text(info),
            normal_style
        )
    )


    story.append(
        Paragraph(
            pdf_text(
                "المعلم/ـة: "
                + (
                    clean(
                        meta.get(
                            "teacher"
                        )
                    )
                    or "________________"
                )
            ),
            normal_style
        )
    )


    story.append(
        Paragraph(
            pdf_text(
                "المدرسة: "
                + (
                    clean(
                        meta.get(
                            "school"
                        )
                    )
                    or "________________"
                )
            ),
            normal_style
        )
    )


    story.append(
        Paragraph(
            pdf_text(
                "اسم الطالب/ـة: ______________________________"
            ),
            normal_style
        )
    )


    story.append(
        Spacer(
            1,
            14
        )
    )


    titles = {

        "mcq":
            "اختر الإجابة الصحيحة:",

        "tf":
            "ضع علامة صح أو خطأ:",

        "fill":
            "أكمل الفراغ باختيار الإجابة المناسبة:"
    }


    counter = 0


    for type_key in [
        "mcq",
        "tf",
        "fill"
    ]:

        items = [
            q
            for q in questions
            if clean(
                q.get("typeKey")
                or q.get("type")
            ) == type_key
        ]


        if not items:

            continue


        story.append(
            Paragraph(
                pdf_text(
                    titles[
                        type_key
                    ]
                ),
                heading_style
            )
        )


        story.append(
            Spacer(
                1,
                6
            )
        )


        for question in items:

            counter += 1

            question_text = (
                f"{counter}. "
                + clean(
                    question.get(
                        "text"
                    )
                )
            )


            story.append(
                Paragraph(
                    pdf_text(
                        question_text
                    ),
                    normal_style
                )
            )


            options = (
                question.get(
                    "options"
                )
                or []
            )


            if type_key in [
                "mcq",
                "fill"
            ]:

                for index, option in enumerate(
                    options,
                    1
                ):

                    story.append(
                        Paragraph(
                            pdf_text(
                                f"{index}) "
                                + clean(option)
                            ),
                            normal_style
                        )
                    )


            elif type_key == "tf":

                story.append(
                    Paragraph(
                        "(        )",
                        normal_style
                    )
                )


            story.append(
                Spacer(
                    1,
                    9
                )
            )


    pdf.build(
        story
    )

    output.seek(0)

    return output


# ============================================================
# EXPORT
#
# index.html uses /api/export
# ============================================================

@app.route(
    "/api/export",
    methods=["POST"]
)
def export_document():

    try:

        data = request.get_json(
            silent=True
        ) or {}


        questions = data.get(
            "questions",
            []
        )


        meta = data.get(
            "meta",
            {}
        )


        export_format = clean(
            data.get("format")
        ).lower()


        if not questions:

            return jsonify({
                "ok": False,
                "error":
                    "لا توجد أسئلة للتصدير."
            }), 400


        # ====================================================
        # WORD
        # ====================================================

        if export_format == "docx":

            file_data = create_docx(
                questions,
                meta
            )

            return send_file(
                file_data,
                as_attachment=True,
                download_name=
                    "exam.docx",
                mimetype=(
                    "application/"
                    "vnd.openxmlformats-"
                    "officedocument."
                    "wordprocessingml."
                    "document"
                )
            )


        # ====================================================
        # PDF
        # ====================================================

        if export_format == "pdf":

            file_data = create_pdf(
                questions,
                meta
            )

            return send_file(
                file_data,
                as_attachment=True,
                download_name=
                    "exam.pdf",
                mimetype=
                    "application/pdf"
            )


        # ====================================================
        # BOTH
        # ====================================================

        if export_format == "both":

            pdf_file = create_pdf(
                questions,
                meta
            )

            docx_file = create_docx(
                questions,
                meta
            )


            zip_buffer = io.BytesIO()


            with zipfile.ZipFile(
                zip_buffer,
                "w",
                zipfile.ZIP_DEFLATED
            ) as archive:

                archive.writestr(
                    "exam.pdf",
                    pdf_file.getvalue()
                )

                archive.writestr(
                    "exam.docx",
                    docx_file.getvalue()
                )


            zip_buffer.seek(0)


            return send_file(
                zip_buffer,
                as_attachment=True,
                download_name=
                    "exam_files.zip",
                mimetype=
                    "application/zip"
            )


        return jsonify({
            "ok": False,
            "error":
                "صيغة التصدير غير صحيحة."
        }), 400


    except Exception as error:

        print(
            "Export error:",
            error
        )

        return jsonify({
            "ok": False,
            "error":
                "حدث خطأ أثناء التصدير."
        }), 500


# ============================================================
# ROUTES
# ============================================================

@app.route("/routes")
def routes():

    result = []

    for rule in app.url_map.iter_rules():

        result.append({
            "route":
                str(rule),

            "methods":
                sorted(
                    list(
                        rule.methods
                    )
                )
        })

    return jsonify(
        result
    )


# ============================================================
# 404
# ============================================================

@app.errorhandler(404)
def not_found(error):

    return jsonify({
        "ok": False,
        "error":
            "الصفحة غير موجودة."
    }), 404


# ============================================================
# 500
# ============================================================

@app.errorhandler(500)
def server_error(error):

    print(
        "Server error:",
        error
    )

    return jsonify({
        "ok": False,
        "error":
            "حدث خطأ داخلي في الخادم."
    }), 500


# ============================================================
# RUN
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
