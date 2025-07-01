from flask import Flask, render_template, request,jsonify, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///data.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

@app.context_processor
def inject_now():
    return {'now': datetime.utcnow()}

class Record(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    epic = db.Column(db.String(50))
    ps = db.Column(db.String(50))
    old_house = db.Column(db.String(100))
    new_house = db.Column(db.String(100))
    payment = db.Column(db.Float, default=0.0)
    paid = db.Column(db.String(10))
    complete = db.Column(db.String(10))
    wife_name = db.Column(db.String(100), default='')
    wife_payment = db.Column(db.Float, default=0.0)
    wife_paid = db.Column(db.String(10), default='')
    wife_complete = db.Column(db.String(10), default='')
    remark = db.Column(db.String(255)) # ✅ Now inside the class!


with app.app_context():
    db.create_all()

@app.route('/')
def index():
    return render_template('index.html', records=Record.query.all())

@app.route('/add', methods=['GET', 'POST'])
def add():
    if request.method == 'POST':
        rec = Record(
            name=request.form['name'], epic=request.form['epic'], ps=request.form['ps'],
            old_house=request.form['old_house'], new_house=request.form['new_house'],
            payment=float(request.form.get('payment') or 0),
            paid=request.form['paid'], complete=request.form['complete'],
            wife_name=request.form.get('wife_name', ''),
            wife_payment=float(request.form.get('wife_payment') or 0),
            wife_paid=request.form.get('wife_paid', ''),
            wife_complete=request.form.get('wife_complete', '')
        )
        db.session.add(rec); db.session.commit()
        return redirect(url_for('index'))
    return render_template('form.html', action='Add', rec=None)

@app.route('/edit/<int:id>', methods=['GET', 'POST'])
def edit(id):
    rec = Record.query.get_or_404(id)
    if request.method == 'POST':
        rec.name = request.form['name']; rec.epic = request.form['epic']
        rec.ps = request.form['ps']; rec.old_house = request.form['old_house']
        rec.new_house = request.form['new_house']
        rec.payment = float(request.form.get('payment') or 0)
        rec.paid = request.form['paid']; rec.complete = request.form['complete']
        rec.wife_name = request.form.get('wife_name', '')
        rec.wife_payment = float(request.form.get('wife_payment') or 0)
        rec.wife_paid = request.form.get('wife_paid', '')
        rec.wife_complete = request.form.get('wife_complete', '')
        db.session.commit(); return redirect(url_for('index'))
    return render_template('form.html', action='Edit', rec=rec)

@app.route('/delete/<int:id>', methods=['POST'])
def delete(id):
    rec = Record.query.get_or_404(id)
    db.session.delete(rec); db.session.commit()
    return redirect(url_for('index'))

@app.route('/update_remark', methods=['POST'])
def update_remark():
    id = request.form['id']
    remark = request.form['remark']
    # Update DB here
    record = Record.query.get(id)
    record.remark = remark
    db.session.commit()
    return '', 204



if __name__ == '__main__':
    app.run(debug=True)