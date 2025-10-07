import streamlit as st
import pandas as pd
import random
import os
from datetime import datetime
import gspread
from google.oauth2 import service_account

# -----------------------------
# CONFIGURACIÓN INICIAL
# -----------------------------
st.set_page_config(page_title="Test de Imágenes: ¿Verdadera o Falsa?", page_icon="🧠", layout="centered")

IMAGES_FOLDER = "images"
N_REAL = 5
N_FAKE = 5
SPREADSHEET_NAME = "idm-2025"
WORKSHEET_NAME = "resultados"

# -----------------------------
# FUNCIÓN DE CONEXIÓN A GOOGLE SHEETS
# -----------------------------
def connect_to_gsheet():
    credentials = service_account.Credentials.from_service_account_info(
        st.secrets["gcp_service_account"],
        scopes=["https://www.googleapis.com/auth/spreadsheets"]
    )
    client = gspread.authorize(credentials)
    sheet = client.open(SPREADSHEET_NAME).worksheet(WORKSHEET_NAME)
    return sheet

def append_to_gsheet(sheet, row_data):
    sheet.append_row(row_data, value_input_option="USER_ENTERED")

# -----------------------------
# CARGA Y SELECCIÓN DE IMÁGENES
# -----------------------------
def load_images():
    real_images = [os.path.join(IMAGES_FOLDER, "real", f)
                   for f in os.listdir(os.path.join(IMAGES_FOLDER, "real"))
                   if f.lower().endswith(('.png', '.jpg', '.jpeg'))]

    firefly_images = [os.path.join(IMAGES_FOLDER, "firefly", f)
                      for f in os.listdir(os.path.join(IMAGES_FOLDER, "firefly"))
                      if f.lower().endswith(('.png', '.jpg', '.jpeg'))]

    midjourney_images = [os.path.join(IMAGES_FOLDER, "midjourney", f)
                         for f in os.listdir(os.path.join(IMAGES_FOLDER, "midjourney"))
                         if f.lower().endswith(('.png', '.jpg', '.jpeg'))]

    # Mezclar y elegir aleatoriamente
    real_sample = random.sample(real_images, N_REAL)
    fake_pool = firefly_images + midjourney_images
    fake_sample = random.sample(fake_pool, N_FAKE)

    all_images = [{"path": p, "label": "real"} for p in real_sample] + \
                 [{"path": p, "label": "fake" if "firefly" in p else "fake"} for p in fake_sample]
    random.shuffle(all_images)
    return all_images

# -----------------------------
# ESTADO DE LA APLICACIÓN
# -----------------------------
if "step" not in st.session_state:
    st.session_state.step = "start"
if "responses" not in st.session_state:
    st.session_state.responses = []
if "index" not in st.session_state:
    st.session_state.index = 0

# -----------------------------
# PANTALLA INICIAL
# -----------------------------
if st.session_state.step == "start":
    st.title("🧠 Test de Imágenes: ¿Verdadera o Falsa?")
    st.write("Queremos conocer tu capacidad para distinguir imágenes reales de las generadas por IA.")

    name = st.text_input("Nombre:")
    age = st.number_input("Edad:", min_value=1, max_value=120, step=1)
    consent = st.checkbox("Acepto que los resultados de este test sean utilizados para actividades académicas.")

    if st.button("Comenzar") and name.strip() and consent:
        st.session_state.name = name
        st.session_state.age = age
        st.session_state.images = load_images()
        st.session_state.step = "quiz"
        st.rerun()
    elif st.button("Comenzar") and not consent:
        st.warning("Debes aceptar el uso de datos para continuar.")

# -----------------------------
# QUIZ
# -----------------------------
elif st.session_state.step == "quiz":
    images = st.session_state.images
    index = st.session_state.index

    if index < len(images):
        image_data = images[index]
        st.image(image_data["path"], use_container_width=True)
        st.write(f"Imagen {index + 1} de {len(images)}")

        col1, col2 = st.columns(2)
        with col1:
            if st.button("Verdadera ✅"):
                st.session_state.responses.append(
                    {"image": image_data["path"], "true_label": image_data["label"], "user_answer": "true"}
                )
                st.session_state.index += 1
                st.rerun()
        with col2:
            if st.button("Falsa ❌"):
                st.session_state.responses.append(
                    {"image": image_data["path"], "true_label": image_data["label"], "user_answer": "false"}
                )
                st.session_state.index += 1
                st.rerun()
    else:
        st.session_state.step = "results"
        st.rerun()

# -----------------------------
# RESULTADOS
# -----------------------------
elif st.session_state.step == "results":
    df = pd.DataFrame(st.session_state.responses)

    # Etiquetas verdaderas: solo las reales son "true"
    df["true_is_true"] = df["true_label"].apply(lambda x: x == "real")

    df["correct"] = df.apply(lambda row: (
        (row["true_is_true"] and row["user_answer"] == "true") or
        (not row["true_is_true"] and row["user_answer"] == "false")
    ), axis=1)

    score = int(df["correct"].sum())
    total = len(df)
    percent = round(score / total * 100, 1)

    st.title("🎉 Resultados del Test")
    st.write(f"**Puntaje total:** {score} / {total} ({percent}%)")

    st.bar_chart(df["correct"].value_counts())

    # Desempeño por tipo de imagen
    df["type"] = df["true_label"]
    type_scores = df.groupby("type")["correct"].mean().to_dict()
    st.subheader("Desempeño por tipo de imagen:")
    for k, v in type_scores.items():
        st.write(f"**{k.capitalize()}**: {v*100:.1f}%")

    # Guardar en Google Sheets
    try:
        sheet = connect_to_gsheet()
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        data = [
            timestamp,
            st.session_state.name,
            st.session_state.age,
            score,
            total,
            percent,
            type_scores.get("real", 0),
            type_scores.get("firefly", 0),
            type_scores.get("midjourney", 0)
        ]
        append_to_gsheet(sheet, data)
        st.success("✅ Resultados enviados correctamente a la hoja de cálculo.")
    except Exception as e:
        st.error(f"No se pudieron guardar los resultados: {e}")

    if st.button("Ver leaderboard"):
        st.session_state.step = "leaderboard"
        st.rerun()

# -----------------------------
# LEADERBOARD
# -----------------------------
elif st.session_state.step == "leaderboard":
    st.title("🏆 Leaderboard")

    try:
        sheet = connect_to_gsheet()
        data = sheet.get_all_values()
        df = pd.DataFrame(data[1:], columns=data[0])
        df["puntaje"] = df["puntaje"].astype(float)
        df = df.sort_values(by="puntaje", ascending=False).head(20)
        st.dataframe(df)
    except Exception as e:
        st.error(f"No se pudo cargar el leaderboard: {e}")

    if st.button("Volver al inicio"):
        for key in ["step", "responses", "index", "images", "name", "age"]:
            if key in st.session_state:
                del st.session_state[key]
        st.rerun()
