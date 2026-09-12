
import json
import os
import re
import zipfile
from pathlib import Path
from typing import List

from flask import Flask, jsonify, render_template, request, send_file
from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Pt
from openai import OpenAI
from pydantic import BaseModel, Field
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

import arabic_reshaper
from bidi.algorithm import get_display


BASE_DIR = Path(__file__).resolve().parent
DATA = BASE_DIR / "data" / "curriculum.json"

app = Flask(__name__)

# النموذج الافتراضي: سريع وتكلفته مناسبة لتوليد عدد كبير من الأسئلة.
OPENAI_MODEL = os.environ.get("OPENAI_MODEL", "gpt-5.6-luna")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "").strip()


# -----------------------------
# تحميل بيانات المناهج
# -----------------------------
def curriculum():
    with open(DATA, "r", encoding="utf-8") as f:
        return json.load(f)


# -----------------------------
# نماذج المخرجات المنظمة من الذكاء الاصطناعي
# -----------------------------
class AIQuestion(BaseModel):
    type: str = Field(description="نوع السؤال بالعربية")
    lesson: str = Field(description="اسم الدرس الذي بُني عليه السؤال")
    text: str = Field(description="نص السؤال")
    options: List[str] = Field(default_factory=list, description="الخيارات إن وجدت")
    answer: str = Field(default="", description="الإجابة الصحيحة")
    explanation: str = Field(default="", description="تفسير مختصر للإجابة")


class AIQuestionSet(BaseModel):
    questions: List[AIQuestion]


# -----------------------------
# أدوات مساعدة
# -----------------------------
TYPE_LABELS = {
    "mcq": "اختيار من متعدد",
    "tf": "صح أو خطأ",
    "fill": "أكمل الفراغ",
    "match": "توصيل الكلمة بالمصطلح المناسب",
    "imageMatch": "توصيل الكلمة بالصورة المناسبة",
}


def int_count(value):
    try:
        return max(0, min(50, int(value or 0)))
    except Exception:
        return 0


def total_requested(counts):
    return sum(int_count(counts.get(k, 0)) for k in TYPE_LABELS)


def strip_option_prefix(value):
    """يحذف أي ترقيم/حروف سابقة من الخيار حتى نعيد ترقيمه 1-4 بشكل موحد."""
    value = str(value or "").strip()
    patterns = [
        r"^\s*[1-4]\s*[\.\-\)\:]\s*",
        r"^\s*[أبجد]\s*[\.\-\)\:]\s*",
        r"^\s*[أبجد]\s*\)\s*",
    ]
    for pattern in patterns:
        value = re.sub(pattern, "", value, count=1)
    return value.strip()


def numbered_mcq_options(options):
    """يعيد أول أربعة خيارات مرقمة من 1 إلى 4."""
    clean = [strip_option_prefix(x) for x in (options or [])]
    clean = [x for x in clean if x][:4]
    return [f"{i}. {value}" for i, value in enumerate(clean, start=1)]


def compact_term(term):
    """يختصر 'الفصل الدراسي الأول' إلى 'الأول' للعنوان المختصر."""
    term = str(term or "").strip()
    return term.replace("الفصل الدراسي ", "").strip() or term


def normalize_lessons(payload):
    lessons = payload.get("lessons") or []
    clean = []
    for x in lessons:
        if isinstance(x, str) and x.strip():
            clean.append(x.strip())
    return clean


def selected_curriculum_context(payload):
    """
    يحاول إحضار الوحدة المرتبطة بكل درس مختار من curriculum.json
    حتى يكون توليد الأسئلة أدق.
    """
    grade = payload.get("grade", "")
    subject = payload.get("subject", "")
    term = payload.get("term", "")
    track = payload.get("track", "")
    lessons = set(normalize_lessons(payload))

    if not grade or not subject or not term:
        return []

    data = curriculum().get("curriculum", {})
    grade_data = data.get(grade, {})

    # السنة الثانية والثالثة قد تكون داخل مسار.
    if track and isinstance(grade_data, dict) and track in grade_data:
        grade_data = grade_data.get(track, {})

    subject_data = grade_data.get(subject, {}) if isinstance(grade_data, dict) else {}
    term_data = subject_data.get(term, {}) if isinstance(subject_data, dict) else {}

    result = []
    if isinstance(term_data, dict):
        for unit_name, unit_lessons in term_data.items():
            if not isinstance(unit_lessons, list):
                continue
            selected = [l for l in unit_lessons if l in lessons]
            if selected:
                result.append({
                    "unit": unit_name,
                    "lessons": selected,
                })
    return result


def build_generation_prompt(payload):
    counts = payload.get("counts") or {}
    lessons = normalize_lessons(payload)
    lesson_details = payload.get("lessonDetails") or selected_curriculum_context(payload)

    stage = payload.get("stage", "")
    grade = payload.get("grade", "")
    track = payload.get("track", "")
    subject = payload.get("subject", "")
    term = payload.get("term", "")
    document_type = payload.get("documentType", "اختبار")
    difficulty = payload.get("difficulty", "متوسط")

    requested = []
    for key, label in TYPE_LABELS.items():
        n = int_count(counts.get(key, 0))
        if n:
            requested.append(f"- {label}: {n}")

    context_text = json.dumps(lesson_details, ensure_ascii=False, indent=2) if lesson_details else json.dumps(lessons, ensure_ascii=False)

    return f"""
أنت معلم خبير في المناهج السعودية. أنشئ أسئلة تعليمية دقيقة ومناسبة للمرحلة والصف والمادة المحددة.

بيانات الطلب:
- المرحلة: {stage}
- الصف: {grade}
- المسار: {track or "لا يوجد"}
- المادة: {subject}
- الفصل الدراسي: {term}
- نوع المستند: {document_type}
- مستوى الصعوبة: {difficulty}

الدروس والوحدات المختارة:
{context_text}

عدد الأسئلة المطلوبة حسب النوع:
{chr(10).join(requested)}

قواعد إلزامية:
1) أنشئ العدد المطلوب بالضبط دون زيادة أو نقص.
2) وزع الأسئلة على الدروس المختارة قدر الإمكان، ولا تخرج عن موضوعها.
3) اجعل صياغة السؤال مناسبة لعمر الطالب والصف الدراسي.
4) في الاختيار من متعدد:
   - أعطِ 4 خيارات فقط.
   - خيار واحد صحيح بوضوح.
   - اجعل الخيارات متقاربة ومعقولة.
   - لا تضع أرقامًا أو حروفًا قبل نص الخيار؛ النظام سيقوم بترقيم الخيارات من 1 إلى 4 تلقائيًا.
5) في صح أو خطأ:
   - اجعل العبارة تعليمية واضحة.
   - answer يجب أن يكون "صح" أو "خطأ".
6) في أكمل الفراغ:
   - ضع فراغًا واضحًا داخل الجملة.
   - answer يحتوي الكلمة أو العبارة المطلوبة.
7) في التوصيل:
   - ضع عناصر التوصيل داخل options بصورة واضحة، مثل:
     "1) المصطلح الأول  —  أ) التعريف"
8) في توصيل الكلمة بالصورة:
   - لا تنشئ روابط صور.
   - اجعل options أوصافًا قصيرة لصور تعليمية يمكن إضافتها لاحقًا.
9) لا تستخدم أسئلة وهمية مثل "اختر الإجابة الصحيحة عن الدرس"؛ يجب أن يكون لكل سؤال محتوى حقيقي.
10) لا تذكر أنك نموذج ذكاء اصطناعي.
11) إذا كانت المادة لغة إنجليزية، اجعل السؤال باللغة المناسبة لمحتوى الكتاب، ويمكن أن يكون الشرح بالعربية عند الحاجة.
12) explanation مختصر جدًا ومفيد للمعلم.
"""


def fallback_questions(payload):
    """
    وضع احتياطي حتى لا يتعطل الموقع إذا لم تتم إضافة مفتاح API بعد.
    الأسئلة هنا تجريبية فقط، ويظهر ذلك في رسالة API.
    """
    counts = payload.get("counts") or {}
    lessons = normalize_lessons(payload) or ["الدرس المحدد"]
    out = []
    n = 1

    for key, label in TYPE_LABELS.items():
        for _ in range(int_count(counts.get(key, 0))):
            lesson = lessons[(n - 1) % len(lessons)]

            if key == "mcq":
                text = f"اختر الإجابة الصحيحة المرتبطة بمفهوم رئيس في درس «{lesson}»."
                options = ["الخيار الأول", "الخيار الثاني", "الخيار الثالث", "الخيار الرابع"]
                answer = ""
            elif key == "tf":
                text = f"صح أم خطأ: اكتب حكم العبارة المتعلقة بدرس «{lesson}»."
                options = []
                answer = ""
            elif key == "fill":
                text = f"أكمل الفراغ بمعلومة صحيحة من درس «{lesson}»: __________."
                options = []
                answer = ""
            elif key == "match":
                text = f"صل بين عناصر درس «{lesson}» وما يناسبها."
                options = ["1) __________   أ) __________", "2) __________   ب) __________"]
                answer = ""
            else:
                text = f"صل الكلمة بوصف الصورة المناسبة من درس «{lesson}»."
                options = ["1) __________   أ) [وصف صورة]", "2) __________   ب) [وصف صورة]"]
                answer = ""

            out.append({
                "n": n,
                "type": label,
                "lesson": lesson,
                "text": text,
                "options": options,
                "answer": answer,
                "explanation": "",
            })
            n += 1

    return out


def ai_generate_questions(payload):
    counts = payload.get("counts") or {}
    total = total_requested(counts)

    if total <= 0:
        raise ValueError("اختر عدداً واحداً على الأقل من الأسئلة.")
    if total > 50:
        raise ValueError("الحد الأقصى في عملية توليد واحدة هو 50 سؤالاً.")
    if not normalize_lessons(payload):
        raise ValueError("اختر درساً واحداً على الأقل.")

    if not OPENAI_API_KEY:
        return fallback_questions(payload), False, "لم تتم إضافة OPENAI_API_KEY بعد؛ تم استخدام الوضع التجريبي."

    client = OpenAI(api_key=OPENAI_API_KEY)
    prompt = build_generation_prompt(payload)

    response = client.responses.parse(
        model=OPENAI_MODEL,
        input=[
            {
                "role": "system",
                "content": (
                    "أنت معلم خبير في بناء الاختبارات وفق المناهج السعودية. "
                    "التزم بدقة بالصف والمادة والدروس المختارة، ولا تختلق معلومات خارجها."
                ),
            },
            {"role": "user", "content": prompt},
        ],
        text_format=AIQuestionSet,
    )

    parsed = response.output_parsed
    if not parsed or not parsed.questions:
        raise RuntimeError("لم يرجع النموذج أسئلة صالحة.")

    questions = []
    for i, q in enumerate(parsed.questions[:total], start=1):
        options = q.options or []
        if q.type == "اختيار من متعدد":
            options = [strip_option_prefix(x) for x in options][:4]

        questions.append({
            "n": i,
            "type": q.type,
            "lesson": q.lesson,
            "text": q.text,
            "options": options,
            "answer": q.answer or "",
            "explanation": q.explanation or "",
        })

    # إذا رجع عددًا أقل لأي سبب، نعد المحاولة خطأ بدل عرض مستند ناقص.
    if len(questions) != total:
        raise RuntimeError(f"تم توليد {len(questions)} سؤالاً فقط من أصل {total}. أعد المحاولة.")

    return questions, True, f"تم التوليد بالذكاء الاصطناعي باستخدام {OPENAI_MODEL}."


# -----------------------------
# Routes
# -----------------------------
@app.get("/")
def home():
    return render_template("index.html", data=curriculum())


@app.get("/api/health")
def health():
    return jsonify({
        "ok": True,
        "ai_enabled": bool(OPENAI_API_KEY),
        "model": OPENAI_MODEL if OPENAI_API_KEY else None,
    })


@app.post("/api/generate")
def gen():
    try:
        payload = request.get_json(force=True) or {}
        questions, ai_used, message = ai_generate_questions(payload)
        return jsonify({
            "ok": True,
            "questions": questions,
            "ai_used": ai_used,
            "message": message,
        })
    except Exception as e:
        return jsonify({
            "ok": False,
            "error": str(e),
        }), 400


# -----------------------------
# Word
# -----------------------------
def set_rtl(paragraph):
    paragraph.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    pPr = paragraph._p.get_or_add_pPr()
    bidi = OxmlElement("w:bidi")
    bidi.set(qn("w:val"), "1")
    pPr.append(bidi)


def add_docx_line(doc, text="", bold=False, size=12, center=False):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER if center else WD_ALIGN_PARAGRAPH.RIGHT
    if not center:
        set_rtl(p)
    r = p.add_run(str(text))
    r.bold = bold
    r.font.name = "Arial"
    r.font.size = Pt(size)
    return p


def docx_bytes(qs, meta):
    d = Document()
    d.styles["Normal"].font.name = "Arial"
    d.styles["Normal"].font.size = Pt(12)

    title = meta.get("title") or meta.get("documentType") or "مستند تعليمي"
    add_docx_line(d, title, bold=True, size=18, center=True)

    # بيانات المستند المختصرة في سطر واحد فوق اسم الطالب
    subject = str(meta.get("subject") or "—")
    grade = str(meta.get("grade") or "—")
    term = compact_term(meta.get("term"))
    teacher = str(meta.get("teacher") or "—")
    info_line = (
        f"المادة: {subject}  |  الصف: {grade}  |  "
        f"الفصل الدراسي: {term or '—'}  |  المعلم: {teacher}"
    )
    add_docx_line(d, info_line, bold=True, size=11)

    p = d.add_paragraph()
    set_rtl(p)
    r = p.add_run("اسم الطالب/ـة: ______________________________")
    r.bold = True
    r.font.name = "Arial"
    r.font.size = Pt(12)

    d.add_paragraph("")

    for q in qs:
        add_docx_line(d, f"{q.get('n', '')}. {q.get('text', '')}", bold=True)

        opts = q.get("options") or []
        if opts:
            # خيارات الاختيار من متعدد في سطر واحد
            if q.get("type") == "اختيار من متعدد":
                add_docx_line(d, "     ".join(numbered_mcq_options(opts)), size=11)
            else:
                for x in opts:
                    add_docx_line(d, x, size=11)

        d.add_paragraph("")

    b = io.BytesIO()
    d.save(b)
    b.seek(0)
    return b.getvalue()


# -----------------------------
# PDF عربي
# -----------------------------
def find_arabic_font():
    candidates = [
        BASE_DIR / "static" / "fonts" / "DejaVuSans.ttf",
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
        Path("/usr/share/fonts/truetype/noto/NotoNaskhArabic-Regular.ttf"),
        Path("/usr/share/fonts/opentype/noto/NotoNaskhArabic-Regular.ttf"),
    ]
    for p in candidates:
        if p.exists():
            return str(p)
    return None


ARABIC_FONT_PATH = find_arabic_font()
PDF_FONT = "Helvetica"

if ARABIC_FONT_PATH:
    try:
        pdfmetrics.registerFont(TTFont("ArabicFont", ARABIC_FONT_PATH))
        PDF_FONT = "ArabicFont"
    except Exception:
        PDF_FONT = "Helvetica"


def ar(text):
    text = str(text or "")
    if PDF_FONT == "Helvetica":
        return text
    return get_display(arabic_reshaper.reshape(text))


def wrap_text(text, max_chars=85):
    text = str(text or "")
    words = text.split()
    lines, current = [], []
    length = 0

    for word in words:
        extra = len(word) + (1 if current else 0)
        if length + extra > max_chars and current:
            lines.append(" ".join(current))
            current = [word]
            length = len(word)
        else:
            current.append(word)
            length += extra

    if current:
        lines.append(" ".join(current))
    return lines or [""]


def pdf_bytes(qs, meta):
    b = io.BytesIO()
    c = canvas.Canvas(b, pagesize=A4)
    w, h = A4
    y = h - 45

    def new_page():
        nonlocal y
        c.showPage()
        y = h - 45
        c.setFont(PDF_FONT, 11)

    def draw_right(text, font_size=11, gap=16):
        nonlocal y
        c.setFont(PDF_FONT, font_size)
        for line in wrap_text(text):
            if y < 50:
                new_page()
                c.setFont(PDF_FONT, font_size)
            c.drawRightString(w - 40, y, ar(line))
            y -= gap

    title = meta.get("title") or meta.get("documentType") or "مستند تعليمي"
    draw_right(title, 17, 22)

    # بيانات المستند المختصرة في سطر واحد فوق اسم الطالب
    subject = str(meta.get("subject") or "—")
    grade = str(meta.get("grade") or "—")
    term = compact_term(meta.get("term"))
    teacher = str(meta.get("teacher") or "—")
    info_line = (
        f"المادة: {subject} | الصف: {grade} | "
        f"الفصل الدراسي: {term or '—'} | المعلم: {teacher}"
    )
    draw_right(info_line, 10, 17)
    draw_right("اسم الطالب/ـة: ______________________________", 11, 19)

    y -= 8

    for q in qs:
        draw_right(f"{q.get('n', '')}. {q.get('text', '')}", 11, 17)
        opts = q.get("options") or []

        if opts:
            if q.get("type") == "اختيار من متعدد":
                draw_right("     ".join(numbered_mcq_options(opts)), 9, 15)
            else:
                for x in opts:
                    draw_right(x, 9, 14)
        y -= 7

    c.save()
    b.seek(0)
    return b.getvalue()


@app.post("/api/export")
def export():
    try:
        p = request.get_json(force=True) or {}
        qs = p.get("questions") or []
        meta = p.get("meta") or {}
        fmt = (p.get("format") or "pdf").lower()

        if fmt == "pdf":
            return send_file(
                io.BytesIO(pdf_bytes(qs, meta)),
                as_attachment=True,
                download_name="المستند.pdf",
                mimetype="application/pdf",
            )

        if fmt == "docx":
            return send_file(
                io.BytesIO(docx_bytes(qs, meta)),
                as_attachment=True,
                download_name="المستند.docx",
                mimetype="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )

        z = io.BytesIO()
        with zipfile.ZipFile(z, "w", zipfile.ZIP_DEFLATED) as f:
            f.writestr("المستند.pdf", pdf_bytes(qs, meta))
            f.writestr("المستند.docx", docx_bytes(qs, meta))

        z.seek(0)
        return send_file(
            z,
            as_attachment=True,
            download_name="المستندات.zip",
            mimetype="application/zip",
        )
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 400


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "5000"))
    app.run(host="0.0.0.0", port=port)
