"""ML Training Pipeline for AquaGuard Disease Classifier.

This script generates synthetic disease data and trains a classifier
for the hackathon demo. It creates sample images with different
color patterns representing different disease categories.
"""
import torch
import torch.nn as nn
import numpy as np
from torch.utils.data import Dataset, DataLoader
from torch.optim import Adam
from pathlib import Path
import os
from PIL import Image
import random


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


class AquacultureDataset(Dataset):
    """Custom dataset for aquaculture disease images."""
    def __init__(self, image_dir, num_samples_per_class=50, transform=None):
        self.image_dir = Path(image_dir)
        self.transform = transform
        self.label_map = {
            0: 'healthy',
            1: 'red_paste',
            2: 'fungus',
            3: 'bacterial',
            4: 'parasitic'
        }
        self.samples = []

        # Create class directories and generate synthetic data
        for class_id in range(5):
            class_dir = self.image_dir / f"class_{class_id}"
            class_dir.mkdir(parents=True, exist_ok=True)

            for i in range(num_samples_per_class):
                # Generate synthetic image with class-specific patterns
                image = self._generate_class_image(class_id)
                filename = f"sample_{class_id}_{i}.jpg"
                image.save(class_dir / filename)
                self.samples.append(class_dir / filename)

    def _generate_class_image(self, class_id):
        """Generate a synthetic image with patterns specific to each disease class."""
        # Create base image
        img_array = np.random.randint(0, 256, (64, 64, 3), dtype=np.uint8)

        # Add class-specific patterns
        if class_id == 0:  # healthy
            # Greenish color for healthy ponds
            img_array[:] = [34, 139, 34]  # Forest green
        elif class_id == 1:  # red_paste
            # Reddish spots for red paste disease
            img_array[:] = [65, 105, 225]  # Royal blue base
            # Add red spots
            for _ in range(5):
                x, y = random.randint(10, 50), random.randint(10, 50)
                img_array[y-3:y+3, x-3:x+3] = [255, 0, 0]
        elif class_id == 2:  # fungus
            # White/gray patches for fungus
            img_array[:] = [240, 240, 240]  # Light gray
            for _ in range(3):
                x, y = random.randint(10, 50), random.randint(10, 50)
                img_array[y-5:y+5, x-5:x+5] = [200, 200, 200]
        elif class_id == 3:  # bacterial
            # Yellowish patches for bacterial infection
            img_array[:] = [255, 215, 0]  # Gold base
            for _ in range(3):
                x, y = random.randint(10, 50), random.randint(10, 50)
                img_array[y-3:y+3, x-3:x+3] = [139, 0, 0]
        elif class_id == 4:  # parasitic
            # Dark spots for parasitic infection
            img_array[:] = [50, 50, 50]  # Dark gray base
            for _ in range(5):
                x, y = random.randint(10, 50), random.randint(10, 50)
                img_array[y-4:y+4, x-4:x+4] = [100, 100, 100]

        img = Image.fromarray(img_array, 'RGB')
        return img

    def __len__(self):
        return len(self.samples)

    def __getitem__(self, idx):
        img_path = self.samples[idx]
        image = Image.open(img_path).convert('RGB')
        label = img_path.parent.name.split('_')[1]  # Extract class from path

        # Convert label to int
        label_map_rev = {v: k for k, v in self.label_map.items()}
        label_int = label_map_rev.get(label, 0)

        # Convert PIL image to tensor (0-1 range)
        img_array = np.array(image).astype(np.float32) / 255.0
        image = torch.from_numpy(img_array).permute(2, 0, 1)

        if self.transform:
            image = self.transform(image)

        return image, label_int


def train_model():
    """Train the disease classification model."""
    print("Starting model training...")

    # Create data directory
    data_dir = Path("data/samples")
    data_dir.mkdir(parents=True, exist_ok=True)

    # Create training dataset
    print("Generating synthetic training data...")
    train_dataset = AquacultureDataset(data_dir / "train", num_samples_per_class=30)

    # Split into train/val
    val_size = int(0.2 * len(train_dataset))
    train_size = len(train_dataset) - val_size
    train_subset, val_subset = torch.utils.data.random_split(
        train_dataset, [train_size, val_size]
    )

    # Create data loaders
    train_loader = DataLoader(train_subset, batch_size=8, shuffle=True)
    val_loader = DataLoader(val_subset, batch_size=8, shuffle=False)

    # Initialize model
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    print(f"Using device: {device}")

    model = SimpleCNN(num_classes=5).to(device)

    # Loss and optimizer
    criterion = nn.CrossEntropyLoss()
    optimizer = Adam(model.parameters(), lr=0.001)

    # Training loop
    epochs = 5
    print(f"Training for {epochs} epochs...")

    for epoch in range(epochs):
        model.train()
        train_loss = 0.0
        train_correct = 0
        train_total = 0

        for batch_idx, (data, target) in enumerate(train_loader):
            data, target = data.to(device), target.to(device)

            optimizer.zero_grad()
            output = model(data)
            loss = criterion(output, target)
            loss.backward()
            optimizer.step()

            train_loss += loss.item()
            _, predicted = torch.max(output.data, 1)
            train_total += target.size(0)
            train_correct += (predicted == target).sum().item()

        # Validation
        model.eval()
        val_loss = 0.0
        val_correct = 0
        val_total = 0

        with torch.no_grad():
            for data, target in val_loader:
                data, target = data.to(device), target.to(device)
                output = model(data)
                loss = criterion(output, target)
                val_loss += loss.item()
                _, predicted = torch.max(output.data, 1)
                val_total += target.size(0)
                val_correct += (predicted == target).sum().item()

        train_acc = 100.0 * train_correct / train_total
        val_acc = 100.0 * val_correct / val_total

        print(f"Epoch {epoch+1}/{epochs}: "
              f"Train Loss: {train_loss/len(train_loader):.4f}, "
              f"Train Acc: {train_acc:.1f}%, "
              f"Val Loss: {val_loss/len(val_loader):.4f}, "
              f"Val Acc: {val_acc:.1f}%")

    # Save model
    model_path = Path("models/disease_classifier.pt")
    model_path.parent.mkdir(parents=True, exist_ok=True)
    torch.save(model.state_dict(), str(model_path))
    print(f"\nModel saved to {model_path}")

    return model


def predict_disease(image_path: str, model_path: str = "models/disease_classifier.pt") -> dict:
    """Predict disease from a given image."""
    # Load model
    model = SimpleCNN(num_classes=5)
    model.load_state_dict(torch.load(model_path, map_location='cpu'))
    model.eval()

    # Load and preprocess image
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

    # Map to label
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


if __name__ == "__main__":
    # Train the model
    model = train_model()

    # Test prediction
    print("\nTesting prediction on first training image...")
    first_image = Path("data/samples/train/class_0/sample_0_0.jpg")
    if first_image.exists():
        result = predict_disease(str(first_image))
        print(f"Prediction: {result['disease']} with {result['confidence']*100:.1f}% confidence")