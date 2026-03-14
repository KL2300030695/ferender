import tensorflow as tf
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import Conv2D, MaxPooling2D, Flatten, Dense, Dropout, BatchNormalization, RandomFlip, RandomRotation
from tensorflow.keras.callbacks import EarlyStopping, ReduceLROnPlateau
import matplotlib.pyplot as plt
import os

# --- Constants ---
DATA_DIR = 'fer2013_dataset'
TRAIN_DIR = os.path.join(DATA_DIR, 'train')
TEST_DIR = os.path.join(DATA_DIR, 'test')

IMG_WIDTH, IMG_HEIGHT = 48, 48
BATCH_SIZE = 64
NUM_CLASSES = 7
EPOCHS = 100

# --- 1. Load Data from Folders ---
def load_data_from_folders():
    """
    Loads and preprocesses the FER-2013 dataset from image folders.
    Uses TensorFlow's utility to create datasets directly from directories.
    """
    if not os.path.exists(DATA_DIR):
        print(f"Error: The directory '{DATA_DIR}' was not found.")
        print("Please make sure your dataset is in a folder named 'fer2013_dataset' inside your project.")
        return None, None

    # Create training dataset from image folders
    train_ds = tf.keras.utils.image_dataset_from_directory(
        TRAIN_DIR,
        labels='inferred',
        label_mode='categorical',
        color_mode='grayscale',
        image_size=(IMG_WIDTH, IMG_HEIGHT),
        batch_size=BATCH_SIZE,
        shuffle=True
    )

    # Create validation (test) dataset from image folders
    val_ds = tf.keras.utils.image_dataset_from_directory(
        TEST_DIR,
        labels='inferred',
        label_mode='categorical',
        color_mode='grayscale',
        image_size=(IMG_WIDTH, IMG_HEIGHT),
        batch_size=BATCH_SIZE,
        shuffle=False
    )
    
    print(f"Found class names: {train_ds.class_names}")

    # --- Data Augmentation and Performance Optimization ---
    
    # Define a simple data augmentation layer to prevent overfitting
    data_augmentation = Sequential([
        RandomFlip("horizontal"),
        RandomRotation(0.1),
    ])

    def preprocess_train(image, label):
        # Apply augmentation only to the training data
        image = data_augmentation(image)
        # Rescale pixel values from [0, 255] to [0, 1]
        return image / 255.0, label
        
    def preprocess_val(image, label):
         # Only rescale the validation data (no augmentation)
        return image / 255.0, label

    # Apply preprocessing and optimize data loading pipeline
    train_ds = train_ds.map(preprocess_train, num_parallel_calls=tf.data.AUTOTUNE)
    val_ds = val_ds.map(preprocess_val, num_parallel_calls=tf.data.AUTOTUNE)

    # Prefetch data to RAM for better performance
    train_ds = train_ds.prefetch(buffer_size=tf.data.AUTOTUNE)
    val_ds = val_ds.prefetch(buffer_size=tf.data.AUTOTUNE)

    return train_ds, val_ds

# --- 2. Build the CNN Model ---
def build_model():
    """
    Builds the CNN model architecture as described in the paper.
    """
    model = Sequential([
        # Add the input layer specification
        tf.keras.Input(shape=(IMG_WIDTH, IMG_HEIGHT, 1)),
        
        # First Convolutional Block
        Conv2D(64, (3, 3), activation='relu', padding='same', kernel_initializer='he_normal'),
        BatchNormalization(),
        Conv2D(64, (3, 3), activation='relu', padding='same', kernel_initializer='he_normal'),
        BatchNormalization(),
        MaxPooling2D(pool_size=(2, 2)),
        Dropout(0.3),

        # Second Convolutional Block
        Conv2D(128, (3, 3), activation='relu', padding='same', kernel_initializer='he_normal'),
        BatchNormalization(),
        Conv2D(128, (3, 3), activation='relu', padding='same', kernel_initializer='he_normal'),
        BatchNormalization(),
        MaxPooling2D(pool_size=(2, 2)),
        Dropout(0.4),

        # Third Convolutional Block
        Conv2D(256, (3, 3), activation='relu', padding='same', kernel_initializer='he_normal'),
        BatchNormalization(),
        Conv2D(256, (3, 3), activation='relu', padding='same', kernel_initializer='he_normal'),
        BatchNormalization(),
        MaxPooling2D(pool_size=(2, 2)),
        Dropout(0.5),

        # Flatten and Dense Layers
        Flatten(),
        Dense(128, activation='relu', kernel_initializer='he_normal'),
        BatchNormalization(),
        Dropout(0.6),
        Dense(NUM_CLASSES, activation='softmax')
    ])

    model.compile(optimizer=tf.keras.optimizers.Adam(learning_rate=0.001),
                  loss='categorical_crossentropy',
                  metrics=['accuracy'])
    
    return model

# --- 3. Plot Training History ---
def plot_history(history):
    """
    Plots the training and validation accuracy and loss curves.
    """
    fig, axs = plt.subplots(1, 2, figsize=(15, 5))
    
    axs[0].plot(history.history['accuracy'], label='train_accuracy')
    axs[0].plot(history.history['val_accuracy'], label='val_accuracy')
    axs[0].set_title('Model Accuracy')
    axs[0].set_ylabel('Accuracy')
    axs[0].set_xlabel('Epoch')
    axs[0].legend(loc='upper left')
    
    axs[1].plot(history.history['loss'], label='train_loss')
    axs[1].plot(history.history['val_loss'], label='val_loss')
    axs[1].set_title('Model Loss')
    axs[1].set_ylabel('Loss')
    axs[1].set_xlabel('Epoch')
    axs[1].legend(loc='upper left')
    
    plt.tight_layout()
    plt.savefig('training_history.png')
    print("\nTraining history plot saved as training_history.png")
    plt.show()

# --- Main Execution ---
if __name__ == "__main__":
    train_ds, val_ds = load_data_from_folders()
    
    if train_ds and val_ds:
        model = build_model()
        model.summary()

        # Callbacks to improve training
        early_stopping = EarlyStopping(monitor='val_loss', patience=15, restore_best_weights=True, verbose=1)
        reduce_lr = ReduceLROnPlateau(monitor='val_loss', factor=0.2, patience=5, min_lr=0.00001, verbose=1)
        
        # Train the model
        history = model.fit(
            train_ds,
            epochs=EPOCHS,
            validation_data=val_ds,
            callbacks=[early_stopping, reduce_lr]
        )

        model.save('emotion_model.h5')
        print("\nModel trained and saved as emotion_model.h5")

        plot_history(history)

