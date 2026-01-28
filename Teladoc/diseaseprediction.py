import os
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier

# ---------------- PATH SETUP ---------------- #

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "templates")

TRAIN_PATH = os.path.join(DATA_DIR, "Training.csv")
TEST_PATH  = os.path.join(DATA_DIR, "Testing.csv")

# ---------------- LOAD DATA ---------------- #

train_df = pd.read_csv(TRAIN_PATH)
test_df  = pd.read_csv(TEST_PATH)

# Drop unwanted column if it exists
if "Unnamed: 133" in train_df.columns:
    train_df = train_df.drop(["Unnamed: 133"], axis=1)

# ---------------- PREP DATA ---------------- #

X = train_df.drop(["prognosis"], axis=1)
y = train_df["prognosis"]

x_train, x_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42
)

# ---------------- TRAIN MODEL ---------------- #

model = RandomForestClassifier(
    n_estimators=100,
    n_jobs=-1,
    criterion="entropy",
    random_state=42
)

model.fit(x_train, y_train)

# ---------------- SYMPTOM DICTIONARY ---------------- #

symptoms = X.columns.values
indices = list(range(len(symptoms)))
dictionary = dict(zip(symptoms, indices))

# ---------------- PREDICTION FUNCTION ---------------- #

def dosomething(symptom_list):
    """
    symptom_list: list of symptom strings
    """
    user_input_label = [0] * len(symptoms)

    for s in symptom_list:
        if s in dictionary:
            idx = dictionary[s]
            user_input_label[idx] = 1

    user_input_label = np.array(user_input_label).reshape(1, -1)
    return model.predict(user_input_label)[0]
