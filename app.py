import io
import json
import os
import zipfile

from flask import Flask, render_template, request, jsonify, send_file
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from docx import Document
from docx.shared import Pt
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import arabic_reshaper
from bidi.algorithm import get_display
app = Flask(__name__)
# خط عربي
FONT_PATH = os.path.join(
    BASE_DIR,
    "fonts",
    "DejaVuSans.ttf"
)

if os.path.exists(FONT_PATH):
    pdfmetrics.registerFont(
        TTFont("ArabicFont", FONT_PATH)
    )


def ar(text):
    """
    تجهيز النص العربي لظهوره بشكل صحيح في PDF
    """
    text = str(text or "")

    try:
        reshaped = arabic_reshaper.reshape(text)
        return get_display(reshaped)
    except Exception:
        return text
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(BASE_DIR, "data", "curriculum.json")


def curriculum():
    with open(DATA, encoding="utf8") as f:
        return json.load(f)


def generate_questions(p):
    c = p["counts"]
    lessons = p["lessons"]
    out = []
    n = 1

    types = [
        ("mcq", "اختيار من متعدد"),
        ("tf", "صح أو خطأ"),
        ("fill", "أكمل الفراغ"),
        ("match", "صل الكلمة بالمصطلح المناسب"),
        ("imageMatch", "صل الكلمة بالصورة المناسبة")
    ]

    for key, label in types:
        for _ in range(int(c.get(key, 0))):

            lesson = lessons[(n - 1) % len(lessons)] if lessons else "الدرس المحدد"

            if key == "mcq":
                text = f"اختر الإجابة الصحيحة وفق محتوى «{lesson}»."
                opts = [
                    "أ) الإجابة الأولى",
                    "ب) الإجابة الثانية",
                    "ج) الإجابة الثالثة",
                    "د) الإجابة الرابعة"
                ]

            elif key == "tf":
                text = f"صح أم خطأ: العبارة التالية مرتبطة بمحتوى «{lesson}»."
                opts = []

            elif key == "fill":
                text = f"أكمل الفراغ من محتوى «{lesson}»: __________."
                opts = []

            elif key == "match":
                text = f"صل عناصر «{lesson}» بالمصطلحات المناسبة."
                opts = [
                    "(1) __________    (أ) __________",
                    "(2) __________    (ب) __________"
                ]

            else:
                text = f"صل الكلمة بالصورة المناسبة من محتوى «{lesson}»."
                opts = [
                    "[صورة 1]    [صورة 2]    [صورة 3]"
                ]

            out.append({
                "n": n,
                "type": label,
                "lesson": lesson,
                "text": text,
                "options": opts
            })

            n += 1

    return out


@app.get("/")
def home():
    return render_template("index.html", data=curriculum())


@app.post("/api/generate")
def gen():
    return jsonify({
        "ok": True,
        "questions": generate_questions(request.get_json())
    })


# ---------------------------------------------------------
# Word
# ---------------------------------------------------------

def docx_bytes(qs, meta):

    d = Document()

    d.styles["Normal"].font.name = "Arial"
    d.styles["Normal"].font.size = Pt(11)

    # العنوان
    p = d.add_paragraph()
    p.alignment = 1

    r = p.add_run(meta.get("title", "مستند تعليمي"))
    r.bold = True
    r.font.size = Pt(16)

    # بيانات الطالب
    student = d.add_paragraph()
    student.alignment = 2

    r = student.add_run("اسم الطالب: ______________________________")
    r.bold = True

    # بيانات المستند
    info = []

    for k in [
        "stage",
        "grade",
        "subject",
        "term",
        "unit",
        "teacher",
        "school"
    ]:
        if meta.get(k):
            info.append(str(meta[k]))

    if info:
        p = d.add_paragraph()
        p.alignment = 2
        p.add_run(" | ".join(info))

    d.add_paragraph("")

    # الأسئلة
    for q in qs:

        p = d.add_paragraph()
        p.paragraph_format.space_after = Pt(2)

        r = p.add_run(f"{q['n']}. {q['text']}")
        r.bold = True

        # الاختيار من متعدد في سطر واحد
        if q.get("options"):

            p = d.add_paragraph()
            p.paragraph_format.space_after = Pt(3)

            if q["type"] == "اختيار من متعدد":
                p.add_run("    ".join(q["options"]))

            else:
                p.add_run("    ".join(q["options"]))

    b = io.BytesIO()
    d.save(b)

    return b.getvalue()


# ---------------------------------------------------------
# PDF
# ---------------------------------------------------------

def pdf_bytes(qs, meta):

    b = io.BytesIO()

    c = canvas.Canvas(b, pagesize=A4)

    w, h = A4

    right = w - 35
    y = h - 35

    # العنوان
    c.setFont("Helvetica-Bold", 15)
    c.drawRightString(
        right,
        y,
        meta.get("title", "مستند تعليمي")
    )

    y -= 25

    # اسم الطالب
    c.setFont("Helvetica-Bold", 11)
    c.drawRightString(
        right,
        y,
        "اسم الطالب: ______________________________"
    )

    y -= 22

    # البيانات
    c.setFont("Helvetica", 9)

    info = []

    for k in [
        "stage",
        "grade",
        "subject",
        "term",
        "unit",
        "teacher",
        "school"
    ]:
        if meta.get(k):
            info.append(str(meta[k]))

    if info:
        c.drawRightString(
            right,
            y,
            " | ".join(info)[:120]
        )

        y -= 20

    # خط فاصل
    c.line(35, y, w - 35, y)

    y -= 18

    # الأسئلة
    for q in qs:

        question = f"{q['n']}. {q['text']}"

        if y < 55:
            c.showPage()
            y = h - 40

        c.setFont("Helvetica-Bold", 9)

        c.drawRightString(
            right,
            y,
            question[:125]
        )

        y -= 13

        # الاختيارات في سطر واحد
        if q.get("options"):

            c.setFont("Helvetica", 8.5)

            if q["type"] == "اختيار من متعدد":

                options_line = "    ".join(q["options"])

                c.drawRightString(
                    right,
                    y,
                    options_line[:125]
                )

                y -= 13

            else:

                for option in q["options"]:

                    if y < 45:
                        c.showPage()
                        y = h - 40
                        c.setFont("Helvetica", 8.5)

                    c.drawRightString(
                        right,
                        y,
                        option[:125]
                    )

                    y -= 12

        # مسافة صغيرة فقط بين الأسئلة
        y -= 5

    c.save()

    return b.getvalue()


# ---------------------------------------------------------
# Export
# ---------------------------------------------------------

@app.post("/api/export")
def export():

    p = request.get_json()

    qs = p["questions"]
    meta = p["meta"]
    fmt = p["format"]

    if fmt == "pdf":

        return send_file(
            io.BytesIO(pdf_bytes(qs, meta)),
            as_attachment=True,
            download_name="المستند.pdf",
            mimetype="application/pdf"
        )

    if fmt == "docx":

        return send_file(
            io.BytesIO(docx_bytes(qs, meta)),
            as_attachment=True,
            download_name="المستند.docx",
            mimetype="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )

    z = io.BytesIO()

    with zipfile.ZipFile(
        z,
        "w",
        zipfile.ZIP_DEFLATED
    ) as f:

        f.writestr(
            "المستند.pdf",
            pdf_bytes(qs, meta)
        )

        f.writestr(
            "المستند.docx",
            docx_bytes(qs, meta)
        )

    z.seek(0)

    return send_file(
        z,
        as_attachment=True,
        download_name="المستندات.zip",
        mimetype="application/zip"
    )


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=5000
    )
