import io,json,os,zipfile
from flask import Flask,render_template,request,jsonify,send_file
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from docx import Document
from docx.shared import Pt
app=Flask(__name__)
DATA='data/curriculum.json'

def curriculum():
    with open(DATA,encoding='utf8') as f:return json.load(f)

def generate_questions(p):
    c=p['counts']; lessons=p['lessons']; out=[]; n=1
    types=[('mcq','اختيار من متعدد'),('tf','صح أو خطأ'),('fill','أكمل الفراغ'),('match','صل الكلمة بالمصطلح المناسب'),('imageMatch','صل الكلمة بالصورة المناسبة')]
    for key,label in types:
        for _ in range(int(c.get(key,0))):
            lesson=lessons[(n-1)%len(lessons)] if lessons else 'الدرس المحدد'
            if key=='mcq': text=f'اختر الإجابة الصحيحة وفق محتوى «{lesson}».'; opts=['أ) الإجابة الأولى','ب) الإجابة الثانية','ج) الإجابة الثالثة','د) الإجابة الرابعة']
            elif key=='tf': text=f'صح أم خطأ: العبارة التالية مرتبطة بمحتوى «{lesson}».'; opts=[]
            elif key=='fill': text=f'أكمل الفراغ من محتوى «{lesson}»: __________.'; opts=[]
            elif key=='match': text=f'صل عناصر «{lesson}» بالمصطلحات المناسبة.'; opts=['(1) __________   (أ) __________','(2) __________   (ب) __________']
            else: text=f'صل الكلمة بالصورة المناسبة من محتوى «{lesson}».'; opts=['[صورة 1]   [صورة 2]   [صورة 3]']
            out.append({'n':n,'type':label,'lesson':lesson,'text':text,'options':opts}); n+=1
    return out

@app.get('/')
def home(): return render_template('index.html',data=curriculum())
@app.post('/api/generate')
def gen(): return jsonify({'ok':True,'questions':generate_questions(request.get_json())})

def docx_bytes(qs,meta):
    d=Document(); d.styles['Normal'].font.name='Arial'; d.styles['Normal'].font.size=Pt(12)
    p=d.add_paragraph(); p.alignment=1; r=p.add_run(meta.get('title','مستند تعليمي')); r.bold=True; r.font.size=Pt(18)
    for k in ['stage','grade','subject','term','unit','teacher','school']:
        if meta.get(k): d.add_paragraph(str(meta[k]))
    for q in qs:
        d.add_paragraph(f"{q['n']}. {q['text']}").runs[0].bold=True
        for x in q.get('options',[]): d.add_paragraph(x)
    b=io.BytesIO(); d.save(b); return b.getvalue()

def pdf_bytes(qs,meta):
    b=io.BytesIO(); c=canvas.Canvas(b,pagesize=A4); w,h=A4; y=h-45
    c.setFont('Helvetica-Bold',16); c.drawRightString(w-40,y,meta.get('title','مستند تعليمي')); y-=25
    c.setFont('Helvetica',10)
    for k in ['stage','grade','subject','term','unit','teacher','school']:
        if meta.get(k): c.drawRightString(w-40,y,str(meta[k])[:110]); y-=15
    c.setFont('Helvetica',10)
    for q in qs:
        for line in [f"{q['n']}. {q['text']}"]+q.get('options',[]):
            if y<45:c.showPage();y=h-45;c.setFont('Helvetica',10)
            c.drawRightString(w-40,y,line[:115]);y-=16
        y-=7
    c.save(); return b.getvalue()

@app.post('/api/export')
def export():
    p=request.get_json(); qs=p['questions']; meta=p['meta']; fmt=p['format']
    if fmt=='pdf': return send_file(io.BytesIO(pdf_bytes(qs,meta)),as_attachment=True,download_name='المستند.pdf',mimetype='application/pdf')
    if fmt=='docx': return send_file(io.BytesIO(docx_bytes(qs,meta)),as_attachment=True,download_name='المستند.docx',mimetype='application/vnd.openxmlformats-officedocument.wordprocessingml.document')
    z=io.BytesIO()
    with zipfile.ZipFile(z,'w',zipfile.ZIP_DEFLATED) as f:f.writestr('المستند.pdf',pdf_bytes(qs,meta));f.writestr('المستند.docx',docx_bytes(qs,meta))
    z.seek(0);return send_file(z,as_attachment=True,download_name='المستندات.zip',mimetype='application/zip')
if __name__=='__main__':app.run(host='0.0.0.0',port=5000)
