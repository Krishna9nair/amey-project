import os
import sqlite3
from datetime import date, datetime
from functools import wraps

from flask import (
    Flask,
    abort,
    flash,
    g,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from werkzeug.security import check_password_hash, generate_password_hash

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DATABASE = os.environ.get("DATABASE_PATH", os.path.join(BASE_DIR, "college.db"))

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-secret-change-me")

CATEGORIES = ["Technical", "Cultural", "Sports", "Literary", "Social"]
CATEGORY_ICONS = {
    "Technical": "cpu",
    "Cultural": "music-note-beamed",
    "Sports": "trophy",
    "Literary": "book",
    "Social": "heart",
}
DEPARTMENTS = [
    "Computer Engineering",
    "Information Technology",
    "Electronics",
    "Electrical",
    "Mechanical",
    "Civil",
    "Other",
]
YEARS = ["First Year", "Second Year", "Third Year", "Final Year"]
ALLOWED_EMAIL_DOMAIN = "student.mes.ac.in"
HOME_ENDPOINTS = {"admin": "admin_dashboard", "club_admin": "club_admin_dashboard", "student": "dashboard"}
ADMIN_EMAIL = os.environ.get("ADMIN_EMAIL", "admin@mes.ac.in")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "admin123")
DEFAULT_CLUB_ADMIN_PASSWORD = os.environ.get("CLUB_ADMIN_PASSWORD", "club123")


def is_college_email(email):
    local, _, domain = email.partition("@")
    return bool(local) and domain == ALLOWED_EMAIL_DOMAIN and " " not in email


def is_valid_email(email):
    local, _, domain = email.partition("@")
    return bool(local) and "." in domain and " " not in email


# ---------------------------------------------------------------- database

def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DATABASE)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


@app.teardown_appcontext
def close_db(exc):
    db = g.pop("db", None)
    if db is not None:
        db.close()


SAMPLE_CLUBS = [
    ("Coding Club", "Technical", "Competitive programming, hackathons and open-source contributions.", "Prof. R. Sharma", "coding@mes.ac.in"),
    ("Robotics Club", "Technical", "Design, build and program robots for national-level competitions.", "Prof. A. Kulkarni", "robotics@mes.ac.in"),
    ("Music Club", "Cultural", "Vocalists, instrumentalists and bands performing at every college event.", "Prof. S. Iyer", "music@mes.ac.in"),
    ("Dance Club", "Cultural", "Classical, western and street dance crews for intercollegiate fests.", "Prof. M. Desai", "dance@mes.ac.in"),
    ("Sports Club", "Sports", "Cricket, football, basketball and athletics teams and tournaments.", "Prof. V. Patil", "sports@mes.ac.in"),
    ("Literary Society", "Literary", "Debates, creative writing, poetry slams and the college magazine.", "Prof. N. Joshi", "literary@mes.ac.in"),
    ("NSS Unit", "Social", "Community service, blood donation drives and social awareness camps.", "Prof. K. Menon", "nss@mes.ac.in"),
]

# (title, fest, club name, description, venue, date, time, max)
SAMPLE_EVENTS = [
    ("24-Hour Hackathon", "TechFest 2026", "Coding Club", "Build a working product in 24 hours in teams of up to 4. Prizes worth Rs. 50,000.", "Main Auditorium", "2026-10-15", "09:00", 120),
    ("Code Sprint", "TechFest 2026", "Coding Club", "Individual competitive programming contest with 6 problems in 2 hours.", "Computer Lab 3", "2026-10-16", "11:00", 80),
    ("Robo Wars", "TechFest 2026", "Robotics Club", "Bring your combat robot and battle it out in the arena.", "Open Ground", "2026-10-16", "14:00", 30),
    ("Battle of Bands", "Utsav 2026", "Music Club", "Live band competition. Each band gets 15 minutes on stage.", "Open Air Theatre", "2026-11-20", "18:00", 15),
    ("Dance Face-Off", "Utsav 2026", "Dance Club", "Solo and group dance competition across all styles.", "Main Auditorium", "2026-11-21", "16:00", 60),
    ("Parliamentary Debate", "Utsav 2026", "Literary Society", "Two-member teams debate on current affairs motions.", "Seminar Hall", "2026-11-21", "10:00", 40),
    ("Inter-Department Cricket", "Sports Meet 2026", "Sports Club", "Box cricket tournament between departments.", "Cricket Ground", "2026-12-05", "08:00", 88),
]


def init_db():
    db = sqlite3.connect(DATABASE)
    db.execute("PRAGMA foreign_keys = ON")
    with open(os.path.join(BASE_DIR, "schema.sql"), encoding="utf-8") as f:
        db.executescript(f.read())

    if db.execute("SELECT COUNT(*) FROM users WHERE role = 'admin'").fetchone()[0] == 0:
        db.execute(
            "INSERT INTO users (name, email, password_hash, role) VALUES (?, ?, ?, 'admin')",
            ("Administrator", ADMIN_EMAIL, generate_password_hash(ADMIN_PASSWORD)),
        )

    if db.execute("SELECT COUNT(*) FROM clubs").fetchone()[0] == 0:
        db.executemany(
            "INSERT INTO clubs (name, category, description, coordinator, contact_email) VALUES (?, ?, ?, ?, ?)",
            SAMPLE_CLUBS,
        )
        club_ids = {row[1]: row[0] for row in db.execute("SELECT id, name FROM clubs")}
        db.executemany(
            """INSERT INTO events (title, fest_name, club_id, description, venue,
                                   event_date, event_time, max_participants)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            [(t, f, club_ids.get(c), d, v, dt, tm, mx) for t, f, c, d, v, dt, tm, mx in SAMPLE_EVENTS],
        )
        db.executemany(
            "INSERT INTO users (name, email, password_hash, role, club_id) VALUES (?, ?, ?, 'club_admin', ?)",
            [(f"{name} Admin", email, generate_password_hash(DEFAULT_CLUB_ADMIN_PASSWORD), club_ids[name])
             for name, _, _, _, email in SAMPLE_CLUBS],
        )

    db.commit()
    db.close()


# ---------------------------------------------------------------- helpers

@app.before_request
def load_user():
    user_id = session.get("user_id")
    g.user = None
    g.club = None
    if user_id is not None:
        db = get_db()
        g.user = db.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
        if g.user is not None and g.user["role"] == "club_admin":
            g.club = db.execute("SELECT * FROM clubs WHERE id = ?", (g.user["club_id"],)).fetchone()


def current_portal():
    user = g.get("user")
    return "club_admin" if user is not None and user["role"] == "club_admin" else "admin"


@app.context_processor
def inject_globals():
    return {
        "user": g.get("user"),
        "my_club": g.get("club"),
        "portal": current_portal(),
        "category_icons": CATEGORY_ICONS,
        "today": date.today().isoformat(),
    }


@app.template_filter("fmt_date")
def fmt_date(value):
    try:
        return datetime.strptime(value, "%Y-%m-%d").strftime("%d %b %Y")
    except (TypeError, ValueError):
        return value


@app.template_filter("fmt_time")
def fmt_time(value):
    try:
        return datetime.strptime(value, "%H:%M").strftime("%I:%M %p")
    except (TypeError, ValueError):
        return value


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if g.user is None:
            flash("Please log in to continue.", "warning")
            return redirect(url_for("login", next=request.path))
        return view(*args, **kwargs)
    return wrapped


def student_required(view):
    @wraps(view)
    @login_required
    def wrapped(*args, **kwargs):
        if g.user["role"] != "student":
            flash("This action is only available to student accounts.", "warning")
            return redirect(request.referrer or url_for("index"))
        return view(*args, **kwargs)
    return wrapped


def admin_required(view):
    @wraps(view)
    @login_required
    def wrapped(*args, **kwargs):
        if g.user["role"] != "admin":
            abort(403)
        return view(*args, **kwargs)
    return wrapped


def club_admin_required(view):
    @wraps(view)
    @login_required
    def wrapped(*args, **kwargs):
        if g.user["role"] != "club_admin" or g.club is None:
            abort(403)
        return view(*args, **kwargs)
    return wrapped


def get_club_or_404(club_id):
    club = get_db().execute("SELECT * FROM clubs WHERE id = ?", (club_id,)).fetchone()
    if club is None:
        abort(404)
    return club


def get_event_or_404(event_id):
    event = get_db().execute(
        """SELECT e.*, c.name AS club_name,
                  (SELECT COUNT(*) FROM registrations r WHERE r.event_id = e.id) AS reg_count
           FROM events e LEFT JOIN clubs c ON c.id = e.club_id
           WHERE e.id = ?""",
        (event_id,),
    ).fetchone()
    if event is None:
        abort(404)
    return event


# ---------------------------------------------------------------- public pages

@app.route("/")
def index():
    db = get_db()
    stats = {
        "clubs": db.execute("SELECT COUNT(*) FROM clubs").fetchone()[0],
        "events": db.execute("SELECT COUNT(*) FROM events").fetchone()[0],
        "students": db.execute("SELECT COUNT(*) FROM users WHERE role = 'student'").fetchone()[0],
        "registrations": db.execute("SELECT COUNT(*) FROM registrations").fetchone()[0],
    }
    upcoming = db.execute(
        """SELECT e.*, c.name AS club_name FROM events e
           LEFT JOIN clubs c ON c.id = e.club_id
           WHERE e.event_date >= ? ORDER BY e.event_date, e.event_time LIMIT 3""",
        (date.today().isoformat(),),
    ).fetchall()
    clubs = db.execute("SELECT * FROM clubs ORDER BY name LIMIT 6").fetchall()
    return render_template("index.html", stats=stats, upcoming=upcoming, clubs=clubs)


@app.route("/register", methods=["GET", "POST"])
def register():
    if g.user:
        return redirect(url_for("index"))

    form = {}
    if request.method == "POST":
        form = {k: request.form.get(k, "").strip() for k in ("name", "email", "roll_no", "department", "department_other", "year", "phone")}
        password = request.form.get("password", "")
        confirm = request.form.get("confirm_password", "")
        form["email"] = form["email"].lower()

        errors = []
        if len(form["name"]) < 2:
            errors.append("Please enter your full name.")
        if not is_college_email(form["email"]):
            errors.append(f"Only college email IDs ending with @{ALLOWED_EMAIL_DOMAIN} are allowed.")
        if not form["roll_no"]:
            errors.append("Roll number is required.")
        if form["department"] not in DEPARTMENTS:
            errors.append("Please select your department.")
        elif form["department"] == "Other" and len(form["department_other"]) < 2:
            errors.append("Please type your course / department.")
        if form["year"] not in YEARS:
            errors.append("Please select your year.")
        if not (form["phone"].isdigit() and len(form["phone"]) == 10):
            errors.append("Phone number must be 10 digits.")
        if len(password) < 6:
            errors.append("Password must be at least 6 characters.")
        if password != confirm:
            errors.append("Passwords do not match.")

        if not errors:
            department = form["department_other"] if form["department"] == "Other" else form["department"]
            db = get_db()
            try:
                db.execute(
                    """INSERT INTO users (name, email, password_hash, roll_no, department, year, phone)
                       VALUES (?, ?, ?, ?, ?, ?, ?)""",
                    (form["name"], form["email"], generate_password_hash(password),
                     form["roll_no"], department, form["year"], form["phone"]),
                )
                db.commit()
            except sqlite3.IntegrityError:
                errors.append("An account with this email already exists.")
            else:
                flash("Registration successful! Please log in.", "success")
                return redirect(url_for("login"))

        for e in errors:
            flash(e, "danger")

    return render_template("register.html", form=form, departments=DEPARTMENTS, years=YEARS)


@app.route("/login", methods=["GET", "POST"])
def login():
    if g.user:
        return redirect(url_for("index"))

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        user = get_db().execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()

        if user is None or not check_password_hash(user["password_hash"], password):
            flash("Invalid email or password.", "danger")
            return render_template("login.html", email=email)

        session.clear()
        session["user_id"] = user["id"]
        flash(f"Welcome back, {user['name']}!", "success")

        next_url = request.args.get("next", "")
        if next_url.startswith("/") and not next_url.startswith("//"):
            return redirect(next_url)
        return redirect(url_for(HOME_ENDPOINTS[user["role"]]))

    return render_template("login.html", email="")


@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for("index"))


# ---------------------------------------------------------------- clubs

@app.route("/clubs")
def clubs():
    db = get_db()
    all_clubs = db.execute(
        """SELECT c.*,
                  (SELECT COUNT(*) FROM memberships m
                   WHERE m.club_id = c.id AND m.status = 'approved') AS member_count
           FROM clubs c ORDER BY c.name"""
    ).fetchall()
    my_status = {}
    if g.user:
        my_status = {
            r["club_id"]: r["status"]
            for r in db.execute("SELECT club_id, status FROM memberships WHERE user_id = ?", (g.user["id"],))
        }
    return render_template("clubs.html", clubs=all_clubs, my_status=my_status, categories=CATEGORIES)


@app.route("/clubs/<int:club_id>")
def club_detail(club_id):
    db = get_db()
    club = get_club_or_404(club_id)
    member_count = db.execute(
        "SELECT COUNT(*) FROM memberships WHERE club_id = ? AND status = 'approved'", (club_id,)
    ).fetchone()[0]
    events = db.execute(
        "SELECT * FROM events WHERE club_id = ? ORDER BY event_date, event_time", (club_id,)
    ).fetchall()
    membership = None
    if g.user:
        membership = db.execute(
            "SELECT * FROM memberships WHERE club_id = ? AND user_id = ?", (club_id, g.user["id"])
        ).fetchone()
    return render_template("club_detail.html", club=club, member_count=member_count,
                           events=events, membership=membership)


@app.route("/clubs/<int:club_id>/join", methods=["POST"])
@student_required
def join_club(club_id):
    club = get_club_or_404(club_id)
    db = get_db()
    existing = db.execute(
        "SELECT status FROM memberships WHERE club_id = ? AND user_id = ?", (club_id, g.user["id"])
    ).fetchone()
    if existing is None:
        db.execute("INSERT INTO memberships (user_id, club_id) VALUES (?, ?)", (g.user["id"], club_id))
        flash(f"Membership request sent to {club['name']}. Awaiting approval.", "success")
    elif existing["status"] == "rejected":
        db.execute(
            "UPDATE memberships SET status = 'pending', joined_at = CURRENT_TIMESTAMP WHERE club_id = ? AND user_id = ?",
            (club_id, g.user["id"]),
        )
        flash(f"Membership request re-sent to {club['name']}.", "success")
    else:
        flash("You have already applied to this club.", "info")
    db.commit()
    return redirect(request.referrer or url_for("club_detail", club_id=club_id))


@app.route("/clubs/<int:club_id>/leave", methods=["POST"])
@student_required
def leave_club(club_id):
    club = get_club_or_404(club_id)
    db = get_db()
    db.execute("DELETE FROM memberships WHERE club_id = ? AND user_id = ?", (club_id, g.user["id"]))
    db.commit()
    flash(f"You have left {club['name']}.", "info")
    return redirect(request.referrer or url_for("club_detail", club_id=club_id))


# ---------------------------------------------------------------- events

@app.route("/events")
def events():
    db = get_db()
    fest = request.args.get("fest", "")
    query = """SELECT e.*, c.name AS club_name,
                      (SELECT COUNT(*) FROM registrations r WHERE r.event_id = e.id) AS reg_count
               FROM events e LEFT JOIN clubs c ON c.id = e.club_id"""
    params = ()
    if fest:
        query += " WHERE e.fest_name = ?"
        params = (fest,)
    query += " ORDER BY e.event_date, e.event_time"
    all_events = db.execute(query, params).fetchall()
    fests = [r[0] for r in db.execute("SELECT DISTINCT fest_name FROM events ORDER BY fest_name")]

    registered = set()
    if g.user:
        registered = {
            r[0] for r in db.execute("SELECT event_id FROM registrations WHERE user_id = ?", (g.user["id"],))
        }
    return render_template("events.html", events=all_events, fests=fests,
                           current_fest=fest, registered=registered)


@app.route("/events/<int:event_id>")
def event_detail(event_id):
    event = get_event_or_404(event_id)
    is_registered = False
    if g.user:
        is_registered = get_db().execute(
            "SELECT 1 FROM registrations WHERE event_id = ? AND user_id = ?", (event_id, g.user["id"])
        ).fetchone() is not None
    return render_template("event_detail.html", event=event, is_registered=is_registered)


@app.route("/events/<int:event_id>/register", methods=["POST"])
@student_required
def register_event(event_id):
    event = get_event_or_404(event_id)
    db = get_db()

    if event["event_date"] < date.today().isoformat():
        flash("Registration is closed for this event.", "warning")
    elif event["reg_count"] >= event["max_participants"]:
        flash("Sorry, this event is full.", "warning")
    else:
        try:
            db.execute("INSERT INTO registrations (user_id, event_id) VALUES (?, ?)", (g.user["id"], event_id))
            db.commit()
            flash(f"You are registered for {event['title']}!", "success")
        except sqlite3.IntegrityError:
            flash("You are already registered for this event.", "info")
    return redirect(request.referrer or url_for("event_detail", event_id=event_id))


@app.route("/events/<int:event_id>/cancel", methods=["POST"])
@student_required
def cancel_registration(event_id):
    event = get_event_or_404(event_id)
    db = get_db()
    db.execute("DELETE FROM registrations WHERE event_id = ? AND user_id = ?", (event_id, g.user["id"]))
    db.commit()
    flash(f"Your registration for {event['title']} was cancelled.", "info")
    return redirect(request.referrer or url_for("event_detail", event_id=event_id))


# ---------------------------------------------------------------- student dashboard

@app.route("/dashboard")
@login_required
def dashboard():
    if g.user["role"] != "student":
        return redirect(url_for(HOME_ENDPOINTS[g.user["role"]]))
    db = get_db()
    memberships = db.execute(
        """SELECT m.*, c.name, c.category FROM memberships m
           JOIN clubs c ON c.id = m.club_id
           WHERE m.user_id = ? ORDER BY m.joined_at DESC""",
        (g.user["id"],),
    ).fetchall()
    registrations = db.execute(
        """SELECT r.registered_at, e.* FROM registrations r
           JOIN events e ON e.id = r.event_id
           WHERE r.user_id = ? ORDER BY e.event_date, e.event_time""",
        (g.user["id"],),
    ).fetchall()
    return render_template("dashboard.html", memberships=memberships, registrations=registrations)


# ---------------------------------------------------------------- shared by admin & club admin portals


def membership_rows(status, club_id=None):
    query = """SELECT m.*, u.name AS student, u.roll_no, u.email, u.department, u.year, u.phone, c.name AS club
               FROM memberships m JOIN users u ON u.id = m.user_id JOIN clubs c ON c.id = m.club_id
               WHERE 1 = 1"""
    params = []
    if club_id is not None:
        query += " AND m.club_id = ?"
        params.append(club_id)
    if status in ("pending", "approved", "rejected"):
        query += " AND m.status = ?"
        params.append(status)
    query += " ORDER BY m.joined_at DESC"
    return get_db().execute(query, params).fetchall()


def event_rows(club_id=None):
    query = """SELECT e.*, c.name AS club_name,
                      (SELECT COUNT(*) FROM registrations r WHERE r.event_id = e.id) AS reg_count
               FROM events e LEFT JOIN clubs c ON c.id = e.club_id"""
    params = ()
    if club_id is not None:
        query += " WHERE e.club_id = ?"
        params = (club_id,)
    query += " ORDER BY e.event_date, e.event_time"
    return get_db().execute(query, params).fetchall()


def render_participants(event, back_url):
    participants = get_db().execute(
        """SELECT u.name, u.email, u.roll_no, u.department, u.year, u.phone, r.registered_at
           FROM registrations r JOIN users u ON u.id = r.user_id
           WHERE r.event_id = ? ORDER BY r.registered_at""",
        (event["id"],),
    ).fetchall()
    return render_template("admin/participants.html", event=event, participants=participants, back_url=back_url)


# ---------------------------------------------------------------- admin portal

def read_club_form():
    data = {k: request.form.get(k, "").strip() for k in ("name", "category", "description", "coordinator", "contact_email")}
    errors = []
    if len(data["name"]) < 2:
        errors.append("Club name is required.")
    if data["category"] not in CATEGORIES:
        errors.append("Please select a valid category.")
    if len(data["description"]) < 10:
        errors.append("Description must be at least 10 characters.")
    if len(data["coordinator"]) < 2:
        errors.append("Faculty coordinator is required.")
    if not is_valid_email(data["contact_email"]):
        errors.append("Please enter a valid contact email.")
    return data, errors


@app.route("/admin/clubs/new", methods=["GET", "POST"])
@app.route("/admin/clubs/<int:club_id>/edit", methods=["GET", "POST"])
@admin_required
def admin_club_form(club_id=None):
    club = get_club_or_404(club_id) if club_id else None
    form = dict(club) if club else {}
    if request.method == "POST":
        db = get_db()
        form, errors = read_club_form()
        if not club:
            form["admin_email"] = request.form.get("admin_email", "").strip().lower()
            admin_password = request.form.get("admin_password", "")
            if not is_valid_email(form["admin_email"]):
                errors.append("Please enter a valid club admin login email.")
            elif db.execute("SELECT 1 FROM users WHERE email = ?", (form["admin_email"],)).fetchone():
                errors.append("An account with this club admin email already exists.")
            if len(admin_password) < 6:
                errors.append("Club admin password must be at least 6 characters.")
        if not errors:
            values = (form["name"], form["category"], form["description"], form["coordinator"], form["contact_email"])
            try:
                if club:
                    db.execute(
                        """UPDATE clubs SET name = ?, category = ?, description = ?,
                                            coordinator = ?, contact_email = ? WHERE id = ?""",
                        values + (club["id"],),
                    )
                else:
                    new_id = db.execute(
                        "INSERT INTO clubs (name, category, description, coordinator, contact_email) VALUES (?, ?, ?, ?, ?)",
                        values,
                    ).lastrowid
                    db.execute(
                        "INSERT INTO users (name, email, password_hash, role, club_id) VALUES (?, ?, ?, 'club_admin', ?)",
                        (f"{form['name']} Admin", form["admin_email"], generate_password_hash(admin_password), new_id),
                    )
                db.commit()
            except sqlite3.IntegrityError:
                db.rollback()
                errors.append("A club with this name already exists.")
            else:
                flash(f"Club {'updated' if club else 'created'} successfully.", "success")
                return redirect(url_for("admin_clubs"))
        for e in errors:
            flash(e, "danger")
    return render_template("admin/club_form.html", club=club, form=form, categories=CATEGORIES)


def read_event_form():
    fields = ("title", "fest_name", "club_id", "description", "venue", "event_date", "event_time", "max_participants")
    data = {k: request.form.get(k, "").strip() for k in fields}
    errors = []
    if len(data["title"]) < 2:
        errors.append("Event title is required.")
    if not data["fest_name"]:
        errors.append("Fest name is required.")
    if len(data["description"]) < 10:
        errors.append("Description must be at least 10 characters.")
    if not data["venue"]:
        errors.append("Venue is required.")
    try:
        datetime.strptime(data["event_date"], "%Y-%m-%d")
    except ValueError:
        errors.append("Please enter a valid date.")
    try:
        datetime.strptime(data["event_time"], "%H:%M")
    except ValueError:
        errors.append("Please enter a valid time.")
    try:
        data["max_participants"] = int(data["max_participants"])
        if data["max_participants"] < 1:
            raise ValueError
    except ValueError:
        errors.append("Max participants must be at least 1.")

    data["club_id"] = int(data["club_id"]) if data["club_id"].isdigit() else None
    if data["club_id"] is None or get_db().execute(
        "SELECT 1 FROM clubs WHERE id = ?", (data["club_id"],)
    ).fetchone() is None:
        errors.append("Please select the organising club.")
    return data, errors


@app.route("/admin/events/new", methods=["GET", "POST"])
@app.route("/admin/events/<int:event_id>/edit", methods=["GET", "POST"])
@admin_required
def admin_event_form(event_id=None):
    db = get_db()
    event = get_event_or_404(event_id) if event_id else None
    form = dict(event) if event else {}
    if request.method == "POST":
        form, errors = read_event_form()
        if not errors:
            values = (form["title"], form["fest_name"], form["club_id"], form["description"], form["venue"],
                      form["event_date"], form["event_time"], form["max_participants"])
            if event:
                db.execute(
                    """UPDATE events SET title = ?, fest_name = ?, club_id = ?, description = ?, venue = ?,
                                         event_date = ?, event_time = ?, max_participants = ?
                       WHERE id = ?""",
                    values + (event["id"],),
                )
            else:
                db.execute(
                    """INSERT INTO events (title, fest_name, club_id, description, venue,
                                           event_date, event_time, max_participants)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                    values,
                )
            db.commit()
            flash(f"Event {'updated' if event else 'created'} successfully.", "success")
            return redirect(url_for("admin_events"))
        for e in errors:
            flash(e, "danger")

    clubs_list = db.execute("SELECT id, name FROM clubs ORDER BY name").fetchall()
    fests = [r[0] for r in db.execute("SELECT DISTINCT fest_name FROM events ORDER BY fest_name")]
    return render_template("admin/event_form.html", event=event, form=form, clubs=clubs_list, fests=fests)


@app.route("/admin")
@admin_required
def admin_dashboard():
    db = get_db()
    stats = {
        "students": db.execute("SELECT COUNT(*) FROM users WHERE role = 'student'").fetchone()[0],
        "clubs": db.execute("SELECT COUNT(*) FROM clubs").fetchone()[0],
        "events": db.execute("SELECT COUNT(*) FROM events").fetchone()[0],
        "registrations": db.execute("SELECT COUNT(*) FROM registrations").fetchone()[0],
        "pending": db.execute("SELECT COUNT(*) FROM memberships WHERE status = 'pending'").fetchone()[0],
        "club_admins": db.execute("SELECT COUNT(*) FROM users WHERE role = 'club_admin'").fetchone()[0],
    }
    pending = membership_rows("pending")
    recent = db.execute(
        """SELECT r.registered_at, u.name AS student, e.title, e.fest_name
           FROM registrations r JOIN users u ON u.id = r.user_id JOIN events e ON e.id = r.event_id
           ORDER BY r.registered_at DESC LIMIT 8"""
    ).fetchall()
    return render_template("admin/dashboard.html", stats=stats, pending=pending, recent=recent)


@app.route("/admin/memberships")
@admin_required
def admin_memberships():
    status = request.args.get("status", "")
    return render_template("admin/memberships.html", memberships=membership_rows(status), current_status=status)


@app.route("/admin/students")
@admin_required
def admin_students():
    students = get_db().execute(
        """SELECT u.*,
                  (SELECT COUNT(*) FROM memberships m WHERE m.user_id = u.id AND m.status = 'approved') AS club_count,
                  (SELECT COUNT(*) FROM registrations r WHERE r.user_id = u.id) AS event_count
           FROM users u WHERE u.role = 'student' ORDER BY u.name"""
    ).fetchall()
    return render_template("admin/students.html", students=students)


@app.route("/admin/clubs")
@admin_required
def admin_clubs():
    rows = get_db().execute(
        """SELECT c.*,
                  (SELECT COUNT(*) FROM memberships m WHERE m.club_id = c.id AND m.status = 'approved') AS member_count,
                  (SELECT COUNT(*) FROM events e WHERE e.club_id = c.id) AS event_count,
                  (SELECT GROUP_CONCAT(u.email, ', ') FROM users u
                   WHERE u.club_id = c.id AND u.role = 'club_admin') AS admin_emails
           FROM clubs c ORDER BY c.name"""
    ).fetchall()
    return render_template("admin/clubs.html", clubs=rows)


@app.route("/admin/clubs/<int:club_id>/delete", methods=["POST"])
@admin_required
def admin_delete_club(club_id):
    club = get_club_or_404(club_id)
    db = get_db()
    db.execute("DELETE FROM clubs WHERE id = ?", (club_id,))
    db.commit()
    flash(f"Club '{club['name']}' deleted.", "info")
    return redirect(url_for("admin_clubs"))


@app.route("/admin/club-admins", methods=["GET", "POST"])
@admin_required
def admin_club_admins():
    db = get_db()
    form = {"club_id": request.args.get("club_id", "")}

    if request.method == "POST":
        form = {k: request.form.get(k, "").strip() for k in ("name", "email", "club_id")}
        form["email"] = form["email"].lower()
        password = request.form.get("password", "")

        errors = []
        if len(form["name"]) < 2:
            errors.append("Please enter the club admin's name.")
        if not is_valid_email(form["email"]):
            errors.append("Please enter a valid email.")
        if not form["club_id"].isdigit() or db.execute(
            "SELECT 1 FROM clubs WHERE id = ?", (form["club_id"],)
        ).fetchone() is None:
            errors.append("Please select a club.")
        if len(password) < 6:
            errors.append("Password must be at least 6 characters.")

        if not errors:
            try:
                db.execute(
                    "INSERT INTO users (name, email, password_hash, role, club_id) VALUES (?, ?, ?, 'club_admin', ?)",
                    (form["name"], form["email"], generate_password_hash(password), int(form["club_id"])),
                )
                db.commit()
            except sqlite3.IntegrityError:
                errors.append("An account with this email already exists.")
            else:
                flash(f"Club admin {form['email']} created.", "success")
                return redirect(url_for("admin_club_admins"))
        for e in errors:
            flash(e, "danger")

    admins = db.execute(
        """SELECT u.id, u.name, u.email, u.created_at, c.name AS club
           FROM users u JOIN clubs c ON c.id = u.club_id
           WHERE u.role = 'club_admin' ORDER BY c.name, u.name"""
    ).fetchall()
    clubs_list = db.execute("SELECT id, name FROM clubs ORDER BY name").fetchall()
    return render_template("admin/club_admins.html", admins=admins, clubs=clubs_list, form=form)


@app.route("/admin/club-admins/<int:user_id>/edit", methods=["GET", "POST"])
@admin_required
def admin_edit_club_admin(user_id):
    db = get_db()
    club_admin = db.execute(
        """SELECT u.*, c.name AS club FROM users u JOIN clubs c ON c.id = u.club_id
           WHERE u.id = ? AND u.role = 'club_admin'""",
        (user_id,),
    ).fetchone()
    if club_admin is None:
        abort(404)
    form = dict(club_admin)

    if request.method == "POST":
        form.update({k: request.form.get(k, "").strip() for k in ("name", "email")})
        form["email"] = form["email"].lower()
        password = request.form.get("password", "")

        errors = []
        if len(form["name"]) < 2:
            errors.append("Please enter the club admin's name.")
        if not is_valid_email(form["email"]):
            errors.append("Please enter a valid email.")
        elif db.execute("SELECT 1 FROM users WHERE email = ? AND id != ?", (form["email"], user_id)).fetchone():
            errors.append("Another account already uses this email.")
        if password and len(password) < 6:
            errors.append("New password must be at least 6 characters.")

        if not errors:
            db.execute("UPDATE users SET name = ?, email = ? WHERE id = ?", (form["name"], form["email"], user_id))
            if password:
                db.execute("UPDATE users SET password_hash = ? WHERE id = ?", (generate_password_hash(password), user_id))
            db.commit()
            flash(f"Club admin for {club_admin['club']} updated.", "success")
            return redirect(url_for("admin_club_admins"))
        for e in errors:
            flash(e, "danger")

    return render_template("admin/club_admin_form.html", club_admin=club_admin, form=form)


@app.route("/admin/club-admins/<int:user_id>/delete", methods=["POST"])
@admin_required
def admin_delete_club_admin(user_id):
    db = get_db()
    db.execute("DELETE FROM users WHERE id = ? AND role = 'club_admin'", (user_id,))
    db.commit()
    flash("Club admin removed.", "info")
    return redirect(url_for("admin_club_admins"))


@app.route("/admin/events")
@admin_required
def admin_events():
    return render_template("admin/events.html", events=event_rows())


@app.route("/admin/events/<int:event_id>/delete", methods=["POST"])
@admin_required
def admin_delete_event(event_id):
    event = get_event_or_404(event_id)
    db = get_db()
    db.execute("DELETE FROM events WHERE id = ?", (event_id,))
    db.commit()
    flash(f"Event '{event['title']}' deleted.", "info")
    return redirect(url_for("admin_events"))


@app.route("/admin/events/<int:event_id>/participants")
@admin_required
def admin_participants(event_id):
    return render_participants(get_event_or_404(event_id), back_url=url_for("admin_events"))


# ---------------------------------------------------------------- club admin portal

@app.route("/club-admin")
@club_admin_required
def club_admin_dashboard():
    events = event_rows(g.club["id"])
    pending = membership_rows("pending", g.club["id"])
    stats = {
        "events": len(events),
        "registrations": sum(e["reg_count"] for e in events),
        "members": len(membership_rows("approved", g.club["id"])),
        "pending": len(pending),
    }
    return render_template("club_admin/dashboard.html", stats=stats, events=events, pending=pending)


@app.route("/club-admin/members")
@club_admin_required
def club_admin_memberships():
    status = request.args.get("status", "")
    return render_template("admin/memberships.html",
                           memberships=membership_rows(status, g.club["id"]), current_status=status)


@app.route("/club-admin/members/<int:membership_id>/<action>", methods=["POST"])
@club_admin_required
def club_admin_update_membership(membership_id, action):
    new_status = {"approve": "approved", "reject": "rejected"}.get(action)
    if new_status is None:
        abort(400)
    db = get_db()
    updated = db.execute(
        "UPDATE memberships SET status = ? WHERE id = ? AND club_id = ?",
        (new_status, membership_id, g.club["id"]),
    ).rowcount
    if not updated:
        abort(404)
    db.commit()
    flash(f"Membership {new_status}.", "success")
    return redirect(request.referrer or url_for("club_admin_memberships"))


@app.route("/club-admin/events/<int:event_id>/participants")
@club_admin_required
def club_admin_participants(event_id):
    event = get_event_or_404(event_id)
    if event["club_id"] != g.club["id"]:
        abort(404)
    return render_participants(event, back_url=url_for("club_admin_dashboard"))


# ---------------------------------------------------------------- errors

@app.errorhandler(403)
def forbidden(e):
    return render_template("error.html", code=403, message="You don't have permission to view this page."), 403


@app.errorhandler(404)
def not_found(e):
    return render_template("error.html", code=404, message="The page you're looking for doesn't exist."), 404


init_db()

if __name__ == "__main__":
    app.run(debug=True)
