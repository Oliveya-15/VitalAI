import pickle
import streamlit as st
from streamlit_option_menu import option_menu
import os

# Dynamically get the path of the models and scalers
base_dir = os.path.dirname(os.path.abspath(__file__))  # Get the base directory of the current file
models_dir = os.path.join(base_dir, 'sav models')  # Folder where models and scalers are saved

# Loading the saved models and scalers using dynamic paths
diabetes_model = pickle.load(open(os.path.join(models_dir, 'trained_model.sav'), 'rb'))
heart_model = pickle.load(open(os.path.join(models_dir, 'heart_disease_trained_model.sav'), 'rb'))
park_model = pickle.load(open(os.path.join(models_dir, 'park_trained_model.sav'), 'rb'))

# Loading the saved scalers
diabetes_scaler = pickle.load(open(os.path.join(models_dir, 'scaler.sav'), 'rb'))
park_scaler = pickle.load(open(os.path.join(models_dir, 'park_scaler.sav'), 'rb'))

# Sidebar for navigation
with st.sidebar:
    selected = option_menu('Multiple Disease Prediction System',
                           ['Diabetes Prediction',
                            'Heart Disease Prediction',
                            'Parkinsons Disease Prediction'],
                           icons=['activity', 'heart-pulse', 'person-wheelchair'],
                           default_index=0)

# Diabetes Prediction Page
if selected == 'Diabetes Prediction':
    # Page title
    st.title('Diabetes Prediction Using ML')

    # Getting the input data from the user
    col1, col2, col3 = st.columns(3)

    with col1:
        Pregnancies = st.text_input('Number of Pregnancies')
    with col2:
        Glucose = st.text_input('Glucose Level')
    with col3:
        BloodPressure = st.text_input('Blood Pressure Value')
    with col1:
        SkinThickness = st.text_input('Skin Thickness Value')
    with col2:
        Insulin = st.text_input('Insulin Level')
    with col3:
        BMI = st.text_input('BMI Value')
    with col1:
        DiabetesPedigreeFunction = st.text_input('Diabetes Pedigree Function Value')
    with col2:
        Age = st.text_input('Age of the Person')

    # Prediction
    diab_diagnosis = ''

    # Creating a button for prediction
    if st.button('Diabetes Test Result'):
        input_data = [[float(Pregnancies), float(Glucose), float(BloodPressure), 
                       float(SkinThickness), float(Insulin), float(BMI), 
                       float(DiabetesPedigreeFunction), float(Age)]]

        # Standardizing the input
        scaled_input_data = diabetes_scaler.transform(input_data)

        # Making prediction using the scaled data
        diab_prediction = diabetes_model.predict(scaled_input_data)

        if diab_prediction[0] == 1:
            diab_diagnosis = 'The Person is Diabetic'
        else:
            diab_diagnosis = 'The Person is Not Diabetic'

        # Display the diagnosis result only on this page
        st.success(diab_diagnosis)

# Heart Disease Prediction Page
if selected == 'Heart Disease Prediction':
    # Page title
    st.title('Heart Disease Prediction Using ML')

    # Input fields for heart disease prediction
    col1, col2, col3 = st.columns(3)

    with col1:
        age = st.text_input('Age')
    with col2:
        sex = st.text_input('Sex (1 = Male, 0 = Female)')
    with col3:
        cp = st.text_input('Chest Pain Type (0, 1, 2, 3)')
    with col1:
        trestbps = st.text_input('Resting Blood Pressure')
    with col2:
        chol = st.text_input('Cholesterol Level')
    with col3:
        fbs = st.text_input('Fasting Blood Sugar (1 = True, 0 = False)')
    with col1:
        restecg = st.text_input('Resting ECG (0, 1, 2)')
    with col2:
        thalach = st.text_input('Max Heart Rate Achieved')
    with col3:
        exang = st.text_input('Exercise Induced Angina (1 = Yes, 0 = No)')
    with col1:
        oldpeak = st.text_input('ST Depression Induced by Exercise')
    with col2:
        slope = st.text_input('Slope of the Peak Exercise ST Segment')
    with col3:
        ca = st.text_input('Number of Major Vessels Colored by Fluoroscopy (0-3)')
    with col1:
        thal = st.text_input('Thalassemia (1 = Normal, 2 = Fixed Defect, 3 = Reversible Defect)')

    # Prediction
    heart_diagnosis = ''

    if st.button('Heart Disease Test Result'):
        input_data = [[float(age), float(sex), float(cp), float(trestbps), float(chol), float(fbs), float(restecg),
                       float(thalach), float(exang), float(oldpeak), float(slope), float(ca), float(thal)]]

        heart_prediction = heart_model.predict(input_data)

        if heart_prediction[0] == 1:
            heart_diagnosis = 'The Person has Heart Disease'
        else:
            heart_diagnosis = 'The Person does not have Heart Disease'

        # Display the diagnosis result only on this page
        st.success(heart_diagnosis)

# Parkinson's Disease Prediction Page
if selected == 'Parkinsons Disease Prediction':
    # Page title
    st.title('Parkinsons Disease Prediction Using ML')

    # Input fields for Parkinson's disease prediction
    col1, col2, col3 = st.columns(3)

    with col1:
        MDVP_Fo = st.text_input('MDVP:Fo(Hz)')
    with col2:
        MDVP_Fhi = st.text_input('MDVP:Fhi(Hz)')
    with col3:
        MDVP_Flo = st.text_input('MDVP:Flo(Hz)')
    with col1:
        MDVP_Jitter_percent = st.text_input('MDVP:Jitter(%)')
    with col2:
        MDVP_Jitter_Abs = st.text_input('MDVP:Jitter(Abs)')
    with col3:
        MDVP_RAP = st.text_input('MDVP:RAP')
    with col1:
        MDVP_PPQ = st.text_input('MDVP:PPQ')
    with col2:
        Jitter_DDP = st.text_input('Jitter:DDP')
    with col3:
        MDVP_Shimmer = st.text_input('MDVP:Shimmer')
    with col1:
        MDVP_Shimmer_dB = st.text_input('MDVP:Shimmer(dB)')
    with col2:
        Shimmer_APQ3 = st.text_input('Shimmer:APQ3')
    with col3:
        Shimmer_APQ5 = st.text_input('Shimmer:APQ5')
    with col1:
        MDVP_APQ = st.text_input('MDVP:APQ')
    with col2:
        Shimmer_DDA = st.text_input('Shimmer:DDA')
    with col3:
        NHR = st.text_input('NHR')
    with col1:
        HNR = st.text_input('HNR')
    with col2:
        RPDE = st.text_input('RPDE')
    with col3:
        DFA = st.text_input('DFA')
    with col1:
        spread1 = st.text_input('Spread1')
    with col2:
        spread2 = st.text_input('Spread2')
    with col3:
        D2 = st.text_input('D2')
    with col1:
        PPE = st.text_input('PPE')

    # Prediction
    park_diagnosis = ''

    if st.button('Parkinsons Test Result'):
        input_data = [[float(MDVP_Fo), float(MDVP_Fhi), float(MDVP_Flo), float(MDVP_Jitter_percent),
                       float(MDVP_Jitter_Abs), float(MDVP_RAP), float(MDVP_PPQ), float(Jitter_DDP),
                       float(MDVP_Shimmer), float(MDVP_Shimmer_dB), float(Shimmer_APQ3), float(Shimmer_APQ5),
                       float(MDVP_APQ), float(Shimmer_DDA), float(NHR), float(HNR), float(RPDE), float(DFA),
                       float(spread1), float(spread2), float(D2), float(PPE)]]

        park_prediction = park_model.predict(input_data)

        if park_prediction[0] == 1:
            park_diagnosis = 'The Person has Parkinsons Disease'
        else:
            park_diagnosis = 'The Person does not have Parkinsons Disease'

        # Display the diagnosis result only on this page
        st.success(park_diagnosis)
