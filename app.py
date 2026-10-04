@app.route("/api/generate-test", methods=["POST"])
@app.route("/generate-test", methods=["POST"])
@app.route("/create-test", methods=["POST"])
@app.route("/generate", methods=["POST"])
@app.route("/generate_exam", methods=["POST"])
@app.route("/create_exam", methods=["POST"])
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
