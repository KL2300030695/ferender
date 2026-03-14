import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import tensorflow as tf
from tensorflow.keras.models import load_model
from sklearn.metrics import confusion_matrix
import itertools
import os

# --- CONFIGURATION ---
DATASET_PATH = 'fer2013.csv'     # Path to your dataset
MODEL_PATH = 'model.h5'          # Path to your trained model
BATCH_SIZE = 64
IMG_SIZE = (48, 48)

# Standard FER2013 Class Labels
LABELS = ['Angry', 'Disgust', 'Fear', 'Happy', 'Sad', 'Surprise', 'Neutral']

def create_dummy_csv(filename):
    """Creates a dummy CSV file if the real one is missing, for testing."""
    print(f"Creating dummy {filename} for demonstration...")
    data = []
    # Create 1000 random samples (increased from 50 for better visualization)
    for _ in range(1000):
        emotion = np.random.randint(0, 7)
        # Generate random pixel string (48*48 = 2304 pixels)
        pixels = ' '.join(map(str, np.random.randint(0, 255, size=48*48)))
        usage = 'PrivateTest'
        data.append([emotion, pixels, usage])
    
    df = pd.DataFrame(data, columns=['emotion', 'pixels', 'Usage'])
    df.to_csv(filename, index=False)
    print("Dummy dataset created successfully.")

def load_data(dataset_path):
    print(f"Loading data from {dataset_path}...")
    try:
        data = pd.read_csv(dataset_path)
    except Exception as e:
        print(f"Error reading CSV: {e}")
        return np.array([]), np.array([])
    
    # We only care about the 'PrivateTest' set for final evaluation
    if 'Usage' in data.columns:
        test_data = data[data['Usage'] == 'PrivateTest']
    else:
        test_data = data # Fallback if Usage column missing
        
    if test_data.empty:
        print("Warning: No 'PrivateTest' data found. Using all data.")
        test_data = data

    pixels = test_data['pixels'].tolist()
    
    # Convert pixels string to numpy array
    X = []
    for sequence in pixels:
        try:
            face = [int(pixel) for pixel in sequence.split(' ')]
            face = np.asarray(face).reshape(IMG_SIZE)
            X.append(face)
        except ValueError:
            continue
        
    X = np.asarray(X)
    if len(X) > 0:
        X = np.expand_dims(X, -1) # Add channel dimension (48, 48, 1)
        # Normalize images
        X = X.astype('float32') / 255.0
    
    # Get labels
    y = test_data['emotion'].values
    
    print(f"Found {len(X)} test images.")
    return X, y

def plot_confusion_matrix(cm, classes, title='Confusion Matrix', cmap=plt.cm.Blues):
    """
    Plots the confusion matrix.
    """
    plt.figure(figsize=(10, 8))
    plt.imshow(cm, interpolation='nearest', cmap=cmap)
    plt.title(title, fontsize=16, fontweight='bold', pad=20)
    plt.colorbar()
    
    tick_marks = np.arange(len(classes))
    plt.xticks(tick_marks, classes, rotation=45)
    plt.yticks(tick_marks, classes)

    thresh = cm.max() / 2.
    
    for i, j in itertools.product(range(cm.shape[0]), range(cm.shape[1])):
        plt.text(j, i, format(cm[i, j], 'd'),
                 horizontalalignment="center",
                 fontsize=10,
                 color="white" if cm[i, j] > thresh else "black")

    plt.ylabel('True Label', fontsize=12, fontweight='bold')
    plt.xlabel('Predicted Label', fontsize=12, fontweight='bold')
    plt.tight_layout()
    plt.savefig('fer2013_confusion_matrix.png', dpi=300)
    print("Matrix saved as 'fer2013_confusion_matrix.png'")
    plt.show()

def main():
    # 1. Check files
    if not os.path.exists(DATASET_PATH):
        print(f"Warning: {DATASET_PATH} not found.")
        print("Generating a dummy dataset so the code can run...")
        create_dummy_csv(DATASET_PATH)

    if not os.path.exists(MODEL_PATH):
        print(f"Warning: {MODEL_PATH} not found.")
        print("Using random predictions for demonstration purposes.")
        mock_mode = True
    else:
        mock_mode = False

    # 2. Load Data
    X_test, y_true = load_data(DATASET_PATH)
    
    if len(X_test) == 0:
        print("No data loaded. Exiting.")
        return

    # 3. Predict
    if not mock_mode:
        print("Loading model...")
        try:
            model = load_model(MODEL_PATH)
            print("Predicting emotions on test set...")
            y_pred_probs = model.predict(X_test, batch_size=BATCH_SIZE)
            y_pred = np.argmax(y_pred_probs, axis=1)
        except Exception as e:
            print(f"Error loading/running model: {e}")
            print("Switching to mock predictions.")
            y_pred = np.random.randint(0, 7, size=len(y_true))
    else:
        # MOCK MODE: Simulate results
        print("Generating mock predictions...")
        y_pred = np.random.randint(0, 7, size=len(y_true))

    # 4. Generate Matrix
    cm = confusion_matrix(y_true, y_pred)
    
    # 5. Plot
    plot_confusion_matrix(cm, LABELS)

if __name__ == "__main__":
    main()