
import csv,numpy as np,pandas as pd
import os
import seaborn as sns
from sklearn.model_selection import train_test_split
from sklearn import metrics
from sklearn.metrics import classification_report
from sklearn.metrics import confusion_matrix
from sklearn.ensemble import RandomForestClassifier


# Get the folder where diseaseprediction.py lives
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Build the path to Training.csv
train = os.path.join(BASE_DIR, "templates", "Training.csv")
test = os.path.join(BASE_DIR, "templates", "Testing.csv")
# Read CSV
df = pd.read_csv(train)
df = pd.read_csv(test)

# check for null values
train.isnull().any()

train = train.drop(["Unnamed: 133"],axis=1)

#split data
A = train[["prognosis"]] # diseases 
B = train.drop(["prognosis"],axis=1) # symptoms 
C = test.drop(["prognosis"],axis=1) # symptoms - testing 
x_train, x_test, y_train, y_test = train_test_split(B,A,test_size=0.2) # 20:80

# Traning random forest model
mod = RandomForestClassifier(n_estimators = 100,n_jobs = 5, criterion= 'entropy',random_state = 42)
mod = mod.fit(x_train,y_train.values.ravel())
pred = mod.predict(x_test)


indices = [i for i in range(132)]
symptoms = df.columns.values[:-1]

dictionary = dict(zip(symptoms,indices))

def dosomething(symptom):
    user_input_symptoms = symptom
    user_input_label = [0 for i in range(132)]
    for i in user_input_symptoms:
        idx = dictionary[i]
        user_input_label[idx] = 1

    user_input_label = np.array(user_input_label)
    user_input_label = user_input_label.reshape((-1,1)).transpose()
    return(mod.predict(user_input_label))



