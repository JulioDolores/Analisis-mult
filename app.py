import json
import sqlite3
import random
from flask import Flask, jsonify, render_template
from flask_cors import CORS
import pandas as pd

# Inicializar Flask
app = Flask(__name__)
CORS(app)

# Nombre de la base de datos
DB_NAME = "nobel.db"


##CArgar el archivo
def init_db():
    # Leer archivo JSON
    with open("Nobel_winners.json", "r", encoding="utf-8") as file:
        data = json.load(file)

    # Convertir en DataFrame
    df = pd.DataFrame(data)

    # Conectar a SQLite
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    # Crear tabla si no existe
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS winners (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            link TEXT,
            name TEXT,
            year INTEGER,
            category TEXT,
            country TEXT,
            born_in TEXT,
            text TEXT,
            date_of_birth TEXT,
            date_of_death TEXT,
            place_of_birth TEXT,
            place_of_death TEXT,
            gender TEXT
        )
    """)

    # Insertar datos
    df.to_sql("winners", conn, if_exists="replace", index=False)

    conn.commit()
    conn.close()
    print("📊 Base de datos creada con éxito.")

# Llamar a la función de inicialización al iniciar la app
init_db()

##Api rest con flask
# Obtener cantidad de ganadores por país
@app.route("/api/winners_by_country", methods=["GET"])
def winners_by_country():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT country, COUNT(*) as count 
        FROM winners 
        WHERE country IS NOT NULL 
        GROUP BY country 
        ORDER BY count DESC
    """)
    result = [{"country": row[0], "count": row[1]} for row in cursor.fetchall()]
    conn.close()
    return jsonify(result)

# Obtener 5 ganadores aleatorios
@app.route("/api/random_winners", methods=["GET"])
def random_winners():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT name, year, category FROM winners ORDER BY RANDOM() LIMIT 5")
    result = [{"name": row[0], "year": row[1], "category": row[2]} for row in cursor.fetchall()]
    conn.close()
    return jsonify(result)

# Obtener cantidad de ganadores por categoría y país
@app.route("/api/categories_by_country", methods=["GET"])
def categories_by_country():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT country, category, COUNT(*) as count 
        FROM winners 
        WHERE country IS NOT NULL 
        GROUP BY country, category
        ORDER BY count DESC
    """)
    result = [{"country": row[0], "category": row[1], "count": row[2]} for row in cursor.fetchall()]
    conn.close()
    return jsonify(result)



#interfaz con flask
@app.route("/")
def home():
    return render_template("plantilla.html")

#Ejecutar la app
if __name__ == "__main__":
    app.run(debug=True, port=5000)
