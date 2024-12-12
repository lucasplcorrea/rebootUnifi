app = Flask(__name__)

@app.route("/")
def index():
    """Página inicial com logs."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM logs ORDER BY timestamp DESC")
    logs = cursor.fetchall()
    conn.close()
    return render_template("index.html", logs=logs)

if __name__ == "__main__":
    app.run(debug=True)
