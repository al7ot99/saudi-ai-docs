import io
import json
import os
import zipfile

from flask import Flask, render_template, request, jsonify, send_file
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from docx import Document
from docx.shared import Pt

app = Flask(__name__)

# مسار المشروع
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(BASE_DIR, "data", "curriculum.json")


def curriculum():
    with open(DATA, encoding="utf8") as f:
        return json.load(f)


# =========================================================
# توليد الأسئلة
# =========================================================

def generate_questions(p):
    counts = p.get("counts", {})
    lessons = p.get("lessons", [])

    if not lessons:
        lessons = ["الدرس المحدد"]

    questions = []
    number = 1

    types = [
        ("mcq", "اختيار من متعدد"),
        ("tf", "صح أو خطأ"),
        ("fill", "أكمل الفراغ"),
        ("match", "صل الكلمة بالمصطلح المناسب"),
        ("imageMatch", "صل الكلمة بالصورة المناسبة")
    ]

    for key, label in types:

        amount = int(counts.get(key, 0))

        for _ in range(amount):

            lesson = lessons[(number - 1) % len(lessons)]

            if key == "mcq":
                text = f"اختر الإجابة الصحيحة وفق محتوى «{lesson}»."

                options = [
                    "أ) الإجابة الأولى",
                    "ب) الإجابة الثانية",
                    "ج) الإجابة الثالثة",
                    "د) الإجابة الرابعة"
                ]

            elif key == "tf":
                text = f"صح أم خطأ: العبارة التالية مرتبطة بمحتوى «{lesson}»."
                options = ["☐ صح", "☐ خطأ"]

            elif key == "fill":
                text = f"أكمل الفراغ من محتوى «{lesson}»: ____________________."
                options = []

            elif key == "match":
                text = f"صل عناصر «{lesson}» بالمصطلحات المناسبة."

                options = [
                    "(1) __________________    (أ) __________________",
                    "(2) __________________    (ب) __________________"
                ]

            else:
                text = f"صل الكلمة بالصورة المناسبة من محتوى «{lesson}»."

                options = [
                    "① صورة    ② صورة    ③ صورة"
                ]

            questions.append({
                "n": number,
                "type": label,
                "lesson": lesson,
                "text": text,
                "options": options
            })

            number += 1

    return questions


# =========================================================
# الصفحة الرئيسية
# =========================================================

@app.get("/")
def home():
    return render_template(
        "index.html",
        data=curriculum()
    )


# =========================================================
# توليد الأسئلة
# =========================================================

@app.post("/api/generate")
def generate():

    data = request.get_json()

    return jsonify({
        "ok": True,
        "questions": generate_questions(data)
    })


# =========================================================
# إنشاء Word
# =========================================================

def docx_bytes(questions, meta):

    document = Document()

    normal = document.styles["Normal"]
    normal.font.name = "Arial"
    normal.font.size = Pt(12)

    # العنوان
    paragraph = document.add_paragraph()
    paragraph.alignment = 1

    run = paragraph.add_run(
        meta.get("title", "مستند تعليمي")
    )

    run.bold = True
    run.font.size = Pt(18)

    # بيانات الاختبار
    info = [
        ("المرحلة", "stage"),
        ("الصف", "grade"),
        ("المادة", "subject"),
        ("الفصل الدراسي", "term"),
        ("الوحدة", "unit"),
        ("المعلم", "teacher"),
        ("المدرسة", "school")
    ]

    for label, key in info:

        if meta.get(key):

            p = document.add_paragraph()

            r = p.add_run(
                f"{label}: {meta.get(key)}"
            )

            r.font.size = Pt(11)

    # اسم الطالب
    p = document.add_paragraph()

    r = p.add_run(
        "اسم الطالب: __________________________________________"
    )

    r.bold = True

    document.add_paragraph("")

    # الأسئلة
    for q in questions:

        p = document.add_paragraph()

        r = p.add_run(
            f"{q['n']}. {q['text']}"
        )

        r.bold = True

        # الاختيارات في نفس السطر
        if q.get("type") == "اختيار من متعدد":

            p = document.add_paragraph()

            options = q.get("options", [])

            r = p.add_run(
                "     ".join(options)
            )

        elif q.get("type") == "صح أو خطأ":

            p = document.add_paragraph()

            p.add_run(
                "☐ صح                 ☐ خطأ"
            )

        elif q.get("options"):

            for option in q["options"]:

                p = document.add_paragraph()

                p.add_run(option)

    output = io.BytesIO()

    document.save(output)

    return output.getvalue()


# =========================================================
# إنشاء PDF
# =========================================================

def pdf_bytes(questions, meta):

    output = io.BytesIO()

    pdf = canvas.Canvas(
        output,
        pagesize=A4
    )

    width, height = A4

    y = height - 45

    # العنوان
    pdf.setFont(
        "Helvetica-Bold",
        16
    )

    pdf.drawRightString(
        width - 40,
        y,
        meta.get("title", "مستند تعليمي")
    )

    y -= 30

    pdf.setFont(
        "Helvetica",
        10
    )

    info = [
        ("المرحلة", "stage"),
        ("الصف", "grade"),
        ("المادة", "subject"),
        ("الفصل الدراسي", "term"),
        ("الوحدة", "unit"),
        ("المعلم", "teacher"),
        ("المدرسة", "school")
    ]

    for label, key in info:

        if meta.get(key):

            pdf.drawRightString(
                width - 40,
                y,
                f"{label}: {meta.get(key)}"
            )

            y -= 15

    # اسم الطالب
    y -= 5

    pdf.setFont(
        "Helvetica-Bold",
        11
    )

    pdf.drawRightString(
        width - 40,
        y,
        "اسم الطالب: __________________________________________"
    )

    y -= 25

    pdf.setFont(
        "Helvetica",
        10
    )

    # الأسئلة
    for q in questions:

        lines = [
            f"{q['n']}. {q['text']}"
        ]

        if q.get("type") == "اختيار من متعدد":

            lines.append(
                "     ".join(q.get("options", []))
            )

        elif q.get("type") == "صح أو خطأ":

            lines.append(
                "☐ صح                 ☐ خطأ"
            )

        else:

            lines.extend(
                q.get("options", [])
            )

        for line in lines:

            if y < 45:

                pdf.showPage()

                y = height - 45

                pdf.setFont(
                    "Helvetica",
                    10
                )

            pdf.drawRightString(
                width - 40,
                y,
                line[:115]
            )

            y -= 16

        y -= 7

    pdf.save()

    return output.getvalue()


# =========================================================
# التصدير
# =========================================================

@app.post("/api/export")
def export():

    data = request.get_json()

    questions = data["questions"]
    meta = data["meta"]
    fmt = data["format"]

    if fmt == "pdf":

        return send_file(
            io.BytesIO(
                pdf_bytes(
                    questions,
                    meta
                )
            ),
            as_attachment=True,
            download_name="المستند.pdf",
            mimetype="application/pdf"
        )

    if fmt == "docx":

        return send_file(
            io.BytesIO(
                docx_bytes(
                    questions,
                    meta
                )
            ),
            as_attachment=True,
            download_name="المستند.docx",
            mimetype="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )

    # PDF + Word
    output = io.BytesIO()

    with zipfile.ZipFile(
        output,
        "w",
        zipfile.ZIP_DEFLATED
    ) as archive:

        archive.writestr(
            "المستند.pdf",
            pdf_bytes(
                questions,
                meta
            )
        )

        archive.writestr(
            "المستند.docx",
            docx_bytes(
                questions,
                meta
            )
        )

    output.seek(0)

    return send_file(
        output,
        as_attachment=True,
        download_name="المستندات.zip",
        mimetype="application/zip"
    )


# =========================================================
# تشغيل الموقع
# =========================================================

if __name__ == "__main__":

    app.run(
        host="0.0.0.0",
        port=5000
    )
