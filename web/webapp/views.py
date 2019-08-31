"""Routes and templating"""
from flask import (
    Response,
    render_template,
    redirect,
    request,
    abort,
    jsonify,
)

from .app import app, db
from .models import Inquiry

from operator import itemgetter
from fuzzywuzzy import fuzz

DEVICE_PIN = 1234
AUTH_TOKEN = 'Token @hvmnt100'


@app.errorhandler(401)
def custom_401(error):
    return Response('Unauthorized: Invalid or missing token.', 401, {'WWW-Authenticate':'Basic realm="Login Required"'})


@app.route('/', methods=['GET'])
def index():
    """Main route. Redirects to dashboard"""
    return redirect('/dashboard')


@app.route('/dashboard/', methods=['GET'])
def dashboard():
    """Route for official Talking Cub Dahsboard"""
    inquiries = [
        dict(
            id = inquiry._id,
            question = str(inquiry.question),
            answer = str(inquiry.answer),
            times_asked = inquiry.times_asked
        ) for inquiry in Inquiry.query.all()
    ]
    return render_template('dashboard.html', inquiries=inquiries)


@app.route('/dashboard/inquiry/<int:inquiry_id>/', methods=['GET', 'POST'])
def edit_inquiry(inquiry_id):
    """Page to edit each question/answer."""
    inquiry_obj = Inquiry.query.get(inquiry_id)
    if request.method == 'GET':
        inquiry = dict(
            id = inquiry_id,
            question = inquiry_obj.question,
            answer = inquiry_obj.answer,
            times_asked = inquiry_obj.times_asked
        )
        return render_template('inquiry.html', inquiry=inquiry)
    elif request.method == 'POST':
        pin = int(request.form['pin']) if any(request.form['pin']) else None
        # Authorizing through an individual speaker PIN
        # TODO get this from an env var
        if pin is None or pin != DEVICE_PIN:
            return "UNAUTHORIZED: WRONG PIN"
        # Update object
        inquiry_obj.question = str(request.form['question'])
        inquiry_obj.answer = str(request.form['answer'])
        db.session.commit()
        return redirect("/")


@app.route('/api/v1/answer/', methods=['GET'])
def get_answer():
    token = request.headers.get('Authorization')
    if token is None or token != AUTH_TOKEN:
        abort(401)
    question = request.args.get('question')

    inquiries = [(
        inquiry, fuzz.ratio(inquiry.question, question)
    ) for inquiry in Inquiry.query.all()] # [(<Inquiry Obj>, 70), ... ]

    # Get tuple (Inquiry_obj, acc) with highest accuracy
    best_inquiry, accuracy = max(inquiries, key=itemgetter(1))

    # Increase times_asked just if almost sure it was asked
    if accuracy >= 80:
        best_inquiry.times_asked += 1

    # Build response
    response = dict(
        question = best_inquiry.question.lower(),
        answer = best_inquiry.answer.lower(),
        accuracy = accuracy,
        times_asked = best_inquiry.times_asked
    )
    db.session.commit()
    return jsonify(response)
    