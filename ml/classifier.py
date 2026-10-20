"""
Disease Classification Model for Aquaculture
CNN-based image classifier for detecting common fish/shrimp diseases
"""
import torch
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader
from transformers import AutoModel, AutoTokenizer, Trainer, TrainingArguments
from PIL import Image
import numpy as np
from sklearn.model_selection import train_test_split
from pathlib import Path
import os


class SimpleCNN(nn.Module):
    """Simple CNN for aquaculture disease classification."""
    def __init__(self, num_classes=5):
        super().__init__()
        self.features = nn.Sequential(
            nn.Conv2d(3, 32, kernel_size=3, padding=1),
            nn.ReLU(),
            nn.MaxPool2d(2, 2),
            nn.Conv2d(32, 64, kernel_size=3, padding=1),
            nn.ReLU(),
            nn.MaxPool2d(2, 2),
            nn.Conv2d(64, 128, kernel_size=3, padding=1),
            nn.ReLU(),
            nn.AdaptiveAvgPool2d((1, 1))
        )
        self.classifier = nn.Sequential(
            nn.Flatten(),
            nn.Linear(128, 64),
            nn.ReLU(),
            nn.Dropout(0.5),
            nn.Linear(64, num_classes)
        )

    def forward(self, x):
        x = self.features(x)
        x = self.classifier(x)
        return x


class AquacultureDiseaseDataset(Dataset):
    """Custom dataset for aquaculture disease images."""
    def __init__(self, image_dir, label_map=None):
        self.image_dir = Path(image_dir)
        self.label_map = label_map or {
            'healthy': 0,
            'red_paste': 1,
            'fungus': 2,
            'bacterial': 3,
            'parasitic': 4,
            'unknown': 5
        }
        self.samples = []
        self.labels = []

    def __len__(self):
        return len(self.samples)

    def __getitem__(self, idx):
        img_path = self.image_dir / self.samples[idx].name
        image = Image.open(img_path).convert('RGB')
        image = image.resize((224, 224))
        return image, self.labels[idx]


def train_model(train_dir, val_dir, output_dir="models/"):
    """Train the disease classifier on aquaculture images."""
    # Load datasets
    train_dataset = AquacultureDiseaseDataset(train_dir)
    val_dataset = AquacultureDiseaseDataset(val_dir)

    # Split data
    train_size = int(0.8 * len(train_dataset))
    val_size = len(train_dataset) - train_size
    train_dataset, val_dataset = train_test_split(
        train_dataset, train_size=train_size, val_size=val_size
    )

    # Training arguments
    training_args = TrainingArguments(
        output_dir=output_dir,
        num_train_epochs=5,
        per_device_train_batch_size=8,
        per_device_eval_batch_size=8,
        evaluation_strategy="epoch",
        logging_dir=f"{output_dir}/logs",
        save_strategy="epoch",
        load_best_model_at_end=True,
        metric_for_best_model="accuracy",
    )

    # Train
    trainer = Trainer(
        model=DiseaseClassifier(num_classes=5),
        args=training_args,
        train_dataset=train_dataset,
        eval_dataset=val_dataset,
    )
    trainer.train()

    # Save model
    model_path = Path(output_dir) / "disease_classifier.pt"
    torch.save(trainer.state_dict(), str(model_path))
    print(f"Model saved to {model_path}")
    return trainer


def load_model(model_path="models/disease_classifier.pt"):
    """Load the trained disease classifier."""
    model = SimpleCNN()
    model.load_state_dict(torch.load(model_path, map_location="cpu"))
    model.eval()
    return model


def predict(image_path: str, model_path: str = "models/disease_classifier.pt") -> dict:
    """Predict disease from an image file."""
    model = load_model(model_path)
    image = Image.open(image_path).convert('RGB')
    image = image.resize((64, 64))

    # Convert to tensor
    img_array = np.array(image).astype(np.float32) / 255.0
    img_tensor = torch.from_numpy(img_array).permute(2, 0, 1).unsqueeze(0)

    # Predict
    with torch.no_grad():
        output = model(img_tensor)
        probabilities = torch.softmax(output, dim=1)
        predicted_class = torch.argmax(probabilities, dim=1).item()
        confidence = probabilities[0][predicted_class].item()

    label_map = {
        0: 'healthy',
        1: 'red_paste',
        2: 'fungus',
        3: 'bacterial',
        4: 'parasitic'
    }

    return {
        "disease": label_map[predicted_class],
        "confidence": float(confidence),
        "class_id": predicted_class
    }